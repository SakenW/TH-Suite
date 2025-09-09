#!/usr/bin/env python3
"""
MC L10n 项目清理脚本
用于清理冗余文件、数据库重复数据和临时文件
"""

import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def clean_database(db_path="backend/mc_l10n.db"):
    """清理数据库重复和过期数据"""
    print("🗄️ 开始数据库清理...")

    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return

    # 备份数据库
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"数据库已备份至: {backup_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 删除重复翻译条目
        cursor.execute("""
            DELETE FROM translation_entries
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM translation_entries
                GROUP BY key, language_file_id
            )
        """)
        duplicate_entries = cursor.rowcount
        print(f"删除重复翻译条目: {duplicate_entries:,}")

        # 删除7天前的扫描会话
        cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("DELETE FROM scan_sessions WHERE started_at < ?", (cutoff_date,))
        old_sessions = cursor.rowcount
        print(f"删除过期扫描会话: {old_sessions}")

        # 清理孤儿记录
        cursor.execute("""
            DELETE FROM translation_entries
            WHERE language_file_id NOT IN (SELECT id FROM language_files)
        """)
        orphan_entries = cursor.rowcount
        print(f"删除孤儿翻译条目: {orphan_entries:,}")

        cursor.execute("""
            DELETE FROM language_files
            WHERE mod_id NOT IN (SELECT id FROM mods)
        """)
        orphan_files = cursor.rowcount
        print(f"删除孤儿语言文件: {orphan_files:,}")

        # 压缩数据库
        cursor.execute("VACUUM")
        conn.commit()

        # 显示清理结果
        file_size = os.path.getsize(db_path) / 1024 / 1024
        print(f"数据库清理完成，当前大小: {file_size:.1f} MB")

    except Exception as e:
        print(f"数据库清理出错: {e}")
        conn.rollback()
    finally:
        conn.close()


def clean_build_artifacts():
    """清理构建产物和临时文件"""
    print("🗑️ 清理构建产物...")

    dirs_to_clean = [
        "frontend/dist",
        "frontend/build",
        "frontend/.next",
        "frontend/node_modules/.cache",
        "backend/__pycache__",
        "backend/.pytest_cache",
        "backend/logs",
    ]

    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"删除目录: {dir_path}")
            except Exception as e:
                print(f"无法删除 {dir_path}: {e}")


def clean_test_files():
    """清理测试文件和调试文件"""
    print("🧪 清理测试文件...")

    test_patterns = [
        "frontend/src/*test*",
        "frontend/src/*Test*",
        "frontend/src/*debug*",
        "frontend/src/*Debug*",
        "frontend/public/test*.html",
        "backend/test_*.py",
        "backend/*_test.py",
    ]

    import glob

    for pattern in test_patterns:
        for file_path in glob.glob(pattern):
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"删除测试文件: {file_path}")
            except Exception as e:
                print(f"无法删除 {file_path}: {e}")


def clean_redundant_files():
    """清理冗余文件"""
    print("📁 清理冗余文件...")

    # 删除重复的App文件（保留主要的App.tsx）
    redundant_files = [
        "frontend/src/App-*.tsx",
        "frontend/src/main-*.tsx",
        "backend/simple_main.py",
        "backend/*_backup.py",
    ]

    import glob

    for pattern in redundant_files:
        for file_path in glob.glob(pattern):
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"删除冗余文件: {file_path}")
            except Exception as e:
                print(f"无法删除 {file_path}: {e}")


def display_cleanup_summary():
    """显示清理摘要"""
    print("\n" + "=" * 50)
    print("🎉 清理完成摘要")
    print("=" * 50)

    # 检查当前项目大小
    total_size = 0
    for root, dirs, files in os.walk("."):
        # 跳过 node_modules 和 .git
        dirs[:] = [d for d in dirs if d not in ["node_modules", ".git", "__pycache__"]]
        for file in files:
            file_path = os.path.join(root, file)
            try:
                total_size += os.path.getsize(file_path)
            except (OSError, FileNotFoundError):
                continue

    print(f"项目大小: {total_size / 1024 / 1024:.1f} MB")

    # 检查数据库大小
    db_path = "backend/mc_l10n.db"
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path) / 1024 / 1024
        print(f"数据库大小: {db_size:.1f} MB")

    print("\n✅ 建议定期运行此脚本保持项目整洁")


def main():
    """主函数"""
    print("🧹 TH Suite MC L10n 项目清理工具")
    print("=" * 50)

    # 确保在正确的目录中运行
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    try:
        clean_database()
        clean_build_artifacts()
        clean_test_files()
        clean_redundant_files()
        display_cleanup_summary()

    except KeyboardInterrupt:
        print("\n⚠️ 清理被用户中断")
    except Exception as e:
        print(f"❌ 清理过程出错: {e}")


if __name__ == "__main__":
    main()
