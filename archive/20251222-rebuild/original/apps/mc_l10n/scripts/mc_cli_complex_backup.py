#!/usr/bin/env python3
"""
MC L10n 统一命令行工具
整合所有管理功能的单一入口
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

# 添加backend目录到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))


class Colors:
    """终端颜色"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class MCL10nCLI:
    """MC L10n 统一CLI工具"""

    def __init__(self):
        self.scripts_dir = Path(__file__).parent
        self.backend_dir = self.scripts_dir.parent / "backend"
        self.frontend_dir = self.scripts_dir.parent / "frontend"
        self.db_path = self.backend_dir / "data" / "mc_l10n_v6.db"
        self.api_url = "http://localhost:18000"

    # ========== 服务管理 ==========

    def server_start(self, args):
        """启动服务器"""
        # 如果指定了 --kill-old 参数，先杀死旧进程
        if hasattr(args, "kill_old") and args.kill_old:
            self._kill_old_processes()

        if args.service == "backend":
            self._start_backend()
        elif args.service == "frontend":
            self._start_frontend()
        elif args.service == "fullstack":
            self._start_fullstack()
        else:
            print(f"{Colors.FAIL}❌ 未知服务: {args.service}{Colors.ENDC}")

    def server_stop(self, args):
        """停止服务器"""
        self._kill_old_processes()
        print(f"{Colors.OKGREEN}✅ 所有服务已停止{Colors.ENDC}")

    def _kill_old_processes(self):
        """杀死旧的服务进程"""
        print(f"{Colors.WARNING}🔄 正在清理旧进程...{Colors.ENDC}")

        # 杀死后端进程（Python运行main.py）
        try:
            # 查找运行 main.py 的Python进程
            result = subprocess.run(
                ["pkill", "-f", "apps/mc_l10n/backend/main.py"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"  {Colors.OKGREEN}✓{Colors.ENDC} 后端进程已停止")
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            pass

        # 杀死前端进程（占用18001端口的node进程）
        try:
            # 使用lsof查找占用端口的进程
            result = subprocess.run(
                ["lsof", "-ti", ":18001"], capture_output=True, text=True
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        subprocess.run(["kill", "-9", pid], check=True)
                        print(
                            f"  {Colors.OKGREEN}✓{Colors.ENDC} 前端进程 (PID: {pid}) 已停止"
                        )
                    except (subprocess.SubprocessError, FileNotFoundError, OSError, Exception):
                        pass
        except (subprocess.SubprocessError, FileNotFoundError, OSError, Exception):
            pass

        # 额外检查18000端口（后端）
        try:
            result = subprocess.run(
                ["lsof", "-ti", ":18000"], capture_output=True, text=True
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        subprocess.run(["kill", "-9", pid], check=True)
                        print(
                            f"  {Colors.OKGREEN}✓{Colors.ENDC} 后端进程 (PID: {pid}) 已停止"
                        )
                    except (subprocess.SubprocessError, FileNotFoundError, OSError, Exception):
                        pass
        except (subprocess.SubprocessError, FileNotFoundError, OSError, Exception):
            pass

        # 等待进程完全释放端口
        time.sleep(1)

    def _start_backend(self):
        """启动后端服务"""
        print(f"{Colors.OKGREEN}🚀 启动后端服务...{Colors.ENDC}")
        print("   地址: http://localhost:18000")
        print("   API文档: http://localhost:18000/docs")

        try:
            subprocess.run(
                ["poetry", "run", "python", "main.py"], cwd=self.backend_dir, check=True
            )
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}⚠️ 后端服务已停止{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}❌ 启动失败: {e}{Colors.ENDC}")

    def _start_frontend(self):
        """启动前端服务"""
        print(f"{Colors.OKGREEN}🚀 启动前端服务...{Colors.ENDC}")
        print("   地址: http://localhost:18001")

        try:
            subprocess.run(["npm", "run", "dev"], cwd=self.frontend_dir, check=True)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}⚠️ 前端服务已停止{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}❌ 启动失败: {e}{Colors.ENDC}")

    def _start_fullstack(self):
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

    # ========== 数据库管理 ==========

    def db_info(self, args):
        """显示数据库信息"""
        if not self.db_path.exists():
            print(f"{Colors.FAIL}❌ 数据库不存在: {self.db_path}{Colors.ENDC}")
            return

        try:
            from core.mc_database import Database

            db = Database(str(self.db_path))

            print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
            print(f"{Colors.BOLD}  MC L10n 数据库信息{Colors.ENDC}")
            print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")

            # 获取统计信息
            stats = db.get_statistics()

            print(f"\n{Colors.OKBLUE}📊 基本统计:{Colors.ENDC}")
            print(f"  MOD数量: {stats.get('total_mods', 0)}")
            print(f"  语言文件: {stats.get('total_language_files', 0)}")
            print(f"  翻译条目: {stats.get('total_translation_entries', 0)}")
            print(f"  项目数量: {stats.get('total_projects', 0)}")

            # 缓存统计
            cache_stats = stats.get("cache_statistics", {})
            if cache_stats:
                print(f"\n{Colors.OKBLUE}💾 缓存统计:{Colors.ENDC}")
                print(f"  缓存文件: {cache_stats.get('total_cached_files', 0)}")
                print(f"  有效缓存: {cache_stats.get('valid_cache_entries', 0)}")
                print(f"  过期缓存: {cache_stats.get('expired_cache_entries', 0)}")
                cache_size_bytes = cache_stats.get("total_cache_size", 0) or 0
                cache_size = cache_size_bytes / 1024 / 1024
                print(f"  缓存大小: {cache_size:.2f} MB")

            # 数据库大小
            db_size = self.db_path.stat().st_size / 1024 / 1024
            print(f"\n{Colors.OKBLUE}📦 数据库大小: {db_size:.2f} MB{Colors.ENDC}")

            print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")

        except Exception as e:
            print(f"{Colors.FAIL}❌ 获取数据库信息失败: {e}{Colors.ENDC}")

    def db_cleanup(self, args):
        """清理数据库"""
        try:
            from core.mc_database import Database

            db = Database(str(self.db_path))

            print(f"{Colors.OKGREEN}🧹 正在清理数据库...{Colors.ENDC}")

            # 清理过期缓存
            db.cleanup_expired_cache()

            # 执行VACUUM
            with db.get_connection() as conn:
                conn.execute("VACUUM")
                conn.execute("ANALYZE")

            print(f"{Colors.OKGREEN}✅ 数据库清理完成{Colors.ENDC}")

        except Exception as e:
            print(f"{Colors.FAIL}❌ 清理失败: {e}{Colors.ENDC}")

    def db_export(self, args):
        """导出数据库"""
        try:
            from core.mc_database import Database

            db = Database(str(self.db_path))

            output_file = (
                args.output
                or f"mc_l10n_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

            print(f"{Colors.OKGREEN}📤 正在导出数据...{Colors.ENDC}")

            with db.get_connection() as conn:
                cursor = conn.cursor()
                data = {}

                # 导出MOD信息
                cursor.execute("""
                    SELECT mod_id, display_name, version, file_path, file_size
                    FROM mods
                """)
                data["mods"] = [dict(row) for row in cursor.fetchall()]

                # 导出语言文件
                cursor.execute("""
                    SELECT m.mod_id, lf.language_code, lf.file_path, lf.entry_count
                    FROM language_files lf
                    JOIN mods m ON lf.mod_id = m.id
                """)
                data["language_files"] = [dict(row) for row in cursor.fetchall()]

                # 导出统计
                data["statistics"] = db.get_statistics()
                data["export_time"] = datetime.now().isoformat()

            # 写入文件
            output_path = Path(output_file)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(
                f"{Colors.OKGREEN}✅ 数据已导出到: {output_path.absolute()}{Colors.ENDC}"
            )

        except Exception as e:
            print(f"{Colors.FAIL}❌ 导出失败: {e}{Colors.ENDC}")

    def db_reset(self, args):
        """重置数据库"""
        if not args.force:
            response = input(
                f"{Colors.WARNING}⚠️ 此操作将删除所有数据，是否继续？(y/N): {Colors.ENDC}"
            )
            if response.lower() != "y":
                print("操作已取消")
                return

        try:
            if self.db_path.exists():
                # 备份现有数据库
                backup_path = self.db_path.with_suffix(
                    f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                )
                import shutil

                shutil.copy2(self.db_path, backup_path)
                print(f"{Colors.OKGREEN}✅ 已备份到: {backup_path}{Colors.ENDC}")

                # 删除数据库
                self.db_path.unlink()

            # 重新初始化
            from core.mc_database import Database

            Database(str(self.db_path))
            print(f"{Colors.OKGREEN}✅ 数据库已重置{Colors.ENDC}")

        except Exception as e:
            print(f"{Colors.FAIL}❌ 重置失败: {e}{Colors.ENDC}")

    def db_viewer(self, args):
        """启动数据库Web查看器"""
        if not self.db_path.exists():
            print(f"{Colors.FAIL}❌ 数据库不存在: {self.db_path}{Colors.ENDC}")
            print("请先进行扫描以创建数据库")
            return

        viewer_script = self.backend_dir / "tools" / "db_viewer" / "db_web_advanced.py"
        if not viewer_script.exists():
            print(f"{Colors.FAIL}❌ 数据库查看器不存在: {viewer_script}{Colors.ENDC}")
            return

        print(f"{Colors.OKBLUE}🚀 正在启动数据库Web查看器...{Colors.ENDC}")
        print(f"📂 数据库: {self.db_path}")
        print(f"🌐 Web界面: http://localhost:{args.port}")
        print(f"📝 按 Ctrl+C 停止服务器")
        print(f"{Colors.HEADER}{'-' * 60}{Colors.ENDC}")

        try:
            import subprocess
            import webbrowser
            import threading
            import time

            # 在新线程中延迟打开浏览器
            if not args.no_browser:
                def open_browser():
                    time.sleep(2)
                    try:
                        webbrowser.open(f"http://localhost:{args.port}")
                        print(f"{Colors.OKGREEN}🌐 已在浏览器中打开数据库查看器{Colors.ENDC}")
                    except:
                        print(f"{Colors.WARNING}💡 请手动打开浏览器访问: http://localhost:{args.port}{Colors.ENDC}")

                browser_thread = threading.Thread(target=open_browser, daemon=True)
                browser_thread.start()

            # 启动查看器
            cmd = [
                "poetry", "run", "python", "db_web_advanced.py",
                "--db", str(self.db_path.resolve()),
                "--port", str(args.port),
                "--host", "127.0.0.1"
            ]

            process = subprocess.run(
                cmd,
                cwd=viewer_script.parent,
                check=False
            )

        except KeyboardInterrupt:
            print(f"\n{Colors.OKGREEN}👋 数据库查看器已停止{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}❌ 启动失败: {e}{Colors.ENDC}")

    # ========== 扫描管理 ==========

    def scan_start(self, args):
        """启动扫描"""
        directory = Path(args.directory).absolute()
        if not directory.exists():
            print(f"{Colors.FAIL}❌ 目录不存在: {directory}{Colors.ENDC}")
            return

        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.api_url}/api/v1/scan-project",
                    json={"directory": str(directory), "incremental": not args.full},
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        scan_id = data.get("scan_id") or data.get("job_id")
                        print(f"{Colors.OKGREEN}✅ 扫描已启动{Colors.ENDC}")
                        print(f"   ID: {scan_id}")
                        print(f"   目录: {directory}")
                        print(f"   模式: {'全量' if args.full else '增量'}")

                        if args.monitor:
                            self._monitor_scan(scan_id)
                    else:
                        print(
                            f"{Colors.FAIL}❌ 启动失败: {data.get('error', {}).get('message', '未知错误')}{Colors.ENDC}"
                        )
                else:
                    print(
                        f"{Colors.FAIL}❌ HTTP错误: {response.status_code}{Colors.ENDC}"
                    )

        except httpx.ConnectError:
            print(
                f"{Colors.FAIL}❌ 无法连接到服务器，请确保后端服务已启动{Colors.ENDC}"
            )
        except Exception as e:
            print(f"{Colors.FAIL}❌ 扫描失败: {e}{Colors.ENDC}")

    def scan_status(self, args):
        """查看扫描状态"""
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.api_url}/api/v1/scan-status/{args.scan_id}"
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        status = data.get("data", {})
                        print(f"{Colors.HEADER}扫描状态{Colors.ENDC}")
                        print(f"  ID: {args.scan_id}")
                        print(f"  状态: {status.get('status', 'unknown')}")
                        print(f"  进度: {status.get('progress', 0):.1f}%")
                        print(
                            f"  文件: {status.get('processed_files', 0)}/{status.get('total_files', 0)}"
                        )

                        if args.monitor:
                            self._monitor_scan(args.scan_id)
                    else:
                        print(f"{Colors.FAIL}❌ 获取状态失败{Colors.ENDC}")
                else:
                    print(
                        f"{Colors.FAIL}❌ HTTP错误: {response.status_code}{Colors.ENDC}"
                    )

        except Exception as e:
            print(f"{Colors.FAIL}❌ 请求失败: {e}{Colors.ENDC}")

    def scan_list(self, args):
        """列出扫描任务"""
        try:
            with httpx.Client() as client:
                response = client.get(f"{self.api_url}/api/v1/scans/active")

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        scans = data.get("data", [])

                        if scans:
                            print(f"{Colors.HEADER}活跃的扫描任务{Colors.ENDC}")
                            print("-" * 60)

                            for scan in scans:
                                print(f"ID: {scan['id']}")
                                print(f"  状态: {scan['status']}")
                                print(f"  进度: {scan['progress']:.1f}%")
                                print(
                                    f"  文件: {scan['processed_files']}/{scan['total_files']}"
                                )
                                print("-" * 60)
                        else:
                            print(f"{Colors.WARNING}没有活跃的扫描任务{Colors.ENDC}")

        except Exception as e:
            print(f"{Colors.FAIL}❌ 获取扫描列表失败: {e}{Colors.ENDC}")

    def _monitor_scan(self, scan_id: str):
        """监控扫描进度"""
        print(f"\n{Colors.OKBLUE}📊 监控扫描进度...{Colors.ENDC}")

        last_progress = -1
        with httpx.Client() as client:
            while True:
                try:
                    response = client.get(
                        f"{self.api_url}/api/v1/scan-status/{scan_id}"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            status = data.get("data", {})
                            progress = status.get("progress", 0)
                            scan_status = status.get("status", "unknown")

                            if progress != last_progress:
                                processed = status.get("processed_files", 0)
                                total = status.get("total_files", 0)

                                # 进度条
                                bar_length = 30
                                filled = int(bar_length * progress / 100)
                                bar = "█" * filled + "░" * (bar_length - filled)

                                print(
                                    f"\r[{bar}] {progress:.1f}% ({processed}/{total})",
                                    end="",
                                )
                                last_progress = progress

                            if scan_status == "completed":
                                print(f"\n{Colors.OKGREEN}✅ 扫描完成！{Colors.ENDC}")
                                break
                            elif scan_status in ["failed", "cancelled"]:
                                print(
                                    f"\n{Colors.FAIL}❌ 扫描{scan_status}{Colors.ENDC}"
                                )
                                break

                    time.sleep(1)

                except KeyboardInterrupt:
                    print(f"\n{Colors.WARNING}⚠️ 监控已停止{Colors.ENDC}")
                    break
                except Exception as e:
                    print(f"\n{Colors.FAIL}❌ 监控失败: {e}{Colors.ENDC}")
                    break

    # ========== 系统管理 ==========

    def system_info(self, args):
        """显示系统信息"""
        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.BOLD}  MC L10n 系统信息{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")

        # 路径信息
        print(f"\n{Colors.OKBLUE}📁 路径信息:{Colors.ENDC}")
        print(f"  脚本目录: {self.scripts_dir}")
        print(f"  后端目录: {self.backend_dir}")
        print(f"  前端目录: {self.frontend_dir}")
        print(f"  数据库: {self.db_path}")

        # 服务状态
        print(f"\n{Colors.OKBLUE}🔌 服务状态:{Colors.ENDC}")

        # 检查后端
        try:
            with httpx.Client(timeout=1.0) as client:
                response = client.get(f"{self.api_url}/health")
                if response.status_code == 200:
                    print(
                        f"  后端: {Colors.OKGREEN}运行中{Colors.ENDC} (http://localhost:18000)"
                    )
                else:
                    print(f"  后端: {Colors.WARNING}异常{Colors.ENDC}")
        except (subprocess.SubprocessError, FileNotFoundError, OSError, Exception):
            print(f"  后端: {Colors.FAIL}未运行{Colors.ENDC}")

        # 检查前端
        try:
            with httpx.Client(timeout=1.0) as client:
                response = client.get("http://localhost:18001")
                print(
                    f"  前端: {Colors.OKGREEN}运行中{Colors.ENDC} (http://localhost:18001)"
                )
        except (subprocess.SubprocessError, FileNotFoundError, OSError, Exception):
            print(f"  前端: {Colors.FAIL}未运行{Colors.ENDC}")

        # Python版本
        print(f"\n{Colors.OKBLUE}🐍 Python版本:{Colors.ENDC}")
        print(f"  {sys.version}")

        print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")

    def system_cleanup(self, args):
        """清理系统"""
        print(f"{Colors.OKGREEN}🧹 正在清理系统...{Colors.ENDC}")

        # 清理Python缓存
        import shutil

        cleaned = 0

        for root, dirs, files in Path(".").walk():
            # 清理__pycache__
            if "__pycache__" in dirs:
                cache_dir = root / "__pycache__"
                shutil.rmtree(cache_dir)
                cleaned += 1

            # 清理.pyc文件
            for file in files:
                if file.endswith(".pyc"):
                    (root / file).unlink()
                    cleaned += 1

        print(f"{Colors.OKGREEN}✅ 清理了 {cleaned} 个缓存文件/目录{Colors.ENDC}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="MC L10n 统一管理工具 - Minecraft 本地化项目管理和翻译工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 常用命令示例:
  %(prog)s server start fullstack           # 启动完整服务 (前端+后端)
  %(prog)s scan start ~/minecraft/mods -m   # 扫描MOD目录并监控进度
  %(prog)s db viewer                        # 启动数据库Web管理界面
  %(prog)s db info                          # 查看项目统计信息

📊 数据库管理:
  %(prog)s db export -o backup.json        # 导出数据备份
  %(prog)s db cleanup                       # 清理过期缓存
  %(prog)s db reset --force                 # 强制重置数据库

🔧 系统维护:
  %(prog)s system info                      # 检查系统状态
  %(prog)s system cleanup                   # 清理Python缓存

🌐 访问地址:
  前端界面: http://localhost:18001
  后端API:  http://localhost:18000/docs
  数据库查看器: http://localhost:8080
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # ========== 服务管理命令 ==========
    server_parser = subparsers.add_parser(
        "server",
        help="服务管理 - 启动/停止前端后端服务"
    )
    server_sub = server_parser.add_subparsers(dest="subcommand")

    server_start = server_sub.add_parser(
        "start",
        help="启动服务 (backend/frontend/fullstack)"
    )
    server_start.add_argument(
        "service", choices=["backend", "frontend", "fullstack"], help="要启动的服务"
    )
    server_start.add_argument(
        "--kill-old", action="store_true", help="启动前先杀死旧进程"
    )

    server_sub.add_parser("stop", help="停止所有运行中的服务")

    # ========== 数据库管理命令 ==========
    db_parser = subparsers.add_parser(
        "db",
        help="数据库管理 - 查看统计、导出数据、Web界面"
    )
    db_sub = db_parser.add_subparsers(dest="subcommand")

    db_sub.add_parser("info", help="显示数据库统计信息 (MOD数量、语言文件等)")
    db_sub.add_parser("cleanup", help="清理过期缓存并优化数据库")

    db_export = db_sub.add_parser("export", help="导出数据库内容到JSON文件")
    db_export.add_argument("-o", "--output", help="输出文件路径 (默认: 自动生成)")

    db_reset = db_sub.add_parser("reset", help="重置数据库 (会自动备份现有数据)")
    db_reset.add_argument("-f", "--force", action="store_true", help="跳过确认提示")

    db_viewer = db_sub.add_parser("viewer", help="启动数据库Web管理界面")
    db_viewer.add_argument("-p", "--port", type=int, default=8080, help="Web服务端口 (默认: 8080)")
    db_viewer.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")

    # ========== 扫描管理命令 ==========
    scan_parser = subparsers.add_parser(
        "scan",
        help="扫描管理 - MOD目录扫描和进度监控"
    )
    scan_sub = scan_parser.add_subparsers(dest="subcommand")

    scan_start = scan_sub.add_parser("start", help="启动MOD目录扫描")
    scan_start.add_argument("directory", help="要扫描的MOD目录路径")
    scan_start.add_argument("--full", action="store_true", help="全量扫描 (默认为增量扫描)")
    scan_start.add_argument("-m", "--monitor", action="store_true", help="实时监控扫描进度")

    scan_status = scan_sub.add_parser("status", help="查看指定扫描的状态和进度")
    scan_status.add_argument("scan_id", help="扫描任务ID")
    scan_status.add_argument("-m", "--monitor", action="store_true", help="持续监控状态变化")

    scan_sub.add_parser("list", help="列出所有活跃的扫描任务")

    # ========== 系统管理命令 ==========
    system_parser = subparsers.add_parser(
        "system",
        help="系统管理 - 状态检查和缓存清理"
    )
    system_sub = system_parser.add_subparsers(dest="subcommand")

    system_sub.add_parser("info", help="显示系统状态和服务运行情况")
    system_sub.add_parser("cleanup", help="清理Python缓存和临时文件")

    # 解析参数
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 创建CLI实例
    cli = MCL10nCLI()

    # 执行命令
    try:
        if args.command == "server":
            if args.subcommand == "start":
                cli.server_start(args)
            elif args.subcommand == "stop":
                cli.server_stop(args)
        elif args.command == "db":
            if args.subcommand == "info":
                cli.db_info(args)
            elif args.subcommand == "cleanup":
                cli.db_cleanup(args)
            elif args.subcommand == "export":
                cli.db_export(args)
            elif args.subcommand == "reset":
                cli.db_reset(args)
            elif args.subcommand == "viewer":
                cli.db_viewer(args)
        elif args.command == "scan":
            if args.subcommand == "start":
                cli.scan_start(args)
            elif args.subcommand == "status":
                cli.scan_status(args)
            elif args.subcommand == "list":
                cli.scan_list(args)
        elif args.command == "system":
            if args.subcommand == "info":
                cli.system_info(args)
            elif args.subcommand == "cleanup":
                cli.system_cleanup(args)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}操作被中断{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.FAIL}错误: {e}{Colors.ENDC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
