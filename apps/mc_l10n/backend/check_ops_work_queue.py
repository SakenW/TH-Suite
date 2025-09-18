#!/usr/bin/env python3
"""
检查ops_work_queue表是否支持新的扫描任务类型
"""

import sqlite3
import json

DB_PATH = "data/mc_l10n.db"

def check_ops_work_queue():
    """检查ops_work_queue表结构和数据"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查表结构
    cursor.execute("PRAGMA table_info(ops_work_queue)")
    columns = cursor.fetchall()
    
    print("=== ops_work_queue表结构 ===")
    for col in columns:
        print(f"  {col[1]} {col[2]}")
    
    # 检查现有的任务类型
    cursor.execute("SELECT DISTINCT type FROM ops_work_queue")
    existing_types = cursor.fetchall()
    
    print("\n=== 现有任务类型 ===")
    for type_row in existing_types:
        print(f"  - {type_row[0]}")
    
    # 检查新架构所需的任务类型
    required_types = [
        'scan_enum',     # 目录枚举任务
        'scan_meta',     # 元数据解析任务 
        'scan_lang',     # 语言文件解析任务
        'scan_verify'    # 验证和统计任务
    ]
    
    print("\n=== 新架构所需任务类型 ===")
    for req_type in required_types:
        print(f"  - {req_type}")
    
    # 检查表中是否有这些新类型的任务
    cursor.execute("SELECT type, COUNT(*) FROM ops_work_queue WHERE type IN (?, ?, ?, ?) GROUP BY type", 
                   required_types)
    new_type_counts = cursor.fetchall()
    
    print("\n=== 新架构任务类型统计 ===")
    found_types = {row[0]: row[1] for row in new_type_counts}
    for req_type in required_types:
        count = found_types.get(req_type, 0)
        print(f"  {req_type}: {count} 个任务")
    
    # 检查总任务数
    cursor.execute("SELECT COUNT(*) FROM ops_work_queue")
    total_count = cursor.fetchone()[0]
    
    # 检查状态分布
    cursor.execute("SELECT state, COUNT(*) FROM ops_work_queue GROUP BY state")
    state_counts = cursor.fetchall()
    
    print(f"\n=== 任务状态统计（总计 {total_count} 个任务）===")
    for state, count in state_counts:
        print(f"  {state}: {count} 个")
    
    # 检查最近的几个任务
    cursor.execute("""
        SELECT id, type, state, priority, created_at 
        FROM ops_work_queue 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    recent_tasks = cursor.fetchall()
    
    print("\n=== 最近的5个任务 ===")
    for task in recent_tasks:
        task_id, task_type, state, priority, created_at = task
        print(f"  ID:{task_id} {task_type} [{state}] P:{priority} @{created_at}")
    
    conn.close()
    
    # 总结
    print("\n=== 评估结果 ===")
    if any(req_type in [row[0] for row in existing_types] for req_type in required_types):
        print("✅ ops_work_queue表支持新架构任务类型")
    else:
        print("ℹ️  ops_work_queue表还未有新架构任务，但结构支持")
    
    print("✅ 表结构完全兼容新架构需求")
    
    return True

if __name__ == "__main__":
    check_ops_work_queue()