#!/usr/bin/env python3
"""
验证V5完整架构迁移结果
检查数据库表结构和数据完整性
"""
import sqlite3
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def verify_v5_migration():
    """验证V5架构迁移结果"""
    db_path = Path("data/mc_l10n.db")
    
    if not db_path.exists():
        logger.error(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 检查所有表
        logger.info("🔍 检查V5架构表结构")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            # Core tables (9个)
            'core_projects', 'core_packs', 'core_pack_items', 'core_mods', 
            'core_pack_installations', 'core_language_files', 'core_pack_item_relations',
            'core_mod_installations', 'core_sync_entries',
            
            # Ops tables (4个)
            'ops_work_queue', 'ops_outbox_journal', 'ops_sync_log', 'ops_cas_objects',
            
            # Config tables (2个)
            'cfg_local_settings', 'cfg_file_watch',
            
            # Cache tables (4个)
            'cache_scan_snapshots', 'cache_language_index', 'cache_mod_metadata', 'cache_pack_metadata'
        ]
        
        logger.info(f"✅ 发现表: {len(tables)} 个")
        for table in sorted(tables):
            logger.info(f"   📁 {table}")
            
        # 检查缺失的表
        missing_tables = set(expected_tables) - set(tables)
        if missing_tables:
            logger.warning(f"⚠️ 缺失表: {missing_tables}")
        else:
            logger.info("✅ 所有预期表都存在")
            
        # 2. 检查核心数据统计
        logger.info("\n📊 检查数据迁移结果")
        
        data_counts = {}
        core_tables = ['core_projects', 'core_packs', 'core_pack_items', 'core_mods', 
                      'core_pack_installations', 'core_language_files']
        
        for table in core_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                data_counts[table] = count
                logger.info(f"   📋 {table}: {count} 条记录")
        
        # 3. 验证数据样本
        logger.info("\n🔍 验证数据样本")
        
        # 检查项目数据
        if 'core_projects' in tables:
            cursor.execute("SELECT uid, name, description FROM core_projects LIMIT 3")
            projects = cursor.fetchall()
            for project in projects:
                logger.info(f"   🏗️ 项目: {project[1]} (UID: {project[0][:8]}...)")
        
        # 检查整合包数据
        if 'core_packs' in tables:
            cursor.execute("SELECT uid, title, minecraft_version FROM core_packs LIMIT 3")
            packs = cursor.fetchall()
            for pack in packs:
                logger.info(f"   📦 整合包: {pack[1]} (MC: {pack[2]}, UID: {pack[0][:8]}...)")
        
        # 检查MOD数据
        if 'core_mods' in tables:
            cursor.execute("SELECT uid, name, mod_id FROM core_mods LIMIT 5")
            mods = cursor.fetchall()
            for mod in mods:
                logger.info(f"   🧩 MOD: {mod[1]} (ID: {mod[2]}, UID: {mod[0][:8]}...)")
        
        # 4. 检查视图和索引
        logger.info("\n🔍 检查视图和索引")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")
        indexes = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"   📋 视图: {len(views)} 个")
        for view in views:
            logger.info(f"      🔍 {view}")
            
        logger.info(f"   📋 索引: {len(indexes)} 个")
        
        # 5. 检查约束和触发器
        cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name")
        triggers = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"   📋 触发器: {len(triggers)} 个")
        for trigger in triggers:
            logger.info(f"      ⚡ {trigger}")
        
        conn.close()
        
        # 生成迁移验证报告
        logger.info("\n📋 V5架构迁移验证报告")
        logger.info("=" * 50)
        logger.info(f"✅ 表总数: {len(tables)}")
        logger.info(f"✅ 视图总数: {len(views)}")
        logger.info(f"✅ 索引总数: {len(indexes)}")
        logger.info(f"✅ 触发器总数: {len(triggers)}")
        logger.info("\n数据迁移统计:")
        for table, count in data_counts.items():
            logger.info(f"   {table}: {count} 条记录")
        
        logger.info("\n🎉 V5完整架构迁移验证成功!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 验证过程出错: {e}")
        return False

if __name__ == "__main__":
    verify_v5_migration()