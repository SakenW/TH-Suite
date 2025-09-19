"""
版本管理API路由 - TH-Suite MC L10n
提供完整的版本控制REST API接口
"""

from fastapi import APIRouter, HTTPException, Query, Body, Path
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from infrastructure.services.version_management_service import (
    get_version_management_service, EntityType
)
from infrastructure.services.version_operations_engine import (
    get_version_operations_engine, RollbackStrategy, MergeStrategy
)
from infrastructure.services.version_diff_engine import VersionDiffEngine, DiffType

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/v1/versions", tags=["版本管理"])

# 服务实例
version_service = get_version_management_service()
operations_engine = get_version_operations_engine()
diff_engine = VersionDiffEngine()


# ============================================================
# 1. 数据模型定义
# ============================================================

class CreateRepositoryRequest(BaseModel):
    """创建仓库请求"""
    entity_type: str = Field(..., description="实体类型")
    entity_uid: str = Field(..., description="实体UID")
    default_branch: str = Field(default="main", description="默认分支名")


class CreateBranchRequest(BaseModel):
    """创建分支请求"""
    name: str = Field(..., description="分支名称")
    description: Optional[str] = Field(None, description="分支描述")
    parent_branch_uid: Optional[str] = Field(None, description="父分支UID")
    is_protected: bool = Field(default=False, description="是否受保护")


class CreateCommitRequest(BaseModel):
    """创建提交请求"""
    branch_name: str = Field(..., description="分支名称")
    author_name: str = Field(..., description="作者名称")
    message: str = Field(..., description="提交消息")
    content_data: Dict[str, Any] = Field(..., description="内容数据")
    author_email: Optional[str] = Field(None, description="作者邮箱")
    description: Optional[str] = Field(None, description="详细描述")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class RollbackRequest(BaseModel):
    """回滚请求"""
    target_commit_uid: str = Field(..., description="目标提交UID")
    strategy: str = Field(default="revert", description="回滚策略")
    author_name: str = Field(default="System", description="操作者")
    message: Optional[str] = Field(None, description="回滚消息")


class MergeRequest(BaseModel):
    """合并请求"""
    source_branch: str = Field(..., description="源分支名")
    target_branch: str = Field(..., description="目标分支名")
    strategy: str = Field(default="three_way", description="合并策略")
    author_name: str = Field(default="System", description="操作者")
    message: Optional[str] = Field(None, description="合并消息")


class CreateTagRequest(BaseModel):
    """创建标签请求"""
    tag_name: str = Field(..., description="标签名称")
    commit_uid: str = Field(..., description="提交UID")
    tag_type: str = Field(default="release", description="标签类型")
    description: Optional[str] = Field(None, description="标签描述")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class DiffRequest(BaseModel):
    """差异请求"""
    from_commit_uid: Optional[str] = Field(None, description="源提交UID")
    to_commit_uid: str = Field(..., description="目标提交UID")
    diff_type: str = Field(default="forward", description="差异类型")


# ============================================================
# 2. 版本仓库管理API
# ============================================================

