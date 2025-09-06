#!/usr/bin/env python3
"""
MC L10n 统一入口管理器
提供所有MC L10n工具的统一访问入口
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
from typing import List, Tuple
import importlib.util

# 添加项目路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPT_DIR.parent))


class MCL10nManager:
    """MC L10n 管理器"""
    
    def __init__(self):
        self.script_dir = SCRIPT_DIR
        self.backend_dir = SCRIPT_DIR.parent / "backend"
        self.frontend_dir = SCRIPT_DIR.parent / "frontend"
        
        # 工具映射
        self.tools = {
            'backend': {
                'description': '启动后端服务',
                'module': 'start_backend',
                'function': 'main'
            },
            'frontend': {
                'description': '启动前端服务',
                'module': 'start_frontend',
                'function': 'main'
            },
            'fullstack': {
                'description': '启动全栈服务（前端+后端）',
                'module': 'start_fullstack',
                'function': 'main'
            },
            'db-reader': {
                'description': '数据库读取工具',
                'module': 'db_reader',
                'function': 'main'
            },
            'db-audit': {
                'description': '数据库审计工具',
                'module': 'db_audit',
                'function': 'main'
            },
            'scan': {
                'description': '扫描管理工具',
                'module': 'scan_manager',
                'function': 'main'
            },
            'cleanup': {
                'description': '清理工具',
                'module': 'cleanup',
                'function': 'main'
            },
            'check-mods': {
                'description': '检查模组表',
                'module': 'check_mods_table',
                'function': 'main'
            },
            'db-transfer': {
                'description': '数据库传输工具（导入/导出/备份）',
                'module': 'db_transfer',
                'function': 'main'
            }
        }
        
        # 快捷命令
        self.shortcuts = {
            'start': 'fullstack',
            'db': 'db-reader',
            'audit': 'db-audit',
            'clean': 'cleanup'
        }
    
    def run_tool(self, tool_name: str, args: List[str] = None):
        """运行指定工具"""
        # 处理快捷命令
        if tool_name in self.shortcuts:
            tool_name = self.shortcuts[tool_name]
        
        if tool_name not in self.tools:
            print(f"❌ 未知工具: {tool_name}")
            self.show_available_tools()
            return False
        
        tool_info = self.tools[tool_name]
        
        try:
            # 动态导入模块
            module_path = self.script_dir / f"{tool_info['module']}.py"
            
            if not module_path.exists():
                print(f"❌ 工具文件不存在: {module_path}")
                return False
            
            # 加载模块
            spec = importlib.util.spec_from_file_location(tool_info['module'], module_path)
            module = importlib.util.module_from_spec(spec)
            
            # 保存原始参数
            original_argv = sys.argv
            
            try:
                # 设置新参数
                sys.argv = [str(module_path)] + (args or [])
                
                # 执行模块
                spec.loader.exec_module(module)
                
                # 调用主函数
                if hasattr(module, tool_info['function']):
                    getattr(module, tool_info['function'])()
                else:
                    print(f"❌ 模块 {tool_info['module']} 没有 {tool_info['function']} 函数")
                    return False
                    
            finally:
                # 恢复原始参数
                sys.argv = original_argv
            
            return True
            
        except Exception as e:
            print(f"❌ 运行工具失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def show_available_tools(self):
        """显示可用工具列表"""
        print("\n📦 可用工具:")
        print("-" * 60)
        
        # 主要工具
        print("\n🚀 启动服务:")
        for cmd in ['backend', 'frontend', 'fullstack']:
            if cmd in self.tools:
                print(f"  {cmd:15} - {self.tools[cmd]['description']}")
        
        # 数据库工具
        print("\n💾 数据库工具:")
        for cmd in ['db-reader', 'db-audit', 'check-mods']:
            if cmd in self.tools:
                print(f"  {cmd:15} - {self.tools[cmd]['description']}")
        
        # 管理工具
        print("\n🛠️ 管理工具:")
        for cmd in ['scan', 'cleanup']:
            if cmd in self.tools:
                print(f"  {cmd:15} - {self.tools[cmd]['description']}")
        
        # 快捷命令
        print("\n⚡ 快捷命令:")
        for short, full in self.shortcuts.items():
            print(f"  {short:15} -> {full}")
        
        print("\n💡 使用方法:")
        print("  mc_l10n <工具名> [参数...]")
        print("  mc_l10n <工具名> --help  # 查看工具帮助")
        print("\n示例:")
        print("  mc_l10n start           # 启动全栈服务")
        print("  mc_l10n db stats        # 查看数据库统计")
        print("  mc_l10n scan start /path/to/mods --monitor")
    
    def check_environment(self):
        """检查环境配置"""
        print("🔍 检查环境配置...")
        
        checks = []
        
        # 检查Python版本
        py_version = sys.version_info
        if py_version >= (3, 8):
            checks.append(("Python版本", f"{py_version.major}.{py_version.minor}.{py_version.micro}", "✅"))
        else:
            checks.append(("Python版本", f"{py_version.major}.{py_version.minor}.{py_version.micro}", "❌"))
        
        # 检查目录结构
        dirs = [
            ("后端目录", self.backend_dir),
            ("前端目录", self.frontend_dir),
            ("脚本目录", self.script_dir)
        ]
        
        for name, path in dirs:
            if path.exists():
                checks.append((name, str(path), "✅"))
            else:
                checks.append((name, str(path), "❌"))
        
        # 检查数据库
        db_path = self.backend_dir / "mc_l10n.db"
        if db_path.exists():
            size = db_path.stat().st_size / 1024  # KB
            checks.append(("数据库", f"{size:.1f} KB", "✅"))
        else:
            checks.append(("数据库", "不存在", "⚠️"))
        
        # 检查依赖
        try:
            import poetry
            checks.append(("Poetry", "已安装", "✅"))
        except ImportError:
            checks.append(("Poetry", "未安装", "⚠️"))
        
        # 打印结果
        print("\n环境检查结果:")
        print("-" * 60)
        for name, value, status in checks:
            print(f"{status} {name:15} : {value}")
        
        # 检查服务状态
        print("\n服务状态:")
        print("-" * 60)
        
        # 检查后端服务
        try:
            import requests
            response = requests.get("http://localhost:18000/health", timeout=1)
            if response.status_code == 200:
                print("✅ 后端服务     : 运行中 (端口 18000)")
            else:
                print("⚠️ 后端服务     : 响应异常")
        except:
            print("❌ 后端服务     : 未运行")
        
        # 检查前端服务
        try:
            import requests
            response = requests.get("http://localhost:5173", timeout=1)
            print("✅ 前端服务     : 运行中 (端口 5173)")
        except:
            print("❌ 前端服务     : 未运行")
    
    def init_project(self):
        """初始化项目"""
        print("🚀 初始化MC L10n项目...")
        
        steps = [
            ("创建目录结构", self._create_directories),
            ("安装依赖", self._install_dependencies),
            ("初始化数据库", self._init_database),
            ("创建配置文件", self._create_config)
        ]
        
        for step_name, step_func in steps:
            print(f"\n⏳ {step_name}...")
            try:
                if step_func():
                    print(f"✅ {step_name} 完成")
                else:
                    print(f"⚠️ {step_name} 跳过")
            except Exception as e:
                print(f"❌ {step_name} 失败: {e}")
                return False
        
        print("\n✨ 初始化完成!")
        return True
    
    def _create_directories(self):
        """创建必要的目录"""
        dirs = [
            self.backend_dir / "exports",
            self.backend_dir / "logs",
            self.frontend_dir / "dist"
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        return True
    
    def _install_dependencies(self):
        """安装依赖"""
        # 检查是否已安装
        if (self.backend_dir / ".venv").exists():
            print("  依赖已安装")
            return False
        
        # 安装后端依赖
        os.chdir(self.backend_dir)
        subprocess.run(["poetry", "install"], check=True)
        
        # 安装前端依赖
        os.chdir(self.frontend_dir)
        subprocess.run(["npm", "install"], check=True)
        
        return True
    
    def _init_database(self):
        """初始化数据库"""
        db_path = self.backend_dir / "mc_l10n.db"
        if db_path.exists():
            print("  数据库已存在")
            return False
        
        # 运行数据库初始化
        os.chdir(self.backend_dir)
        subprocess.run([sys.executable, "init_db.py"], check=True)
        
        return True
    
    def _create_config(self):
        """创建配置文件"""
        config_path = self.backend_dir / ".env"
        if config_path.exists():
            print("  配置文件已存在")
            return False
        
        config_content = """# MC L10n 配置文件
