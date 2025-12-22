#!/usr/bin/env python
"""
V6 数据库表结构定义
定义所有V6架构的数据库表SQL语句
"""

from typing import Dict, List

# 核心域表 core_*

CORE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS core_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CORE_PACKS_TABLE = """
CREATE TABLE IF NOT EXISTS core_packs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    platform TEXT CHECK(platform IN ('modrinth','curseforge','custom')) NOT NULL,
    slug TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    homepage TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CORE_PACK_VERSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS core_pack_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    pack_uid TEXT NOT NULL REFERENCES core_packs(uid),
    mc_version TEXT NOT NULL,
    loader TEXT CHECK(loader IN ('forge','neoforge','fabric','quilt','multi','unknown')) NOT NULL,
    manifest_json TEXT CHECK(json_valid(manifest_json)),
    manifest_hash_b3 TEXT NOT NULL,
    manifest_hash_md5 TEXT,
    created_at TEXT NOT NULL
)
"""

CORE_PACK_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS core_pack_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_version_uid TEXT NOT NULL REFERENCES core_pack_versions(uid),
    item_type TEXT CHECK(item_type IN ('mod','resourcepack','datapack','override')) NOT NULL,
    source_platform TEXT CHECK(source_platform IN ('modrinth','curseforge','url','local')) NOT NULL,
    identity TEXT NOT NULL,
    constraints TEXT CHECK(json_valid(constraints)),
    position INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(pack_version_uid, item_type, identity)
)
"""

CORE_PACK_INSTALLATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS core_pack_installations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    pack_version_uid TEXT NOT NULL REFERENCES core_pack_versions(uid),
    root_path TEXT,
    launcher TEXT CHECK(launcher IN ('curseforge','modrinth','vanilla','custom')),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CORE_MODS_TABLE = """
CREATE TABLE IF NOT EXISTS core_mods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    modid TEXT UNIQUE,
    slug TEXT,
    name TEXT NOT NULL,
    homepage TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CORE_MOD_VERSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS core_mod_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    mod_uid TEXT NOT NULL REFERENCES core_mods(uid),
    loader TEXT NOT NULL,
    mc_version TEXT NOT NULL,
    version TEXT NOT NULL,
    meta_json TEXT CHECK(json_valid(meta_json)),
    source TEXT,
    discovered_at TEXT NOT NULL,
    UNIQUE(mod_uid, loader, mc_version, version)
)
"""

CORE_LANGUAGE_FILES_TABLE = """
CREATE TABLE IF NOT EXISTS core_language_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    carrier_type TEXT CHECK(carrier_type IN ('mod','resource_pack','data_pack','override')) NOT NULL,
    carrier_uid TEXT NOT NULL,
    locale TEXT NOT NULL,
    rel_path TEXT NOT NULL,
    format TEXT CHECK(format IN ('json','lang','properties')) NOT NULL,
    size INTEGER DEFAULT 0,
    discovered_at TEXT NOT NULL,
    UNIQUE(carrier_uid, locale, rel_path)
)
"""

CORE_TRANSLATION_ENTRIES_TABLE = """
CREATE TABLE IF NOT EXISTS core_translation_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    language_file_uid TEXT NOT NULL REFERENCES core_language_files(uid),
    key TEXT NOT NULL,
    src_text TEXT NOT NULL,
    dst_text TEXT DEFAULT '',
    status TEXT CHECK(status IN ('new','mt','reviewed','locked','rejected','conflict')) DEFAULT 'new',
    qa_flags TEXT CHECK(json_valid(qa_flags)) DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL,
    uida_keys_b64 TEXT,
    uida_hash TEXT,
    UNIQUE(language_file_uid, key)
)
"""

# 运维和同步表 ops_*

OPS_WORK_QUEUE_TABLE = """
CREATE TABLE IF NOT EXISTS ops_work_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT CHECK(type IN ('import_delta_block','export_stream','tm_index','qa_run','merge_resolve','sync_out','sync_in')) NOT NULL,
    payload_json TEXT CHECK(json_valid(payload_json)) NOT NULL,
    state TEXT CHECK(state IN ('pending','leased','done','err','dead')) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    not_before TEXT,
    dedupe_key TEXT UNIQUE,
    attempt INTEGER DEFAULT 0,
    last_error TEXT,
    lease_owner TEXT,
    lease_expires_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

OPS_OUTBOX_JOURNAL_TABLE = """
CREATE TABLE IF NOT EXISTS ops_outbox_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_uid TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    base_version TEXT,
    diff_json TEXT CHECK(json_valid(diff_json)) NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL,
    state TEXT CHECK(state IN ('pending','sent','acked','err')) DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

OPS_SYNC_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS ops_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT CHECK(direction IN ('up','down')) NOT NULL,
    endpoint TEXT NOT NULL,
    request_meta TEXT CHECK(json_valid(request_meta)),
    response_meta TEXT CHECK(json_valid(response_meta)),
    result TEXT CHECK(result IN ('success','fail','partial')) NOT NULL,
    idempotency_key TEXT,
    created_at TEXT NOT NULL
)
"""

