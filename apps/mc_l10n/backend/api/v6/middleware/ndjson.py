"""
V6 NDJSON流处理中间件
支持流式NDJSON数据的解析和生成
"""
import json
from typing import AsyncGenerator, Dict, Any, List
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class NDJSONMiddleware(BaseHTTPMiddleware):
    """
    NDJSON (Newline Delimited JSON) 处理中间件
    
    功能:
    - 自动识别 application/x-ndjson Content-Type
    - 流式解析NDJSON请求体
    - 生成NDJSON响应流
    """
    
    async def dispatch(self, request: Request, call_next):
        """处理NDJSON请求和响应"""
        
        # 处理NDJSON请求
        if self._is_ndjson_request(request):
            request = await self._process_ndjson_request(request)
        
        response = await call_next(request)
        
        # 处理NDJSON响应
        if self._should_generate_ndjson_response(request):
            response = await self._process_ndjson_response(response)
            
        return response
    
    def _is_ndjson_request(self, request: Request) -> bool:
        """检查是否为NDJSON请求"""
        content_type = request.headers.get("Content-Type", "")
        return "application/x-ndjson" in content_type
    
    def _should_generate_ndjson_response(self, request: Request) -> bool:
        """检查是否应该生成NDJSON响应"""
        accept = request.headers.get("Accept", "")
        return "application/x-ndjson" in accept
    
    async def _process_ndjson_request(self, request: Request) -> Request:
        """处理NDJSON请求体"""
        try:
            # 读取请求体
            body = await request.body()
            
            # 解析NDJSON
            parsed_objects = []
            for line in body.decode().strip().split('\n'):
                if line.strip():
                    try:
                        obj = json.loads(line)
                        parsed_objects.append(obj)
                    except json.JSONDecodeError as e:
                        logger.warning(f"跳过无效的NDJSON行: {line[:100]}...", error=str(e))
            
            # 将解析后的对象列表存储到request中
            request.state.ndjson_objects = parsed_objects
            
            logger.info(f"成功解析 {len(parsed_objects)} 个NDJSON对象")
            
        except Exception as e:
            logger.error("处理NDJSON请求失败", error=str(e))
            # 保持原始请求不变
            
        return request
    
    async def _process_ndjson_response(self, response: Response) -> StreamingResponse:
        """将响应转换为NDJSON流"""
        try:
            # 如果已经是StreamingResponse且内容类型正确，直接返回
            if isinstance(response, StreamingResponse):
                if response.media_type == "application/x-ndjson":
                    return response
            
            # 读取响应体
            response_body = b""
            if hasattr(response, 'body_iterator'):
                async for chunk in response.body_iterator:
                    response_body += chunk
            elif hasattr(response, 'body'):
                response_body = response.body
            
            # 解析响应数据
            try:
                response_data = json.loads(response_body.decode())
            except:
                # 如果不是JSON，返回原响应
                return response
            
            # 生成NDJSON流
            async def ndjson_generator():
                if isinstance(response_data, list):
                    # 如果是列表，每个元素一行
                    for item in response_data:
                        yield json.dumps(item, ensure_ascii=False) + '\n'
                elif isinstance(response_data, dict):
                    # 如果包含数据列表，处理分页响应
                    if 'data' in response_data and isinstance(response_data['data'], list):
                        for item in response_data['data']:
                            yield json.dumps(item, ensure_ascii=False) + '\n'
                    else:
                        # 单个对象
                        yield json.dumps(response_data, ensure_ascii=False) + '\n'
                else:
                    # 其他类型，直接输出
                    yield json.dumps(response_data, ensure_ascii=False) + '\n'
            
            # 创建流式响应
            headers = dict(response.headers) if hasattr(response, 'headers') else {}
            headers.update({
                "Content-Type": "application/x-ndjson; charset=utf-8",
                "X-Content-Format": "ndjson",
                "X-TH-DB-Schema": "v6.0"
            })
            
            return StreamingResponse(
                ndjson_generator(),
                media_type="application/x-ndjson",
                headers=headers
            )
            
        except Exception as e:
            logger.error("处理NDJSON响应失败", error=str(e))
            return response


class NDJSONStreamGenerator:
    """NDJSON流生成器工具类"""
    
    @staticmethod
    async def from_async_iterator(async_iter: AsyncGenerator[Dict[str, Any], None]) -> AsyncGenerator[str, None]:
        """从异步迭代器生成NDJSON流"""
        async for item in async_iter:
            yield json.dumps(item, ensure_ascii=False) + '\n'
    
    @staticmethod
    async def from_list(items: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
        """从列表生成NDJSON流"""
        for item in items:
            yield json.dumps(item, ensure_ascii=False) + '\n'
    
    @staticmethod
    def parse_ndjson_string(ndjson_str: str) -> List[Dict[str, Any]]:
        """解析NDJSON字符串"""
        objects = []
        for line in ndjson_str.strip().split('\n'):
            if line.strip():
                try:
                    obj = json.loads(line)
                    objects.append(obj)
                except json.JSONDecodeError as e:
                    logger.warning(f"跳过无效的NDJSON行: {line[:100]}...", error=str(e))
        return objects
    
    @staticmethod
    def create_streaming_response(
        generator: AsyncGenerator[str, None], 
        headers: Dict[str, str] = None
    ) -> StreamingResponse:
        """创建NDJSON流式响应"""
        default_headers = {
            "Content-Type": "application/x-ndjson; charset=utf-8",
            "X-Content-Format": "ndjson",
            "X-TH-DB-Schema": "v6.0"
        }
        
        if headers:
            default_headers.update(headers)
        
        return StreamingResponse(
            generator,
            media_type="application/x-ndjson",
            headers=default_headers
        )


# 实用函数
def get_ndjson_objects_from_request(request: Request) -> List[Dict[str, Any]]:
    """从请求中获取解析后的NDJSON对象"""
    if hasattr(request.state, 'ndjson_objects'):
        return request.state.ndjson_objects
    return []


def is_ndjson_request(request: Request) -> bool:
    """检查请求是否为NDJSON格式"""
    content_type = request.headers.get("Content-Type", "")
    return "application/x-ndjson" in content_type


def wants_ndjson_response(request: Request) -> bool:
    """检查客户端是否期望NDJSON响应"""
    accept = request.headers.get("Accept", "")
    return "application/x-ndjson" in accept