"""
进程管理器模块
用于管理应用程序的单实例运行，自动清理旧进程
"""

import atexit
import logging
import os
import signal
import sys
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


class ProcessManager:
    """进程管理器，确保只有一个实例在运行"""

    def __init__(self, pid_file: str = "mc_l10n.pid"):
        self.pid_file = Path(pid_file)
        self.current_pid = os.getpid()

    def check_and_kill_old_process(self) -> bool:
        """检查并终止旧进程"""
        if self.pid_file.exists():
            try:
                old_pid = int(self.pid_file.read_text().strip())

                # 检查进程是否存在
                if old_pid != self.current_pid and psutil.pid_exists(old_pid):
                    try:
                        old_process = psutil.Process(old_pid)
                        # 检查是否是同一个程序
                        if "python" in old_process.name().lower():
                            cmdline = " ".join(old_process.cmdline())
                            if "main.py" in cmdline:
                                logger.info(f"发现旧进程 PID={old_pid}，正在终止...")
                                old_process.terminate()

                                # 等待进程结束
                                try:
                                    old_process.wait(timeout=5)
                                except psutil.TimeoutExpired:
                                    logger.warning(
                                        f"进程 {old_pid} 未响应终止信号，强制结束"
                                    )
                                    old_process.kill()

                                logger.info(f"已终止旧进程 PID={old_pid}")
                                return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        logger.debug(f"无法访问进程 {old_pid}: {e}")
            except (OSError, ValueError) as e:
                logger.debug(f"读取PID文件失败: {e}")

        return False

    def write_pid(self):
        """写入当前进程PID"""
        try:
            self.pid_file.write_text(str(self.current_pid))
            logger.info(f"已记录当前进程 PID={self.current_pid}")

            # 注册退出时清理
            atexit.register(self.cleanup)
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        except OSError as e:
            logger.error(f"无法写入PID文件: {e}")

    def cleanup(self):
        """清理PID文件"""
        try:
            if self.pid_file.exists():
                stored_pid = int(self.pid_file.read_text().strip())
                if stored_pid == self.current_pid:
                    self.pid_file.unlink()
                    logger.info("已清理PID文件")
        except Exception as e:
            logger.debug(f"清理PID文件失败: {e}")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，正在退出...")
        self.cleanup()
        sys.exit(0)

    def kill_all_instances(self):
        """终止所有相同的Python进程实例"""
        killed_count = 0
        current_process = psutil.Process(self.current_pid)
        " ".join(current_process.cmdline())

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["pid"] == self.current_pid:
                    continue

                if proc.info["name"] and "python" in proc.info["name"].lower():
                    cmdline = " ".join(proc.info["cmdline"] or [])
                    if "main.py" in cmdline and "mc_l10n" in cmdline:
                        logger.info(f"终止进程 PID={proc.info['pid']}")
                        proc.terminate()
                        killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed_count > 0:
            logger.info(f"共终止 {killed_count} 个重复进程")
        return killed_count

    def start(self, kill_all: bool = False):
        """启动进程管理"""
        if kill_all:
            # 终止所有实例
            self.kill_all_instances()
        else:
            # 只终止PID文件中记录的旧进程
            self.check_and_kill_old_process()

        # 记录当前进程
        self.write_pid()


def setup_process_manager(kill_all: bool = False) -> ProcessManager:
    """设置进程管理器"""
    manager = ProcessManager()
    manager.start(kill_all=kill_all)
    return manager
