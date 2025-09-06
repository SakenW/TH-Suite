#!/usr/bin/env python3
"""
MC L10n 服务管理器
统一管理前端、后端和全栈服务
"""

import sys
import subprocess
from pathlib import Path

def show_help():
    """显示帮助信息"""
    print("=" * 60)
    print("🎯 MC L10n 服务管理器")
    print("=" * 60)
    print("\n📋 可用命令:")
    print("  backend     - 启动后端服务器 (端口 18000)")
    print("  frontend    - 启动前端服务器 (端口 5173)")
    print("  fullstack   - 启动全栈服务 (前端 + 后端)")
    print("  cleanup     - 清理所有相关进程")
    print("  help        - 显示此帮助信息")
    print("\n🚀 使用示例:")
    print("  python manage.py backend")
    print("  python manage.py fullstack")
    print("  python manage.py cleanup")
    print("\n📍 服务地址:")
    print("  前端: http://localhost:5173")
    print("  后端: http://localhost:18000")
    print("  API文档: http://localhost:18000/docs")

def run_script(script_name):
    """运行指定脚本"""
    scripts_dir = Path(__file__).parent
    script_path = scripts_dir / f"{script_name}.py"
    
    if not script_path.exists():
        print(f"❌ 脚本不存在: {script_path}")
        return False
    
    try:
        subprocess.run([sys.executable, str(script_path)], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 脚本执行失败: {e}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 操作被用户中断")
        return True

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    command_map = {
        'backend': 'start_backend',
        'frontend': 'start_frontend', 
        'fullstack': 'start_fullstack',
        'cleanup': 'cleanup',
        'help': None,
        '--help': None,
        '-h': None
    }
    
    if command in ['help', '--help', '-h']:
        show_help()
        return
    
    if command not in command_map:
        print(f"❌ 未知命令: {command}")
        print("💡 运行 'python manage.py help' 查看可用命令")
        sys.exit(1)
    
    script_name = command_map[command]
    if not run_script(script_name):
        sys.exit(1)

if __name__ == "__main__":
    main()