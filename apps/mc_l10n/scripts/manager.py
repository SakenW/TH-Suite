#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MC L10n 统一脚本管理器
跨平台的应用启动和管理工具
"""

import os
import sys
import subprocess
import platform
import signal
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import psutil  # 需要安装：pip install psutil

class LogManager:
    """日志管理器"""
    
    @staticmethod
    def log(level: str, message: str, service: str = "mc-l10n-manager", **extra):
        """输出结构化日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            'event': message,
            'service': service,
            'level': level.lower(),
            'timestamp': timestamp,
            **extra
        }
        
        # 颜色代码
        colors = {
            'INFO': '\033[92m',
            'WARN': '\033[93m',
            'ERROR': '\033[91m',
            'DEBUG': '\033[94m',
            'RESET': '\033[0m'
        }
        
        # 根据平台选择是否使用颜色
        use_color = platform.system() != 'Windows' or os.environ.get('TERM')
        
        if use_color:
            prefix = f"{colors.get(level.upper(), '')}{level.upper():8}{colors['RESET']} {timestamp}"
        else:
            prefix = f"{level.upper():8} {timestamp}"
        
        print(f"{prefix} {json.dumps(log_entry, ensure_ascii=False)}")
    
    @staticmethod
    def info(message: str, **extra):
        LogManager.log('INFO', message, **extra)
    
    @staticmethod
    def warn(message: str, **extra):
        LogManager.log('WARN', message, **extra)
    
    @staticmethod
    def error(message: str, **extra):
        LogManager.log('ERROR', message, **extra)
    
    @staticmethod
    def debug(message: str, **extra):
        LogManager.log('DEBUG', message, **extra)

