#!/usr/bin/env python3
"""
测试新的迁移文件系统和数据库初始化
验证001-009迁移文件的完整性和功能
"""

import sqlite3
import tempfile
import shutil
from pathlib import Path
import sys

# 添加项目路径以便导入模块
sys.path.append(str(Path(__file__).parent))

from infrastructure.db_initializer import DatabaseInitializer


def test_migration_system():
    """测试新的迁移文件系统"""
    print("🚀 开始测试新的迁移文件系统...")
    
    # 创建临时数据库文件
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    try:
        # 测试数据库初始化
        print(f"📊 创建测试数据库: {test_db_path}")
        initializer = DatabaseInitializer(test_db_path)
        
        # 执行数据库初始化
        success = initializer.ensure_database_exists()
        if not success:
            print("❌ 数据库初始化失败")
            return False
        
        print("✅ 数据库初始化成功")
        
        # 验证数据库结构
        success = verify_database_structure(test_db_path)
        if not success:
            print("❌ 数据库结构验证失败")
            return False
        
        print("✅ 数据库结构验证通过")
        
        # 获取数据库统计信息
        stats = initializer.get_database_stats()
        print(f"📈 数据库统计: {stats}")
        
        # 验证temp_extracts目录功能
        test_temp_extracts(Path(test_db_path).parent)
        
        return True
        
    finally:
        # 清理测试文件
        if Path(test_db_path).exists():
            Path(test_db_path).unlink()
        backup_path = Path(test_db_path).with_suffix('.backup.db')
        if backup_path.exists():
            backup_path.unlink()


def verify_database_structure(db_path: str) -> bool:
    """验证数据库表结构是否完整"""
    print("🔍 验证数据库表结构...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查所有必需的表
        expected_tables = [
            # Core tables (从001_create_core_tables.sql)
            'core_projects', 'core_packs', 'core_pack_versions', 'core_mods',
            'core_mod_versions', 'core_pack_installations', 'core_pack_items',
            'core_language_files', 'core_translation_entries',
            
            # Operations tables (从002_create_operations_tables.sql)
            'ops_work_queue', 'ops_event_log', 'ops_sync_log', 'ops_cas_objects',
            
            # Configuration tables (从003_create_configuration_tables.sql)
            'cfg_local_settings', 'cfg_file_watch',
            
            # Cache tables (从004_create_cache_tables.sql)
            'cache_scan_results', 'cache_lang_file', 'cache_entry', 'cache_stats',
            'cache_checkpoint',
            
            # Scan architecture tables (从005_create_scan_tables.sql - 实际表名)
            'cache_scan_snapshots', 'cache_scan_delta', 'cache_scan_sessions', 
            'cache_recent_active_set', 'cache_content_addressed'
        ]
        
        # 获取实际存在的表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        actual_tables = {row[0] for row in cursor.fetchall()}
        
        print(f"📋 实际表数量: {len(actual_tables)}")
        print(f"📋 期望表数量: {len(expected_tables)}")
        
        # 检查缺少的表
        missing_tables = set(expected_tables) - actual_tables
        if missing_tables:
            print(f"❌ 缺少的表: {missing_tables}")
            return False
        
        # 检查额外的表（除了sqlite_*系统表）
        extra_tables = actual_tables - set(expected_tables)
        if extra_tables:
            print(f"ℹ️ 额外的表: {extra_tables}")
        
        # 检查ops_work_queue表结构（之前有问题的表）
        cursor.execute("PRAGMA table_info(ops_work_queue)")
        columns = {row[1] for row in cursor.fetchall()}
        required_columns = {
            'id', 'type', 'payload_json', 'state', 'priority', 'not_before',
            'dedupe_key', 'attempt', 'last_error', 'lease_owner', 'lease_expires_at',
            'created_at', 'updated_at'
        }
        
        missing_columns = required_columns - columns
        if missing_columns:
            print(f"❌ ops_work_queue缺少字段: {missing_columns}")
            return False
        
        print(f"✅ ops_work_queue字段完整: {len(columns)} 个字段")
        
        # 检查视图
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='view'
        """)
        views = [row[0] for row in cursor.fetchall()]
        print(f"📊 视图数量: {len(views)}")
        if views:
            print(f"📊 视图列表: {views}")
        
        # 检查索引
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"🗂️ 索引数量: {len(indexes)}")
        
        # 检查触发器
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='trigger'
        """)
        triggers = [row[0] for row in cursor.fetchall()]
        print(f"⚡ 触发器数量: {len(triggers)}")
        
        return True
        
    finally:
        conn.close()


def test_temp_extracts(data_dir: Path):
    """测试temp_extracts目录功能"""
    print("🗂️ 测试temp_extracts目录功能...")
    
    temp_extracts_dir = data_dir / "temp_extracts"
    
    # 创建测试目录
    temp_extracts_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建测试文件
    test_file = temp_extracts_dir / "test_extraction.txt"
    test_file.write_text("测试JAR提取功能")
    
    if test_file.exists():
        print("✅ temp_extracts目录创建和写入测试通过")
    else:
        print("❌ temp_extracts目录测试失败")
        return False
    
    # 清理测试文件
    test_file.unlink()
    
    # 如果目录为空，删除它
    try:
        temp_extracts_dir.rmdir()
        print("✅ temp_extracts清理测试通过")
    except OSError:
        print("ℹ️ temp_extracts目录不为空（正常情况）")
    
    return True


def test_jar_extraction_system():
    """测试JAR提取系统"""
    print("📦 测试JAR提取系统...")
    
    try:
        from infrastructure.services.jar_extraction_helper import AsyncJarReader
        print("✅ JAR提取模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ JAR提取模块导入失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TH-Suite MC L10n 迁移文件系统测试")
    print("=" * 60)
    
    # 测试数据库迁移系统
    db_test_success = test_migration_system()
    
    # 测试JAR提取系统
    jar_test_success = test_jar_extraction_system()
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    print(f"  • 数据库迁移系统: {'✅ 通过' if db_test_success else '❌ 失败'}")
    print(f"  • JAR提取系统: {'✅ 通过' if jar_test_success else '❌ 失败'}")
    
    if db_test_success and jar_test_success:
        print("🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("💥 部分测试失败！")
        sys.exit(1)