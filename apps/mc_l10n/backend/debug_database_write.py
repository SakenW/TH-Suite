#!/usr/bin/env python3
"""
数据库写入问题专用调试脚本
用于彻底解决数据写入失败的问题
"""

import sqlite3
import sys
import traceback
import logging
from pathlib import Path
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

def test_database_write():
    """测试数据库写入功能"""
    logger.info("🔍 开始数据库写入调试测试")
    
    # 数据库路径
    db_path = Path("data/mc_l10n_v2_1.db")
    logger.info(f"📁 数据库路径: {db_path.absolute()}")
    
    # 检查数据库文件是否存在
    if not db_path.exists():
        logger.error(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    logger.info(f"✅ 数据库文件存在，大小: {db_path.stat().st_size} 字节")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(str(db_path))
        logger.info("✅ 数据库连接成功")
        
        # 检查表结构
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"📋 数据库包含表: {[table[0] for table in tables]}")
        
        # 检查各表的记录数
        for table in tables:
            table_name = table[0]
            if not table_name.startswith('sqlite_'):
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                logger.info(f"📊 表 {table_name}: {count} 条记录")
        
        # 测试简单插入操作
        logger.info("🧪 开始测试数据插入...")
        
        now = datetime.now().isoformat()
        
        # 开始事务
        conn.execute("BEGIN TRANSACTION")
        logger.info("🔄 事务已开始")
        
        # 1. 插入测试包
        pack_sql = """
        INSERT OR IGNORE INTO packs (pack_name, pack_type, source_path, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(pack_sql, (
            "test_pack_debug",
            "modpack", 
            "/test/path",
            now,
            now
        ))
        pack_id = cursor.lastrowid or 1  # 如果已存在则获取ID
        logger.info(f"📦 测试包插入成功，pack_id: {pack_id}")
        
        # 获取实际的pack_id（如果是IGNORE的情况）
        cursor.execute("SELECT pack_id FROM packs WHERE pack_name = ?", ("test_pack_debug",))
        actual_pack_id = cursor.fetchone()[0]
        logger.info(f"📦 实际pack_id: {actual_pack_id}")
        
        # 2. 插入包版本
        version_sql = """
        INSERT OR IGNORE INTO pack_versions (pack_id, version_name, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(version_sql, (
            actual_pack_id,
            "1.0.0-debug",
            True,
            now,
            now
        ))
        pack_version_id = cursor.lastrowid or 1
        
        # 获取实际的pack_version_id
        cursor.execute("SELECT pack_version_id FROM pack_versions WHERE pack_id = ? AND version_name = ?", 
                      (actual_pack_id, "1.0.0-debug"))
        result = cursor.fetchone()
        if result:
            actual_pack_version_id = result[0]
            logger.info(f"📦 实际pack_version_id: {actual_pack_version_id}")
        else:
            logger.error("❌ 无法获取pack_version_id")
            return False
        
        # 3. 插入测试MOD实例
        mod_sql = """
        INSERT INTO mod_version_instances (
            mod_name, jar_file_path, jar_file_size, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(mod_sql, (
            "test_mod_debug",
            "/test/mod.jar",
            1024,
            now,
            now
        ))
        mod_instance_id = cursor.lastrowid
        logger.info(f"🔧 测试MOD插入成功，mod_instance_id: {mod_instance_id}")
        
        # 4. 插入关联关系
        relation_sql = """
        INSERT INTO pack_mod_relations (
            pack_version_id, mod_instance_id, relation_type, detected_at, detection_method, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor.execute(relation_sql, (
            actual_pack_version_id,
            mod_instance_id,
            "included",
            now,
            "filesystem_scan",
            now
        ))
        logger.info(f"🔗 关联关系插入成功")
        
        # 提交事务
        conn.commit()
        logger.info("✅ 事务已提交")
        
        # 验证数据是否真正写入
        cursor.execute("SELECT COUNT(*) FROM packs WHERE pack_name = ?", ("test_pack_debug",))
        pack_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mod_version_instances WHERE mod_name = ?", ("test_mod_debug",))
        mod_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pack_mod_relations WHERE mod_instance_id = ?", (mod_instance_id,))
        relation_count = cursor.fetchone()[0]
        
        logger.info(f"🔍 验证结果:")
        logger.info(f"  - 测试包记录数: {pack_count}")
        logger.info(f"  - 测试MOD记录数: {mod_count}")
        logger.info(f"  - 关联关系记录数: {relation_count}")
        
        if pack_count > 0 and mod_count > 0 and relation_count > 0:
            logger.info("✅ 数据库写入测试完全成功！")
            return True
        else:
            logger.error("❌ 数据库写入验证失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 数据库写入测试失败: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        try:
            conn.rollback()
            logger.info("🔄 事务已回滚")
        except:
            pass
        return False
    finally:
        try:
            conn.close()
            logger.info("🔌 数据库连接已关闭")
        except:
            pass

def test_scanner_service():
    """测试扫描服务是否能正确保存数据"""
    logger.info("🔍 测试扫描服务数据保存功能")
    
    try:
        # 导入扫描服务
        sys.path.insert(0, '/home/saken/project/TH-Suite/apps/mc_l10n/backend')
        from infrastructure.services.simple_minecraft_scanner import get_simple_minecraft_scanner_service
        
        # 获取服务实例
        service = get_simple_minecraft_scanner_service()
        logger.info("✅ 扫描服务实例创建成功")
        
        # 检查数据库路径
        logger.info(f"📁 扫描服务数据库路径: {service.db_path}")
        
        # 模拟一些扫描结果
        mock_results = {
            "discovered_items": [
                {
                    "name": "test_mod_scanner",
                    "path": "/test/scanner/mod.jar",
                    "size": 2048,
                    "type": "mod"
                }
            ],
            "statistics": {
                "mods_found": 1,
                "total_translation_keys": 100
            }
        }
        
        # 调用保存方法 - 需要使用正确的参数
        import asyncio
        asyncio.run(service._save_scan_results_to_database(
            "test_scan_123",  # scan_id
            mock_results["discovered_items"],  # discovered_items
            mock_results["statistics"]  # statistics
        ))
        logger.info("✅ 扫描结果保存调用完成")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 扫描服务测试失败: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logger.info("🚀 开始数据库写入问题彻底调试")
    
    # 测试1: 直接数据库写入
    success1 = test_database_write()
    
    # 测试2: 通过扫描服务写入
    success2 = test_scanner_service()
    
    if success1 and success2:
        logger.info("🎉 所有测试通过，数据库写入功能正常")
    else:
        logger.error("❌ 测试失败，需要进一步调试")
        sys.exit(1)