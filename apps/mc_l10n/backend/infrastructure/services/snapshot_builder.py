"""
快照构建引擎
实现快速目录遍历、文件指纹生成和快照存储功能，支持中断恢复
"""

import json
import hashlib
import sqlite3
import structlog
from pathlib import Path
from typing import Optional, Dict, List, Any, Set, Tuple
from datetime import datetime
import os
import zipfile
import uuid

logger = structlog.get_logger(__name__)


class FileSnapshot:
    """文件快照信息"""
    
    def __init__(self, path: str, size: int, mtime: float, 
                 is_jar: bool = False, jar_entries: Optional[List[str]] = None):
        self.path = path
        self.size = size
        self.mtime = mtime
        self.is_jar = is_jar
        self.jar_entries = jar_entries or []
        self._fingerprint = None
    
    @property
    def basic_fingerprint(self) -> str:
        """基础指纹：size+mtime"""
        return f"{self.size}:{int(self.mtime)}"
    
    @property  
    def jar_fingerprint(self) -> str:
        """JAR指纹：central directory entries"""
        if not self.is_jar or not self.jar_entries:
            return ""
        return hashlib.md5('|'.join(sorted(self.jar_entries)).encode()).hexdigest()[:16]
    
    @property
    def content_hash(self) -> str:
        """内容哈希：BLAKE3（延迟计算）"""
        if self._fingerprint is None:
            self._fingerprint = self._calculate_blake3_hash()
        return self._fingerprint
    
    def _calculate_blake3_hash(self) -> str:
        """计算BLAKE3哈希"""
        try:
            import blake3
            hasher = blake3.blake3()
            
            if self.is_jar:
                # JAR文件使用central directory哈希
                hasher.update(self.jar_fingerprint.encode())
            else:
                # 普通文件读取内容计算哈希
                with open(self.path, 'rb') as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
            
            return hasher.hexdigest()[:32]  # 128位截断
        except ImportError:
            # 降级到SHA256
            hasher = hashlib.sha256()
            if self.is_jar:
                hasher.update(self.jar_fingerprint.encode())
            else:
                with open(self.path, 'rb') as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
            return hasher.hexdigest()[:32]
        except Exception as e:
            logger.warning(f"无法计算文件哈希: {self.path}, {e}")
            return f"error:{self.basic_fingerprint}"
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "path": self.path,
            "size": self.size,
            "mtime": self.mtime,
            "is_jar": self.is_jar,
            "jar_entries": self.jar_entries,
            "fingerprint": self.basic_fingerprint,
            "jar_fingerprint": self.jar_fingerprint,
            "content_hash": self.content_hash if self._fingerprint else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileSnapshot':
        """从字典反序列化"""
        snapshot = cls(
            path=data["path"],
            size=data["size"],
            mtime=data["mtime"],
            is_jar=data.get("is_jar", False),
            jar_entries=data.get("jar_entries", [])
        )
        snapshot._fingerprint = data.get("content_hash")
        return snapshot


