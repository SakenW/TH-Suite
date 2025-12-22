#!/usr/bin/env python
"""
压缩中间件
FastAPI中间件，支持基于locale的智能压缩
"""

import json
import gzip
from typing import Optional, Dict, Any, List
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from services.zstd_compression import get_compression_service, CompressionLevel

logger = structlog.get_logger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """压缩中间件 - 支持Zstd、Gzip等多种压缩算法"""
    
    def __init__(self,
                 app: ASGIApp,
                 minimum_size: int = 1024,  # 最小压缩字节数
                 compression_level: CompressionLevel = CompressionLevel.BALANCED,
                 enable_zstd: bool = True,
                 enable_gzip: bool = True,
                 zstd_training_enabled: bool = True):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level
        self.enable_zstd = enable_zstd
        self.enable_gzip = enable_gzip
        self.zstd_training_enabled = zstd_training_enabled
        
        # 支持的媒体类型
        self.compressible_types = {
            'application/json',
            'application/javascript', 
            'text/plain',
            'text/html',
            'text/css',
            'text/xml',
            'application/xml'
        }
        
        # 获取压缩服务
        if self.enable_zstd:
            self.compression_service = get_compression_service()
        
        logger.info("压缩中间件初始化",
                   minimum_size=minimum_size,
                   zstd_enabled=enable_zstd,
                   gzip_enabled=enable_gzip,
                   training_enabled=zstd_training_enabled)
    
    async def dispatch(self, request: Request, call_next):
        """处理请求和响应"""
        # 解析客户端支持的压缩算法
        accept_encoding = request.headers.get('accept-encoding', '')
        supports_zstd = 'zstd' in accept_encoding and self.enable_zstd
        supports_gzip = 'gzip' in accept_encoding and self.enable_gzip
        
        # 提取locale信息
        locale = self._extract_locale(request)
        
        # 处理请求
        response = await call_next(request)
        
        # 检查是否需要压缩
        if not self._should_compress(response):
            return response
        
        # 获取响应内容
        response_content = await self._get_response_content(response)
        if not response_content or len(response_content) < self.minimum_size:
            return response
        
        # 执行压缩
        if supports_zstd:
            return await self._compress_with_zstd(response, response_content, locale)
        elif supports_gzip:
            return await self._compress_with_gzip(response, response_content)
        
        return response
    
    def _extract_locale(self, request: Request) -> Optional[str]:
        """从请求中提取locale信息"""
        # 1. 从查询参数获取
        if 'locale' in request.query_params:
            return request.query_params['locale']
        
        # 2. 从路径参数获取
        if hasattr(request, 'path_params') and 'locale' in request.path_params:
            return request.path_params['locale']
        
        # 3. 从头部获取
        if 'x-locale' in request.headers:
            return request.headers['x-locale']
        
        # 4. 从Accept-Language解析
        accept_language = request.headers.get('accept-language', '')
        if accept_language:
            # 简单解析第一个语言标签
            lang = accept_language.split(',')[0].split(';')[0].strip()
            if lang:
                return lang.replace('-', '_').lower()
        
        return None
    
    def _should_compress(self, response: Response) -> bool:
        """判断是否应该压缩响应"""
        # 检查状态码
        if response.status_code < 200 or response.status_code >= 300:
            return False
        
        # 检查是否已经压缩
        if 'content-encoding' in response.headers:
            return False
        
        # 检查内容类型
        content_type = response.headers.get('content-type', '').split(';')[0]
        return content_type in self.compressible_types
    
    async def _get_response_content(self, response: Response) -> Optional[bytes]:
        """获取响应内容"""
        try:
            if hasattr(response, 'body'):
                content = response.body
            elif hasattr(response, 'content'):
                content = response.content
            else:
                return None
            
            if isinstance(content, str):
                return content.encode('utf-8')
            elif isinstance(content, bytes):
                return content
            else:
                return None
                
        except Exception as e:
            logger.warning("获取响应内容失败", error=str(e))
            return None
    
    async def _compress_with_zstd(self, 
                                  original_response: Response, 
                                  content: bytes, 
                                  locale: Optional[str]) -> Response:
        """使用Zstd压缩响应"""
        try:
            # 训练数据收集 (仅JSON内容)
            if (self.zstd_training_enabled and locale and 
                original_response.headers.get('content-type', '').startswith('application/json')):
                try:
                    # 解析JSON并添加为训练样本
                    json_data = json.loads(content.decode('utf-8'))
                    self.compression_service.add_training_sample(locale, json_data)
                    
                    # 如果样本足够，训练字典
                    if locale in self.compression_service.training_samples:
                        sample_count = len(self.compression_service.training_samples[locale])
                        if sample_count >= 20 and sample_count % 20 == 0:  # 每20个样本重新训练
                            self.compression_service.train_dictionary(locale, force_retrain=True)
                except:
                    pass  # 忽略训练错误
            
            # 执行压缩
            compressed_data, stats = self.compression_service.compress(
                content, locale, self.compression_level
            )
            
            # 创建新的响应
            headers = dict(original_response.headers)
            headers['content-encoding'] = 'zstd'
            headers['content-length'] = str(len(compressed_data))
            headers['x-original-size'] = str(stats.original_size)
            headers['x-compression-ratio'] = f"{stats.compression_ratio:.3f}"
            if stats.dictionary_used:
                headers['x-zstd-dict'] = locale
            
            return Response(
                content=compressed_data,
                status_code=original_response.status_code,
                headers=headers,
                media_type=original_response.media_type
            )
            
        except Exception as e:
            logger.error("Zstd压缩失败", locale=locale, error=str(e))
            return original_response
    
    async def _compress_with_gzip(self, 
                                  original_response: Response, 
                                  content: bytes) -> Response:
        """使用Gzip压缩响应"""
        try:
            compressed_data = gzip.compress(content, compresslevel=6)
            
            headers = dict(original_response.headers)
            headers['content-encoding'] = 'gzip'
            headers['content-length'] = str(len(compressed_data))
            headers['x-original-size'] = str(len(content))
            headers['x-compression-ratio'] = f"{len(compressed_data) / len(content):.3f}"
            
            return Response(
                content=compressed_data,
                status_code=original_response.status_code,
                headers=headers,
                media_type=original_response.media_type
            )
            
        except Exception as e:
            logger.error("Gzip压缩失败", error=str(e))
            return original_response


