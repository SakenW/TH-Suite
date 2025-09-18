"""
差异对比引擎
对比两个快照并生成增量变化，识别文件的添加/修改/移动/删除
"""

import json
import hashlib
import sqlite3
import structlog
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime
import uuid

from .snapshot_builder import FileSnapshot

logger = structlog.get_logger(__name__)


class DeltaChange:
    """单个文件变化"""
    
    def __init__(self, change_type: str, path: str, 
                 old_snapshot: Optional[FileSnapshot] = None,
                 new_snapshot: Optional[FileSnapshot] = None,
                 old_path: Optional[str] = None):
        self.change_type = change_type  # added, modified, moved, removed
        self.path = path
        self.old_snapshot = old_snapshot
        self.new_snapshot = new_snapshot
        self.old_path = old_path  # 仅用于moved类型
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        result = {
            "change_type": self.change_type,
            "path": self.path
        }
        
        if self.old_snapshot:
            result["old_snapshot"] = self.old_snapshot.to_dict()
        
        if self.new_snapshot:
            result["new_snapshot"] = self.new_snapshot.to_dict()
            
        if self.old_path:
            result["old_path"] = self.old_path
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeltaChange':
        """从字典反序列化"""
        old_snapshot = None
        if "old_snapshot" in data:
            old_snapshot = FileSnapshot.from_dict(data["old_snapshot"])
            
        new_snapshot = None
        if "new_snapshot" in data:
            new_snapshot = FileSnapshot.from_dict(data["new_snapshot"])
        
        return cls(
            change_type=data["change_type"],
            path=data["path"],
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
            old_path=data.get("old_path")
        )


