#!/usr/bin/env python3
"""
MC L10n 进程清理脚本
清理所有相关的开发服务器进程
"""

import subprocess
import sys
import time

def cleanup_processes():
    """清理所有相关进程"""
    print("🧹 开始清理 MC L10n 相关进程...")
    
    # 要清理的进程模式
    patterns = [
        "uvicorn.*simple_backend",
        "python.*simple_backend",
        "python.*start_server",
        "python.*enhanced_server",
        "vite.*5174",
        "npm.*run.*dev",
        "node.*vite"
    ]
    
    for pattern in patterns:
        try:
            print(f"🔍 查找进程: {pattern}")
            result = subprocess.run(['pkill', '-f', pattern], capture_output=True, check=False)
            if result.returncode == 0:
                print(f"✅ 已清理: {pattern}")
            else:
                print(f"ℹ️ 未找到: {pattern}")
        except FileNotFoundError:
            print("⚠️ pkill 命令不可用，跳过...")
    
    print("⏳ 等待进程终止...")
    time.sleep(3)
    
    # 强制清理端口占用
    ports_to_check = [18000, 5174]
    for port in ports_to_check:
        try:
            result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid.strip():
                        print(f"🔧 强制终止端口 {port} 上的进程 {pid}")
                        subprocess.run(['kill', '-9', pid.strip()], check=False)
        except FileNotFoundError:
            pass
    
    print("✅ 清理完成！")

def main():
    """主函数"""
    print("=" * 50)
    print("🧹 MC L10n 进程清理器")
    print("=" * 50)
    
    cleanup_processes()

if __name__ == "__main__":
    main()