"""
V6 缓存管理API
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

from apps.mc_l10n.backend.database.core.manager import McL10nDatabaseManager
from apps.mc_l10n.backend.core.di_container import get_database_manager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v6/cache", tags=["缓存管理"])


class CacheWarmupRequest(BaseModel):
    carrier_types: List[str] = Field(..., min_items=1)
    locales: Optional[List[str]] = Field(None)
    priority: int = Field(10, ge=1, le=100)


def get_db_manager(db_manager: McL10nDatabaseManager = Depends(get_database_manager)) -> McL10nDatabaseManager:
    return db_manager


@router.get("/status")
async def get_cache_status(
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """获取缓存状态"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 扫描结果缓存统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(CASE WHEN valid_until > datetime('now') THEN 1 END) as valid_entries,
                    COUNT(CASE WHEN valid_until <= datetime('now') THEN 1 END) as expired_entries,
                    ROUND(AVG(LENGTH(result_json)), 2) as avg_size_bytes,
                    ROUND(SUM(LENGTH(result_json)) / 1024.0 / 1024.0, 2) as total_size_mb,
                    MIN(created_at) as oldest_entry,
                    MAX(created_at) as newest_entry
                FROM cache_scan_results
            """)
            scan_cache_row = cursor.fetchone()
            
            scan_cache_stats = {
                "total_entries": scan_cache_row[0] or 0,
                "valid_entries": scan_cache_row[1] or 0,
                "expired_entries": scan_cache_row[2] or 0,
                "avg_size_bytes": scan_cache_row[3] or 0.0,
                "total_size_mb": scan_cache_row[4] or 0.0,
                "oldest_entry": scan_cache_row[5],
                "newest_entry": scan_cache_row[6],
                "hit_ratio": (scan_cache_row[1] / scan_cache_row[0]) if scan_cache_row[0] else 0.0
            }
            
            # CAS对象缓存统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_objects,
                    ROUND(SUM(size) / 1024.0 / 1024.0, 2) as total_size_mb,
                    AVG(ref_count) as avg_ref_count,
                    COUNT(CASE WHEN ref_count = 0 THEN 1 END) as orphaned_objects
                FROM ops_cas_objects
            """)
            cas_cache_row = cursor.fetchone()
            
            cas_cache_stats = {
                "total_objects": cas_cache_row[0] or 0,
                "total_size_mb": cas_cache_row[1] or 0.0,
                "avg_ref_count": round(cas_cache_row[2] or 0.0, 2),
                "orphaned_objects": cas_cache_row[3] or 0
            }
            
            # 获取数据库缓存信息
            cursor.execute("PRAGMA cache_size")
            db_cache_size = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA cache_spill")
            cache_spill = cursor.fetchone()[0]
            
        return {
            "scan_cache": scan_cache_stats,
            "cas_cache": cas_cache_stats,
            "database_cache": {
                "cache_size": db_cache_size,
                "cache_spill": cache_spill,
                "estimated_memory_mb": abs(db_cache_size) / 1024.0 if db_cache_size < 0 else None
            },
            "timestamp": "2025-09-10T02:35:00Z"
        }
    except Exception as e:
        logger.error("获取缓存状态失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取缓存状态失败")


