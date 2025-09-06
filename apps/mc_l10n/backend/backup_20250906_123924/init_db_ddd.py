#!/usr/bin/env python3
"""
基于DDD领域模型的数据库初始化
遵循 docs/mc-domain-model-design.md 的设计
"""
import sqlite3
import os
from datetime import datetime
from pathlib import Path


def init_ddd_database(db_path: str = 'mc_l10n.db'):
    """初始化符合DDD设计的数据库表"""
    
    # 备份旧数据库
    if Path(db_path).exists():
        backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(db_path, backup_path)
        print(f"📦 已备份旧数据库到: {backup_path}")
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔨 开始创建DDD架构的数据库表...")
        
        # ========== 核心聚合：翻译项目 ==========
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS translation_projects (
            project_id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            target_language TEXT NOT NULL DEFAULT 'zh_cn',
            source_language TEXT NOT NULL DEFAULT 'en_us',
            status TEXT DEFAULT 'active',
            settings TEXT,  -- JSON格式的项目设置
            statistics TEXT,  -- JSON格式的统计信息
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("✅ 创建表: translation_projects")
        
        # ========== 模组聚合 ==========
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mods (
            mod_id TEXT PRIMARY KEY,  -- 唯一模组ID
            name TEXT NOT NULL,
            display_name TEXT,  -- 显示名称
            version TEXT,
            minecraft_version TEXT,
            mod_loader TEXT,  -- forge/fabric/quilt/neoforge
            file_path TEXT,
            file_hash TEXT,  -- 文件指纹，用于检测变更
            metadata TEXT,  -- JSON格式的元数据
            scan_result TEXT,  -- JSON格式的扫描结果
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("✅ 创建表: mods")
        
        # ========== 项目-模组关联表 ==========
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_mods (
            project_id TEXT NOT NULL,
            mod_id TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            removed_at TIMESTAMP,  -- 软删除
            is_active BOOLEAN DEFAULT TRUE,
            PRIMARY KEY (project_id, mod_id),
            FOREIGN KEY (project_id) REFERENCES translation_projects(project_id) ON DELETE CASCADE,
            FOREIGN KEY (mod_id) REFERENCES mods(mod_id) ON DELETE CASCADE
        )
        """)
        print("✅ 创建表: project_mods")
        
        # ========== 语言文件实体 ==========
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS language_files (
            file_id TEXT PRIMARY KEY,
            mod_id TEXT NOT NULL,
            language_code TEXT NOT NULL,
            file_path TEXT,  -- 在JAR中的相对路径
            file_format TEXT DEFAULT 'json',  -- json/properties/yaml
            content_hash TEXT,  -- 内容指纹
            entry_count INTEGER DEFAULT 0,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(mod_id, language_code),  -- 每个模组每种语言只有一个文件
            FOREIGN KEY (mod_id) REFERENCES mods(mod_id) ON DELETE CASCADE
        )
        """)
        print("✅ 创建表: language_files")
        
        # ========== 翻译条目实体 ==========
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS translation_entries (
            entry_id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            translation_key TEXT NOT NULL,  -- 翻译键
            key_type TEXT,  -- item/block/gui/tooltip等
            original_value TEXT,  -- 原文
            translated_value TEXT,  -- 译文
            machine_translation TEXT,  -- 机器翻译
            status TEXT DEFAULT 'untranslated',  -- untranslated/translated/reviewed/approved
            translator TEXT,
            reviewer TEXT,
            context TEXT,  -- 上下文信息
            notes TEXT,  -- 备注
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(file_id, translation_key),  -- 每个文件每个键唯一
            FOREIGN KEY (file_id) REFERENCES language_files(file_id) ON DELETE CASCADE
        )
        """)
        print("✅ 创建表: translation_entries")
        
        # ========== 术语库 ==========
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS terminology (
            term_id TEXT PRIMARY KEY,
            project_id TEXT,
            term TEXT NOT NULL,  -- 原文术语
            translation TEXT NOT NULL,  -- 译文
            category TEXT,  -- 分类：item/block/entity/gui等
            description TEXT,
            usage_count INTEGER DEFAULT 0,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES translation_projects(project_id) ON DELETE CASCADE
        )
        """)
        print("✅ 创建表: terminology")
        
        # ========== 翻译记忆库 ==========
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS translation_memory (
            memory_id TEXT PRIMARY KEY,
            source_text TEXT NOT NULL,
            target_text TEXT NOT NULL,
            source_language TEXT DEFAULT 'en_us',
            target_language TEXT DEFAULT 'zh_cn',
            context TEXT,
            mod_id TEXT,
            quality_score REAL DEFAULT 0.0,  -- 质量评分
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mod_id) REFERENCES mods(mod_id) ON DELETE SET NULL
        )
        """)
        print("✅ 创建表: translation_memory")
        
        # ========== 扫描会话（关联到项目） ==========
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_sessions (
            scan_id TEXT PRIMARY KEY,
            project_id TEXT,  -- 可选，扫描可以不关联项目
            scan_type TEXT DEFAULT 'full',  -- full/incremental/single_mod
            target_path TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            progress_percent REAL DEFAULT 0,
            current_item TEXT,  -- 当前正在处理的项目
            statistics TEXT,  -- JSON格式的统计
            error_message TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES translation_projects(project_id) ON DELETE SET NULL
        )
        """)
        print("✅ 创建表: scan_sessions")
        
        # ========== 扫描发现的模组（临时表） ==========
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_discoveries (
            discovery_id TEXT PRIMARY KEY,
            scan_id TEXT NOT NULL,
            mod_id TEXT,
            mod_name TEXT,
            mod_version TEXT,
            file_path TEXT,
            file_size INTEGER,
            language_files_count INTEGER DEFAULT 0,
            total_keys INTEGER DEFAULT 0,
            is_processed BOOLEAN DEFAULT FALSE,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scan_id) REFERENCES scan_sessions(scan_id) ON DELETE CASCADE
        )
        """)
        print("✅ 创建表: scan_discoveries")
        
        # ========== 领域事件表 ==========
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS domain_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            aggregate_id TEXT,
            aggregate_type TEXT,
            event_data TEXT,  -- JSON格式
            occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP
        )
        """)
        print("✅ 创建表: domain_events")
        
        # ========== 创建索引 ==========
        print("\n📐 创建索引以优化查询性能...")
        
        # 模组索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mods_name ON mods(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mods_version ON mods(version)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mods_loader ON mods(mod_loader)")
        
        # 语言文件索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_language_files_mod ON language_files(mod_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_language_files_lang ON language_files(language_code)")
        
        # 翻译条目索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_file ON translation_entries(file_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_key ON translation_entries(translation_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_status ON translation_entries(status)")
        
        # 翻译记忆索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_source ON translation_memory(source_text)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_languages ON translation_memory(source_language, target_language)")
        
        # 扫描索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_project ON scan_sessions(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_status ON scan_sessions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_discoveries_scan ON scan_discoveries(scan_id)")
        
        print("✅ 所有索引创建完成")
        
        # ========== 创建视图 ==========
        print("\n👁️ 创建便捷查询视图...")
        
        # 模组统计视图
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS v_mod_statistics AS
        SELECT 
            m.mod_id,
            m.name as mod_name,
            m.version,
            m.mod_loader,
            COUNT(DISTINCT lf.language_code) as language_count,
            SUM(lf.entry_count) as total_entries,
            MAX(lf.last_modified) as last_updated
        FROM mods m
        LEFT JOIN language_files lf ON m.mod_id = lf.mod_id
        GROUP BY m.mod_id
        """)
        
        # 项目进度视图
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS v_project_progress AS
        SELECT 
            p.project_id,
            p.name as project_name,
            COUNT(DISTINCT pm.mod_id) as mod_count,
            COUNT(DISTINCT te.entry_id) as total_entries,
            SUM(CASE WHEN te.status = 'translated' THEN 1 ELSE 0 END) as translated_count,
            SUM(CASE WHEN te.status = 'approved' THEN 1 ELSE 0 END) as approved_count,
            CASE 
                WHEN COUNT(te.entry_id) > 0 
                THEN CAST(SUM(CASE WHEN te.status IN ('translated', 'approved') THEN 1 ELSE 0 END) AS REAL) / COUNT(te.entry_id) * 100
                ELSE 0
            END as completion_percent
        FROM translation_projects p
        LEFT JOIN project_mods pm ON p.project_id = pm.project_id AND pm.is_active = TRUE
        LEFT JOIN language_files lf ON pm.mod_id = lf.mod_id AND lf.language_code = p.target_language
        LEFT JOIN translation_entries te ON lf.file_id = te.file_id
        GROUP BY p.project_id
        """)
        
        print("✅ 视图创建完成")
        
        # ========== 插入默认数据 ==========
        print("\n📝 插入默认数据...")
        
        # 创建默认项目
        cursor.execute("""
        INSERT OR IGNORE INTO translation_projects (
            project_id, name, description, target_language
        ) VALUES (
            'default-project',
            '默认翻译项目',
            '用于管理所有模组的翻译',
            'zh_cn'
        )
        """)
        
        # 提交更改
        conn.commit()
        print(f"\n✅ DDD数据库初始化成功: {db_path}")
        
        # 显示创建的表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        print(f"\n📊 创建的表 ({len(tables)}个):")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"   - {table[0]}: {count} 条记录")
        
        # 显示视图
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = cursor.fetchall()
        if views:
            print(f"\n👁️ 创建的视图 ({len(views)}个):")
            for view in views:
                print(f"   - {view[0]}")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def migrate_from_old_db(old_db_path: str = 'mc_l10n_unified.db', new_db_path: str = 'mc_l10n.db'):
    """从旧数据库迁移数据到新的DDD架构"""
    
    if not Path(old_db_path).exists():
        print(f"⚠️ 旧数据库不存在: {old_db_path}")
        return
    
    print(f"\n🔄 开始从 {old_db_path} 迁移数据到 {new_db_path}...")
    
    old_conn = sqlite3.connect(old_db_path)
    old_conn.row_factory = sqlite3.Row
    new_conn = sqlite3.connect(new_db_path)
    
    try:
        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()
        
        # 迁移扫描结果中的模组信息
        print("\n📦 迁移模组数据...")
        old_cursor.execute("""
            SELECT DISTINCT mod_id, mod_name, mod_version, file_path
            FROM scan_results
            WHERE mod_id IS NOT NULL
        """)
        
        mods = old_cursor.fetchall()
        migrated_mods = 0
        
        for mod in mods:
            # 插入或更新模组
            new_cursor.execute("""
                INSERT OR REPLACE INTO mods (
                    mod_id, name, display_name, version, file_path, created_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                mod['mod_id'] or f"unknown_{migrated_mods}",
                mod['mod_name'] or mod['mod_id'] or 'Unknown',
                mod['mod_name'],
                mod['mod_version'],
                mod['file_path']
            ))
            
            # 关联到默认项目
            new_cursor.execute("""
                INSERT OR IGNORE INTO project_mods (
                    project_id, mod_id
                ) VALUES ('default-project', ?)
            """, (mod['mod_id'] or f"unknown_{migrated_mods}",))
            
            migrated_mods += 1
        
        print(f"✅ 迁移了 {migrated_mods} 个模组")
        
        # 迁移语言文件信息
        print("\n🌐 迁移语言文件数据...")
        old_cursor.execute("""
            SELECT mod_id, mod_name, language_code, file_path, keys_count
            FROM scan_results
            WHERE mod_id IS NOT NULL AND language_code IS NOT NULL
        """)
        
        lang_files = old_cursor.fetchall()
        migrated_files = 0
        
        for lf in lang_files:
            file_id = f"{lf['mod_id']}_{lf['language_code']}"
            
            new_cursor.execute("""
                INSERT OR REPLACE INTO language_files (
                    file_id, mod_id, language_code, file_path, entry_count
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                file_id,
                lf['mod_id'],
                lf['language_code'] or 'en_us',
                lf['file_path'],
                lf['keys_count'] or 0
            ))
            migrated_files += 1
        
        print(f"✅ 迁移了 {migrated_files} 个语言文件")
        
        # 迁移扫描会话
        print("\n🔍 迁移扫描会话...")
        old_cursor.execute("SELECT * FROM scan_sessions")
        sessions = old_cursor.fetchall()
        
        for session in sessions:
            new_cursor.execute("""
                INSERT OR IGNORE INTO scan_sessions (
                    scan_id, project_id, target_path, status, 
                    progress_percent, started_at, completed_at
                ) VALUES (?, 'default-project', ?, ?, ?, ?, ?)
            """, (
                session['scan_id'],
                session['target_path'] or session['path'],
                session['status'],
                session['progress_percent'],
                session['started_at'],
                session['completed_at']
            ))
        
        print(f"✅ 迁移了 {len(sessions)} 个扫描会话")
        
        new_conn.commit()
        print("\n✅ 数据迁移完成!")
        
    except Exception as e:
        print(f"❌ 数据迁移失败: {e}")
        new_conn.rollback()
        raise
    finally:
        old_conn.close()
        new_conn.close()


if __name__ == "__main__":
    import sys
    
    # 初始化新数据库
    init_ddd_database()
    
    # 如果指定了迁移参数，执行数据迁移
    if len(sys.argv) > 1 and sys.argv[1] == '--migrate':
        migrate_from_old_db()