#!/usr/bin/env python3
"""
MC L10n 简化命令行工具
保留核心功能，去除冗余特性
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


class Colors:
    """终端颜色"""
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


class MCL10nSimpleCLI:
    """MC L10n 简化CLI工具"""

    def __init__(self):
        self.scripts_dir = Path(__file__).parent
        self.backend_dir = self.scripts_dir.parent / "backend"
        self.frontend_dir = self.scripts_dir.parent / "frontend"
        self.db_path = self.backend_dir / "data" / "mc_l10n_v6.db"

    def start_backend(self):
        """启动后端服务"""
        print(f"{Colors.OKGREEN}🚀 启动后端服务 (端口 18000)...{Colors.ENDC}")
        try:
            subprocess.run(["poetry", "run", "python", "main.py"], cwd=self.backend_dir, check=True)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}⚠️ 后端服务已停止{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}❌ 启动失败: {e}{Colors.ENDC}")

    def start_frontend(self):
        """启动前端服务"""
        print(f"{Colors.OKGREEN}🚀 启动前端服务 (端口 18001)...{Colors.ENDC}")
        try:
            subprocess.run(["npm", "run", "dev"], cwd=self.frontend_dir, check=True)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}⚠️ 前端服务已停止{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}❌ 启动失败: {e}{Colors.ENDC}")

    def start_fullstack(self):
        """启动全栈服务"""
        print(f"{Colors.OKGREEN}🚀 启动全栈服务...{Colors.ENDC}")
        print("   后端: http://localhost:18000")
        print("   前端: http://localhost:18001")
        print("   API文档: http://localhost:18000/docs")
        print(f"\n{Colors.WARNING}提示: 按 Ctrl+C 停止所有服务{Colors.ENDC}")

        import threading
        import time

        def run_backend():
            subprocess.run(["poetry", "run", "python", "main.py"], cwd=self.backend_dir)

        def run_frontend():
            time.sleep(2)  # 等待后端启动
            subprocess.run(["npm", "run", "dev"], cwd=self.frontend_dir)

        try:
            backend_thread = threading.Thread(target=run_backend)
            frontend_thread = threading.Thread(target=run_frontend)

            backend_thread.start()
            frontend_thread.start()

            backend_thread.join()
            frontend_thread.join()
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}⚠️ 正在停止所有服务...{Colors.ENDC}")

    def kill_services(self):
        """停止所有服务"""
        print(f"{Colors.WARNING}🔄 正在清理进程...{Colors.ENDC}")
        
        # 杀死后端进程
        try:
            subprocess.run(["pkill", "-f", "apps/mc_l10n/backend/main.py"], capture_output=True)
            print(f"  {Colors.OKGREEN}✓{Colors.ENDC} 后端进程已停止")
        except:
            pass

        # 杀死占用端口的进程
        for port in ["18000", "18001"]:
            try:
                result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
                if result.stdout.strip():
                    pids = result.stdout.strip().split("\n")
                    for pid in pids:
                        try:
                            subprocess.run(["kill", "-9", pid], check=True)
                            print(f"  {Colors.OKGREEN}✓{Colors.ENDC} 端口 {port} 进程已停止")
                        except:
                            pass
            except:
                pass

        time.sleep(1)
        print(f"{Colors.OKGREEN}✅ 所有服务已停止{Colors.ENDC}")

    def db_status(self):
        """显示数据库状态"""
        if not self.db_path.exists():
            print(f"{Colors.FAIL}❌ 数据库不存在: {self.db_path}{Colors.ENDC}")
            return

        try:
            import sqlite3
            
            print(f"{Colors.BOLD}📊 数据库状态:{Colors.ENDC}")
            print(f"   📂 路径: {self.db_path}")
            
            # 获取文件大小
            size_mb = self.db_path.stat().st_size / (1024 * 1024)
            print(f"   📏 大小: {size_mb:.1f} MB")
            
            # 连接数据库查看表信息
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 获取所有表名
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                
                print(f"   📋 表数量: {len(tables)} 个")
                
                # 显示核心表
                core_tables = [t for t in tables if t.startswith('core_')]
                if core_tables:
                    print(f"   🎯 核心表: {', '.join(core_tables)}")
                    
                    # 显示核心表的记录数量
                    for table in core_tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            count = cursor.fetchone()[0]
                            print(f"      - {table}: {count:,} 条记录")
                        except:
                            pass

        except Exception as e:
            print(f"{Colors.FAIL}❌ 数据库查询失败: {e}{Colors.ENDC}")

    def start_db_viewer(self):
        """启动数据库查看器"""
        viewer_script = self.scripts_dir / "start_db_viewer.py"
        if viewer_script.exists():
            print(f"{Colors.OKGREEN}🚀 启动数据库查看器...{Colors.ENDC}")
            try:
                subprocess.run([sys.executable, str(viewer_script)], check=True)
            except KeyboardInterrupt:
                print(f"\n{Colors.WARNING}⚠️ 数据库查看器已停止{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}❌ 数据库查看器脚本不存在{Colors.ENDC}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MC L10n 简化管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 服务管理
    service_parser = subparsers.add_parser("start", help="启动服务")
    service_parser.add_argument("service", choices=["backend", "frontend", "fullstack"], 
                              help="要启动的服务")

    # 停止服务
    subparsers.add_parser("stop", help="停止所有服务")

    # 数据库状态
    subparsers.add_parser("db", help="显示数据库状态")

    # 数据库查看器
    subparsers.add_parser("viewer", help="启动数据库查看器")

    args = parser.parse_args()
    cli = MCL10nSimpleCLI()

    if not args.command:
        parser.print_help()
        return

    if args.command == "start":
        if args.service == "backend":
            cli.start_backend()
        elif args.service == "frontend":
            cli.start_frontend()
        elif args.service == "fullstack":
            cli.start_fullstack()
    elif args.command == "stop":
        cli.kill_services()
    elif args.command == "db":
        cli.db_status()
    elif args.command == "viewer":
        cli.start_db_viewer()


if __name__ == "__main__":
    main()