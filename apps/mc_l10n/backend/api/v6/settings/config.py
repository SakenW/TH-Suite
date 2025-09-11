"""
V6 配置管理API
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import json
import structlog

from apps.mc_l10n.backend.database.core.manager import McL10nDatabaseManager
from apps.mc_l10n.backend.core.di_container import get_database_manager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/settings", tags=["配置管理"])


class SettingUpdateRequest(BaseModel):
    value: Any = Field(...)


def get_db_manager(db_manager: McL10nDatabaseManager = Depends(get_database_manager)) -> McL10nDatabaseManager:
    return db_manager


@router.get("")
async def list_settings(
    prefix: Optional[str] = None,
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """列出所有配置项"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            if prefix:
                cursor.execute("""
                    SELECT key, value_json, updated_at 
                    FROM cfg_local_settings 
                    WHERE key LIKE ? 
                    ORDER BY key
                """, (f"{prefix}%",))
            else:
                cursor.execute("""
                    SELECT key, value_json, updated_at 
                    FROM cfg_local_settings 
                    ORDER BY key
                """)
            
            settings = {}
            for row in cursor.fetchall():
                try:
                    settings[row[0]] = {
                        "value": json.loads(row[1]),
                        "updated_at": row[2]
                    }
                except json.JSONDecodeError:
                    logger.warning("配置项JSON解析失败", key=row[0])
                    settings[row[0]] = {
                        "value": row[1],
                        "updated_at": row[2],
                        "error": "JSON解析失败"
                    }
            
        return {"settings": settings}
    except Exception as e:
        logger.error("列出配置项失败", error=str(e))
        raise HTTPException(status_code=500, detail="列出配置项失败")


@router.get("/{key}")
async def get_setting(
    key: str,
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """获取单个配置项"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT value_json, updated_at 
                FROM cfg_local_settings 
                WHERE key = ?
            """, (key,))
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="配置项不存在")
            
            try:
                value = json.loads(row[0])
            except json.JSONDecodeError:
                value = row[0]
            
            return {
                "key": key,
                "value": value,
                "updated_at": row[1]
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取配置项失败", key=key, error=str(e))
        raise HTTPException(status_code=500, detail="获取配置项失败")


@router.put("/{key}")
async def update_setting(
    key: str,
    setting_data: SettingUpdateRequest,
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """更新配置项"""
    try:
        # 将值序列化为JSON
        value_json = json.dumps(setting_data.value, ensure_ascii=False)
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cfg_local_settings (key, value_json, updated_at)
                VALUES (?, ?, datetime('now'))
            """, (key, value_json))
            conn.commit()
        
        return {
            "key": key,
            "value": setting_data.value,
            "message": "配置项更新成功"
        }
    except Exception as e:
        logger.error("更新配置项失败", key=key, error=str(e))
        raise HTTPException(status_code=500, detail="更新配置项失败")


@router.delete("/{key}")
async def delete_setting(
    key: str,
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """删除配置项"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cfg_local_settings WHERE key = ?", (key,))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="配置项不存在")
                
            conn.commit()
        
        return {"message": "配置项删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("删除配置项失败", key=key, error=str(e))
        raise HTTPException(status_code=500, detail="删除配置项失败")


@router.post("/batch")
async def batch_update_settings(
    settings: Dict[str, Any],
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """批量更新配置项"""
    try:
        if not settings:
            raise HTTPException(status_code=400, detail="配置项不能为空")
            
        if len(settings) > 100:
            raise HTTPException(status_code=400, detail="批量更新数量不能超过100个")
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            for key, value in settings.items():
                value_json = json.dumps(value, ensure_ascii=False)
                cursor.execute("""
                    INSERT OR REPLACE INTO cfg_local_settings (key, value_json, updated_at)
                    VALUES (?, ?, datetime('now'))
                """, (key, value_json))
            
            conn.commit()
        
        return {
            "updated_count": len(settings),
            "keys": list(settings.keys()),
            "message": "批量更新配置项成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("批量更新配置项失败", error=str(e))
        raise HTTPException(status_code=500, detail="批量更新配置项失败")


# 预定义的默认配置项
DEFAULT_SETTINGS = {
    "sync.interval_seconds": 300,
    "sync.chunk_size_mb": 2,
    "sync.max_concurrent": 4,
    "sync.retry_attempts": 3,
    "cache.scan_results_ttl_hours": 24,
    "cache.max_size_mb": 100,
    "queue.max_pending": 1000,
    "queue.cleanup_interval_hours": 6,
    "ui.theme": "light",
    "ui.language": "zh_cn",
    "scan.parallel_workers": 4,
    "scan.deep_scan_enabled": True,
    "export.default_format": "json",
    "export.batch_size": 1000
}


@router.post("/reset")
async def reset_to_defaults(
    keys: Optional[str] = None,  # 逗号分隔的key列表，为空则重置所有
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """重置配置项到默认值"""
    try:
        if keys:
            key_list = [k.strip() for k in keys.split(',') if k.strip()]
            settings_to_reset = {k: v for k, v in DEFAULT_SETTINGS.items() if k in key_list}
            
            # 检查是否有不存在的key
            missing_keys = [k for k in key_list if k not in DEFAULT_SETTINGS]
            if missing_keys:
                raise HTTPException(
                    status_code=400, 
                    detail=f"以下配置项没有默认值: {', '.join(missing_keys)}"
                )
        else:
            settings_to_reset = DEFAULT_SETTINGS
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            for key, value in settings_to_reset.items():
                value_json = json.dumps(value, ensure_ascii=False)
                cursor.execute("""
                    INSERT OR REPLACE INTO cfg_local_settings (key, value_json, updated_at)
                    VALUES (?, ?, datetime('now'))
                """, (key, value_json))
            
            conn.commit()
        
        return {
            "reset_count": len(settings_to_reset),
            "reset_keys": list(settings_to_reset.keys()),
            "message": "配置项重置成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("重置配置项失败", error=str(e))
        raise HTTPException(status_code=500, detail="重置配置项失败")


@router.get("/defaults")
async def get_default_settings() -> Dict[str, Any]:
    """获取默认配置项"""
    return {"default_settings": DEFAULT_SETTINGS}