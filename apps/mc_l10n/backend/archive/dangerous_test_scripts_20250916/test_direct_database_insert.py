#!/usr/bin/env python3
"""
直接测试数据库插入，使用正确的字段名
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

def test_direct_insert():
    """直接测试数据库插入"""
    db_path = Path("data/mc_l10n_v2_1.db")
    
    print(f"📁 连接数据库: {db_path}")
    conn = sqlite3.connect(str(db_path))
    
    try:
        now = datetime.now().isoformat()
        
        # 1. 插入pack记录（使用正确的字段名）
        pack_sql = """
        INSERT INTO packs (name, project_type, game_type, path, description, created_at, updated_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor = conn.execute(pack_sql, (
            "test_direct_pack",  # name 
            "modpack",          # project_type
            "minecraft",        # game_type
            "/test/direct/path", # path
            "直接测试插入的包",    # description
            now,                # created_at
            now,                # updated_at
            True                # is_active
        ))
        pack_id = cursor.lastrowid
        print(f"✅ Pack插入成功，pack_id: {pack_id}")
        
        # 2. 插入pack_version记录
        pack_version_sql = """
        INSERT INTO pack_versions (pack_id, version_tag, minecraft_version, loader_type, display_name, is_default, is_stable, local_path, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor = conn.execute(pack_version_sql, (
            pack_id,              # pack_id
            "1.0.0-direct",      # version_tag
            "1.20.1",            # minecraft_version
            "forge",             # loader_type
            "直接测试版本",        # display_name
            True,                # is_default
            True,                # is_stable
            "/test/direct/path", # local_path
            now,                 # created_at
            now                  # updated_at
        ))
        pack_version_id = cursor.lastrowid
        print(f"✅ PackVersion插入成功，pack_version_id: {pack_version_id}")
        
        # 3. 插入mod_version_instances记录
        mod_instance_sql = """
        INSERT INTO mod_version_instances 
        (mod_id, mod_version, mod_name, jar_file_path, jar_file_size, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor = conn.execute(mod_instance_sql, (
            str(uuid.uuid4()),      # mod_id
            "1.0.0",               # mod_version
            "test_direct_mod",     # mod_name
            "/test/direct/mod.jar", # jar_file_path
            2048,                  # jar_file_size
            now,                   # created_at
            now                    # updated_at
        ))
        mod_instance_id = cursor.lastrowid
        print(f"✅ ModInstance插入成功，mod_instance_id: {mod_instance_id}")
        
        # 4. 插入pack_mod_relations关联
        relation_sql = """
        INSERT INTO pack_mod_relations (pack_version_id, mod_instance_id, relation_type, detected_at, detection_method, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        conn.execute(relation_sql, (
            pack_version_id,      # pack_version_id
            mod_instance_id,      # mod_instance_id
            "included",           # relation_type
            now,                  # detected_at
            "filesystem_scan",    # detection_method
            now                   # created_at
        ))
        print(f"✅ 关联关系插入成功")
        
        # 提交事务
        conn.commit()
        print("✅ 事务提交成功")
        
        # 验证数据
        cursor.execute("SELECT COUNT(*) FROM packs WHERE name = ?", ("test_direct_pack",))
        pack_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mod_version_instances WHERE mod_name = ?", ("test_direct_mod",))
        mod_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pack_mod_relations WHERE mod_instance_id = ?", (mod_instance_id,))
        relation_count = cursor.fetchone()[0]
        
        print(f"🔍 验证结果:")
        print(f"  - Pack记录: {pack_count}")
        print(f"  - Mod记录: {mod_count}")
        print(f"  - 关联记录: {relation_count}")
        
        if pack_count == 1 and mod_count == 1 and relation_count == 1:
            print("🎉 直接数据库插入测试成功！")
            return True
        else:
            print("❌ 数据验证失败")
            return False
            
    except Exception as e:
        print(f"❌ 插入失败: {e}")
        import traceback
        print(traceback.format_exc())
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = test_direct_insert()
    exit(0 if success else 1)