class DiffEngine:
    """差异对比引擎"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
    
    def compare_snapshots(self, current_snapshot_id: str, base_snapshot_id: str,
                         session_id: str) -> Tuple[str, Dict[str, List[DeltaChange]]]:
        """对比两个快照生成差异
        
        Args:
            current_snapshot_id: 当前快照ID
            base_snapshot_id: 基准快照ID
            session_id: 会话ID
            
        Returns:
            (delta_id, changes_dict)
        """
        logger.info(f"🔍 开始对比快照", 
                   current=current_snapshot_id, 
                   base=base_snapshot_id,
                   session_id=session_id)
        
        # 加载快照数据
        current_snapshot = self._load_snapshot(current_snapshot_id)
        base_snapshot = self._load_snapshot(base_snapshot_id)
        
        if not current_snapshot or not base_snapshot:
            raise ValueError("快照不存在")
        
        # 执行差异对比
        changes = self._calculate_diff(
            current_snapshot['files'], 
            base_snapshot['files']
        )
        
        # 生成delta哈希
        delta_hash = self._calculate_delta_hash(changes)
        
        # 保存差异到数据库
        delta_id = f"delta_{uuid.uuid4().hex[:16]}"
        self._save_delta(
            delta_id=delta_id,
            snapshot_id=current_snapshot_id,
            session_id=session_id,
            base_snapshot_id=base_snapshot_id,
            changes=changes,
            delta_hash=delta_hash
        )
        
        logger.info(f"✅ 快照对比完成", 
                   delta_id=delta_id,
                   total_changes=sum(len(changes_list) for changes_list in changes.values()),
                   delta_hash=delta_hash)
        
        return delta_id, changes
    
    def _load_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """加载快照数据"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute("""
                SELECT files_json FROM cache_scan_snapshots 
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
            
            return {'files': files_snapshot}
            
        finally:
            conn.close()
    
    def _calculate_diff(self, current_files: Dict[str, FileSnapshot], 
                       base_files: Dict[str, FileSnapshot]) -> Dict[str, List[DeltaChange]]:
        """计算两个文件集合的差异"""
        
        changes = {
            'added': [],
            'modified': [],
            'moved': [],
            'removed': []
        }
        
        current_paths = set(current_files.keys())
        base_paths = set(base_files.keys())
        
        # 1. 找出新增和删除的文件
        added_paths = current_paths - base_paths
        removed_paths = base_paths - current_paths
        
        # 2. 找出共同存在的文件
        common_paths = current_paths & base_paths
        
        # 3. 构建内容哈希映射，用于检测移动/重命名
        base_hash_to_path = {}
        current_hash_to_path = {}
        
        for path, snapshot in base_files.items():
            content_hash = snapshot.content_hash
            if content_hash not in base_hash_to_path:
                base_hash_to_path[content_hash] = []
            base_hash_to_path[content_hash].append(path)
            
        for path, snapshot in current_files.items():
            content_hash = snapshot.content_hash
            if content_hash not in current_hash_to_path:
                current_hash_to_path[content_hash] = []
            current_hash_to_path[content_hash].append(path)
        
        # 4. 检测移动/重命名（内容哈希相同但路径不同）
        moved_pairs = []
        remaining_added = set(added_paths)
        remaining_removed = set(removed_paths)
        
        for removed_path in list(remaining_removed):
            if removed_path not in base_files:
                continue
                
            removed_hash = base_files[removed_path].content_hash
            
            # 查找相同哈希的新增文件
            if removed_hash in current_hash_to_path:
                for added_path in current_hash_to_path[removed_hash]:
                    if added_path in remaining_added:
                        # 发现移动：同样的内容哈希
                        moved_pairs.append((removed_path, added_path))
                        remaining_added.discard(added_path)
                        remaining_removed.discard(removed_path)
                        break
        
        # 5. 生成变化记录
        
        # 移动的文件
        for old_path, new_path in moved_pairs:
            changes['moved'].append(DeltaChange(
                change_type='moved',
                path=new_path,
                old_snapshot=base_files[old_path],
                new_snapshot=current_files[new_path],
                old_path=old_path
            ))
        
        # 新增的文件（排除已识别为移动的）
        for path in remaining_added:
            changes['added'].append(DeltaChange(
                change_type='added',
                path=path,
                new_snapshot=current_files[path]
            ))
        
        # 删除的文件（排除已识别为移动的）
        for path in remaining_removed:
            changes['removed'].append(DeltaChange(
                change_type='removed',
                path=path,
                old_snapshot=base_files[path]
            ))
        
        # 修改的文件（路径相同但内容不同）
        for path in common_paths:
            current_snapshot = current_files[path]
            base_snapshot = base_files[path]
            
            # 比较文件指纹
            if self._has_content_changed(current_snapshot, base_snapshot):
                changes['modified'].append(DeltaChange(
                    change_type='modified',
                    path=path,
                    old_snapshot=base_snapshot,
                    new_snapshot=current_snapshot
                ))
        
        return changes
    
    def _has_content_changed(self, current: FileSnapshot, base: FileSnapshot) -> bool:
        """检查文件内容是否发生变化"""
        # 首先比较基础指纹（size+mtime）
        if current.basic_fingerprint != base.basic_fingerprint:
            return True
        
        # 对于JAR文件，比较central directory
        if current.is_jar and base.is_jar:
            if current.jar_fingerprint != base.jar_fingerprint:
                return True
        
        # 最终比较内容哈希（延迟计算）
        return current.content_hash != base.content_hash
    
    def _calculate_delta_hash(self, changes: Dict[str, List[DeltaChange]]) -> str:
        """计算差异的哈希值"""
        hasher = hashlib.sha256()
        
        # 按类型和路径排序确保一致性
        for change_type in sorted(changes.keys()):
            change_list = sorted(changes[change_type], key=lambda c: c.path)
            for change in change_list:
                hasher.update(f"{change_type}:{change.path}".encode())
                if change.old_path:
                    hasher.update(f":old_path={change.old_path}".encode())
        
        return hasher.hexdigest()[:16]
    
    def _save_delta(self, delta_id: str, snapshot_id: str, session_id: str,
                   base_snapshot_id: str, changes: Dict[str, List[DeltaChange]],
                   delta_hash: str) -> None:
        """保存差异到数据库"""
        
        # 序列化变化数据
        delta_json = json.dumps({
            change_type: [change.to_dict() for change in change_list]
            for change_type, change_list in changes.items()
        }, ensure_ascii=False, separators=(',', ':'))
        
        # 识别受影响的MOD
        touched_mods = self._identify_touched_mods(changes)
        touched_mods_json = json.dumps(touched_mods, ensure_ascii=False)
        
        # 统计变化数量
        affected_files = sum(len(change_list) for change_list in changes.values())
        
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                INSERT INTO cache_scan_delta 
                (snapshot_id, session_id, base_snapshot_id, delta_json, 
                 delta_hash, affected_files, touched_mods, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id, session_id, base_snapshot_id, delta_json,
                delta_hash, affected_files, touched_mods_json,
                datetime.now().isoformat()
            ))
            conn.commit()
            
        finally:
            conn.close()
    
    def _identify_touched_mods(self, changes: Dict[str, List[DeltaChange]]) -> List[str]:
        """识别受变化影响的MOD"""
        touched_mods = set()
        
        for change_list in changes.values():
            for change in change_list:
                # 尝试从路径中提取MOD名称
                path_parts = Path(change.path).parts
                
                # 检查常见的MOD路径模式
                for i, part in enumerate(path_parts):
                    if part.endswith('.jar'):
                        # JAR文件本身就是MOD
                        mod_name = part[:-4]  # 去掉.jar后缀
                        touched_mods.add(mod_name)
                        break
                    elif part == 'mods' and i + 1 < len(path_parts):
                        # mods目录下的文件
                        next_part = path_parts[i + 1]
                        if next_part.endswith('.jar'):
                            mod_name = next_part[:-4]
                            touched_mods.add(mod_name)
                        break
                    elif 'assets' in path_parts:
                        # 资源包中的assets路径
                        try:
                            assets_idx = path_parts.index('assets')
                            if assets_idx + 1 < len(path_parts):
                                mod_name = path_parts[assets_idx + 1]
                                touched_mods.add(mod_name)
                        except ValueError:
                            pass
        
        return sorted(list(touched_mods))
    
    def get_delta(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """获取差异数据"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute("""
                SELECT * FROM cache_scan_delta 
                WHERE snapshot_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (snapshot_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # 解析差异数据
            delta_data = json.loads(row['delta_json'])
            changes = {}
            
            for change_type, change_list in delta_data.items():
                changes[change_type] = [
                    DeltaChange.from_dict(change_data)
                    for change_data in change_list
                ]
            
            return {
                'snapshot_id': row['snapshot_id'],
                'session_id': row['session_id'],
                'base_snapshot_id': row['base_snapshot_id'],
                'changes': changes,
                'delta_hash': row['delta_hash'],
                'affected_files': row['affected_files'],
                'touched_mods': json.loads(row['touched_mods']),
                'created_at': row['created_at']
            }
            
        finally:
            conn.close()
    
    def list_deltas(self, session_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """列出差异记录"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        try:
            sql = """
                SELECT snapshot_id, session_id, base_snapshot_id,
                       delta_hash, affected_files, touched_mods, created_at
                FROM cache_scan_delta 
            """
            params = []
            
            if session_id:
                sql += " WHERE session_id = ?"
                params.append(session_id)
            
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql, params)
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result['touched_mods'] = json.loads(result['touched_mods'])
                results.append(result)
            
            return results
            
        finally:
            conn.close()
    
    def get_incremental_changes(self, current_snapshot_id: str, 
                               last_known_snapshot_id: Optional[str] = None) -> Dict[str, Any]:
        """获取增量变化（用于UI渐进式更新）"""
        if not last_known_snapshot_id:
            # 首次扫描，返回所有文件作为"新增"
            current_snapshot = self._load_snapshot(current_snapshot_id)
            if not current_snapshot:
                return {'changes': {}, 'summary': {}}
            
            added_changes = [
                DeltaChange('added', path, new_snapshot=snapshot)
                for path, snapshot in current_snapshot['files'].items()
            ]
            
            changes = {
                'added': added_changes,
                'modified': [],
                'moved': [],
                'removed': []
            }
        else:
            # 增量对比
            _, changes = self.compare_snapshots(
                current_snapshot_id, last_known_snapshot_id, 
                f"incremental_{uuid.uuid4().hex[:8]}"
            )
        
        # 生成摘要统计
        summary = {
            'total_files': sum(len(change_list) for change_list in changes.values()),
            'by_type': {
                change_type: len(change_list)
                for change_type, change_list in changes.items()
            },
            'touched_mods': self._identify_touched_mods(changes)
        }
        
        return {
            'changes': changes,
            'summary': summary
        }