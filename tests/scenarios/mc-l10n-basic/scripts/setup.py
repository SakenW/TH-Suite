#!/usr/bin/env python3
"""
环境设置脚本
用于初始化测试环境和数据库
"""

import sqlite3
from pathlib import Path


def setup_database():
    """设置测试数据库"""
    # 创建数据库目录
    db_dir = Path(".artifacts/db")
    db_dir.mkdir(parents=True, exist_ok=True)

    # 创建测试数据库
    db_path = db_dir / "test_mc_l10n.db"

    if db_path.exists():
        db_path.unlink()

    # 连接数据库并创建表
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 创建mods表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mods (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            description TEXT,
            author TEXT,
            loader TEXT,
            mc_version TEXT,
            file_path TEXT,
            file_size INTEGER,
            sha256 TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建language_entries表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS language_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mod_id TEXT,
            key TEXT NOT NULL,
            source_text TEXT NOT NULL,
            source_lang TEXT NOT NULL,
            target_text TEXT,
            target_lang TEXT,
            file_path TEXT,
            line_number INTEGER,
            context TEXT,
            category TEXT,
            translatable BOOLEAN DEFAULT 1,
            translated BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mod_id) REFERENCES mods(id)
        )
    """)

    # 创建translation_requests表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translation_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER,
            source_lang TEXT NOT NULL,
            target_lang TEXT NOT NULL,
            source_text TEXT NOT NULL,
            translated_text TEXT,
            translator TEXT,
            confidence REAL,
            status TEXT DEFAULT 'pending',
            reviewed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entry_id) REFERENCES language_entries(id)
        )
    """)

    conn.commit()
    conn.close()

    print(f"测试数据库已创建: {db_path}")


def setup_directories():
    """设置必要的目录"""
    directories = [
        ".artifacts/temp",
        ".artifacts/output",
        ".artifacts/logs",
        ".artifacts/db",
        "tests/fixtures/mc-modpack/mods",
        "tests/fixtures/mc-modpack/resourcepacks",
    ]

    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    print("测试目录已创建")


def main():
    """主函数"""
    print("开始环境设置...")

    # 设置目录
    setup_directories()

    # 设置数据库
    setup_database()

    print("环境设置完成")


if __name__ == "__main__":
    main()
