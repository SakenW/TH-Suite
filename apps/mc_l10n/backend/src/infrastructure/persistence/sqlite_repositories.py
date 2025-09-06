"""
SQLite Repository实现
实现领域层定义的Repository接口
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import logging

from domain.models.mod import Mod, ModId, ModMetadata, ModVersion
from domain.models.translation_project import TranslationProject
from domain.repositories import (
    ModRepository,
    TranslationProjectRepository,
    TranslationRepository,
    EventRepository,
    ScanResultRepository
)

logger = logging.getLogger(__name__)


class SqliteModRepository(ModRepository):
    """SQLite Mod仓储实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mods (
                    mod_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    authors TEXT,
                    description TEXT,
                    minecraft_version TEXT,
                    loader_type TEXT,
                    file_path TEXT NOT NULL,
                    scan_status TEXT,
                    last_scanned TIMESTAMP,
                    content_hash TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mods_status ON mods(scan_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mods_file_path ON mods(file_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mods_content_hash ON mods(content_hash)")
    
    def find_by_id(self, mod_id: ModId) -> Optional[Mod]:
        """根据ID查找Mod"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM mods WHERE mod_id = ?",
                (str(mod_id),)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_mod(row)
            return None
    
    def find_by_file_path(self, file_path: str) -> Optional[Mod]:
        """根据文件路径查找Mod"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM mods WHERE file_path = ?",
                (file_path,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_mod(row)
            return None
    
    def find_by_content_hash(self, content_hash: str) -> Optional[Mod]:
        """根据内容哈希查找Mod"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM mods WHERE content_hash = ?",
                (content_hash,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_mod(row)
            return None
    
    def find_all(self, limit: int = 100, offset: int = 0) -> List[Mod]:
        """查找所有Mod"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM mods LIMIT ? OFFSET ?",
                (limit, offset)
            )
            
            return [self._row_to_mod(row) for row in cursor.fetchall()]
    
    def find_by_status(self, status: str) -> List[Mod]:
        """根据状态查找Mod"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM mods WHERE scan_status = ?",
                (status,)
            )
            
            return [self._row_to_mod(row) for row in cursor.fetchall()]
    
    def find_needs_rescan(self) -> List[Mod]:
        """查找需要重新扫描的Mod"""
        # 这里简化实现，实际应该比较文件修改时间
        return self.find_by_status("pending")
    
    def save(self, mod: Mod) -> Mod:
        """保存Mod"""
        with sqlite3.connect(self.db_path) as conn:
            metadata_json = json.dumps({
                'authors': mod.metadata.authors,
                'dependencies': mod.metadata.dependencies,
                'tags': list(mod.metadata.tags)
            })
            
            conn.execute("""
                INSERT INTO mods (
                    mod_id, name, version, authors, description,
                    minecraft_version, loader_type, file_path,
                    scan_status, last_scanned, content_hash, metadata,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(mod.mod_id),
                mod.metadata.name,
                str(mod.metadata.version),
                json.dumps(mod.metadata.authors),
                mod.metadata.description,
                mod.metadata.minecraft_version,
                mod.metadata.loader_type,
                mod.file_path,
                mod.scan_status,
                mod.last_scanned,
                mod.content_hash,
                metadata_json,
                mod.created_at,
                mod.updated_at
            ))
            
            conn.commit()
            return mod
    
    def update(self, mod: Mod) -> Mod:
        """更新Mod"""
        with sqlite3.connect(self.db_path) as conn:
            metadata_json = json.dumps({
                'authors': mod.metadata.authors,
                'dependencies': mod.metadata.dependencies,
                'tags': list(mod.metadata.tags)
            })
            
            conn.execute("""
                UPDATE mods SET
                    name = ?, version = ?, authors = ?, description = ?,
                    minecraft_version = ?, loader_type = ?, file_path = ?,
                    scan_status = ?, last_scanned = ?, content_hash = ?,
                    metadata = ?, updated_at = ?
                WHERE mod_id = ?
            """, (
                mod.metadata.name,
                str(mod.metadata.version),
                json.dumps(mod.metadata.authors),
                mod.metadata.description,
                mod.metadata.minecraft_version,
                mod.metadata.loader_type,
                mod.file_path,
                mod.scan_status,
                mod.last_scanned,
                mod.content_hash,
                metadata_json,
                mod.updated_at,
                str(mod.mod_id)
            ))
            
            conn.commit()
            return mod
    
    def delete(self, mod_id: ModId) -> bool:
        """删除Mod"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM mods WHERE mod_id = ?",
                (str(mod_id),)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def exists(self, mod_id: ModId) -> bool:
        """检查Mod是否存在"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM mods WHERE mod_id = ?",
                (str(mod_id),)
            )
            return cursor.fetchone()[0] > 0
    
    def count(self) -> int:
        """统计Mod数量"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM mods")
            return cursor.fetchone()[0]
    
    def count_by_status(self, status: str) -> int:
        """统计指定状态的Mod数量"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM mods WHERE scan_status = ?",
                (status,)
            )
            return cursor.fetchone()[0]
    
    def search(self, query: str) -> List[Mod]:
        """搜索Mod"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM mods 
                WHERE name LIKE ? OR mod_id LIKE ? OR description LIKE ?
                LIMIT 100
            """, (f"%{query}%", f"%{query}%", f"%{query}%"))
            
            return [self._row_to_mod(row) for row in cursor.fetchall()]
    
    def _row_to_mod(self, row: sqlite3.Row) -> Mod:
        """将数据库行转换为Mod对象"""
        # 解析元数据
        metadata_json = json.loads(row['metadata'] or '{}')
        
        # 创建ModMetadata
        metadata = ModMetadata(
            name=row['name'],
            version=ModVersion.from_string(row['version']),
            authors=json.loads(row['authors'] or '[]'),
            description=row['description'],
            minecraft_version=row['minecraft_version'],
            loader_type=row['loader_type'],
            dependencies=metadata_json.get('dependencies', []),
            tags=set(metadata_json.get('tags', []))
        )
        
        # 创建Mod
        mod = Mod(
            mod_id=ModId(row['mod_id']),
            metadata=metadata,
            file_path=row['file_path']
        )
        
        # 设置其他属性
        mod.scan_status = row['scan_status']
        mod.last_scanned = datetime.fromisoformat(row['last_scanned']) if row['last_scanned'] else None
        mod.content_hash = row['content_hash']
        mod.created_at = datetime.fromisoformat(row['created_at'])
        mod.updated_at = datetime.fromisoformat(row['updated_at'])
        
        return mod