class ZstdDecompressionMiddleware(BaseHTTPMiddleware):
    """Zstd解压中间件 - 处理客户端发送的压缩请求"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.compression_service = get_compression_service()
        logger.info("Zstd解压中间件初始化")
    
    async def dispatch(self, request: Request, call_next):
        """处理压缩的请求体"""
        # 检查请求是否使用了压缩
        content_encoding = request.headers.get('content-encoding', '')
        
        if content_encoding == 'zstd':
            request = await self._decompress_zstd_request(request)
        elif content_encoding == 'gzip':
            request = await self._decompress_gzip_request(request)
        
        return await call_next(request)
    
    async def _decompress_zstd_request(self, request: Request) -> Request:
        """解压Zstd压缩的请求"""
        try:
            # 获取请求体
            compressed_body = await request.body()
            if not compressed_body:
                return request
            
            # 提取locale
            locale = self._extract_locale_from_headers(request)
            
            # 解压
            decompressed_body = self.compression_service.decompress(
                compressed_body, locale
            )
            
            # 创建新的请求对象
            new_headers = dict(request.headers)
            del new_headers['content-encoding']
            new_headers['content-length'] = str(len(decompressed_body))
            
            # 修改请求体 
            request._body = decompressed_body
            request.headers.__dict__['_list'] = [
                (k.encode(), v.encode()) for k, v in new_headers.items()
            ]
            
            logger.debug("Zstd请求解压完成",
                        compressed_size=len(compressed_body),
                        decompressed_size=len(decompressed_body),
                        locale=locale)
            
            return request
            
        except Exception as e:
            logger.error("Zstd请求解压失败", error=str(e))
            return request
    
    async def _decompress_gzip_request(self, request: Request) -> Request:
        """解压Gzip压缩的请求"""
        try:
            compressed_body = await request.body()
            if not compressed_body:
                return request
            
            decompressed_body = gzip.decompress(compressed_body)
            
            new_headers = dict(request.headers)
            del new_headers['content-encoding']
            new_headers['content-length'] = str(len(decompressed_body))
            
            request._body = decompressed_body
            request.headers.__dict__['_list'] = [
                (k.encode(), v.encode()) for k, v in new_headers.items()
            ]
            
            logger.debug("Gzip请求解压完成",
                        compressed_size=len(compressed_body),
                        decompressed_size=len(decompressed_body))
            
            return request
            
        except Exception as e:
            logger.error("Gzip请求解压失败", error=str(e))
            return request
    
    def _extract_locale_from_headers(self, request: Request) -> Optional[str]:
        """从请求头提取locale"""
        if 'x-locale' in request.headers:
            return request.headers['x-locale']
        if 'x-zstd-dict' in request.headers:
            return request.headers['x-zstd-dict']
        return None


def create_compression_middleware(enable_zstd: bool = True,
                                enable_gzip: bool = True,
                                minimum_size: int = 1024,
                                compression_level: CompressionLevel = CompressionLevel.BALANCED) -> CompressionMiddleware:
    """创建压缩中间件的工厂函数"""
    return CompressionMiddleware(
        app=None,  # 将在添加时设置
        enable_zstd=enable_zstd,
        enable_gzip=enable_gzip,
        minimum_size=minimum_size,
        compression_level=compression_level
    )