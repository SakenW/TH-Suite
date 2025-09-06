#!/usr/bin/env python
"""
离线变更跟踪器
跟踪所有离线状态下的数据变更，以便在线时同步
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChangeOperation(Enum):
    """变更操作类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"


class EntityType(Enum):
    """实体类型"""
    PROJECT = "project"
    MOD = "mod"
    TRANSLATION = "translation"
    TERMINOLOGY = "terminology"
    SETTING = "setting"


class OfflineChangeTracker:
    """离线变更跟踪器"""
    
    def __init__(self, db_path: str = "mc_l10n_local.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # 启用触发器自动跟踪
        self.setup_triggers()
        
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        try:
            yield self.conn
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"事务失败: {e}")
            raise
            
    def setup_triggers(self):
        """设置自动跟踪触发器"""
        
        # 翻译条目变更触发器
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS track_translation_update
            AFTER UPDATE ON translation_entry_cache
            WHEN NEW.translated_text != OLD.translated_text
            BEGIN
                INSERT INTO offline_changes (
                    entity_type, entity_id, operation, change_data
                ) VALUES (
                    'translation',
                    NEW.entry_id,
                    'update',
                    json_object(
                        'cache_id', NEW.cache_id,
                        'translation_key', NEW.translation_key,
                        'old_text', OLD.translated_text,
                        'new_text', NEW.translated_text,
                        'status', NEW.status
                    )
                );
            END
        """)
        
        # 项目创建触发器
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS track_project_create
            AFTER INSERT ON local_projects
            WHEN NEW.project_id != 'default-project'
            BEGIN
                INSERT INTO offline_changes (
                    entity_type, entity_id, operation, change_data
                ) VALUES (
                    'project',
                    NEW.project_id,
                    'create',
                    json_object(
                        'project_name', NEW.project_name,
                        'target_language', NEW.target_language,
                        'source_language', NEW.source_language
                    )
                );
            END
        """)
        
        # 项目更新触发器
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS track_project_update
            AFTER UPDATE ON local_projects
            WHEN NEW.project_id != 'default-project'
            BEGIN
                INSERT INTO offline_changes (
                    entity_type, entity_id, operation, change_data
                ) VALUES (
                    'project',
                    NEW.project_id,
                    'update',
                    json_object(
                        'project_name', NEW.project_name,
                        'scan_paths', NEW.scan_paths,
                        'auto_scan', NEW.auto_scan
                    )
                );
            END
        """)
        
        self.conn.commit()
        logger.info("离线跟踪触发器已设置")
        
    def track_change(self, entity_type: EntityType, entity_id: str, 
                    operation: ChangeOperation, change_data: Dict,
                    conflict_resolution: str = "client_wins"):
        """手动跟踪变更"""
        
        with self.transaction():
            self.conn.execute("""
                INSERT INTO offline_changes (
                    entity_type, entity_id, operation, 
                    change_data, conflict_resolution
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                entity_type.value,
                entity_id,
                operation.value,
                json.dumps(change_data, ensure_ascii=False),
                conflict_resolution
            ))
            
        logger.info(f"跟踪变更: {entity_type.value}/{entity_id} - {operation.value}")
        
    def batch_track_changes(self, changes: List[Dict]):
        """批量跟踪变更"""
        
        with self.transaction():
            for change in changes:
                self.conn.execute("""
                    INSERT INTO offline_changes (
                        entity_type, entity_id, operation, 
                        change_data, conflict_resolution
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    change['entity_type'],
                    change['entity_id'],
                    change['operation'],
                    json.dumps(change.get('change_data', {}), ensure_ascii=False),
                    change.get('conflict_resolution', 'client_wins')
                ))
                
        logger.info(f"批量跟踪了 {len(changes)} 个变更")
        
    def get_pending_changes(self, entity_type: Optional[EntityType] = None,
                           limit: int = 100) -> List[Dict]:
        """获取待同步的变更"""
        
        query = """
            SELECT * FROM offline_changes 
            WHERE is_synced = 0
        """
        params = []
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type.value)
            
        query += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        
        changes = []
        for row in cursor.fetchall():
            changes.append({
                'change_id': row['change_id'],
                'entity_type': row['entity_type'],
                'entity_id': row['entity_id'],
                'operation': row['operation'],
                'change_data': json.loads(row['change_data']) if row['change_data'] else {},
                'conflict_resolution': row['conflict_resolution'],
                'created_at': row['created_at']
            })
            
        return changes
        
    def mark_changes_synced(self, change_ids: List[str]):
        """标记变更为已同步"""
        
        if not change_ids:
            return
            
        placeholders = ','.join(['?'] * len(change_ids))
        
        with self.transaction():
            self.conn.execute(f"""
                UPDATE offline_changes 
                SET is_synced = 1, synced_at = CURRENT_TIMESTAMP
                WHERE change_id IN ({placeholders})
            """, change_ids)
            
        logger.info(f"标记 {len(change_ids)} 个变更为已同步")
        
    def get_change_summary(self) -> Dict:
        """获取变更摘要"""
        
        cursor = self.conn.cursor()
        
        # 按实体类型统计
        cursor.execute("""
            SELECT 
                entity_type,
                COUNT(*) as total,
                SUM(CASE WHEN is_synced = 0 THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN is_synced = 1 THEN 1 ELSE 0 END) as synced
            FROM offline_changes
            GROUP BY entity_type
        """)
        
        by_entity = {}
        for row in cursor.fetchall():
            by_entity[row['entity_type']] = {
                'total': row['total'],
                'pending': row['pending'],
                'synced': row['synced']
            }
            
        # 按操作类型统计
        cursor.execute("""
            SELECT 
                operation,
                COUNT(*) as count
            FROM offline_changes
            WHERE is_synced = 0
            GROUP BY operation
        """)
        
        by_operation = {}
        for row in cursor.fetchall():
            by_operation[row['operation']] = row['count']
            
        # 最近变更
        cursor.execute("""
            SELECT * FROM offline_changes
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        recent = []
        for row in cursor.fetchall():
            recent.append({
                'entity_type': row['entity_type'],
                'entity_id': row['entity_id'],
                'operation': row['operation'],
                'created_at': row['created_at'],
                'is_synced': row['is_synced']
            })
            
        return {
            'by_entity': by_entity,
            'by_operation': by_operation,
            'recent_changes': recent,
            'total_pending': sum(e['pending'] for e in by_entity.values())
        }
        
    def resolve_conflicts(self, local_changes: List[Dict], server_changes: List[Dict]) -> List[Dict]:
        """解决冲突"""
        
        resolved = []
        conflicts = []
        
        # 创建服务器变更索引
        server_index = {}
        for change in server_changes:
            key = f"{change['entity_type']}:{change['entity_id']}"
            server_index[key] = change
            
        for local in local_changes:
            key = f"{local['entity_type']}:{local['entity_id']}"
            
            if key in server_index:
                server = server_index[key]
                
                # 检测冲突
                if self.is_conflict(local, server):
                    resolution = local['conflict_resolution']
                    
                    if resolution == 'client_wins':
                        resolved.append(local)
                    elif resolution == 'server_wins':
                        resolved.append(server)
                    elif resolution == 'newest_wins':
                        local_time = datetime.fromisoformat(local['created_at'])
                        server_time = datetime.fromisoformat(server['created_at'])
                        resolved.append(local if local_time > server_time else server)
                    else:  # manual
                        conflicts.append({
                            'local': local,
                            'server': server
                        })
                else:
                    # 无冲突，合并变更
                    merged = self.merge_changes(local, server)
                    resolved.append(merged)
            else:
                # 仅本地有变更
                resolved.append(local)
                
        # 添加仅服务器有的变更
        for server in server_changes:
            key = f"{server['entity_type']}:{server['entity_id']}"
            if key not in {f"{l['entity_type']}:{l['entity_id']}" for l in local_changes}:
                resolved.append(server)
                
        if conflicts:
            logger.warning(f"检测到 {len(conflicts)} 个冲突需要手动解决")
            
        return resolved
        
    def is_conflict(self, local: Dict, server: Dict) -> bool:
        """检测是否存在冲突"""
        
        # 相同实体的不同操作
        if local['operation'] != server['operation']:
            return True
            
        # UPDATE操作时，检查是否修改了相同字段
        if local['operation'] == 'update':
            local_fields = set(local['change_data'].keys())
            server_fields = set(server['change_data'].keys())
            
            # 有重叠字段且值不同
            common_fields = local_fields & server_fields
            for field in common_fields:
                if local['change_data'][field] != server['change_data'][field]:
                    return True
                    
        return False
        
    def merge_changes(self, local: Dict, server: Dict) -> Dict:
        """合并无冲突的变更"""
        
        merged = local.copy()
        
        # 合并change_data
        if 'change_data' in server:
            merged['change_data'].update(server['change_data'])
            
        return merged
        
    def cleanup_old_changes(self, days: int = 30):
        """清理旧的已同步变更"""
        
        with self.transaction():
            cursor = self.conn.execute("""
                DELETE FROM offline_changes
                WHERE is_synced = 1 
                AND synced_at < datetime('now', '-' || ? || ' days')
            """, (days,))
            
        deleted = cursor.rowcount
        logger.info(f"清理了 {deleted} 个旧变更记录")
        
    def export_changes(self, file_path: str):
        """导出变更记录"""
        
        changes = self.get_pending_changes(limit=10000)
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'total_changes': len(changes),
            'changes': changes
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"导出了 {len(changes)} 个变更到 {file_path}")
        
    def import_changes(self, file_path: str):
        """导入变更记录"""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        changes = data.get('changes', [])
        
        with self.transaction():
            for change in changes:
                # 检查是否已存在
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as count FROM offline_changes
                    WHERE entity_type = ? AND entity_id = ? 
                    AND operation = ? AND created_at = ?
                """, (
                    change['entity_type'],
                    change['entity_id'],
                    change['operation'],
                    change['created_at']
                ))
                
                if cursor.fetchone()['count'] == 0:
                    self.conn.execute("""
                        INSERT INTO offline_changes (
                            entity_type, entity_id, operation,
                            change_data, conflict_resolution, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        change['entity_type'],
                        change['entity_id'],
                        change['operation'],
                        json.dumps(change.get('change_data', {})),
                        change.get('conflict_resolution', 'client_wins'),
                        change['created_at']
                    ))
                    
        logger.info(f"导入了 {len(changes)} 个变更记录")