@router.post("/repositories", summary="创建版本仓库")
async def create_repository(request: CreateRepositoryRequest) -> Dict[str, Any]:
    """创建新的版本仓库"""
    try:
        # 验证实体类型
        try:
            entity_type = EntityType(request.entity_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的实体类型: {request.entity_type}"
            )
        
        result = await version_service.create_repository(
            entity_type=entity_type,
            entity_uid=request.entity_uid,
            default_branch=request.default_branch
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "版本仓库创建成功",
                "data": result["repository"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建版本仓库失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建版本仓库失败: {str(e)}")


@router.get("/repositories/{repository_uid}", summary="获取版本仓库信息")
async def get_repository(
    repository_uid: str = Path(..., description="仓库UID")
) -> Dict[str, Any]:
    """获取版本仓库详细信息"""
    try:
        result = await version_service.get_repository(repository_uid)
        
        if result["success"]:
            return {
                "success": True,
                "data": result["repository"]
            }
        else:
            raise HTTPException(status_code=404, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取版本仓库失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取版本仓库失败: {str(e)}")


# ============================================================
# 3. 分支管理API
# ============================================================

@router.post("/repositories/{repository_uid}/branches", summary="创建分支")
async def create_branch(
    repository_uid: str = Path(..., description="仓库UID"),
    request: CreateBranchRequest = Body(...)
) -> Dict[str, Any]:
    """创建新分支"""
    try:
        result = await version_service.create_branch(
            repository_uid=repository_uid,
            name=request.name,
            description=request.description,
            parent_branch_uid=request.parent_branch_uid,
            is_protected=request.is_protected
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "分支创建成功",
                "data": result["branch"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建分支失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建分支失败: {str(e)}")


@router.get("/repositories/{repository_uid}/branches", summary="列出分支")
async def list_branches(
    repository_uid: str = Path(..., description="仓库UID")
) -> Dict[str, Any]:
    """列出仓库的所有分支"""
    try:
        result = await version_service.list_branches(repository_uid)
        
        if result["success"]:
            return {
                "success": True,
                "data": {
                    "branches": result["branches"],
                    "total_count": result["total_count"]
                }
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出分支失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出分支失败: {str(e)}")


# ============================================================
# 4. 提交管理API
# ============================================================

@router.post("/repositories/{repository_uid}/commits", summary="创建提交")
async def create_commit(
    repository_uid: str = Path(..., description="仓库UID"),
    request: CreateCommitRequest = Body(...)
) -> Dict[str, Any]:
    """创建新的版本提交"""
    try:
        result = await version_service.create_commit(
            repository_uid=repository_uid,
            branch_name=request.branch_name,
            author_name=request.author_name,
            message=request.message,
            content_data=request.content_data,
            author_email=request.author_email,
            description=request.description,
            metadata=request.metadata
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "提交创建成功",
                "data": result["commit"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建提交失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建提交失败: {str(e)}")


@router.get("/repositories/{repository_uid}/commits", summary="获取提交历史")
async def get_commit_history(
    repository_uid: str = Path(..., description="仓库UID"),
    branch_name: Optional[str] = Query(None, description="分支名称"),
    limit: int = Query(50, ge=1, le=1000, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量")
) -> Dict[str, Any]:
    """获取提交历史记录"""
    try:
        result = await version_service.get_commit_history(
            repository_uid=repository_uid,
            branch_name=branch_name,
            limit=limit,
            offset=offset
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": {
                    "commits": result["commits"],
                    "total_count": result["total_count"],
                    "pagination": {
                        "limit": limit,
                        "offset": offset
                    }
                }
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取提交历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取提交历史失败: {str(e)}")


# ============================================================
# 5. 版本回滚API
# ============================================================

@router.post("/repositories/{repository_uid}/rollback", summary="版本回滚")
async def rollback_version(
    repository_uid: str = Path(..., description="仓库UID"),
    request: RollbackRequest = Body(...)
) -> Dict[str, Any]:
    """回滚到指定版本"""
    try:
        # 验证回滚策略
        try:
            strategy = RollbackStrategy(request.strategy)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的回滚策略: {request.strategy}"
            )
        
        result = await operations_engine.rollback_to_commit(
            repository_uid=repository_uid,
            target_commit_uid=request.target_commit_uid,
            strategy=strategy,
            author_name=request.author_name,
            message=request.message
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "版本回滚成功",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"版本回滚失败: {e}")
        raise HTTPException(status_code=500, detail=f"版本回滚失败: {str(e)}")


# ============================================================
# 6. 分支合并API
# ============================================================

@router.post("/repositories/{repository_uid}/merge", summary="分支合并")
async def merge_branches(
    repository_uid: str = Path(..., description="仓库UID"),
    request: MergeRequest = Body(...)
) -> Dict[str, Any]:
    """合并分支"""
    try:
        # 验证合并策略
        try:
            strategy = MergeStrategy(request.strategy)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的合并策略: {request.strategy}"
            )
        
        result = await operations_engine.merge_branches(
            repository_uid=repository_uid,
            source_branch=request.source_branch,
            target_branch=request.target_branch,
            strategy=strategy,
            author_name=request.author_name,
            message=request.message
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "分支合并成功",
                "data": result
            }
        else:
            # 检查是否是合并冲突
            if "conflicts" in result:
                return JSONResponse(
                    status_code=409,  # Conflict
                    content={
                        "success": False,
                        "message": result["message"],
                        "conflicts": result["conflicts"],
                        "merge_uid": result.get("merge_uid")
                    }
                )
            else:
                raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分支合并失败: {e}")
        raise HTTPException(status_code=500, detail=f"分支合并失败: {str(e)}")


# ============================================================
# 7. 标签管理API
# ============================================================

@router.post("/repositories/{repository_uid}/tags", summary="创建标签")
async def create_tag(
    repository_uid: str = Path(..., description="仓库UID"),
    request: CreateTagRequest = Body(...)
) -> Dict[str, Any]:
    """创建版本标签"""
    try:
        result = await operations_engine.create_tag(
            repository_uid=repository_uid,
            tag_name=request.tag_name,
            commit_uid=request.commit_uid,
            tag_type=request.tag_type,
            description=request.description,
            metadata=request.metadata
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "标签创建成功",
                "data": result["tag"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建标签失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建标签失败: {str(e)}")


@router.get("/repositories/{repository_uid}/tags", summary="列出标签")
async def list_tags(
    repository_uid: str = Path(..., description="仓库UID"),
    tag_type: Optional[str] = Query(None, description="标签类型")
) -> Dict[str, Any]:
    """列出版本标签"""
    try:
        result = await operations_engine.list_tags(
            repository_uid=repository_uid,
            tag_type=tag_type
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": {
                    "tags": result["tags"],
                    "total_count": result["total_count"]
                }
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出标签失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出标签失败: {str(e)}")


# ============================================================
# 8. 版本比较API
# ============================================================

@router.post("/repositories/{repository_uid}/diff", summary="版本差异比较")
async def compare_versions(
    repository_uid: str = Path(..., description="仓库UID"),
    request: DiffRequest = Body(...)
) -> Dict[str, Any]:
    """比较两个版本的差异"""
    try:
        # 验证差异类型
        try:
            diff_type = DiffType(request.diff_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的差异类型: {request.diff_type}"
            )
        
        # 获取提交内容
        if request.from_commit_uid:
            from_content_result = await operations_engine._get_commit_content(request.from_commit_uid)
            if not from_content_result["success"]:
                raise HTTPException(status_code=404, detail="源提交不存在或无法获取内容")
            from_content = from_content_result["content"]
        else:
            from_content = {}
        
        to_content_result = await operations_engine._get_commit_content(request.to_commit_uid)
        if not to_content_result["success"]:
            raise HTTPException(status_code=404, detail="目标提交不存在或无法获取内容")
        to_content = to_content_result["content"]
        
        # 计算差异
        version_diff = diff_engine.calculate_diff(from_content, to_content, diff_type)
        
        return {
            "success": True,
            "data": {
                "diff_uid": version_diff.uid,
                "from_commit_uid": request.from_commit_uid,
                "to_commit_uid": request.to_commit_uid,
                "diff_type": diff_type.value,
                "operations": [
                    {
                        "op": op.op.value,
                        "path": op.path,
                        "value": op.value,
                        "old_value": op.old_value,
                        "from_path": op.from_path
                    }
                    for op in version_diff.operations
                ],
                "metadata": version_diff.metadata,
                "created_at": version_diff.created_at.isoformat() if version_diff.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"版本比较失败: {e}")
        raise HTTPException(status_code=500, detail=f"版本比较失败: {str(e)}")


# ============================================================
# 9. 版本统计API
# ============================================================

@router.get("/repositories/{repository_uid}/stats", summary="版本仓库统计")
async def get_repository_stats(
    repository_uid: str = Path(..., description="仓库UID")
) -> Dict[str, Any]:
    """获取版本仓库统计信息"""
    try:
        # 获取仓库基本信息
        repo_result = await version_service.get_repository(repository_uid)
        if not repo_result["success"]:
            raise HTTPException(status_code=404, detail=repo_result["message"])
        
        # 获取分支列表
        branches_result = await version_service.list_branches(repository_uid)
        
        # 获取提交历史
        commits_result = await version_service.get_commit_history(repository_uid, limit=1000)
        
        # 获取标签列表
        tags_result = await operations_engine.list_tags(repository_uid)
        
        # 统计信息
        stats = {
            "repository": repo_result["repository"],
            "branches_count": branches_result.get("total_count", 0),
            "commits_count": commits_result.get("total_count", 0),
            "tags_count": tags_result.get("total_count", 0),
            "last_activity": None
        }
        
        # 计算最后活动时间
        if commits_result["success"] and commits_result["commits"]:
            latest_commit = commits_result["commits"][0]
            stats["last_activity"] = latest_commit["created_at"]
        
        return {
            "success": True,
            "data": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取仓库统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取仓库统计失败: {str(e)}")


# ============================================================
# 10. 健康检查API
# ============================================================

@router.get("/health", summary="版本管理服务健康检查")
async def health_check() -> Dict[str, Any]:
    """版本管理服务健康检查"""
    try:
        # 简单的健康检查
        return {
            "success": True,
            "service": "version_management",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "features": {
                "repository_management": True,
                "branch_management": True,
                "commit_management": True,
                "rollback_operations": True,
                "merge_operations": True,
                "tag_management": True,
                "diff_calculation": True
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


# 注册路由
def register_version_routes(app):
    """注册版本管理路由到FastAPI应用"""
    app.include_router(router)