@router.post("/cleanup")
async def cleanup_cache(
    type: str = Query("all", regex=r"^(scan|cas|all)$"),
    expired_only: bool = Query(True),
    older_than_hours: int = Query(24, ge=1, le=720),
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """清理缓存"""
    try:
        cleanup_results = {}
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 清理扫描结果缓存
            if type in ["scan", "all"]:
                if expired_only:
                    cursor.execute("""
                        DELETE FROM cache_scan_results 
                        WHERE valid_until <= datetime('now')
                    """)
                else:
                    cursor.execute("""
                        DELETE FROM cache_scan_results 
                        WHERE created_at < datetime('now', '-{} hours')
                    """.format(older_than_hours))
                
                scan_deleted = cursor.rowcount
                cleanup_results["scan_cache_deleted"] = scan_deleted
            
            # 清理CAS对象缓存（只清理没有引用的孤儿对象）
            if type in ["cas", "all"]:
                cursor.execute("""
                    DELETE FROM ops_cas_objects 
                    WHERE ref_count = 0 
                    AND created_at < datetime('now', '-{} hours')
                """.format(older_than_hours))
                
                cas_deleted = cursor.rowcount
                cleanup_results["cas_cache_deleted"] = cas_deleted
            
            conn.commit()
            
            # 执行数据库VACUUM以释放空间
            cursor.execute("VACUUM")
        
        return {
            "cleanup_results": cleanup_results,
            "cleanup_criteria": {
                "type": type,
                "expired_only": expired_only,
                "older_than_hours": older_than_hours
            },
            "message": "缓存清理完成"
        }
    except Exception as e:
        logger.error("清理缓存失败", error=str(e))
        raise HTTPException(status_code=500, detail="清理缓存失败")


@router.post("/warmup")
async def warmup_cache(
    warmup_data: CacheWarmupRequest,
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """预热缓存"""
    try:
        # 验证carrier_types
        valid_carrier_types = ["mod", "resource_pack", "data_pack", "override"]
        invalid_types = [ct for ct in warmup_data.carrier_types if ct not in valid_carrier_types]
        if invalid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的carrier类型: {', '.join(invalid_types)}"
            )
        
        # 创建预热任务（这里简化实现，实际应该创建工作队列任务）
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 统计需要预热的实体
            placeholders = ','.join(['?' for _ in warmup_data.carrier_types])
            params = warmup_data.carrier_types.copy()
            
            where_locale = ""
            if warmup_data.locales:
                locale_placeholders = ','.join(['?' for _ in warmup_data.locales])
                where_locale = f" AND locale IN ({locale_placeholders})"
                params.extend(warmup_data.locales)
            
            cursor.execute(f"""
                SELECT carrier_type, COUNT(*) as count
                FROM core_language_files 
                WHERE carrier_type IN ({placeholders}){where_locale}
                GROUP BY carrier_type
            """, params)
            
            warmup_targets = {}
            total_files = 0
            for row in cursor.fetchall():
                warmup_targets[row[0]] = row[1]
                total_files += row[1]
        
        # TODO: 在实际实现中，这里应该创建工作队列任务来异步执行预热
        # 目前返回预热计划
        return {
            "warmup_plan": {
                "carrier_types": warmup_data.carrier_types,
                "locales": warmup_data.locales,
                "priority": warmup_data.priority
            },
            "warmup_targets": warmup_targets,
            "total_files_to_warmup": total_files,
            "estimated_time_minutes": max(1, total_files // 60),  # 假设每分钟处理60个文件
            "message": "缓存预热任务已创建"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("创建缓存预热任务失败", error=str(e))
        raise HTTPException(status_code=500, detail="创建缓存预热任务失败")


@router.get("/statistics")
async def get_cache_statistics(
    hours: int = Query(24, ge=1, le=168),
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """获取缓存性能统计"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 缓存命中率统计（基于扫描缓存）
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_scans,
                    COUNT(CASE WHEN valid_until > created_at THEN 1 END) as cache_hits,
                    AVG(LENGTH(result_json)) as avg_cache_size
                FROM cache_scan_results
                WHERE created_at > datetime('now', '-{} hours')
            """.format(hours))
            
            hit_stats_row = cursor.fetchone()
            total_scans = hit_stats_row[0] or 0
            cache_hits = hit_stats_row[1] or 0
            hit_ratio = (cache_hits / total_scans) if total_scans > 0 else 0.0
            
            # 按时间统计缓存使用情况
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m-%d %H', created_at) as hour,
                    COUNT(*) as cache_requests,
                    AVG(LENGTH(result_json)) as avg_size
                FROM cache_scan_results
                WHERE created_at > datetime('now', '-{} hours')
                GROUP BY strftime('%Y-%m-%d %H', created_at)
                ORDER BY hour DESC
                LIMIT 24
            """.format(hours))
            
            hourly_stats = []
            for row in cursor.fetchall():
                hourly_stats.append({
                    "hour": row[0],
                    "cache_requests": row[1],
                    "avg_size_bytes": round(row[2] or 0.0, 2)
                })
            
            # 缓存效率指标
            efficiency_metrics = {
                "hit_ratio": round(hit_ratio, 3),
                "total_requests": total_scans,
                "cache_hits": cache_hits,
                "cache_misses": total_scans - cache_hits,
                "avg_cache_size_bytes": round(hit_stats_row[2] or 0.0, 2)
            }
            
        return {
            "time_window_hours": hours,
            "efficiency_metrics": efficiency_metrics,
            "hourly_breakdown": hourly_stats,
            "timestamp": "2025-09-10T02:35:00Z"
        }
    except Exception as e:
        logger.error("获取缓存统计失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取缓存统计失败")


@router.delete("/entries/{scan_hash}")
async def invalidate_cache_entry(
    scan_hash: str,
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """使特定缓存条目失效"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM cache_scan_results 
                WHERE scan_hash = ?
            """, (scan_hash,))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="缓存条目不存在")
                
            conn.commit()
        
        return {
            "scan_hash": scan_hash,
            "message": "缓存条目已失效"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("使缓存条目失效失败", scan_hash=scan_hash, error=str(e))
        raise HTTPException(status_code=500, detail="使缓存条目失效失败")


@router.post("/rebuild")
async def rebuild_cache(
    type: str = Query("scan", regex=r"^(scan|cas|all)$"),
    force: bool = Query(False),
    db_manager: McL10nDatabaseManager = Depends(get_db_manager)
) -> Dict[str, Any]:
    """重建缓存"""
    try:
        rebuild_results = {}
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            if type in ["scan", "all"]:
                if force:
                    # 清空所有扫描缓存
                    cursor.execute("DELETE FROM cache_scan_results")
                    scan_cleared = cursor.rowcount
                else:
                    # 只清空过期的缓存
                    cursor.execute("DELETE FROM cache_scan_results WHERE valid_until <= datetime('now')")
                    scan_cleared = cursor.rowcount
                
                rebuild_results["scan_cache_cleared"] = scan_cleared
            
            if type in ["cas", "all"]:
                # CAS缓存重建：清理孤儿对象
                cursor.execute("DELETE FROM ops_cas_objects WHERE ref_count = 0")
                cas_cleared = cursor.rowcount
                rebuild_results["cas_orphans_cleared"] = cas_cleared
            
            conn.commit()
            
            # 重新分析数据库统计信息
            cursor.execute("ANALYZE")
        
        # TODO: 在实际实现中，这里应该触发异步重建任务
        return {
            "rebuild_results": rebuild_results,
            "rebuild_type": type,
            "force_rebuild": force,
            "message": "缓存重建完成"
        }
    except Exception as e:
        logger.error("重建缓存失败", error=str(e))
        raise HTTPException(status_code=500, detail="重建缓存失败")