def main():
    """测试函数"""
    tracker = OfflineChangeTracker()
    
    # 测试跟踪变更
    tracker.track_change(
        EntityType.TRANSLATION,
        "test-entry-001",
        ChangeOperation.UPDATE,
        {
            'translation_key': 'item.minecraft.diamond',
            'old_text': 'Diamond',
            'new_text': '钻石'
        }
    )
    
    # 批量跟踪
    changes = [
        {
            'entity_type': 'project',
            'entity_id': 'test-project',
            'operation': 'create',
            'change_data': {'name': '测试项目'}
        },
        {
            'entity_type': 'mod',
            'entity_id': 'test-mod',
            'operation': 'update',
            'change_data': {'version': '1.0.1'}
        }
    ]
    tracker.batch_track_changes(changes)
    
    # 获取摘要
    summary = tracker.get_change_summary()
    print("\n📊 变更摘要:")
    print(f"  待同步: {summary['total_pending']}")
    print(f"  按类型:")
    for entity_type, stats in summary['by_entity'].items():
        print(f"    - {entity_type}: {stats['pending']}/{stats['total']}")
        
    # 获取待同步变更
    pending = tracker.get_pending_changes(limit=5)
    print(f"\n📝 最近变更 ({len(pending)} 条):")
    for change in pending:
        print(f"  - [{change['operation']}] {change['entity_type']}/{change['entity_id']}")
        
    # 导出变更
    tracker.export_changes("offline_changes.json")
    print("\n✅ 变更已导出到 offline_changes.json")


if __name__ == "__main__":
    main()