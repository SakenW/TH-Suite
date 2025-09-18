#!/usr/bin/env python3
"""
测试数据库初始化问题
验证migration文件是否能正确创建完整的数据库架构
"""

import tempfile
import sqlite3
from pathlib import Path
from infrastructure.db_initializer import DatabaseInitializer


def test_fresh_database_creation():
    """测试全新数据库创建是否完整"""
    print("=== 测试全新数据库创建 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_fresh.db"
        
        # 创建数据库初始化器
        initializer = DatabaseInitializer(str(db_path))
        
        # 初始化数据库
        success = initializer.ensure_database_exists()
        print(f"数据库创建结果: {'成功' if success else '失败'}")
        
        if success:
            # 检查表结构
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"创建的表数量: {len(tables)}")
            print("表列表:", tables)
            
            # 检查期望的表是否存在
            expected_tables = [
                # Core tables (9个)
                'core_projects', 'core_packs', 'core_pack_versions', 'core_mods',
                'core_mod_versions', 'core_pack_installations', 'core_pack_items',
                'core_language_files', 'core_translation_entries',
                # Operations tables (4个)  
                'ops_work_queue', 'ops_sync_log', 'ops_cas_objects', 'ops_outbox_journal',
                # Configuration tables (2个)
                'cfg_local_settings', 'cfg_file_watch',
                # Cache tables (4个)
                'cache_entry', 'cache_lang_file', 'cache_scan_results', 'cache_stats'
            ]
            
            missing_tables = set(expected_tables) - set(tables)
            extra_tables = set(tables) - set(expected_tables)
            
            if missing_tables:
                print(f"❌ 缺少的表: {missing_tables}")
            
            if extra_tables:
                print(f"✅ 额外的表: {extra_tables}")
            
            # 检查ops_work_queue表结构
            cursor.execute("PRAGMA table_info(ops_work_queue)")
            columns = [(row[1], row[2]) for row in cursor.fetchall()]
            print("ops_work_queue表结构:", columns)
            
            # 检查期望字段
            expected_columns = [
                'id', 'type', 'payload_json', 'state', 'priority', 
                'not_before', 'dedupe_key', 'attempt', 'last_error', 
                'lease_owner', 'lease_expires_at', 'created_at', 'updated_at'
            ]
            
            actual_columns = [col[0] for col in columns]
            missing_columns = set(expected_columns) - set(actual_columns)
            
            if missing_columns:
                print(f"❌ ops_work_queue缺少字段: {missing_columns}")
            else:
                print("✅ ops_work_queue字段完整")
                
            conn.close()
        
        return success


def test_migration_sql_validity():
    """测试migration SQL文件的有效性"""
    print("\n=== 测试migration SQL文件有效性 ===")
    
    migrations_dir = Path("migrations")
    migration_files = [
        "003_v5_complete_architecture.sql",
        "004_async_incremental_scan_architecture.sql", 
        "005_extend_work_queue_scan_types.sql",
        "006_checkpoint_and_idempotency_tables.sql"
    ]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_migration.db"
        
        conn = sqlite3.connect(str(db_path))
        
        for migration_file in migration_files:
            file_path = migrations_dir / migration_file
            if not file_path.exists():
                print(f"❌ 找不到迁移文件: {migration_file}")
                continue
            
            print(f"测试迁移文件: {migration_file}")
            
            try:
                sql_content = file_path.read_text(encoding='utf-8')
                
                # 分步执行SQL，捕获具体的错误
                statements = []
                current_statement = ""
                in_comment_block = False
                
                for line in sql_content.split('\n'):
                    line = line.strip()
                    
                    # 处理注释
                    if line.startswith('/*'):
                        in_comment_block = True
                        continue
                    if '*/' in line:
                        in_comment_block = False
                        continue
                    if in_comment_block or line.startswith('--') or not line:
                        continue
                    
                    current_statement += line + " "
                    
                    if line.endswith(';'):
                        statements.append(current_statement.strip())
                        current_statement = ""
                
                # 执行每个语句
                for i, statement in enumerate(statements):
                    if statement:
                        try:
                            conn.executescript(statement)
                            conn.commit()
                        except Exception as e:
                            print(f"❌ 语句 {i+1} 执行失败: {statement[:100]}...")
                            print(f"   错误: {e}")
                            conn.close()
                            return False
                
                print(f"✅ {migration_file} 执行成功")
                
            except Exception as e:
                print(f"❌ {migration_file} 执行失败: {e}")
                conn.close()
                return False
        
        conn.close()
        return True


def main():
    """主测试函数"""
    print("测试数据库初始化问题")
    
    # 测试1: 全新数据库创建
    success1 = test_fresh_database_creation()
    
    # 测试2: migration SQL有效性
    success2 = test_migration_sql_validity()
    
    print("\n=== 测试总结 ===")
    print(f"全新数据库创建: {'✅ 成功' if success1 else '❌ 失败'}")
    print(f"Migration SQL有效性: {'✅ 成功' if success2 else '❌ 失败'}")
    
    if success1 and success2:
        print("✅ 所有测试通过")
    else:
        print("❌ 存在问题需要修复")


if __name__ == "__main__":
    main()