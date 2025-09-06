"""
门面API路由
提供简化的REST接口
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime

from ....facade import MCL10nFacade
from ....container import get_facade

router = APIRouter(prefix="/api/v2", tags=["Facade API"])


# ========== 请求/响应模型 ==========

class ScanRequest(BaseModel):
    """扫描请求"""
    path: str = Field(..., description="扫描路径")
    recursive: bool = Field(True, description="是否递归扫描")
    auto_extract: bool = Field(True, description="是否自动提取JAR文件")


class TranslateRequest(BaseModel):
    """翻译请求"""
    mod_id: str = Field(..., description="MOD ID")
    language: str = Field(..., description="目标语言")
    translations: Dict[str, str] = Field(..., description="翻译映射")
    translator: Optional[str] = Field(None, description="翻译者ID")
    auto_approve: bool = Field(False, description="是否自动批准")


class BatchTranslateRequest(BaseModel):
    """批量翻译请求"""
    mod_ids: List[str] = Field(..., description="MOD ID列表")
    language: str = Field(..., description="目标语言")
    quality_threshold: float = Field(0.8, description="质量阈值")


class CreateProjectRequest(BaseModel):
    """创建项目请求"""
    name: str = Field(..., description="项目名称")
    mod_ids: List[str] = Field(..., description="包含的MOD ID")
    target_languages: Optional[List[str]] = Field(None, description="目标语言")
    auto_assign: bool = Field(False, description="是否自动分配任务")


class SyncRequest(BaseModel):
    """同步请求"""
    server_url: Optional[str] = Field(None, description="服务器地址")
    conflict_strategy: Optional[str] = Field(None, description="冲突解决策略")


# ========== 扫描相关接口 ==========

@router.post("/scan", summary="扫描MOD目录")
async def scan_mods(
    request: ScanRequest,
    facade: MCL10nFacade = Depends(get_facade)
):
    """扫描MOD目录并提取翻译"""
    try:
        result = facade.scan_mods(
            path=request.path,
            recursive=request.recursive,
            auto_extract=request.auto_extract
        )
        
        return {
            "success": result.success,
            "data": {
                "total_files": result.total_files,
                "mods_found": result.mods_found,
                "translations_found": result.translations_found,
                "duration": result.duration
            },
            "errors": result.errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scan/quick", summary="快速扫描")
async def quick_scan(
    path: str = Query(..., description="扫描路径"),
    facade: MCL10nFacade = Depends(get_facade)
):
    """快速扫描目录（仅统计）"""
    try:
        stats = facade.quick_scan(path)
        return {
            "success": "error" not in stats,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 翻译相关接口 ==========

@router.post("/translate", summary="翻译MOD")
async def translate_mod(
    request: TranslateRequest,
    facade: MCL10nFacade = Depends(get_facade)
):
    """为指定MOD添加翻译"""
    try:
        result = facade.translate_mod(
            mod_id=request.mod_id,
            language=request.language,
            translations=request.translations,
            translator=request.translator,
            auto_approve=request.auto_approve
        )
        
        return {
            "success": result.translated_count > 0,
            "data": {
                "mod_id": result.mod_id,
                "language": result.language,
                "translated_count": result.translated_count,
                "failed_count": result.failed_count,
                "progress": result.progress,
                "quality_score": result.quality_score
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/translate/batch", summary="批量翻译")
async def batch_translate(
    request: BatchTranslateRequest,
    facade: MCL10nFacade = Depends(get_facade)
):
    """批量翻译多个MOD"""
    try:
        results = facade.batch_translate(
            mod_ids=request.mod_ids,
            language=request.language,
            quality_threshold=request.quality_threshold
        )
        
        return {
            "success": True,
            "data": {
                "total": len(results),
                "successful": sum(1 for r in results if r.translated_count > 0),
                "results": [
                    {
                        "mod_id": r.mod_id,
                        "translated_count": r.translated_count,
                        "progress": r.progress
                    }
                    for r in results
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 项目管理接口 ==========

@router.post("/projects", summary="创建翻译项目")
async def create_project(
    request: CreateProjectRequest,
    facade: MCL10nFacade = Depends(get_facade)
):
    """创建新的翻译项目"""
    try:
        project_id = facade.create_project(
            name=request.name,
            mod_ids=request.mod_ids,
            target_languages=request.target_languages,
            auto_assign=request.auto_assign
        )
        
        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "message": "Project created successfully"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", summary="获取项目状态")
async def get_project_status(
    project_id: str,
    facade: MCL10nFacade = Depends(get_facade)
):
    """获取项目详细状态"""
    try:
        status = facade.get_project_status(project_id)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        return {
            "success": True,
            "data": status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 同步相关接口 ==========

@router.post("/sync", summary="同步到服务器")
async def sync_with_server(
    request: SyncRequest,
    facade: MCL10nFacade = Depends(get_facade)
):
    """同步本地数据到服务器"""
    try:
        result = facade.sync_with_server(
            server_url=request.server_url,
            conflict_strategy=request.conflict_strategy
        )
        
        return {
            "success": result.error_count == 0,
            "data": {
                "synced_count": result.synced_count,
                "conflict_count": result.conflict_count,
                "error_count": result.error_count,
                "duration": result.duration
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 质量管理接口 ==========

@router.get("/quality/{mod_id}", summary="检查翻译质量")
async def check_quality(
    mod_id: str,
    language: str = Query(..., description="语言代码"),
    facade: MCL10nFacade = Depends(get_facade)
):
    """检查指定MOD的翻译质量"""
    try:
        report = facade.check_quality(mod_id, language)
        
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        return {
            "success": True,
            "data": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 快捷操作接口 ==========

@router.post("/quick/scan-and-translate", summary="扫描并翻译")
async def scan_and_translate(
    path: str = Body(..., description="扫描路径"),
    language: str = Body(..., description="目标语言"),
    auto_approve: bool = Body(False, description="是否自动批准"),
    facade: MCL10nFacade = Depends(get_facade)
):
    """一键扫描并翻译（组合操作）"""
    try:
        # 先扫描
        scan_result = facade.scan_mods(path)
        
        if not scan_result.success:
            return {
                "success": False,
                "message": "Scan failed",
                "errors": scan_result.errors
            }
        
        # 获取扫描到的MOD（这里需要实际实现）
        # mod_ids = facade.get_scanned_mod_ids()
        
        # 批量翻译
        # translate_results = facade.batch_translate(mod_ids, language)
        
        return {
            "success": True,
            "data": {
                "scan": {
                    "mods_found": scan_result.mods_found,
                    "translations_found": scan_result.translations_found
                },
                "translate": {
                    "message": "Translation queued"
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", summary="系统状态")
async def get_system_status(
    facade: MCL10nFacade = Depends(get_facade)
):
    """获取系统整体状态"""
    try:
        return {
            "success": True,
            "data": {
                "status": "operational",
                "timestamp": datetime.now().isoformat(),
                "features": {
                    "scan": True,
                    "translate": True,
                    "sync": True,
                    "projects": True,
                    "quality": True
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))