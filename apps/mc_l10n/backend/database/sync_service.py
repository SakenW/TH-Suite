#!/usr/bin/env python
"""
数据同步服务
处理本地客户端与Trans-Hub服务器之间的数据同步
"""

import sqlite3
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyncDirection(Enum):
    """同步方向"""
    UPLOAD = "upload"      # 本地到服务器
    DOWNLOAD = "download"  # 服务器到本地
    BIDIRECTIONAL = "bidirectional"  # 双向同步


class ConflictResolution(Enum):
    """冲突解决策略"""
    CLIENT_WINS = "client_wins"  # 客户端优先
    SERVER_WINS = "server_wins"  # 服务器优先
    NEWEST_WINS = "newest_wins"  # 最新优先
    MANUAL = "manual"            # 手动解决


class DataSyncService:
    """数据同步服务"""
    
    def __init__(self, db_path: str = "mc_l10n_local.db", server_url: str = None):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Trans-Hub服务器配置
        self.server_url = server_url or "http://localhost:8001"
        self.api_key = None
        self.session = None
        
    async def initialize(self):
        """初始化异步会话"""
        self.session = aiohttp.ClientSession(
            headers={
                'Content-Type': 'application/json',
                'X-Client-Type': 'mc-l10n'
            }
        )
        
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
        self.conn.close()
        
    def get_sync_settings(self) -> Dict:
        """获取同步设置"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT setting_key, setting_value 
            FROM local_settings 
            WHERE setting_key IN ('auto_sync', 'sync_interval', 'conflict_resolution')
        """)
        
        settings = {}
        for row in cursor.fetchall():
            settings[row['setting_key']] = row['setting_value']
            
        return {
            'auto_sync': settings.get('auto_sync', 'false') == 'true',
            'sync_interval': int(settings.get('sync_interval', '300')),
            'conflict_resolution': settings.get('conflict_resolution', 'client_wins')
        }
        
    async def sync_projects(self, direction: SyncDirection = SyncDirection.BIDIRECTIONAL):
        """同步项目数据"""
        sync_log_id = self.create_sync_log('projects', direction.value)
        
        try:
            if direction in [SyncDirection.UPLOAD, SyncDirection.BIDIRECTIONAL]:
                await self.upload_local_projects()
                
            if direction in [SyncDirection.DOWNLOAD, SyncDirection.BIDIRECTIONAL]:
                await self.download_server_projects()
                
            self.complete_sync_log(sync_log_id, success=True)
            
        except Exception as e:
            logger.error(f"项目同步失败: {e}")
            self.complete_sync_log(sync_log_id, success=False, error=str(e))
            raise
            
    async def upload_local_projects(self):
        """上传本地项目到服务器"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM local_projects 
            WHERE project_id != 'default-project'
        """)
        
        projects = []
        for row in cursor.fetchall():
            projects.append({
                'project_id': row['project_id'],
                'project_name': row['project_name'],
                'target_language': row['target_language'],
                'source_language': row['source_language'],
                'scan_paths': json.loads(row['scan_paths']) if row['scan_paths'] else [],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
            
        if projects:
            async with self.session.post(
                f"{self.server_url}/api/sync/projects",
                json={'projects': projects}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"上传了 {len(projects)} 个项目")
                else:
                    logger.error(f"项目上传失败: {response.status}")
                    
    async def download_server_projects(self):
        """从服务器下载项目"""
        async with self.session.get(f"{self.server_url}/api/projects") as response:
            if response.status == 200:
                data = await response.json()
                projects = data.get('projects', [])
                
                for project in projects:
                    self.conn.execute("""
                        INSERT OR REPLACE INTO local_projects (
                            project_id, project_name, target_language, source_language,
                            scan_paths, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        project['project_id'],
                        project['project_name'],
                        project['target_language'],
                        project['source_language'],
                        json.dumps(project.get('scan_paths', [])),
                        project.get('created_at'),
                        project.get('updated_at')
                    ))
                    
                self.conn.commit()
                logger.info(f"下载了 {len(projects)} 个项目")
            else:
                logger.error(f"项目下载失败: {response.status}")
                
    async def sync_mod_discoveries(self):
        """同步MOD发现数据"""
        sync_log_id = self.create_sync_log('mod_discoveries', 'upload')
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM mod_discoveries 
                WHERE is_uploaded = 0
                LIMIT 100
            """)
            
            mods = []
            mod_ids = []
            
            for row in cursor.fetchall():
                mods.append({
                    'mod_id': row['mod_id'],
                    'mod_name': row['mod_name'],
                    'display_name': row['display_name'],
                    'version': row['version'],
                    'minecraft_version': row['minecraft_version'],
                    'mod_loader': row['mod_loader'],
                    'file_path': row['file_path'],
                    'file_hash': row['file_hash'],
                    'file_size': row['file_size'],
                    'language_count': row['language_count'],
                    'total_keys': row['total_keys'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'discovered_at': row['discovered_at']
                })
                mod_ids.append(row['mod_id'])
                
            if mods:
                async with self.session.post(
                    f"{self.server_url}/api/sync/mods",
                    json={'mods': mods}
                ) as response:
                    if response.status == 200:
                        # 标记为已上传
                        placeholders = ','.join(['?'] * len(mod_ids))
                        self.conn.execute(f"""
                            UPDATE mod_discoveries 
                            SET is_uploaded = 1, uploaded_at = CURRENT_TIMESTAMP
                            WHERE mod_id IN ({placeholders})
                        """, mod_ids)
                        self.conn.commit()
                        
                        self.complete_sync_log(sync_log_id, success=True, entity_count=len(mods))
                        logger.info(f"上传了 {len(mods)} 个MOD发现")
                    else:
                        raise Exception(f"上传失败: {response.status}")
            else:
                self.complete_sync_log(sync_log_id, success=True, entity_count=0)
                
        except Exception as e:
            logger.error(f"MOD同步失败: {e}")
            self.complete_sync_log(sync_log_id, success=False, error=str(e))
            raise
            
    async def sync_translations(self, project_id: str):
        """同步翻译数据"""
        sync_log_id = self.create_sync_log('translations', 'bidirectional')
        
        try:
            # 获取本地变更
            local_changes = self.get_offline_changes('translation', project_id)
            
            # 上传本地变更
            if local_changes:
                await self.upload_translation_changes(local_changes)
                
            # 下载服务器更新
            await self.download_translation_updates(project_id)
            
            self.complete_sync_log(sync_log_id, success=True)
            
        except Exception as e:
            logger.error(f"翻译同步失败: {e}")
            self.complete_sync_log(sync_log_id, success=False, error=str(e))
            raise
            
    def get_offline_changes(self, entity_type: str, entity_id: Optional[str] = None) -> List[Dict]:
        """获取离线变更"""
        query = """
            SELECT * FROM offline_changes 
            WHERE entity_type = ? AND is_synced = 0
        """
        params = [entity_type]
        
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
            
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
                'created_at': row['created_at']
            })
            
        return changes
        
    async def upload_translation_changes(self, changes: List[Dict]):
        """上传翻译变更"""
        async with self.session.post(
            f"{self.server_url}/api/sync/translation-changes",
            json={'changes': changes}
        ) as response:
            if response.status == 200:
                # 标记变更为已同步
                change_ids = [c['change_id'] for c in changes]
                placeholders = ','.join(['?'] * len(change_ids))
                
                self.conn.execute(f"""
                    UPDATE offline_changes 
                    SET is_synced = 1, synced_at = CURRENT_TIMESTAMP
                    WHERE change_id IN ({placeholders})
                """, change_ids)
                self.conn.commit()
                
                logger.info(f"上传了 {len(changes)} 个翻译变更")
            else:
                raise Exception(f"变更上传失败: {response.status}")
                
    async def download_translation_updates(self, project_id: str):
        """下载翻译更新"""
        # 获取最后同步时间
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT MAX(completed_at) as last_sync 
            FROM sync_log 
            WHERE sync_type = 'translations' AND completed_at IS NOT NULL
        """)
        result = cursor.fetchone()
        last_sync = result['last_sync'] if result else None
        
        params = {'project_id': project_id}
        if last_sync:
            params['since'] = last_sync
            
        async with self.session.get(
            f"{self.server_url}/api/translations/updates",
            params=params
        ) as response:
            if response.status == 200:
                data = await response.json()
                translations = data.get('translations', [])
                
                for trans in translations:
                    # 更新本地翻译缓存
                    self.update_translation_cache(trans)
                    
                logger.info(f"下载了 {len(translations)} 个翻译更新")
            else:
                logger.error(f"翻译下载失败: {response.status}")
                
    def update_translation_cache(self, translation: Dict):
        """更新翻译缓存"""
        self.conn.execute("""
            UPDATE translation_entry_cache 
            SET translated_text = ?, status = ?, cached_at = CURRENT_TIMESTAMP
            WHERE translation_key = ? AND cache_id IN (
                SELECT cache_id FROM language_file_cache 
                WHERE mod_id = ? AND language_code = ?
            )
        """, (
            translation['translated_text'],
            translation['status'],
            translation['translation_key'],
            translation['mod_id'],
            translation['language_code']
        ))
        self.conn.commit()
        
    def track_offline_change(self, entity_type: str, entity_id: str, operation: str, change_data: Dict):
        """跟踪离线变更"""
        settings = self.get_sync_settings()
        conflict_resolution = settings['conflict_resolution']
        
        self.conn.execute("""
            INSERT INTO offline_changes (
                entity_type, entity_id, operation, change_data, conflict_resolution
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            entity_type,
            entity_id,
            operation,
            json.dumps(change_data, ensure_ascii=False),
            conflict_resolution
        ))
        self.conn.commit()
        
    def resolve_conflicts(self, local_data: Dict, server_data: Dict, strategy: ConflictResolution) -> Dict:
        """解决冲突"""
        if strategy == ConflictResolution.CLIENT_WINS:
            return local_data
        elif strategy == ConflictResolution.SERVER_WINS:
            return server_data
        elif strategy == ConflictResolution.NEWEST_WINS:
            local_time = datetime.fromisoformat(local_data.get('updated_at', ''))
            server_time = datetime.fromisoformat(server_data.get('updated_at', ''))
            return local_data if local_time > server_time else server_data
        else:  # MANUAL
            # 需要用户手动解决，这里先返回本地数据
            logger.warning(f"需要手动解决冲突: {local_data['id']}")
            return local_data
            
    def create_sync_log(self, sync_type: str, direction: str) -> int:
        """创建同步日志"""
        cursor = self.conn.execute("""
            INSERT INTO sync_log (sync_type, sync_direction)
            VALUES (?, ?)
        """, (sync_type, direction))
        
        self.conn.commit()
        return cursor.lastrowid
        
    def complete_sync_log(self, log_id: int, success: bool, entity_count: int = 0, error: Optional[str] = None):
        """完成同步日志"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT started_at FROM sync_log WHERE log_id = ?
        """, (log_id,))
        
        result = cursor.fetchone()
        if result:
            started_at = datetime.fromisoformat(result['started_at'])
            duration = (datetime.now() - started_at).total_seconds()
            
            if success:
                self.conn.execute("""
                    UPDATE sync_log 
                    SET completed_at = CURRENT_TIMESTAMP,
                        entity_count = ?,
                        success_count = ?,
                        duration_seconds = ?
                    WHERE log_id = ?
                """, (entity_count, entity_count, duration, log_id))
            else:
                self.conn.execute("""
                    UPDATE sync_log 
                    SET completed_at = CURRENT_TIMESTAMP,
                        error_count = 1,
                        sync_data = ?,
                        duration_seconds = ?
                    WHERE log_id = ?
                """, (json.dumps({'error': error}), duration, log_id))
                
            self.conn.commit()
            
    async def auto_sync_loop(self):
        """自动同步循环"""
        settings = self.get_sync_settings()
        
        if not settings['auto_sync']:
            logger.info("自动同步已禁用")
            return
            
        interval = settings['sync_interval']
        logger.info(f"启动自动同步，间隔: {interval}秒")
        
        while True:
            try:
                # 同步各种数据
                await self.sync_projects()
                await self.sync_mod_discoveries()
                
                # 获取所有项目并同步翻译
                cursor = self.conn.cursor()
                cursor.execute("SELECT project_id FROM local_projects")
                for row in cursor.fetchall():
                    await self.sync_translations(row['project_id'])
                    
                logger.info("自动同步完成")
                
            except Exception as e:
                logger.error(f"自动同步失败: {e}")
                
            # 等待下一次同步
            await asyncio.sleep(interval)
            
    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        cursor = self.conn.cursor()
        
        # 最近同步记录
        cursor.execute("""
            SELECT * FROM sync_log 
            ORDER BY started_at DESC 
            LIMIT 10
        """)
        recent_syncs = []
        for row in cursor.fetchall():
            recent_syncs.append({
                'sync_type': row['sync_type'],
                'direction': row['sync_direction'],
                'started_at': row['started_at'],
                'completed_at': row['completed_at'],
                'entity_count': row['entity_count'],
                'success_count': row['success_count'],
                'error_count': row['error_count'],
                'duration': row['duration_seconds']
            })
            
        # 待同步统计
        cursor.execute("""
            SELECT COUNT(*) as pending FROM mod_discoveries WHERE is_uploaded = 0
        """)
        pending_mods = cursor.fetchone()['pending']
        
        cursor.execute("""
            SELECT COUNT(*) as pending FROM offline_changes WHERE is_synced = 0
        """)
        pending_changes = cursor.fetchone()['pending']
        
        return {
            'recent_syncs': recent_syncs,
            'pending': {
                'mods': pending_mods,
                'changes': pending_changes
            },
            'settings': self.get_sync_settings()
        }


async def main():
    """测试函数"""
    service = DataSyncService()
    await service.initialize()
    
    try:
        # 获取同步状态
        status = service.get_sync_status()
        print("📊 同步状态:")
        print(f"  待上传MOD: {status['pending']['mods']}")
        print(f"  待同步变更: {status['pending']['changes']}")
        print(f"  自动同步: {status['settings']['auto_sync']}")
        
        # 执行一次同步
        print("\n开始同步...")
        await service.sync_projects()
        await service.sync_mod_discoveries()
        
        print("✅ 同步完成")
        
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())