#!/usr/bin/env python3
"""
智能后端启动脚本
自动检测和清理卡死的进程，然后在默认端口启动后端
"""

import os
import signal
import subprocess
import time
import sys
from pathlib import Path

# 默认配置
DEFAULT_PORT = 18000
DEFAULT_HOST = "127.0.0.1"

def find_processes_on_port(port):
    """查找占用指定端口的进程"""
    try:
        # 使用 lsof 或 netstat 查找进程
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'], 
            capture_output=True, 
            text=True, 
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid.strip()]
            return pids
        
        # 如果 lsof 不可用，尝试 ss (更常见在WSL中)
        result = subprocess.run(
            ['ss', '-tlnp'], 
            capture_output=True, 
            text=True, 
            check=False
        )
        pids = []
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'pid=' in line:
                    try:
                        pid_part = line.split('pid=')[1].split(',')[0]
                        pids.append(int(pid_part))
                    except (IndexError, ValueError):
                        continue
        return pids
    except FileNotFoundError:
        return []

def kill_process_tree(pid):
    """杀死进程树"""
    try:
        # 首先尝试温和终止
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        
        # 检查进程是否还活着
        try:
            os.kill(pid, 0)  # 不发送信号，只检查进程是否存在
            # 如果还活着，强制杀死
            print(f"🔧 强制杀死进程 {pid}")
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            print(f"✅ 进程 {pid} 已终止")
    except ProcessLookupError:
        print(f"⚠️ 进程 {pid} 不存在")
    except PermissionError:
        print(f"❌ 没有权限杀死进程 {pid}")
        return False
    return True

def cleanup_stuck_processes():
    """清理卡死的后端进程"""
    print("🔍 检查端口占用情况...")
    
    pids = find_processes_on_port(DEFAULT_PORT)
    if pids:
        print(f"🚨 发现进程占用端口 {DEFAULT_PORT}: {pids}")
        for pid in pids:
            print(f"🛑 终止进程 {pid}")
            kill_process_tree(pid)
        
        # 等待进程清理完成
        time.sleep(3)
        
        # 再次检查
        remaining_pids = find_processes_on_port(DEFAULT_PORT)
        if remaining_pids:
            print(f"⚠️ 仍有进程占用端口: {remaining_pids}")
            return False
        else:
            print("✅ 端口清理完成")
    else:
        print(f"✅ 端口 {DEFAULT_PORT} 可用")
    
    return True

def start_backend():
    """启动后端服务"""
    print(f"🚀 启动 MC L10n 后端服务器...")
    print(f"📍 服务器: http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    print(f"📚 API 文档: http://{DEFAULT_HOST}:{DEFAULT_PORT}/docs")
    print("🔧 按 Ctrl+C 停止服务器")
    
    # 启动 uvicorn 服务器
    try:
        subprocess.run([
            'poetry', 'run', 'uvicorn', 
            'simple_backend:app',
            '--host', DEFAULT_HOST,
            '--port', str(DEFAULT_PORT),
            '--log-level', 'info',
            '--reload'
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("🎯 MC L10n 智能后端启动器")
    print("=" * 50)
    
    # 确保在正确的目录
    backend_dir = Path(__file__).parent.parent / "backend"  # 从 scripts 目录到 backend 目录
    os.chdir(backend_dir)
    print(f"📂 工作目录: {backend_dir}")
    
    # 清理卡死进程
    if not cleanup_stuck_processes():
        print("❌ 无法清理端口，启动失败")
        sys.exit(1)
    
    # 启动后端
    if not start_backend():
        print("❌ 后端启动失败")
        sys.exit(1)

if __name__ == "__main__":
    main()