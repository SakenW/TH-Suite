"""
优化扫描API路由
提供高性能扫描功能，专门针对大型整合包优化
"""

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from infrastructure.services.optimized_minecraft_scanner import get_optimized_minecraft_scanner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scan-optimized", tags=["优化扫描"])


class OptimizedScanRequest(BaseModel):
    """优化扫描请求"""
    directory: str
    incremental: bool = True
    max_concurrent_jars: int = 8
    max_file_size_mb: int = 100
    enable_cache: bool = True
    skip_known_non_mods: bool = True


@router.post("/start")
async def start_optimized_scan(request: OptimizedScanRequest) -> Dict[str, Any]:
    """
    启动优化扫描
    
    针对大型整合包进行优化：
    - 🔄 并发处理JAR文件
    - 💾 智能缓存系统
    - 📁 分层目录扫描策略
    - ⚡ 增量更新机制
    """
    try:
        logger.info(f"🚀 启动优化扫描请求: {request.directory}")
        
        # 验证目录存在
        if not os.path.exists(request.directory):
            raise HTTPException(
                status_code=400,
                detail=f"目录不存在: {request.directory}"
            )
        
        # 获取优化扫描服务
        scanner = get_optimized_minecraft_scanner()
        
        # 准备扫描选项
        scan_options = {
            "max_concurrent_jars": request.max_concurrent_jars,
            "max_file_size_mb": request.max_file_size_mb,
            "enable_cache": request.enable_cache,
            "skip_known_non_mods": request.skip_known_non_mods
        }
        
        # 启动扫描
        result = await scanner.start_scan(
            target_path=request.directory,
            incremental=request.incremental,
            scan_options=scan_options
        )
        
        if result["success"]:
            logger.info(f"✅ 优化扫描启动成功: {result['scan_id']}")
        else:
            logger.error(f"❌ 优化扫描启动失败: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"优化扫描启动异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"启动优化扫描失败: {str(e)}"
        )


@router.get("/status/{scan_id}")
async def get_optimized_scan_status(scan_id: str) -> Dict[str, Any]:
    """
    获取优化扫描状态
    
    返回详细的扫描进度和性能指标
    """
    try:
        scanner = get_optimized_minecraft_scanner()
        result = await scanner.get_scan_status(scan_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "扫描记录不存在")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取优化扫描状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取扫描状态失败: {str(e)}"
        )


@router.post("/cancel/{scan_id}")
async def cancel_optimized_scan(scan_id: str) -> Dict[str, Any]:
    """取消优化扫描"""
    try:
        scanner = get_optimized_minecraft_scanner()
        success = await scanner.cancel_scan(scan_id)
        
        if success:
            return {
                "success": True,
                "message": f"优化扫描已取消: {scan_id}"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="扫描记录不存在或无法取消"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消优化扫描失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"取消扫描失败: {str(e)}"
        )


@router.get("/config")
async def get_scan_config() -> Dict[str, Any]:
    """获取优化扫描配置"""
    scanner = get_optimized_minecraft_scanner()
    return {
        "success": True,
        "config": {
            "max_concurrent_jars": scanner.config.max_concurrent_jars,
            "max_file_size_mb": scanner.config.max_file_size_mb,
            "enable_cache": scanner.config.enable_cache,
            "cache_ttl_hours": scanner.config.cache_ttl_hours,
            "skip_known_non_mods": scanner.config.skip_known_non_mods,
            "deep_scan_threshold": scanner.config.deep_scan_threshold
        },
        "optimizations": [
            "🔄 并发JAR处理 - 同时处理多个文件",
            "💾 智能缓存 - 避免重复扫描相同文件",
            "📁 分层扫描 - 优先扫描已知MOD目录",
            "⚡ 增量更新 - 只处理变更的文件",
            "🚫 智能过滤 - 跳过已知非MOD文件",
            "🎯 整合包检测 - 针对整合包结构优化"
        ]
    }


@router.post("/benchmark")
async def benchmark_scan_performance(
    directory: str = Query(..., description="测试目录路径"),
    compare_with_original: bool = Query(False, description="是否与原始扫描器对比")
) -> Dict[str, Any]:
    """
    性能基准测试
    
    对比优化扫描器与原始扫描器的性能差异
    """
    try:
        import time
        import asyncio
        from infrastructure.services.simple_minecraft_scanner import get_simple_minecraft_scanner_service
        
        if not os.path.exists(directory):
            raise HTTPException(
                status_code=400,
                detail=f"测试目录不存在: {directory}"
            )
        
        results = {
            "success": True,
            "test_directory": directory,
            "optimized_scanner": {},
            "performance_improvement": {}
        }
        
        # 测试优化扫描器
        logger.info(f"🧪 开始优化扫描器性能测试: {directory}")
        opt_scanner = get_optimized_minecraft_scanner()
        
        opt_start_time = time.time()
        opt_result = await opt_scanner.start_scan(
            target_path=directory,
            incremental=False,  # 禁用增量扫描确保公平对比
            scan_options={"enable_cache": False}  # 禁用缓存确保公平对比
        )
        
        if opt_result["success"]:
            # 等待扫描完成
            opt_scan_id = opt_result["scan_id"]
            while True:
                status = await opt_scanner.get_scan_status(opt_scan_id)
                if status["status"] in ["completed", "failed", "cancelled"]:
                    break
                await asyncio.sleep(0.5)
            
            opt_duration = time.time() - opt_start_time
            opt_final_status = await opt_scanner.get_scan_status(opt_scan_id)
            
            results["optimized_scanner"] = {
                "duration_seconds": opt_duration,
                "mods_found": opt_final_status.get("statistics", {}).get("mods_found", 0),
                "language_files_found": opt_final_status.get("statistics", {}).get("language_files_found", 0),
                "total_translation_keys": opt_final_status.get("statistics", {}).get("total_translation_keys", 0)
            }
        
        # 可选：与原始扫描器对比
        if compare_with_original:
            logger.info(f"🧪 开始原始扫描器性能测试: {directory}")
            simple_scanner = get_simple_minecraft_scanner_service()
            
            simple_start_time = time.time()
            simple_result = await simple_scanner.start_scan(
                target_path=directory,
                incremental=False
            )
            
            if simple_result["success"]:
                # 等待扫描完成
                simple_scan_id = simple_result["scan_id"]
                while True:
                    status = await simple_scanner.get_scan_status(simple_scan_id)
                    if status["status"] in ["completed", "failed", "cancelled"]:
                        break
                    await asyncio.sleep(0.5)
                
                simple_duration = time.time() - simple_start_time
                simple_final_status = await simple_scanner.get_scan_status(simple_scan_id)
                
                results["original_scanner"] = {
                    "duration_seconds": simple_duration,
                    "mods_found": simple_final_status.get("statistics", {}).get("mods_found", 0),
                    "language_files_found": simple_final_status.get("statistics", {}).get("language_files_found", 0),
                    "total_translation_keys": simple_final_status.get("statistics", {}).get("total_translation_keys", 0)
                }
                
                # 计算性能提升
                if simple_duration > 0:
                    speed_improvement = (simple_duration - opt_duration) / simple_duration * 100
                    results["performance_improvement"] = {
                        "speed_improvement_percent": round(speed_improvement, 2),
                        "time_saved_seconds": round(simple_duration - opt_duration, 2),
                        "efficiency_ratio": round(simple_duration / opt_duration, 2)
                    }
        
        logger.info(f"🧪 性能测试完成: 优化扫描器用时 {opt_duration:.2f}s")
        return results
        
    except Exception as e:
        logger.error(f"性能基准测试失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"性能测试失败: {str(e)}"
        )