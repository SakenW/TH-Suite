"""
VERIFY Worker - 去重、冲突检测和统计
负责检测重复项目、解决冲突、生成统计信息、标记墓碑记录等
"""

import json
import structlog
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, Counter

from ..worker_manager import BaseWorker, WorkTask, WorkerResult, WorkerType
from ..event_applier import ScanEvent, EventType, create_tombstone_event, create_count_patch_event

logger = structlog.get_logger(__name__)


class VerifyWorker(BaseWorker):
    """验证和统计Worker"""
    
    def __init__(self, db_path: str):
        super().__init__(WorkerType.VERIFY, db_path)
    
    async def process_task(self, task: WorkTask) -> WorkerResult:
        """处理验证任务"""
        try:
            payload = task.payload
            session_id = task.session_id
            verification_type = payload.get('verification_type', 'full')  # full, duplicate, conflict, stats
            snapshot_id = payload.get('snapshot_id')
            
            logger.info("🔍 开始验证处理", 
                       session_id=session_id, 
                       verification_type=verification_type)
            
            events = []
            
            # 根据验证类型执行不同的处理
            if verification_type == 'full' or verification_type == 'duplicate':
                duplicate_events = await self._process_duplicates(session_id, snapshot_id)
                events.extend(duplicate_events)
            
            if verification_type == 'full' or verification_type == 'conflict':
                conflict_events = await self._process_conflicts(session_id, snapshot_id)
                events.extend(conflict_events)
            
            if verification_type == 'full' or verification_type == 'stats':
                stats_events = await self._generate_statistics(session_id, snapshot_id)
                events.extend(stats_events)
            
            if verification_type == 'full' or verification_type == 'tombstone':
                tombstone_events = await self._process_tombstones(session_id, snapshot_id)
                events.extend(tombstone_events)
            
            logger.info("✅ 验证处理完成",
                       events_count=len(events),
                       verification_type=verification_type)
            
            return WorkerResult(
                task_id=task.task_id,
                success=True,
                events=events,
                metrics={
                    'verification_type': verification_type,
                    'events_generated': len(events)
                }
            )
            
        except Exception as e:
            logger.error("❌ 验证处理失败", error=str(e))
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                events=[],
                error_message=str(e)
            )
    
    async def _process_duplicates(self, session_id: str, snapshot_id: str) -> List[ScanEvent]:
        """处理重复项检测"""
        events = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 1. 检测重复的MOD文件（基于文件名和大小）
            cursor = conn.execute("""
                SELECT file_path, file_size, COUNT(*) as count
                FROM (
                    SELECT JSON_EXTRACT(payload_json, '$.file_path') as file_path,
                           JSON_EXTRACT(payload_json, '$.file_size') as file_size
                    FROM ops_event_log 
                    WHERE session_id = ? AND event_type = 'LIST_UPSERT'
                      AND JSON_EXTRACT(payload_json, '$.type') = 'mod_file'
                )
                GROUP BY file_path, file_size
                HAVING count > 1
            """, (session_id,))
            
            duplicates = cursor.fetchall()
            
            for file_path, file_size, count in duplicates:
                # 标记重复文件
                tombstone_event = create_tombstone_event(
                    session_id,
                    f"duplicate:{file_path}",
                    {
                        'reason': 'duplicate_file',
                        'original_path': file_path,
                        'duplicate_count': count,
                        'file_size': file_size,
                        'snapshot_id': snapshot_id
                    }
                )
                events.append(tombstone_event)
            
            # 2. 检测重复的MOD ID
            cursor = conn.execute("""
                SELECT modid, COUNT(*) as count, GROUP_CONCAT(file_path) as files
                FROM (
                    SELECT JSON_EXTRACT(payload_json, '$.modid') as modid,
                           JSON_EXTRACT(payload_json, '$.file_path') as file_path
                    FROM ops_event_log 
                    WHERE session_id = ? AND event_type = 'FIELD_PATCH'
                      AND JSON_EXTRACT(payload_json, '$.modid') IS NOT NULL
                      AND JSON_EXTRACT(payload_json, '$.modid') != ''
                )
                GROUP BY modid
                HAVING count > 1
            """, (session_id,))
            
            mod_duplicates = cursor.fetchall()
            
            for modid, count, files in mod_duplicates:
                tombstone_event = create_tombstone_event(
                    session_id,
                    f"duplicate_modid:{modid}",
                    {
                        'reason': 'duplicate_modid',
                        'modid': modid,
                        'duplicate_count': count,
                        'affected_files': files.split(',') if files else [],
                        'snapshot_id': snapshot_id
                    }
                )
                events.append(tombstone_event)
            
            conn.close()
            
            logger.info("📝 重复项检测完成", 
                       file_duplicates=len(duplicates),
                       modid_duplicates=len(mod_duplicates))
            
        except Exception as e:
            logger.error("❌ 重复项检测失败", error=str(e))
        
        return events
    
    async def _process_conflicts(self, session_id: str, snapshot_id: str) -> List[ScanEvent]:
        """处理冲突检测"""
        events = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 1. 检测版本冲突（同一MOD的不同版本）
            cursor = conn.execute("""
                SELECT modid, COUNT(DISTINCT version) as version_count, 
                       GROUP_CONCAT(DISTINCT version) as versions,
                       GROUP_CONCAT(file_path) as files
                FROM (
                    SELECT JSON_EXTRACT(payload_json, '$.modid') as modid,
                           JSON_EXTRACT(payload_json, '$.version') as version,
                           JSON_EXTRACT(payload_json, '$.file_path') as file_path
                    FROM ops_event_log 
                    WHERE session_id = ? AND event_type = 'FIELD_PATCH'
                      AND JSON_EXTRACT(payload_json, '$.modid') IS NOT NULL
                      AND JSON_EXTRACT(payload_json, '$.version') IS NOT NULL
                )
                GROUP BY modid
                HAVING version_count > 1
            """, (session_id,))
            
            version_conflicts = cursor.fetchall()
            
            for modid, version_count, versions, files in version_conflicts:
                tombstone_event = create_tombstone_event(
                    session_id,
                    f"conflict_version:{modid}",
                    {
                        'reason': 'version_conflict',
                        'modid': modid,
                        'conflicting_versions': versions.split(',') if versions else [],
                        'affected_files': files.split(',') if files else [],
                        'conflict_count': version_count,
                        'snapshot_id': snapshot_id
                    }
                )
                events.append(tombstone_event)
            
            # 2. 检测Loader冲突（同一MOD支持不同Loader）
            cursor = conn.execute("""
                SELECT modid, COUNT(DISTINCT loader) as loader_count,
                       GROUP_CONCAT(DISTINCT loader) as loaders,
                       GROUP_CONCAT(file_path) as files
                FROM (
                    SELECT JSON_EXTRACT(payload_json, '$.modid') as modid,
                           JSON_EXTRACT(payload_json, '$.loader') as loader,
                           JSON_EXTRACT(payload_json, '$.file_path') as file_path
                    FROM ops_event_log 
                    WHERE session_id = ? AND event_type = 'FIELD_PATCH'
                      AND JSON_EXTRACT(payload_json, '$.modid') IS NOT NULL
                      AND JSON_EXTRACT(payload_json, '$.loader') IS NOT NULL
                )
                GROUP BY modid
                HAVING loader_count > 1
            """, (session_id,))
            
            loader_conflicts = cursor.fetchall()
            
            for modid, loader_count, loaders, files in loader_conflicts:
                tombstone_event = create_tombstone_event(
                    session_id,
                    f"conflict_loader:{modid}",
                    {
                        'reason': 'loader_conflict',
                        'modid': modid,
                        'conflicting_loaders': loaders.split(',') if loaders else [],
                        'affected_files': files.split(',') if files else [],
                        'conflict_count': loader_count,
                        'snapshot_id': snapshot_id
                    }
                )
                events.append(tombstone_event)
            
            conn.close()
            
            logger.info("⚠️ 冲突检测完成",
                       version_conflicts=len(version_conflicts),
                       loader_conflicts=len(loader_conflicts))
            
        except Exception as e:
            logger.error("❌ 冲突检测失败", error=str(e))
        
        return events
    
    async def _generate_statistics(self, session_id: str, snapshot_id: str) -> List[ScanEvent]:
        """生成统计信息"""
        events = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 1. 统计文件类型分布
            cursor = conn.execute("""
                SELECT JSON_EXTRACT(payload_json, '$.type') as file_type,
                       COUNT(*) as count
                FROM ops_event_log 
                WHERE session_id = ? AND event_type = 'LIST_UPSERT'
                GROUP BY JSON_EXTRACT(payload_json, '$.type')
            """, (session_id,))
            
            file_type_stats = dict(cursor.fetchall())
            
            # 2. 统计Loader分布
            cursor = conn.execute("""
                SELECT JSON_EXTRACT(payload_json, '$.loader') as loader,
                       COUNT(*) as count
                FROM ops_event_log 
                WHERE session_id = ? AND event_type = 'FIELD_PATCH'
                  AND JSON_EXTRACT(payload_json, '$.loader') IS NOT NULL
                GROUP BY JSON_EXTRACT(payload_json, '$.loader')
            """, (session_id,))
            
            loader_stats = dict(cursor.fetchall())
            
            # 3. 统计语言文件分布
            cursor = conn.execute("""
                SELECT JSON_EXTRACT(payload_json, '$.locale') as locale,
                       COUNT(*) as count
                FROM ops_event_log 
                WHERE session_id = ? AND event_type = 'LANG_UPSERT'
                  AND JSON_EXTRACT(payload_json, '$.locale') IS NOT NULL
                GROUP BY JSON_EXTRACT(payload_json, '$.locale')
            """, (session_id,))
            
            locale_stats = dict(cursor.fetchall())
            
            # 4. 统计总的翻译条目数
            cursor = conn.execute("""
                SELECT SUM(JSON_EXTRACT(payload_json, '$.entries_count')) as total_entries
                FROM ops_event_log 
                WHERE session_id = ? AND event_type = 'LANG_UPSERT'
                  AND JSON_EXTRACT(payload_json, '$.entries_count') IS NOT NULL
            """, (session_id,))
            
            total_entries_result = cursor.fetchone()
            total_entries = total_entries_result[0] if total_entries_result and total_entries_result[0] else 0
            
            conn.close()
            
            # 生成统计事件
            stats_data = {
                'session_id': session_id,
                'snapshot_id': snapshot_id,
                'file_type_distribution': file_type_stats,
                'loader_distribution': loader_stats,
                'locale_distribution': locale_stats,
                'total_translation_entries': total_entries,
                'total_mods': file_type_stats.get('mod_file', 0),
                'total_resource_packs': file_type_stats.get('resource_pack', 0),
                'total_config_files': file_type_stats.get('config_file', 0)
            }
            
            stats_event = create_count_patch_event(
                session_id,
                'session_statistics',
                stats_data
            )
            events.append(stats_event)
            
            logger.info("📊 统计信息生成完成",
                       total_mods=stats_data['total_mods'],
                       total_entries=total_entries,
                       locales_count=len(locale_stats))
            
        except Exception as e:
            logger.error("❌ 统计信息生成失败", error=str(e))
        
        return events
    
    async def _process_tombstones(self, session_id: str, snapshot_id: str) -> List[ScanEvent]:
        """处理墓碑标记（删除/移动的文件）"""
        events = []
        
        try:
            # 这里可以实现墓碑逻辑，比如：
            # 1. 检测在前一个快照中存在但当前快照中不存在的文件
            # 2. 标记被移动或重命名的文件
            # 3. 处理被禁用的MOD文件
            
            # 暂时实现一个简单的禁用MOD检测
            conn = sqlite3.connect(self.db_path)
            
            cursor = conn.execute("""
                SELECT JSON_EXTRACT(payload_json, '$.file_path') as file_path,
                       JSON_EXTRACT(payload_json, '$.file_type') as file_type
                FROM ops_event_log 
                WHERE session_id = ? AND event_type = 'LIST_UPSERT'
                  AND JSON_EXTRACT(payload_json, '$.file_type') LIKE '%disabled%'
            """, (session_id,))
            
            disabled_files = cursor.fetchall()
            
            for file_path, file_type in disabled_files:
                tombstone_event = create_tombstone_event(
                    session_id,
                    f"disabled:{file_path}",
                    {
                        'reason': 'disabled_mod',
                        'file_path': file_path,
                        'file_type': file_type,
                        'snapshot_id': snapshot_id
                    }
                )
                events.append(tombstone_event)
            
            conn.close()
            
            logger.info("🪦 墓碑处理完成", disabled_files=len(disabled_files))
            
        except Exception as e:
            logger.error("❌ 墓碑处理失败", error=str(e))
        
        return events