class SqliteTranslationProjectRepository(TranslationProjectRepository):
    """SQLite翻译项目仓储实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    target_languages TEXT,
                    mod_ids TEXT,
                    settings TEXT,
                    contributors TEXT,
                    tasks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def find_by_id(self, project_id: str) -> Optional[TranslationProject]:
        """根据ID查找项目"""
        # 简化实现
        return None
    
    def find_all(self, limit: int = 100, offset: int = 0) -> List[TranslationProject]:
        """查找所有项目"""
        return []
    
    def find_by_status(self, status: str) -> List[TranslationProject]:
        """根据状态查找项目"""
        return []
    
    def find_by_contributor(self, user_id: str) -> List[TranslationProject]:
        """查找用户参与的项目"""
        return []
    
    def find_containing_mod(self, mod_id: ModId) -> List[TranslationProject]:
        """查找包含指定Mod的项目"""
        return []
    
    def save(self, project: TranslationProject) -> TranslationProject:
        """保存项目"""
        return project
    
    def update(self, project: TranslationProject) -> TranslationProject:
        """更新项目"""
        return project
    
    def delete(self, project_id: str) -> bool:
        """删除项目"""
        return False
    
    def exists(self, project_id: str) -> bool:
        """检查项目是否存在"""
        return False


class SqliteTranslationRepository(TranslationRepository):
    """SQLite翻译仓储实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mod_id TEXT NOT NULL,
                    language TEXT NOT NULL,
                    key TEXT NOT NULL,
                    original TEXT,
                    translated TEXT,
                    status TEXT DEFAULT 'pending',
                    translator TEXT,
                    reviewed_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(mod_id, language, key)
                )
            """)
    
    def find_by_mod_and_language(self, mod_id: ModId, language: str) -> Dict[str, str]:
        """查找指定Mod和语言的翻译"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT key, translated FROM translations
                WHERE mod_id = ? AND language = ?
            """, (str(mod_id), language))
            
            return {row[0]: row[1] for row in cursor.fetchall()}
    
    def find_by_key(self, key: str, language: str) -> List[Dict[str, Any]]:
        """根据键查找翻译"""
        return []
    
    def save_translations(self, mod_id: ModId, language: str, translations: Dict[str, str]) -> bool:
        """保存翻译"""
        with sqlite3.connect(self.db_path) as conn:
            for key, value in translations.items():
                conn.execute("""
                    INSERT OR REPLACE INTO translations
                    (mod_id, language, key, translated)
                    VALUES (?, ?, ?, ?)
                """, (str(mod_id), language, key, value))
            conn.commit()
            return True
    
    def update_translation(self, mod_id: ModId, language: str, key: str, value: str) -> bool:
        """更新单个翻译"""
        return False
    
    def delete_translations(self, mod_id: ModId, language: str) -> bool:
        """删除翻译"""
        return False
    
    def get_translation_stats(self, mod_id: ModId) -> Dict[str, int]:
        """获取翻译统计"""
        return {}
    
    def get_untranslated_keys(self, mod_id: ModId, language: str) -> List[str]:
        """获取未翻译的键"""
        return []
    
    def search_translations(self, query: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """搜索翻译"""
        return []


class SqliteEventRepository(EventRepository):
    """SQLite事件仓储实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def save_event(self, event: Any) -> bool:
        """保存事件"""
        return True
    
    def find_by_aggregate_id(self, aggregate_id: str) -> List[Any]:
        """根据聚合ID查找事件"""
        return []
    
    def find_by_type(self, event_type: str, limit: int = 100) -> List[Any]:
        """根据类型查找事件"""
        return []
    
    def find_between(self, start: datetime, end: datetime) -> List[Any]:
        """查找时间范围内的事件"""
        return []
    
    def get_event_stream(self, aggregate_id: str, from_version: int = 0) -> List[Any]:
        """获取事件流"""
        return []


class SqliteScanResultRepository(ScanResultRepository):
    """SQLite扫描结果仓储实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def save_scan_result(self, mod_id: ModId, result: Dict[str, Any]) -> bool:
        """保存扫描结果"""
        return True
    
    def find_latest_scan(self, mod_id: ModId) -> Optional[Dict[str, Any]]:
        """查找最新的扫描结果"""
        return None
    
    def find_scan_history(self, mod_id: ModId, limit: int = 10) -> List[Dict[str, Any]]:
        """查找扫描历史"""
        return []
    
    def delete_old_scans(self, before: datetime) -> int:
        """删除旧的扫描结果"""
        return 0