#!/usr/bin/env python3
"""
调试工作队列数据库连接问题
这个脚本模拟服务的实际数据库访问流程，找出ops_work_queue错误的根本原因
"""

import sqlite3
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from infrastructure.repositories.repository_factory import get_repository_factory
from infrastructure.repositories.ops_work_queue_repository_v2 import OpsWorkQueueRepository
from infrastructure.services.work_queue_processor import WorkQueueProcessor
import structlog

logger = structlog.get_logger(__name__)

def debug_database_connections():
    print("🔍 调试工作队列数据库连接问题")
    print("=" * 60)
    
    # 1. 检查Repository工厂的数据库路径
    print("\n1️⃣ 检查Repository工厂的数据库路径")
    factory = get_repository_factory()
    print(f"   工厂数据库路径: {factory.db_path}")
    factory_db_path = Path(factory.db_path)
    print(f"   工厂数据库文件是否存在: {factory_db_path.exists()}")
    
    if factory_db_path.exists():
        print(f"   工厂数据库文件大小: {factory_db_path.stat().st_size} 字节")
    
    # 2. 直接测试ops_work_queue Repository
    print("\n2️⃣ 直接测试OpsWorkQueueRepository")
    try:
        work_queue_repo = factory.get_ops_work_queue_repo()
        print(f"   Repository数据库路径: {work_queue_repo.db_path}")
        print(f"   Repository数据库文件是否存在: {work_queue_repo.db_path.exists()}")
        
        # 尝试访问ops_work_queue表
        print("   尝试查询ops_work_queue表...")
        tasks = work_queue_repo.get_pending_tasks()
        print(f"   ✅ 成功查询到 {len(tasks)} 个待处理任务")
        
    except Exception as e:
        print(f"   ❌ Repository访问失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. 测试工作队列处理器
    print("\n3️⃣ 测试WorkQueueProcessor")
    try:
        processor = WorkQueueProcessor()
        print(f"   处理器工厂数据库路径: {processor.factory.db_path}")
        print(f"   处理器队列Repository数据库路径: {processor.queue_repo.db_path}")
        
        # 尝试获取统计信息
        print("   尝试获取队列统计信息...")
        stats = processor.queue_repo.get_queue_stats()
        print(f"   ✅ 成功获取队列统计: {stats}")
        
    except Exception as e:
        print(f"   ❌ 工作队列处理器访问失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. 直接连接数据库检查表
    print("\n4️⃣ 直接连接数据库检查")
    db_path = Path("data/mc_l10n.db")
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ops_work_queue'")
            table_exists = cursor.fetchone()
            print(f"   ops_work_queue表是否存在: {'✅ 是' if table_exists else '❌ 否'}")
            
            if table_exists:
                # 获取表结构
                cursor.execute("PRAGMA table_info(ops_work_queue)")
                columns = cursor.fetchall()
                print(f"   ops_work_queue表列数: {len(columns)}")
                
                # 获取记录数
                cursor.execute("SELECT COUNT(*) FROM ops_work_queue")
                count = cursor.fetchone()[0]
                print(f"   ops_work_queue表记录数: {count}")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ 直接数据库连接失败: {e}")
    else:
        print(f"   ❌ 数据库文件不存在: {db_path}")
    
    # 5. 检查工作目录和相对路径
    print("\n5️⃣ 检查工作目录和路径解析")
    current_dir = Path.cwd()
    print(f"   当前工作目录: {current_dir}")
    
    relative_db_path = Path("data/mc_l10n.db")
    absolute_db_path = current_dir / relative_db_path
    print(f"   相对路径: {relative_db_path}")
    print(f"   解析为绝对路径: {absolute_db_path}")
    print(f"   绝对路径文件是否存在: {absolute_db_path.exists()}")
    
    # 6. 检查backend目录下的数据库路径
    backend_db_path = Path(__file__).parent / "data" / "mc_l10n.db"
    print(f"   backend目录数据库路径: {backend_db_path}")
    print(f"   backend目录数据库文件是否存在: {backend_db_path.exists()}")
    
    if backend_db_path.exists():
        print(f"   backend目录数据库文件大小: {backend_db_path.stat().st_size} 字节")

if __name__ == "__main__":
    debug_database_connections()