class SnapshotBuilder:
    """快照构建引擎"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.supported_extensions = {
            '.jar', '.zip', '.json', '.lang', '.properties', 
            '.toml', '.yml', '.yaml', '.txt', '.md'
        }
        self.jar_lang_patterns = {
            'assets/*/lang/*.json',
            'assets/*/lang/*.lang', 
            'data/*/lang/*.json',
            'lang/*.properties'
        }
    
    def build_snapshot(self, root_path: str, session_id: str, 
                      pack_uid: Optional[str] = None,
                      pack_version_uid: Optional[str] = None,
                      resume_snapshot_id: Optional[str] = None) -> Tuple[str, int]:
        """构建目录快照
        
        Args:
            root_path: 扫描根目录
            session_id: 会话ID
            pack_uid: 包ID（可选）
            pack_version_uid: 包版本ID（可选）
            resume_snapshot_id: 恢复的快照ID（用于中断续扫）
            
        Returns:
            (snapshot_id, file_count)
        """
        root_path = Path(root_path).resolve()
        if not root_path.exists():
            raise ValueError(f"路径不存在: {root_path}")
        
        snapshot_id = resume_snapshot_id or f"snap_{uuid.uuid4().hex[:16]}"
        
        logger.info(f"🔍 开始构建快照", 
                   snapshot_id=snapshot_id, root_path=str(root_path), 
                   session_id=session_id)
        
        # 快速遍历文件系统
        files_snapshot = self._scan_directory(root_path)
        
        # 生成快照哈希
        snapshot_hash = self._calculate_snapshot_hash(files_snapshot)
        
        # 保存到数据库
        self._save_snapshot(
            snapshot_id=snapshot_id,
            session_id=session_id,
            pack_uid=pack_uid,
            pack_version_uid=pack_version_uid,
            root_path=str(root_path),
            files_snapshot=files_snapshot,
            snapshot_hash=snapshot_hash
        )
        
        logger.info(f"✅ 快照构建完成", 
                   snapshot_id=snapshot_id, file_count=len(files_snapshot),
                   snapshot_hash=snapshot_hash)
        
        return snapshot_id, len(files_snapshot)
    
    def _scan_directory(self, root_path: Path) -> Dict[str, FileSnapshot]:
        """快速扫描目录结构（≤2秒）"""
        files_snapshot = {}
        
        try:
            # 使用os.walk进行快速遍历
            for root, dirs, files in os.walk(root_path):
                # 跳过隐藏目录和系统目录
                dirs[:] = [d for d in dirs if not d.startswith('.') 
                          and d not in {'__pycache__', 'node_modules'}]
                
                for file in files:
                    if file.startswith('.'):
                        continue
                        
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(root_path)
                    
                    # 只关注相关文件类型
                    if file_path.suffix.lower() not in self.supported_extensions:
                        continue
                    
                    try:
                        stat = file_path.stat()
                        is_jar = file_path.suffix.lower() in {'.jar', '.zip'}
                        jar_entries = []
                        
                        # 对JAR文件快速读取central directory
                        if is_jar and stat.st_size < 50 * 1024 * 1024:  # 限制50MB以下
                            jar_entries = self._get_jar_entries(file_path)
                        
                        snapshot = FileSnapshot(
                            path=str(rel_path),
                            size=stat.st_size,
                            mtime=stat.st_mtime,
                            is_jar=is_jar,
                            jar_entries=jar_entries
                        )
                        
                        files_snapshot[str(rel_path)] = snapshot
                        
                    except (OSError, PermissionError) as e:
                        logger.warning(f"跳过无法访问的文件: {file_path}, {e}")
                        
        except Exception as e:
            logger.error(f"目录扫描失败: {root_path}, {e}")
            raise
        
        return files_snapshot
    
    def _get_jar_entries(self, jar_path: Path) -> List[str]:
        """快速获取JAR文件的central directory entries"""
        entries = []
        try:
            with zipfile.ZipFile(jar_path, 'r') as zf:
                # 只获取语言文件相关的条目
                for entry in zf.namelist():
                    if any(self._match_pattern(entry, pattern) 
                          for pattern in self.jar_lang_patterns):
                        entries.append(entry)
                        
                    # 限制条目数量，避免过大的JAR文件
                    if len(entries) > 1000:
                        break
                        
        except (zipfile.BadZipFile, PermissionError, OSError):
            # 损坏的ZIP文件或权限问题，返回空列表
            pass
            
        return entries
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """简单的glob模式匹配"""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)
    
    def _calculate_snapshot_hash(self, files_snapshot: Dict[str, FileSnapshot]) -> str:
        """计算快照整体哈希"""
        # 按路径排序确保一致性
        sorted_files = sorted(files_snapshot.items())
        
        hasher = hashlib.sha256()
        for path, snapshot in sorted_files:
            hasher.update(f"{path}:{snapshot.basic_fingerprint}".encode())
            
        return hasher.hexdigest()[:16]
    
    def _save_snapshot(self, snapshot_id: str, session_id: str,
                      pack_uid: Optional[str], pack_version_uid: Optional[str],
                      root_path: str, files_snapshot: Dict[str, FileSnapshot],
                      snapshot_hash: str) -> None:
        """保存快照到数据库"""
        
        # 序列化文件快照
        files_json = json.dumps({
            path: snapshot.to_dict() 
            for path, snapshot in files_snapshot.items()
        }, ensure_ascii=False, separators=(',', ':'))
        
        # 统计信息
        file_count = len(files_snapshot)
        total_size = sum(s.size for s in files_snapshot.values())
        
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cache_scan_snapshots 
                (snapshot_id, session_id, pack_uid, pack_version_uid, root_path, 
                 files_json, snapshot_hash, file_count, total_size_bytes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id, session_id, pack_uid, pack_version_uid, root_path,
                files_json, snapshot_hash, file_count, total_size,
                datetime.now().isoformat()
            ))
            conn.commit()
            
        finally:
            conn.close()
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """获取快照数据"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute("""
                SELECT * FROM cache_scan_snapshots 
                WHERE snapshot_id = ?
            """, (snapshot_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # 解析文件快照
            files_data = json.loads(row['files_json'])
            files_snapshot = {
                path: FileSnapshot.from_dict(data)
                for path, data in files_data.items()
            }
            
            return {
                'snapshot_id': row['snapshot_id'],
                'session_id': row['session_id'],
                'pack_uid': row['pack_uid'],
                'pack_version_uid': row['pack_version_uid'],
                'root_path': row['root_path'],
                'files': files_snapshot,
                'snapshot_hash': row['snapshot_hash'],
                'file_count': row['file_count'],
                'total_size_bytes': row['total_size_bytes'],
                'created_at': row['created_at']
            }
            
        finally:
            conn.close()
    
    def list_snapshots(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的快照"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute("""
                SELECT snapshot_id, session_id, pack_uid, root_path,
                       snapshot_hash, file_count, total_size_bytes, created_at
                FROM cache_scan_snapshots 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    def cleanup_old_snapshots(self, keep_count: int = 10) -> int:
        """清理旧快照，保留最新的N个"""
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            # 获取要删除的快照ID
            cursor = conn.execute("""
                SELECT snapshot_id FROM cache_scan_snapshots 
                ORDER BY created_at DESC 
                LIMIT -1 OFFSET ?
            """, (keep_count,))
            
            to_delete = [row[0] for row in cursor.fetchall()]
            
            if to_delete:
                placeholders = ','.join('?' * len(to_delete))
                conn.execute(f"""
                    DELETE FROM cache_scan_snapshots 
                    WHERE snapshot_id IN ({placeholders})
                """, to_delete)
                
                conn.commit()
                logger.info(f"清理了 {len(to_delete)} 个旧快照")
            
            return len(to_delete)
            
        finally:
            conn.close()