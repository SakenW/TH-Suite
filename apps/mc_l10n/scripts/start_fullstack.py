#!/usr/bin/env python3
"""
MC L10n 全栈启动脚本
同时启动前端和后端
"""

import os
import subprocess
import sys
import time
from pathlib import Path
import threading

def run_script(script_path, name):
    """在新进程中运行脚本"""
    try:
        print(f"🚀 启动 {name}...")
        result = subprocess.run([sys.executable, str(script_path)], check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ {name} 启动失败: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n🛑 {name} 被用户中断")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🎯 MC L10n 全栈启动器")
    print("=" * 60)
    
    scripts_dir = Path(__file__).parent
    backend_script = scripts_dir / "start_backend.py"
    frontend_script = scripts_dir / "start_frontend.py"
    
    # 验证脚本存在
    if not backend_script.exists():
        print(f"❌ 后端脚本不存在: {backend_script}")
        sys.exit(1)
    
    if not frontend_script.exists():
        print(f"❌ 前端脚本不存在: {frontend_script}")
        sys.exit(1)
    
    print("📋 启动计划:")
    print("  1. 启动后端服务器 (端口 18000)")
    print("  2. 启动前端开发服务器 (端口 5173)")
    print("  3. 两个服务将并行运行")
    print("\n🔧 按 Ctrl+C 停止所有服务")
    
    try:
        # 启动后端
        print("\n" + "=" * 30)
        print("📦 第1步: 启动后端服务")
        print("=" * 30)
        
        backend_process = subprocess.Popen([sys.executable, str(backend_script)])
        
        # 等待后端启动
        print("⏳ 等待后端启动...")
        time.sleep(5)
        
        # 启动前端
        print("\n" + "=" * 30)
        print("🎨 第2步: 启动前端服务")
        print("=" * 30)
        
        frontend_process = subprocess.Popen([sys.executable, str(frontend_script)])
        
        print("\n✅ 全栈服务启动完成!")
        print("🌐 前端: http://localhost:5173")
        print("🔧 后端: http://localhost:18000")
        print("📚 API文档: http://localhost:18000/docs")
        print("\n按 Ctrl+C 停止所有服务...")
        
        # 等待进程结束
        try:
            backend_process.wait()
            frontend_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 正在停止服务...")
            
            # 终止进程
            backend_process.terminate()
            frontend_process.terminate()
            
            # 等待进程结束
            try:
                backend_process.wait(timeout=10)
                frontend_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("🔨 强制停止进程...")
                backend_process.kill()
                frontend_process.kill()
            
            print("✅ 所有服务已停止")
    
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()