OPS_CAS_OBJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS ops_cas_objects (
    cid TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    algo TEXT CHECK(algo IN ('zstd','gzip','none')) DEFAULT 'zstd',
    dict_id TEXT,
    ref_count INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
)
"""

# 配置和缓存表 cfg_*/cache_*

CFG_LOCAL_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS cfg_local_settings (
    key TEXT PRIMARY KEY,
    value_json TEXT CHECK(json_valid(value_json)) NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CFG_FILE_WATCH_TABLE = """
CREATE TABLE IF NOT EXISTS cfg_file_watch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_path TEXT NOT NULL,
    globs TEXT CHECK(json_valid(globs)) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL
)
"""

CACHE_SCAN_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS cache_scan_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_path TEXT NOT NULL,
    scan_hash TEXT NOT NULL,
    result_json TEXT CHECK(json_valid(result_json)) NOT NULL,
    valid_until TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(scan_path, scan_hash)
)
"""


# 表创建顺序列表（考虑外键依赖）
TABLES_CREATE_ORDER = [
    # 核心域表（无依赖的先创建）
    ("core_projects", CORE_PROJECTS_TABLE),
    ("core_packs", CORE_PACKS_TABLE),
    ("core_mods", CORE_MODS_TABLE),
    
    # 依赖核心表的表
    ("core_pack_versions", CORE_PACK_VERSIONS_TABLE),
    ("core_mod_versions", CORE_MOD_VERSIONS_TABLE),
    
    # 依赖版本表的表
    ("core_pack_items", CORE_PACK_ITEMS_TABLE),
    ("core_pack_installations", CORE_PACK_INSTALLATIONS_TABLE),
    ("core_language_files", CORE_LANGUAGE_FILES_TABLE),
    
    # 依赖语言文件表的表
    ("core_translation_entries", CORE_TRANSLATION_ENTRIES_TABLE),
    
    # 运维表（相对独立）
    ("ops_work_queue", OPS_WORK_QUEUE_TABLE),
    ("ops_outbox_journal", OPS_OUTBOX_JOURNAL_TABLE),
    ("ops_sync_log", OPS_SYNC_LOG_TABLE),
    ("ops_cas_objects", OPS_CAS_OBJECTS_TABLE),
    
    # 配置和缓存表（无依赖）
    ("cfg_local_settings", CFG_LOCAL_SETTINGS_TABLE),
    ("cfg_file_watch", CFG_FILE_WATCH_TABLE),
    ("cache_scan_results", CACHE_SCAN_RESULTS_TABLE),
]


def get_all_tables() -> Dict[str, str]:
    """获取所有表定义"""
    return dict(TABLES_CREATE_ORDER)


def get_table_create_order() -> List[tuple]:
    """获取表创建顺序"""
    return TABLES_CREATE_ORDER


def get_core_tables() -> Dict[str, str]:
    """获取核心域表"""
    return {
        name: sql for name, sql in TABLES_CREATE_ORDER 
        if name.startswith('core_')
    }


def get_ops_tables() -> Dict[str, str]:
    """获取运维表"""
    return {
        name: sql for name, sql in TABLES_CREATE_ORDER 
        if name.startswith('ops_')
    }


def get_cfg_cache_tables() -> Dict[str, str]:
    """获取配置和缓存表"""
    return {
        name: sql for name, sql in TABLES_CREATE_ORDER 
        if name.startswith(('cfg_', 'cache_'))
    }


def create_tables(conn, table_subset=None):
    """在给定连接上创建表
    
    Args:
        conn: 数据库连接
        table_subset: 要创建的表名列表，None表示创建所有表
    """
    tables_to_create = TABLES_CREATE_ORDER
    if table_subset:
        tables_to_create = [
            (name, sql) for name, sql in TABLES_CREATE_ORDER 
            if name in table_subset
        ]
    
    for table_name, table_sql in tables_to_create:
        try:
            conn.execute(table_sql)
            print(f"✓ 创建表: {table_name}")
        except Exception as e:
            print(f"✗ 创建表失败 {table_name}: {e}")
            raise


if __name__ == "__main__":
    # 测试表定义
    import sqlite3
    
    # 创建内存数据库测试
    conn = sqlite3.connect(":memory:")
    
    try:
        create_tables(conn)
        print(f"\n✓ 成功创建 {len(TABLES_CREATE_ORDER)} 个表")
        
        # 验证表存在
        tables = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """).fetchall()
        
        print("\n已创建的表:")
        for table in tables:
            print(f"  - {table[0]}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
    finally:
        conn.close()