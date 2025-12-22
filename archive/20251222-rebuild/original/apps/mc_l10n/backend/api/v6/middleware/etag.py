"""
V6 ETag版本控制中间件
实现基于ETag的HTTP缓存和条件请求支持
"""
import hashlib
import json
from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class ETagMiddleware(BaseHTTPMiddleware):
    """
    ETag版本控制中间件
    
    功能:
    - 自动生成响应的ETag
    - 处理If-Match/If-None-Match条件请求
    - 支持强ETag和弱ETag
    - 304 Not Modified优化
    """
    
    def __init__(self, app, enable_weak_etag: bool = True):
        super().__init__(app)
        self.enable_weak_etag = enable_weak_etag
    
    async def dispatch(self, request: Request, call_next):
        """处理ETag相关的请求和响应"""
        
        # 处理条件请求头
        if_match = request.headers.get("If-Match")
        if_none_match = request.headers.get("If-None-Match")
        
        # 对于需要ETag验证的操作 (PUT/PATCH/DELETE)
        if request.method in ["PUT", "PATCH", "DELETE"] and if_match:
            # 验证If-Match条件
            if not self._validate_if_match(request, if_match):
                return JSONResponse(
                    status_code=412,
                    content={
                        "error": "precondition_failed",
                        "message": "If-Match条件不满足，资源可能已被修改",
                        "required_header": "If-Match"
                    }
                )
        
        # 获取响应
        response = await call_next(request)
        
        # 为成功响应生成ETag
        if 200 <= response.status_code < 300:
            etag = await self._generate_etag(response)
            if etag:
                response.headers["ETag"] = etag
                
                # 处理If-None-Match (通常用于GET请求)
                if if_none_match and request.method == "GET":
                    if self._matches_etag(etag, if_none_match):
                        return Response(status_code=304, headers={"ETag": etag})
        
        return response
    
    def _validate_if_match(self, request: Request, if_match: str) -> bool:
        """验证If-Match条件"""
        # 这里应该查询资源的当前ETag
        # 简化实现，实际应该从数据库获取
        
        # 如果是 "*"，表示资源必须存在
        if if_match == "*":
            return True  # 简化处理
        
        # 获取资源UID（从路径参数中提取）
        resource_uid = self._extract_resource_uid(request)
        if not resource_uid:
            return False
        
        # 获取当前资源的ETag
        current_etag = self._get_current_etag(resource_uid)
        if not current_etag:
            return False
        
        # 比较ETag
        return self._matches_etag(current_etag, if_match)
    
    def _extract_resource_uid(self, request: Request) -> Optional[str]:
        """从请求路径中提取资源UID"""
        path_parts = request.url.path.split('/')
        
        # 查找可能的UID模式
        for i, part in enumerate(path_parts):
            # 假设UID是较长的字符串
            if len(part) > 10 and ('_' in part or '-' in part):
                return part
        
        return None
    
    def _get_current_etag(self, resource_uid: str) -> Optional[str]:
        """获取资源的当前ETag"""
        # TODO: 实际实现应该查询数据库
        # 这里返回基于UID的简单ETag
        return f'"{hashlib.md5(resource_uid.encode()).hexdigest()}"'
    
    async def _generate_etag(self, response: Response) -> Optional[str]:
        """为响应生成ETag"""
        try:
            # 读取响应体
            response_body = b""
            if hasattr(response, 'body_iterator'):
                body_chunks = []
                async for chunk in response.body_iterator:
                    body_chunks.append(chunk)
                    response_body += chunk
                
                # 重新创建body_iterator
                response.body_iterator = iter(body_chunks)
            elif hasattr(response, 'body'):
                response_body = response.body
            
            if not response_body:
                return None
            
            # 生成内容哈希
            content_hash = hashlib.md5(response_body).hexdigest()
            
            # 弱ETag (以W/开头) - 基于内容语义
            if self.enable_weak_etag:
                return f'W/"{content_hash}"'
            else:
                # 强ETag - 基于字节完全匹配
                return f'"{content_hash}"'
                
        except Exception as e:
            logger.warning("生成ETag失败", error=str(e))
            return None
    
    def _matches_etag(self, etag: str, match_value: str) -> bool:
        """检查ETag是否匹配"""
        # 处理多个ETag值 (逗号分隔)
        match_values = [v.strip() for v in match_value.split(',')]
        
        for value in match_values:
            if value == "*":
                return True
            
            # 移除W/前缀进行比较 (弱ETag比较)
            clean_etag = etag.replace('W/', '')
            clean_value = value.replace('W/', '')
            
            if clean_etag == clean_value:
                return True
        
        return False


class EntityETagMixin:
    """
    实体ETag混入类
    为数据模型提供ETag生成功能
    """
    
    def generate_etag(self) -> str:
        """生成实体的ETag"""
        # 基于实体的关键字段生成ETag
        etag_data = {
            "id": getattr(self, 'id', None),
            "uid": getattr(self, 'uid', None),
            "updated_at": getattr(self, 'updated_at', None),
            # 可以添加其他版本相关字段
        }
        
        # 移除None值
        etag_data = {k: v for k, v in etag_data.items() if v is not None}
        
        # 生成哈希
        content = json.dumps(etag_data, sort_keys=True, default=str)
        etag_hash = hashlib.md5(content.encode()).hexdigest()
        
        return f'"{etag_hash}"'
    
    def matches_etag(self, etag: str) -> bool:
        """检查是否匹配指定的ETag"""
        current_etag = self.generate_etag()
        
        # 移除W/前缀进行比较
        clean_current = current_etag.replace('W/', '').strip('"')
        clean_provided = etag.replace('W/', '').strip('"')
        
        return clean_current == clean_provided


def generate_collection_etag(items: list, include_count: bool = True) -> str:
    """为集合生成ETag"""
    etag_data = []
    
    for item in items:
        if hasattr(item, 'generate_etag'):
            etag_data.append(item.generate_etag())
        elif hasattr(item, 'get') and callable(item.get):
            # 字典类型
            etag_data.append(str(item.get('updated_at', item.get('id', str(item)))))
        else:
            etag_data.append(str(item))
    
    if include_count:
        etag_data.append(f"count:{len(items)}")
    
    # 生成集合哈希
    content = json.dumps(sorted(etag_data))
    etag_hash = hashlib.md5(content.encode()).hexdigest()
    
    return f'W/"{etag_hash}"'  # 集合使用弱ETag


def extract_etag_from_header(etag_header: str) -> str:
    """从ETag头部提取纯哈希值"""
    return etag_header.replace('W/', '').strip('"')


def add_etag_to_response(response: Response, etag: str):
    """为响应添加ETag头部"""
    response.headers["ETag"] = etag
    return response


# 装饰器
def requires_etag(f):
    """要求If-Match头部的装饰器"""
    async def wrapper(request: Request, *args, **kwargs):
        if request.method in ["PUT", "PATCH", "DELETE"]:
            if_match = request.headers.get("If-Match")
            if not if_match:
                raise HTTPException(
                    status_code=428,
                    detail={
                        "error": "precondition_required",
                        "message": "此操作需要If-Match头部",
                        "required_header": "If-Match"
                    }
                )
        
        return await f(request, *args, **kwargs)
    
    return wrapper