class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent.parent.parent
        self.backend_dir = self.script_dir.parent / "backend"
        self.frontend_dir = self.script_dir.parent / "frontend"
        self.processes = {}
        self.log = LogManager()
        
        # 配置
        self.config = {
            'backend': {
                'port': 18000,
                'host': '0.0.0.0',
                'workers': 1,
                'reload': True
            },
            'frontend': {
                'port': 5173,
                'host': 'localhost',
                'mode': 'development'
            },
            'database': {
                'port': 18081,
                'host': '127.0.0.1'
            }
        }
    
    def check_dependencies(self) -> Dict[str, bool]:
        """检查依赖"""
        deps = {
            'python': self._check_command(['python', '--version']),
            'poetry': self._check_command(['poetry', '--version']),
            'node': self._check_command(['node', '--version']),
            'npm': self._check_command(['npm', '--version']),
        }
        
        # 可选依赖
        deps['cargo'] = self._check_command(['cargo', '--version'])  # Tauri需要
        
        return deps
    
    def _check_command(self, cmd: List[str]) -> bool:
        """检查命令是否可用"""
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def start_backend(self, detached: bool = True) -> Optional[subprocess.Popen]:
        """启动后端服务"""
        self.log.info("Starting backend server...", service="backend")
        
        # 检查Poetry
        if not self._check_command(['poetry', '--version']):
            self.log.error("Poetry not found! Please install Poetry first.", service="backend")
            return None
        
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.project_root / "packages" / "core" / "src")
        env['ENVIRONMENT'] = 'development'
        env['DEBUG'] = 'true'
        env['LOG_LEVEL'] = 'INFO'
        
        # 构建命令
        cmd = ['poetry', 'run', 'python', 'main.py']
        
        try:
            if detached:
                # 后台运行
                process = subprocess.Popen(
                    cmd,
                    cwd=self.backend_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                self.processes['backend'] = process
                self.log.info(f"Backend server started (PID: {process.pid})", 
                            service="backend",
                            pid=process.pid,
                            url=f"http://localhost:{self.config['backend']['port']}")
                return process
            else:
                # 前台运行
                subprocess.run(cmd, cwd=self.backend_dir, env=env)
                return None
        except Exception as e:
            self.log.error(f"Failed to start backend: {e}", service="backend")
            return None
    
    def start_frontend(self, mode: str = "tauri", detached: bool = True) -> Optional[subprocess.Popen]:
        """启动前端服务"""
        self.log.info(f"Starting frontend ({mode} mode)...", service="frontend", mode=mode)
        
        # 检查Node.js
        if not self._check_command(['node', '--version']):
            self.log.error("Node.js not found! Please install Node.js first.", service="frontend")
            return None
        
        # 检查依赖是否安装
        if not (self.frontend_dir / "node_modules").exists():
            self.log.info("Installing frontend dependencies...", service="frontend")
            subprocess.run(['npm', 'install'], cwd=self.frontend_dir, check=True)
        
        # 根据模式选择命令
        if mode == "tauri":
            # 检查Rust/Cargo
            if not self._check_command(['cargo', '--version']):
                self.log.warn("Cargo not found! Falling back to web mode.", service="frontend")
                mode = "web"
            else:
                cmd = ['npm', 'run', 'tauri:dev']
        
        if mode == "web":
            cmd = ['npm', 'run', 'dev']
        
        try:
            if detached:
                process = subprocess.Popen(
                    cmd,
                    cwd=self.frontend_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                self.processes['frontend'] = process
                self.log.info(f"Frontend started (PID: {process.pid})", 
                            service="frontend",
                            pid=process.pid,
                            mode=mode,
                            url=f"http://localhost:{self.config['frontend']['port']}")
                return process
            else:
                subprocess.run(cmd, cwd=self.frontend_dir)
                return None
        except Exception as e:
            self.log.error(f"Failed to start frontend: {e}", service="frontend")
            return None
    
    def start_database_viewer(self, detached: bool = True) -> Optional[subprocess.Popen]:
        """启动数据库查看器"""
        self.log.info("Starting database viewer...", service="db-viewer")
        
        db_manager = self.project_root / "tools" / "database" / "viewer" / "mc_db_manager.py"
        
        if not db_manager.exists():
            self.log.error(f"Database manager not found at {db_manager}", service="db-viewer")
            return None
        
        cmd = ['poetry', 'run', 'python', str(db_manager), 
               '--port', str(self.config['database']['port'])]
        
        try:
            if detached:
                process = subprocess.Popen(
                    cmd,
                    cwd=self.project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                self.processes['db-viewer'] = process
                self.log.info(f"Database viewer started (PID: {process.pid})", 
                            service="db-viewer",
                            pid=process.pid,
                            url=f"http://{self.config['database']['host']}:{self.config['database']['port']}")
                return process
            else:
                subprocess.run(cmd, cwd=self.project_root)
                return None
        except Exception as e:
            self.log.error(f"Failed to start database viewer: {e}", service="db-viewer")
            return None
    
    def start_all(self, mode: str = "tauri"):
        """启动所有服务"""
        self.log.info("Starting all services...", mode=mode)
        
        # 启动后端
        backend = self.start_backend(detached=True)
        if not backend:
            self.log.error("Failed to start backend, aborting...")
            return
        
        # 等待后端启动
        self.log.info("Waiting for backend to be ready...")
        time.sleep(3)
        
        # 检查后端是否启动成功
        if not self._check_service_health('backend'):
            self.log.error("Backend failed to start properly")
            self.stop_all()
            return
        
        # 启动前端
        frontend = self.start_frontend(mode=mode, detached=False)
    
    def stop_all(self):
        """停止所有服务"""
        self.log.info("Stopping all services...")
        
        # 停止记录的进程
        for name, process in self.processes.items():
            if process and process.poll() is None:
                self.log.info(f"Stopping {name} (PID: {process.pid})...", service=name)
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.log.warn(f"Force killing {name}...", service=name)
                    process.kill()
        
        # 清理端口占用
        self._cleanup_ports()
        
        self.processes.clear()
        self.log.info("All services stopped")
    
    def _cleanup_ports(self):
        """清理端口占用"""
        ports = [
            self.config['backend']['port'],
            self.config['frontend']['port'],
            self.config['database']['port']
        ]
        
        for port in ports:
            self._kill_port_process(port)
    
    def _kill_port_process(self, port: int):
        """杀死占用端口的进程"""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    process = psutil.Process(conn.pid)
                    self.log.info(f"Killing process {conn.pid} on port {port}", 
                                pid=conn.pid, port=port)
                    process.terminate()
                    break
        except Exception as e:
            self.log.debug(f"Failed to kill process on port {port}: {e}")
    
    def _check_service_health(self, service: str) -> bool:
        """检查服务健康状态"""
        import urllib.request
        import urllib.error
        
        urls = {
            'backend': f"http://localhost:{self.config['backend']['port']}/health",
            'frontend': f"http://localhost:{self.config['frontend']['port']}/",
            'db-viewer': f"http://localhost:{self.config['database']['port']}/"
        }
        
        url = urls.get(service)
        if not url:
            return False
        
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError):
            return False
    
    def status(self):
        """显示服务状态"""
        self.log.info("Service Status:")
        
        services = ['backend', 'frontend', 'db-viewer']
        
        for service in services:
            process = self.processes.get(service)
            if process and process.poll() is None:
                status = "Running"
                pid = process.pid
                health = "Healthy" if self._check_service_health(service) else "Unhealthy"
            else:
                status = "Stopped"
                pid = None
                health = "N/A"
            
            self.log.info(f"  {service:12} : {status:10} (PID: {pid or 'N/A':6}, Health: {health})",
                        service=service, status=status, pid=pid, health=health)

def signal_handler(signum, frame):
    """信号处理器"""
    print("\nReceived interrupt signal. Shutting down...")
    manager.stop_all()
    sys.exit(0)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MC L10n Service Manager")
    parser.add_argument('command', choices=['start', 'stop', 'restart', 'status', 
                                           'backend', 'frontend', 'db-viewer', 'check'],
                       help='Command to execute')
    parser.add_argument('--mode', choices=['tauri', 'web'], default='tauri',
                       help='Frontend mode (default: tauri)')
    parser.add_argument('--detached', '-d', action='store_true',
                       help='Run in detached mode')
    
    args = parser.parse_args()
    
    global manager
    manager = ServiceManager()
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 执行命令
    if args.command == 'check':
        deps = manager.check_dependencies()
        manager.log.info("Dependency Check:")
        for name, available in deps.items():
            status = "✓" if available else "✗"
            manager.log.info(f"  {name:10} : {status}")
    
    elif args.command == 'start':
        manager.start_all(mode=args.mode)
    
    elif args.command == 'stop':
        manager.stop_all()
    
    elif args.command == 'restart':
        manager.stop_all()
        time.sleep(2)
        manager.start_all(mode=args.mode)
    
    elif args.command == 'status':
        manager.status()
    
    elif args.command == 'backend':
        manager.start_backend(detached=args.detached)
        if not args.detached:
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                manager.stop_all()
    
    elif args.command == 'frontend':
        manager.start_frontend(mode=args.mode, detached=args.detached)
        if not args.detached:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                manager.stop_all()
    
    elif args.command == 'db-viewer':
        manager.start_database_viewer(detached=args.detached)
        if not args.detached:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                manager.stop_all()

if __name__ == "__main__":
    main()