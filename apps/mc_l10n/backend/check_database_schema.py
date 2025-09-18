#!/usr/bin/env python3
"""
检查当前数据库架构并创建缺失的表
根据《扫描规则.md》的完整规范实现
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = "data/mc_l10n.db"

def check_and_create_tables():
    """检查并创建所有必需的表"""
    
    # 确保数据库目录存在
    Path("data").mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 启用WAL模式和外键约束
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    
    print("=== 当前数据库表结构 ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    existing_tables = [row[0] for row in cursor.fetchall()]
    for table in existing_tables:
        print(f"✓ {table}")
    
    print("\n=== 根据扫描规则.md创建缺失的表 ===")
    
    # 1. cache_scan_snapshots - 快照表（A7节定义）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_scan_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            pack_uid TEXT,
            pack_version_uid TEXT,
            root_path TEXT NOT NULL,
            files_json TEXT NOT NULL,  -- JSON格式：[{path,size,mtime,is_archive,jar_cd_entries,jar_cd_crc,hash_short}]
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES scan_sessions(session_id)
        )
    """)
    print("✓ cache_scan_snapshots")
    
    # 2. cache_scan_delta - 差异表（A7节定义）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_scan_delta (
            delta_id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            delta_json TEXT NOT NULL,  -- JSON格式：{added[],modified[],moved[],removed[],touched_mods[]}
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (snapshot_id) REFERENCES cache_scan_snapshots(snapshot_id),
            FOREIGN KEY (session_id) REFERENCES scan_sessions(session_id)
        )
    """)
    print("✓ cache_scan_delta")
    
    # 3. cache_checkpoint - 检查点表（A6节定义）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_checkpoint (
            checkpoint_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            artifact_ref TEXT,
            artifact_hash TEXT,
            last_step TEXT,
            offset_info TEXT,
            payload_json TEXT,  -- JSON格式检查点数据
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES scan_sessions(session_id)
        )
    """)
    print("✓ cache_checkpoint")
    
    # 4. 确保 ops_work_queue 表存在并支持新的扫描任务类型
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ops_work_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,  -- 包括: scan_enum, scan_meta, scan_lang, scan_verify
            priority INTEGER DEFAULT 50,
            state TEXT DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
            dedupe_key TEXT,
            lease_expires_at TIMESTAMP,
            attempt_count INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            payload_json TEXT NOT NULL,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ ops_work_queue")
    
    # 5. 修复 cache_stats 表结构
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_key TEXT NOT NULL,  -- 改名避免关键字冲突
            stat_value TEXT,
            category TEXT,
            session_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ cache_stats")
    
    # 6. scan_sessions - 扫描会话表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_sessions (
            session_id TEXT PRIMARY KEY,
            root_path TEXT NOT NULL,
            scan_type TEXT NOT NULL,
            stage TEXT DEFAULT 'initializing',
            progress REAL DEFAULT 0.0,
            incremental BOOLEAN DEFAULT FALSE,
            metadata_json TEXT,  -- JSON格式元数据
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    print("✓ scan_sessions")
    
    # 7. ops_event_log - 事件流水表（可选，A7节）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ops_event_log (
            event_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,  -- LIST_UPSERT, FIELD_PATCH, LANG_UPSERT, COUNT_PATCH, TOMB_STONE, CONFLICT, PROGRESS, ERROR
            entity_ref TEXT,
            stage TEXT,
            artifact_hash TEXT,
            payload_json TEXT NOT NULL,
            dedupe_key TEXT,  -- 幂等键：session_id + event_type + entity_ref + stage + artifact_hash
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES scan_sessions(session_id)
        )
    """)
    print("✓ ops_event_log")
    
    # 创建索引（A7节建议）
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_cache_scan_snapshots_created_at ON cache_scan_snapshots(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_cache_scan_delta_snapshot_id ON cache_scan_delta(snapshot_id)",
        "CREATE INDEX IF NOT EXISTS idx_cache_checkpoint_session_id ON cache_checkpoint(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_ops_work_queue_state ON ops_work_queue(state)",
        "CREATE INDEX IF NOT EXISTS idx_ops_work_queue_type ON ops_work_queue(type)",
        "CREATE INDEX IF NOT EXISTS idx_ops_work_queue_priority ON ops_work_queue(priority DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ops_event_log_session_ts ON ops_event_log(session_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_ops_event_log_type_entity ON ops_event_log(event_type, entity_ref)",
        "CREATE INDEX IF NOT EXISTS idx_scan_sessions_stage ON scan_sessions(stage)",
        "CREATE INDEX IF NOT EXISTS idx_cache_stats_key ON cache_stats(stat_key)",
    ]
    
    print("\n=== 创建索引 ===")
    for index_sql in indexes:
        cursor.execute(index_sql)
        index_name = index_sql.split("IF NOT EXISTS ")[1].split(" ON")[0]
        print(f"✓ {index_name}")
    
    conn.commit()
    
    print("\n=== 验证表结构 ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    final_tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = [
        'cache_scan_snapshots',
        'cache_scan_delta', 
        'cache_checkpoint',
        'cache_stats',
        'ops_work_queue',
        'scan_sessions',
        'ops_event_log'
    ]
    
    missing_tables = []
    for table in required_tables:
        if table in final_tables:
            print(f"✅ {table}")
        else:
            print(f"❌ {table} - 缺失")
            missing_tables.append(table)
    
    if missing_tables:
        print(f"\n⚠️  仍有 {len(missing_tables)} 个表缺失")
        return False
    else:
        print(f"\n🎉 所有必需的表已创建完成！共 {len(final_tables)} 个表")
        return True

if __name__ == "__main__":
    success = check_and_create_tables()
    exit(0 if success else 1)