#!/usr/bin/env python3
"""
测试扫描并验证数据持久化
创建一些测试数据然后运行扫描，确保数据不会被意外清除
"""

import sqlite3
import asyncio
from pathlib import Path

async def test_scan_with_preserved_data():
    """测试扫描功能并验证数据保留"""
    
    # 1. 创建测试数据
    db_path = "data/mc_l10n.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 插入测试项目
    cursor.execute("""
        INSERT INTO packs (name, project_type, path, description) 
        VALUES ('测试整合包', 'modpack', '/test/path', '用于测试数据持久化')
    """)
    pack_id = cursor.lastrowid
    
    # 插入测试版本
    cursor.execute("""
        INSERT INTO pack_versions (pack_id, version_tag, minecraft_version, loader_type) 
        VALUES (?, '1.0.0', '1.21.1', 'fabric')
    """, (pack_id,))
    version_id = cursor.lastrowid
    
    # 插入测试MOD
    cursor.execute("""
        INSERT INTO mod_version_instances (mod_id, mod_version, mod_name) 
        VALUES ('test_mod', '1.0.0', '测试MOD')
    """)
    mod_id = cursor.lastrowid
    
    # 插入测试内容
    cursor.execute("""
        INSERT INTO content_instances (
            content_key, content_source, source_identifier,
            source_text, language_code, content_type, 
            file_path, file_format
        ) VALUES (
            'test.key', 'mod_jar', 'test_mod',
            'Test Content', 'en_us', 'translation',
            '/test/path/lang/en_us.json', 'json'
        )
    """)
    content_id = cursor.lastrowid
    
    conn.commit()
    
    # 验证数据已插入
    cursor.execute("SELECT COUNT(*) FROM packs")
    pack_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM content_instances")
    content_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"✅ 测试数据已创建:")
    print(f"   - 整合包: {pack_count} 个")
    print(f"   - 内容实例: {content_count} 个")
    
    # 2. 测试数据库初始化器不会清除数据
    from infrastructure.db_initializer import DatabaseInitializer
    
    initializer = DatabaseInitializer(db_path)
    result = initializer.ensure_database_exists()
    
    print(f"📊 数据库初始化结果: {'成功' if result else '失败'}")
    
    # 3. 验证数据仍然存在
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM packs")
    pack_count_after = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM content_instances")
    content_count_after = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📈 数据持久化验证:")
    print(f"   - 整合包: {pack_count_after} 个 (之前: {pack_count})")
    print(f"   - 内容实例: {content_count_after} 个 (之前: {content_count})")
    
    if pack_count_after == pack_count and content_count_after == content_count:
        print("✅ 数据持久化测试通过 - 数据未被清除")
        return True
    else:
        print("❌ 数据持久化测试失败 - 数据被意外清除")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_scan_with_preserved_data())
    exit(0 if result else 1)