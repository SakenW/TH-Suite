"""
低内存扫描API路由
专为配置受限的电脑设计，确保在低内存环境下稳定运行
"""

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from infrastructure.services.low_memory_minecraft_scanner import get_low_memory_minecraft_scanner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scan-low-memory", tags=["低内存扫描"])


class LowMemoryScanRequest(BaseModel):
    """低内存扫描请求"""
    directory: str
    incremental: bool = True
    memory_limit_mb: int = 512  # 内存限制
    batch_size: int = 2         # 批处理大小
    max_file_size_mb: int = 50  # 最大文件大小


@router.post("/start")
async def start_low_memory_scan(request: LowMemoryScanRequest) -> Dict[str, Any]:
    """
    启动低内存扫描
    
    专为配置受限的电脑优化：
    - 🧠 恒定内存使用 - 不超过设定的内存限制
    - 🔄 小批量处理 - 避免内存峰值
    - 📊 实时内存监控 - 自动垃圾回收
    - ⚡ 流式读取 - 不在内存中积累大量数据
    
    推荐配置：
    - 4GB内存电脑：memory_limit_mb=256, batch_size=1
    - 8GB内存电脑：memory_limit_mb=512, batch_size=2  
    - 16GB内存电脑：memory_limit_mb=1024, batch_size=4
    """
    try:
        logger.info(f"🧠 启动低内存扫描请求: {request.directory}")
        
        # 验证目录存在
        if not os.path.exists(request.directory):
            raise HTTPException(
                status_code=400,
                detail=f"目录不存在: {request.directory}"
            )
        
        # 验证内存限制
        if request.memory_limit_mb < 128:
            raise HTTPException(
                status_code=400,
                detail="内存限制不能小于128MB"
            )
        
        if request.memory_limit_mb > 4096:
            logger.warning(f"内存限制过高: {request.memory_limit_mb}MB，建议使用标准扫描器")
        
        # 获取低内存扫描服务
        scanner = get_low_memory_minecraft_scanner(
            memory_limit_mb=request.memory_limit_mb
        )
        
        # 准备扫描选项
        scan_options = {
            "batch_size": request.batch_size,
            "max_file_size_mb": request.max_file_size_mb
        }
        
        # 启动扫描
        result = await scanner.start_scan(
            target_path=request.directory,
            incremental=request.incremental,
            scan_options=scan_options
        )
        
        if result["success"]:
            logger.info(f"✅ 低内存扫描启动成功: {result['scan_id']}")
        else:
            logger.error(f"❌ 低内存扫描启动失败: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"低内存扫描启动异常: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"启动低内存扫描失败: {str(e)}"
        )


@router.get("/status/{scan_id}")
async def get_low_memory_scan_status(scan_id: str) -> Dict[str, Any]:
    """
    获取低内存扫描状态
    
    返回详细的扫描进度和内存使用情况
    """
    try:
        scanner = get_low_memory_minecraft_scanner()
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
        logger.error(f"获取低内存扫描状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取扫描状态失败: {str(e)}"
        )


@router.post("/cancel/{scan_id}")
async def cancel_low_memory_scan(scan_id: str) -> Dict[str, Any]:
    """取消低内存扫描"""
    try:
        scanner = get_low_memory_minecraft_scanner()
        success = await scanner.cancel_scan(scan_id)
        
        if success:
            return {
                "success": True,
                "message": f"低内存扫描已取消: {scan_id}"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="扫描记录不存在或无法取消"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消低内存扫描失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"取消扫描失败: {str(e)}"
        )


@router.get("/memory-recommendations")
async def get_memory_recommendations() -> Dict[str, Any]:
    """获取内存配置推荐"""
    try:
        import psutil
        
        # 获取系统内存信息
        memory = psutil.virtual_memory()
        total_gb = memory.total / (1024**3)
        available_gb = memory.available / (1024**3)
        
        # 基于系统内存推荐配置
        if total_gb <= 4:
            recommendation = {
                "config_level": "低配置模式",
                "memory_limit_mb": 256,
                "batch_size": 1,
                "max_file_size_mb": 30,
                "description": "适用于4GB以下内存的电脑，保守配置确保系统稳定"
            }
        elif total_gb <= 8:
            recommendation = {
                "config_level": "中等配置模式", 
                "memory_limit_mb": 512,
                "batch_size": 2,
                "max_file_size_mb": 50,
                "description": "适用于4-8GB内存的电脑，平衡性能和稳定性"
            }
        elif total_gb <= 16:
            recommendation = {
                "config_level": "高配置模式",
                "memory_limit_mb": 1024,
                "batch_size": 4,
                "max_file_size_mb": 100,
                "description": "适用于8-16GB内存的电脑，较好的扫描性能"
            }
        else:
            recommendation = {
                "config_level": "高端配置模式",
                "memory_limit_mb": 2048,
                "batch_size": 8,
                "max_file_size_mb": 200,
                "description": "适用于16GB以上内存的电脑，建议使用标准扫描器获得最佳性能"
            }
        
        return {
            "success": True,
            "system_info": {
                "total_memory_gb": round(total_gb, 1),
                "available_memory_gb": round(available_gb, 1),
                "memory_usage_percent": memory.percent
            },
            "recommended_config": recommendation,
            "memory_optimization_tips": [
                "💡 关闭其他大型应用程序释放内存",
                "🔄 如果扫描过程中内存不足，会自动降低批处理大小",
                "📊 实时监控内存使用，超过80%时自动清理",
                "⚠️ 如果经常触发内存清理，请降低memory_limit_mb设置",
                "🚀 扫描完成后内存会自动释放到初始水平"
            ]
        }
        
    except Exception as e:
        logger.error(f"获取内存推荐失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取内存推荐失败: {str(e)}"
        )