DEBUG=false
ENVIRONMENT=production
HOST=127.0.0.1
PORT=18000
DATABASE_PATH=mc_l10n.db
"""
        
        config_path.write_text(config_content)
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='MC L10n 统一管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  mc_l10n start              # 启动全栈服务
  mc_l10n backend            # 仅启动后端
  mc_l10n db stats           # 查看数据库统计
  mc_l10n scan start /path   # 启动扫描
  mc_l10n check              # 检查环境
        """
    )
    
    parser.add_argument('command', nargs='?', help='要执行的命令')
    parser.add_argument('args', nargs='*', help='命令参数')
    parser.add_argument('--list', action='store_true', help='列出所有可用工具')
    parser.add_argument('--check', action='store_true', help='检查环境配置')
    parser.add_argument('--init', action='store_true', help='初始化项目')
    
    args = parser.parse_args()
    
    manager = MCL10nManager()
    
    # 处理特殊命令
    if args.list or (not args.command and not args.check and not args.init):
        manager.show_available_tools()
        return
    
    if args.check:
        manager.check_environment()
        return
    
    if args.init:
        manager.init_project()
        return
    
    # 处理工具命令
    if args.command:
        if args.command == 'check':
            manager.check_environment()
        elif args.command == 'help':
            manager.show_available_tools()
        else:
            success = manager.run_tool(args.command, args.args)
            if not success:
                sys.exit(1)


if __name__ == '__main__':
    main()