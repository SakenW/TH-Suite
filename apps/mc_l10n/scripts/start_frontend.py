#!/usr/bin/env python3
"""
MC L10n 前端启动脚本
"""

import os
import signal
import subprocess
import time
import sys
from pathlib import Path

DEFAULT_PORT = 5173

def cleanup_frontend_processes():
    """清理前端进程"""
    print("🔍 检查前端进程...")
    
    try:
        result = subprocess.run(['pkill', '-f', 'vite'], capture_output=True, check=False)
        if result.returncode == 0:
            print("✅ 清理完成")
            time.sleep(2)
    except FileNotFoundError:
        pass

def start_frontend():
    """启动前端开发服务器"""
    print("🚀 启动 MC L10n 前端服务器...")
    print(f"📍 Web 地址: http://localhost:{DEFAULT_PORT}")
    print("🔧 按 Ctrl+C 停止服务器")
    
    try:
        subprocess.run(['npm', 'run', 'dev'], check=True)
    except KeyboardInterrupt:
        print("\n🛑 前端服务器已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("🎯 MC L10n 前端启动器")
    print("=" * 50)
    
    # 确保在前端目录
    frontend_dir = Path(__file__).parent.parent / "frontend"
    if not frontend_dir.exists():
        print(f"❌ 前端目录不存在: {frontend_dir}")
        sys.exit(1)
    
    os.chdir(frontend_dir)
    print(f"📂 工作目录: {frontend_dir}")
    
    # 清理进程
    cleanup_frontend_processes()
    
    # 启动前端
    if not start_frontend():
        print("❌ 前端启动失败")
        sys.exit(1)

if __name__ == "__main__":
    main()