@router.get("/system-memory")
async def get_system_memory_info() -> Dict[str, Any]:
    """获取系统内存信息"""
    try:
        import psutil
        
        # 系统内存
        memory = psutil.virtual_memory()
        
        # 当前进程内存
        process = psutil.Process()
        process_memory = process.memory_info()
        
        return {
            "success": True,
            "system_memory": {
                "total_mb": round(memory.total / (1024**2), 1),
                "available_mb": round(memory.available / (1024**2), 1),
                "used_mb": round(memory.used / (1024**2), 1),
                "percent": memory.percent,
                "free_mb": round(memory.free / (1024**2), 1)
            },
            "process_memory": {
                "rss_mb": round(process_memory.rss / (1024**2), 1),
                "vms_mb": round(process_memory.vms / (1024**2), 1),
                "percent": round(process.memory_percent(), 2)
            },
            "recommendations": {
                "safe_limit_mb": round(memory.available * 0.3 / (1024**2)),
                "conservative_limit_mb": round(memory.available * 0.2 / (1024**2)),
                "status": "充足" if memory.percent < 70 else "紧张" if memory.percent < 85 else "不足"
            }
        }
        
    except Exception as e:
        logger.error(f"获取系统内存信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取系统信息失败: {str(e)}"
        )


@router.post("/memory-test")
async def test_memory_usage(
    memory_limit_mb: int = Query(512, description="内存限制(MB)"),
    duration_seconds: int = Query(30, description="测试时长(秒)")
) -> Dict[str, Any]:
    """
    内存使用测试
    
    模拟扫描过程的内存使用，帮助确定合适的配置
    """
    if duration_seconds > 300:  # 限制最长5分钟
        raise HTTPException(status_code=400, detail="测试时长不能超过5分钟")
    
    try:
        import psutil
        import time
        import gc
        
        # 获取初始内存
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024**2)
        
        logger.info(f"🧪 开始内存测试: 限制={memory_limit_mb}MB, 时长={duration_seconds}s")
        
        # 模拟内存使用
        test_data = []
        max_memory = initial_memory
        gc_count = 0
        
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            # 模拟处理数据
            chunk = ['test_data'] * 1000  # 约8KB数据
            test_data.append(chunk)
            
            # 检查内存使用
            current_memory = process.memory_info().rss / (1024**2)
            max_memory = max(max_memory, current_memory)
            
            # 模拟内存限制检查
            if current_memory > memory_limit_mb * 0.8:
                gc.collect()
                test_data.clear()
                gc_count += 1
                current_memory = process.memory_info().rss / (1024**2)
            
            time.sleep(0.1)
        
        # 清理测试数据
        test_data.clear()
        gc.collect()
        
        final_memory = process.memory_info().rss / (1024**2)
        
        return {
            "success": True,
            "test_results": {
                "initial_memory_mb": round(initial_memory, 1),
                "max_memory_mb": round(max_memory, 1),
                "final_memory_mb": round(final_memory, 1),
                "memory_increase_mb": round(max_memory - initial_memory, 1),
                "gc_triggered_count": gc_count,
                "memory_limit_mb": memory_limit_mb,
                "limit_exceeded": max_memory > memory_limit_mb
            },
            "assessment": {
                "memory_efficiency": "优秀" if max_memory < memory_limit_mb * 0.7 else 
                                   "良好" if max_memory < memory_limit_mb * 0.9 else "需要调整",
                "recommended_action": 
                    "当前配置合适" if max_memory < memory_limit_mb * 0.8 else
                    f"建议降低memory_limit_mb到{int(max_memory * 1.2)}MB" if max_memory > memory_limit_mb else
                    "配置偏保守，可以适当提高内存限制"
            }
        }
        
    except Exception as e:
        logger.error(f"内存测试失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"内存测试失败: {str(e)}"
        )