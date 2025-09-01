# apps/mc-l10n/backend/api/routes/scan_routes.py
"""
扫描相关API路由

提供项目和MOD扫描的REST API端点
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/scan", tags=["扫描"])


@router.get("/health")
async def scan_health_check():
    """扫描服务健康检查"""
    return {"status": "healthy", "service": "scan"}


@router.get("/test")
async def scan_test():
    """扫描服务测试端点"""
    return {
        "message": "扫描服务正在运行",
        "available_endpoints": [
            "/api/scan/health",
            "/api/scan/test",
            "/api/scan/project/start",
            "/api/scan/progress/{task_id}",
            "/api/v1/scan-project"
        ]
    }


from pydantic import BaseModel

class ScanRequest(BaseModel):
    path: str

@router.post("/project/start")
async def start_project_scan(request: ScanRequest):
    """启动项目扫描任务（模拟）"""
    import uuid
    import asyncio
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 模拟异步扫描任务
    async def simulate_scan():
        await asyncio.sleep(2)  # 模拟扫描时间
    
    # 启动后台任务
    asyncio.create_task(simulate_scan())
    
    return {
        "task_id": task_id,
        "message": "扫描任务已启动",
        "status": "started"
    }


# 存储扫描进度的简单内存存储
scan_progress_store = {}


@router.get("/progress/{task_id}")
async def get_scan_progress(task_id: str):
    """获取扫描进度"""
    import time
    
    # 模拟渐进式进度
    current_time = time.time()
    
    # 简单的进度计算：基于时间的模拟进度
    if task_id not in scan_progress_store:
        scan_progress_store[task_id] = {
            "start_time": current_time,
            "status": "running"
        }
    
    task_data = scan_progress_store[task_id]
    elapsed_time = current_time - task_data["start_time"]
    
    # 模拟3秒完成
    progress = min(elapsed_time / 3.0, 1.0)
    
    if progress >= 1.0:
        return {
            "status": "completed",
            "progress": 1.0,
            "current_step": "扫描完成",
            "processed_files": 10,
            "total_files": 10,
            "result": {
                "success": True,
                "project_info": {
                    "name": "Test Project",
                    "total_mods": 5,
                    "total_files": 10
                },
                "mods": []
            }
        }
    else:
        steps = ["初始化扫描", "扫描文件结构", "分析MOD文件", "解析语言文件", "生成结果"]
        step_index = int(progress * len(steps))
        current_step = steps[min(step_index, len(steps) - 1)]
        
        processed_files = int(progress * 10)
        
        return {
            "status": "running", 
            "progress": progress,
            "current_step": current_step,
            "processed_files": processed_files,
            "total_files": 10
        }


# 添加兼容性端点用于旧的前端代码
@router.post("/v1/scan-project", deprecated=True)
async def start_scan_v1_compat(request: dict):
    """兼容旧版API的扫描端点"""
    import uuid
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 直接返回任务信息，不调用其他函数以避免路由冲突
    return {
        "success": True,
        "data": {
            "task_id": task_id,
            "scan_id": task_id,  # 添加scan_id字段
            "message": "扫描任务已启动",
            "status": "started"
        }
    }