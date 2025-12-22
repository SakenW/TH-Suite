#!/usr/bin/env python3
"""
启动 MC L10n 数据库查看器
便捷的数据库查看器启动脚本
"""

import subprocess
import sys
import webbrowser
from pathlib import Path
import time

def main():
    """启动数据库查看器"""
    
    # 检查路径
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent / "backend"
    db_viewer_path = backend_dir / "tools" / "db_viewer" / "db_web_advanced.py"
    db_path = backend_dir / "data" / "mc_l10n_v6.db"
    
    if not db_viewer_path.exists():
        print(f"❌ 数据库查看器文件不存在: {db_viewer_path}")
        sys.exit(1)
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        print("请先进行扫描以创建数据库")
        sys.exit(1)
    
    print("🚀 正在启动 MC L10n 数据库查看器...")
    print(f"📂 数据库路径: {db_path}")
    print("🌐 Web界面地址: http://localhost:8080")
    print("📝 按 Ctrl+C 停止服务器")
    print("-" * 50)
    
    try:
        # 切换到正确的目录
        import os
        os.chdir(db_viewer_path.parent)
        
        # 启动数据库查看器
        cmd = [
            "poetry", "run", "python", "db_web_advanced.py",
            "--db", str(db_path.resolve()),
            "--port", "8080",
            "--host", "127.0.0.1"
        ]
        
        # 延迟打开浏览器
        def open_browser():
            time.sleep(2)  # 等待服务器启动
            try:
                webbrowser.open("http://localhost:8080")
                print("🌐 已在浏览器中打开数据库查看器")
            except:
                print("💡 请手动打开浏览器访问: http://localhost:8080")
        
        # 在新线程中打开浏览器
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # 启动服务器
        process = subprocess.run(cmd, cwd=db_viewer_path.parent)
        
    except KeyboardInterrupt:
        print("\n👋 数据库查看器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()