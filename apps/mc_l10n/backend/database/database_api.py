#!/usr/bin/env python
"""
数据库查询API接口
提供FastAPI路由接口用于数据库查询和操作
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import sqlite3
import json
from pathlib import Path

# 导入服务模块
from .scan_service import ScanDatabaseService
from .sync_service import DataSyncService, SyncDirection
from .offline_tracker import OfflineChangeTracker, EntityType, ChangeOperation


# Pydantic模型定义

class ModInfo(BaseModel):
    """MOD信息模型"""
    mod_id: str
    mod_name: str
    display_name: Optional[str]
    version: Optional[str]
    minecraft_version: Optional[str]
    mod_loader: Optional[str]
    file_path: str
    language_count: int = 0
    total_keys: int = 0


class TranslationEntry(BaseModel):
    """翻译条目模型"""
    entry_id: str
    translation_key: str
    original_text: Optional[str]
    translated_text: Optional[str]
    status: str = "pending"


class ScanRequest(BaseModel):
    """扫描请求模型"""
    scan_path: str
    recursive: bool = True
    force_rescan: bool = False


class TranslationUpdate(BaseModel):
    """翻译更新模型"""
    entry_id: str
    translated_text: str
    status: Optional[str] = "translated"


class ProjectCreate(BaseModel):
    """项目创建模型"""
    project_name: str
    target_language: str = "zh_cn"
    source_language: str = "en_us"
    scan_paths: List[str] = Field(default_factory=list)


class SyncRequest(BaseModel):
    """同步请求模型"""
    sync_type: str  # projects, mods, translations
    direction: str = "bidirectional"  # upload, download, bidirectional


class DatabaseStatistics(BaseModel):
    """数据库统计模型"""
    mods_total: int
    mods_uploaded: int
    language_files: int
    translation_entries: int
    pending_changes: int
    cache_entries: int


# 创建API路由
router = APIRouter(prefix="/api/database", tags=["database"])


# 依赖注入函数
def get_scan_service():
    """获取扫描服务实例"""
    return ScanDatabaseService("mc_l10n_local.db")


def get_sync_service():
    """获取同步服务实例"""
    return DataSyncService("mc_l10n_local.db")


def get_tracker():
    """获取离线跟踪器实例"""
    return OfflineChangeTracker("mc_l10n_local.db")


# API端点

@router.get("/statistics", response_model=DatabaseStatistics)
async def get_statistics(scan_service: ScanDatabaseService = Depends(get_scan_service)):
    """获取数据库统计信息"""
    try:
        stats = scan_service.get_statistics()
        
        return DatabaseStatistics(
            mods_total=stats['mods']['total'],
            mods_uploaded=stats['mods']['uploaded'],
            language_files=stats['language_files'],
            translation_entries=stats['translation_entries']['total'],
            pending_changes=stats.get('pending_changes', 0),
            cache_entries=stats.get('cache_entries', 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mods", response_model=List[ModInfo])
async def get_mods(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    scan_service: ScanDatabaseService = Depends(get_scan_service)
):
    """获取MOD列表"""
    try:
        cursor = scan_service.conn.cursor()
        cursor.execute("""
            SELECT * FROM mod_discoveries
            ORDER BY discovered_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        mods = []
        for row in cursor.fetchall():
            mods.append(ModInfo(
                mod_id=row['mod_id'],
                mod_name=row['mod_name'],
                display_name=row['display_name'],
                version=row['version'],
                minecraft_version=row['minecraft_version'],
                mod_loader=row['mod_loader'],
                file_path=row['file_path'],
                language_count=row['language_count'],
                total_keys=row['total_keys']
            ))
            
        return mods
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mods/{mod_id}")
async def get_mod_detail(
    mod_id: str,
    scan_service: ScanDatabaseService = Depends(get_scan_service)
):
    """获取MOD详细信息"""
    try:
        cursor = scan_service.conn.cursor()
        cursor.execute("""
            SELECT * FROM mod_discoveries WHERE mod_id = ?
        """, (mod_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="MOD not found")
            
        # 获取语言文件
        cursor.execute("""
            SELECT * FROM language_file_cache WHERE mod_id = ?
        """, (mod_id,))
        
        language_files = []
        for lang_row in cursor.fetchall():
            language_files.append({
                'language_code': lang_row['language_code'],
                'file_path': lang_row['file_path'],
                'entry_count': lang_row['entry_count'],
                'cached_at': lang_row['cached_at']
            })
            
        return {
            'mod_info': ModInfo(
                mod_id=row['mod_id'],
                mod_name=row['mod_name'],
                display_name=row['display_name'],
                version=row['version'],
                minecraft_version=row['minecraft_version'],
                mod_loader=row['mod_loader'],
                file_path=row['file_path'],
                language_count=row['language_count'],
                total_keys=row['total_keys']
            ),
            'language_files': language_files,
            'metadata': json.loads(row['metadata']) if row['metadata'] else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/translations/{mod_id}/{language_code}")
async def get_translations(
    mod_id: str,
    language_code: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    scan_service: ScanDatabaseService = Depends(get_scan_service)
):
    """获取翻译条目"""
    try:
        # 获取语言文件缓存ID
        cursor = scan_service.conn.cursor()
        cursor.execute("""
            SELECT cache_id FROM language_file_cache
            WHERE mod_id = ? AND language_code = ?
        """, (mod_id, language_code))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Language file not found")
            
        cache_id = result['cache_id']
        
        # 构建查询
        query = """
            SELECT * FROM translation_entry_cache
            WHERE cache_id = ?
        """
        params = [cache_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
            
        query += " ORDER BY translation_key LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        entries = []
        for row in cursor.fetchall():
            entries.append(TranslationEntry(
                entry_id=row['entry_id'],
                translation_key=row['translation_key'],
                original_text=row['original_text'],
                translated_text=row['translated_text'],
                status=row['status']
            ))
            
        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan")
async def scan_directory(
    request: ScanRequest,
    scan_service: ScanDatabaseService = Depends(get_scan_service)
):
    """扫描目录"""
    try:
        scan_path = Path(request.scan_path)
        
        if not scan_path.exists():
            raise HTTPException(status_code=400, detail="Path does not exist")
            
        if scan_path.is_file():
            # 扫描单个文件
            result = scan_service.discover_mod(scan_path)
            if result:
                return {"success": True, "mods": [result]}
            else:
                return {"success": False, "error": "Failed to parse mod"}
        else:
            # 扫描目录
            results = scan_service.scan_directory(scan_path)
            return {
                "success": True,
                "total_files": results['total_files'],
                "successful": results['successful'],
                "failed": results['failed'],
                "mods": results['mods'][:10]  # 返回前10个结果
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/translations/{entry_id}")
async def update_translation(
    entry_id: str,
    update: TranslationUpdate,
    tracker: OfflineChangeTracker = Depends(get_tracker)
):
    """更新翻译"""
    try:
        # 更新数据库
        conn = sqlite3.connect("mc_l10n_local.db")
        cursor = conn.cursor()
        
        # 获取当前值
        cursor.execute("""
            SELECT * FROM translation_entry_cache WHERE entry_id = ?
        """, (entry_id,))
        
        current = cursor.fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Translation entry not found")
            
        # 更新翻译
        cursor.execute("""
            UPDATE translation_entry_cache
            SET translated_text = ?, status = ?, cached_at = CURRENT_TIMESTAMP
            WHERE entry_id = ?
        """, (update.translated_text, update.status, entry_id))
        
        conn.commit()
        
        # 跟踪变更（触发器会自动处理）
        
        return {"success": True, "message": "Translation updated"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()


@router.post("/projects")
async def create_project(
    project: ProjectCreate,
    tracker: OfflineChangeTracker = Depends(get_tracker)
):
    """创建项目"""
    try:
        import uuid
        project_id = str(uuid.uuid4())
        
        conn = sqlite3.connect("mc_l10n_local.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO local_projects (
                project_id, project_name, target_language, 
                source_language, scan_paths
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            project_id,
            project.project_name,
            project.target_language,
            project.source_language,
            json.dumps(project.scan_paths)
        ))
        
        conn.commit()
        
        return {
            "success": True,
            "project_id": project_id,
            "message": "Project created"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()


@router.post("/sync")
async def sync_data(
    request: SyncRequest,
    sync_service: DataSyncService = Depends(get_sync_service)
):
    """同步数据"""
    try:
        await sync_service.initialize()
        
        direction_map = {
            'upload': SyncDirection.UPLOAD,
            'download': SyncDirection.DOWNLOAD,
            'bidirectional': SyncDirection.BIDIRECTIONAL
        }
        
        direction = direction_map.get(request.direction, SyncDirection.BIDIRECTIONAL)
        
        if request.sync_type == 'projects':
            await sync_service.sync_projects(direction)
        elif request.sync_type == 'mods':
            await sync_service.sync_mod_discoveries()
        elif request.sync_type == 'translations':
            # 需要项目ID
            raise HTTPException(status_code=400, detail="Project ID required for translation sync")
            
        return {"success": True, "message": f"Sync {request.sync_type} completed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await sync_service.close()


@router.get("/sync/status")
async def get_sync_status(sync_service: DataSyncService = Depends(get_sync_service)):
    """获取同步状态"""
    try:
        status = sync_service.get_sync_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/changes/summary")
async def get_change_summary(tracker: OfflineChangeTracker = Depends(get_tracker)):
    """获取变更摘要"""
    try:
        summary = tracker.get_change_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/changes/pending")
async def get_pending_changes(
    entity_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    tracker: OfflineChangeTracker = Depends(get_tracker)
):
    """获取待同步变更"""
    try:
        entity_type_enum = None
        if entity_type:
            entity_type_enum = EntityType(entity_type)
            
        changes = tracker.get_pending_changes(entity_type_enum, limit)
        return changes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/cleanup")
async def cleanup_cache(scan_service: ScanDatabaseService = Depends(get_scan_service)):
    """清理过期缓存"""
    try:
        scan_service.cleanup_expired_cache()
        return {"success": True, "message": "Cache cleanup completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings")
async def get_settings():
    """获取本地设置"""
    try:
        conn = sqlite3.connect("mc_l10n_local.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM local_settings")
        
        settings = {}
        for row in cursor.fetchall():
            settings[row['setting_key']] = {
                'value': row['setting_value'],
                'type': row['setting_type'],
                'description': row['description']
            }
            
        return settings
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()


@router.put("/settings/{key}")
async def update_setting(key: str, value: str):
    """更新设置"""
    try:
        conn = sqlite3.connect("mc_l10n_local.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE local_settings
            SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE setting_key = ?
        """, (value, key))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Setting not found")
            
        conn.commit()
        
        return {"success": True, "message": "Setting updated"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()


# 导出路由
__all__ = ['router']