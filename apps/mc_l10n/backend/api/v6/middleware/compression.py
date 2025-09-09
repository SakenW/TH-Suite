"""
V6 压缩中间件
实现Zstd压缩和locale-specific字典支持
"""

import io
import gzip
import zlib
from typing import Optional, Dict, Any, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
import structlog

logger = structlog.get_logger(__name__)

# 尝试导入zstd，如果不可用则使用gzip作为fallback
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    logger.warning("zstd库不可用，将使用gzip压缩")


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    压缩中间件
    
    支持多种压缩算法:
    - zstd (优先，如果可用)
    - gzip (fallback)
    - deflate (基础支持)
    
    特性:
    - 基于locale的compression字典
    - 动态压缩级别调整
    - 自适应压缩策略
    """
    
    def __init__(
        self, 
        app,
        min_response_size: int = 1024,  # 最小压缩大小
        compression_level: int = 6,     # 压缩级别 (1-22 for zstd, 1-9 for gzip)
        enable_dictionary: bool = True,  # 启用字典压缩
        max_dict_size: int = 110 * 1024  # 字典最大大小 (110KB)
    ):
        super().__init__(app)
        self.min_response_size = min_response_size
        self.compression_level = compression_level
        self.enable_dictionary = enable_dictionary
        self.max_dict_size = max_dict_size
        
        # 初始化locale字典
        self.locale_dictionaries = {}
        
        if ZSTD_AVAILABLE:
            logger.info("Zstd压缩中间件初始化",
                       compression_level=compression_level,
                       dictionary_enabled=enable_dictionary)
        else:
            logger.info("Gzip压缩中间件初始化 (zstd不可用)",
                       compression_level=compression_level)
    
    async def dispatch(self, request: Request, call_next):
        """处理请求和响应压缩"""
        
        # 检查客户端支持的压缩格式
        accept_encoding = request.headers.get("accept-encoding", "")
        
        # 处理请求解压缩
        await self._decompress_request_if_needed(request)
        
        # 获取响应
        response = await call_next(request)
        
        # 判断是否需要压缩响应
        if not self._should_compress_response(request, response, accept_encoding):
            return response
        
        # 压缩响应
        return await self._compress_response(request, response, accept_encoding)
    
    async def _decompress_request_if_needed(self, request: Request):
        """解压缩请求体 (如果需要)"""
        content_encoding = request.headers.get("content-encoding")
        
        if not content_encoding:
            return
        
        try:
            if hasattr(request, '_body'):
                body = request._body
            else:
                body = await request.body()
            
            if content_encoding == "zstd" and ZSTD_AVAILABLE:
                decompressor = zstd.ZstdDecompressor()
                decompressed = decompressor.decompress(body)
                request._body = decompressed
                logger.debug("请求Zstd解压缩完成", 
                           compressed_size=len(body),
                           decompressed_size=len(decompressed))
            
            elif content_encoding == "gzip":
                decompressed = gzip.decompress(body)
                request._body = decompressed
                logger.debug("请求Gzip解压缩完成",
                           compressed_size=len(body), 
                           decompressed_size=len(decompressed))
            
            elif content_encoding == "deflate":
                decompressed = zlib.decompress(body)
                request._body = decompressed
                logger.debug("请求Deflate解压缩完成",
                           compressed_size=len(body),
                           decompressed_size=len(decompressed))
                           
        except Exception as e:
            logger.error("请求解压缩失败",
                        content_encoding=content_encoding,
                        error=str(e))
    
    def _should_compress_response(self, request: Request, response: Response, accept_encoding: str) -> bool:
        """判断响应是否应该被压缩"""
        
        # 检查HTTP状态码
        if response.status_code < 200 or response.status_code >= 300:
            return False
        
        # 检查响应头
        if response.headers.get("content-encoding"):
            return False  # 已经压缩
        
        # 检查内容类型
        content_type = response.headers.get("content-type", "")
        compressible_types = [
            "application/json",
            "text/plain", 
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/xml",
            "text/xml"
        ]
        
        if not any(ct in content_type for ct in compressible_types):
            return False
        
        # 检查客户端支持
        if not accept_encoding:
            return False
        
        supported = ["zstd", "gzip", "deflate"]
        if not any(alg in accept_encoding for alg in supported):
            return False
        
        return True
    
    async def _compress_response(self, request: Request, response: Response, accept_encoding: str) -> Response:
        """压缩响应"""
        
        try:
            # 获取响应体
            response_body = b""
            if hasattr(response, 'body_iterator'):
                body_chunks = []
                async for chunk in response.body_iterator:
                    body_chunks.append(chunk)
                    response_body += chunk
            elif hasattr(response, 'body'):
                response_body = response.body
            else:
                return response
            
            # 检查大小
            if len(response_body) < self.min_response_size:
                return response
            
            # 选择压缩算法
            compression_algo, compressed_body = await self._choose_and_compress(
                request, response_body, accept_encoding
            )
            
            if not compressed_body:
                return response
            
            # 计算压缩比
            compression_ratio = len(compressed_body) / len(response_body)
            
            logger.info("响应压缩完成",
                       algorithm=compression_algo,
                       original_size=len(response_body),
                       compressed_size=len(compressed_body),
                       compression_ratio=round(compression_ratio, 3))
            
            # 创建新的响应
            new_response = Response(
                content=compressed_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
            # 更新响应头
            new_response.headers["content-encoding"] = compression_algo
            new_response.headers["content-length"] = str(len(compressed_body))
            new_response.headers["vary"] = "accept-encoding"
            
            return new_response
            
        except Exception as e:
            logger.error("响应压缩失败", error=str(e))
            return response
    
    async def _choose_and_compress(
        self, 
        request: Request, 
        data: bytes, 
        accept_encoding: str
    ) -> tuple[str, Optional[bytes]]:
        """选择最佳压缩算法并执行压缩"""
        
        # 提取locale信息 (用于选择字典)
        locale = self._extract_locale(request)
        
        # 优先使用Zstd
        if "zstd" in accept_encoding and ZSTD_AVAILABLE:
            compressed = await self._compress_with_zstd(data, locale)
            if compressed:
                return "zstd", compressed
        
        # Fallback到Gzip
        if "gzip" in accept_encoding:
            compressed = await self._compress_with_gzip(data)
            if compressed:
                return "gzip", compressed
        
        # 最后使用Deflate
        if "deflate" in accept_encoding:
            compressed = await self._compress_with_deflate(data)
            if compressed:
                return "deflate", compressed
        
        return "", None
    
    def _extract_locale(self, request: Request) -> Optional[str]:
        """从请求中提取locale信息"""
        
        # 从查询参数提取
        if hasattr(request, 'query_params'):
            locale = request.query_params.get('locale')
            if locale:
                return locale
        
        # 从路径提取
        path = request.url.path
        if '/zh_cn' in path or '/zh-cn' in path:
            return 'zh_cn'
        elif '/en_us' in path or '/en-us' in path:
            return 'en_us'
        
        # 从Accept-Language头部提取
        accept_lang = request.headers.get('accept-language', '')
        if 'zh' in accept_lang:
            return 'zh_cn'
        elif 'en' in accept_lang:
            return 'en_us'
        
        return None
    
    async def _compress_with_zstd(self, data: bytes, locale: Optional[str] = None) -> Optional[bytes]:
        """使用Zstd压缩"""
        if not ZSTD_AVAILABLE:
            return None
        
        try:
            if self.enable_dictionary and locale:
                # 使用locale-specific字典
                dictionary = self._get_or_create_dictionary(locale)
                if dictionary:
                    compressor = zstd.ZstdCompressor(
                        level=self.compression_level,
                        dict_data=zstd.ZstdCompressionDict(dictionary)
                    )
                else:
                    compressor = zstd.ZstdCompressor(level=self.compression_level)
            else:
                compressor = zstd.ZstdCompressor(level=self.compression_level)
            
            return compressor.compress(data)
            
        except Exception as e:
            logger.error("Zstd压缩失败", locale=locale, error=str(e))
            return None
    
    async def _compress_with_gzip(self, data: bytes) -> Optional[bytes]:
        """使用Gzip压缩"""
        try:
            return gzip.compress(data, compresslevel=min(self.compression_level, 9))
        except Exception as e:
            logger.error("Gzip压缩失败", error=str(e))
            return None
    
    async def _compress_with_deflate(self, data: bytes) -> Optional[bytes]:
        """使用Deflate压缩"""
        try:
            return zlib.compress(data, level=min(self.compression_level, 9))
        except Exception as e:
            logger.error("Deflate压缩失败", error=str(e))
            return None
    
    def _get_or_create_dictionary(self, locale: str) -> Optional[bytes]:
        """获取或创建locale-specific压缩字典"""
        
        if locale in self.locale_dictionaries:
            return self.locale_dictionaries[locale]
        
        # 创建locale字典
        dictionary = self._create_locale_dictionary(locale)
        if dictionary:
            self.locale_dictionaries[locale] = dictionary
            logger.info("创建locale压缩字典", 
                       locale=locale,
                       dict_size=len(dictionary))
        
        return dictionary
    
    def _create_locale_dictionary(self, locale: str) -> Optional[bytes]:
        """创建locale-specific压缩字典"""
        
        # 定义常见的翻译文本模式
        common_patterns = {
            'zh_cn': [
                # 中文常见词汇
                '"key":', '"src_text":', '"dst_text":', '"status":', '"locale":',
                '物品', '方块', '实体', '配方', '进度', '界面', '菜单', '设置',
                '描述', '标题', '名称', '类型', '版本', '模组', '资源包',
                '翻译', '条目', '语言', '文件', '更新', '创建', '删除',
                # JSON结构
                '{"', '":"', '","', '"}', '[{', '}]', 'true', 'false', 'null',
                # MC相关
                'item.', 'block.', 'entity.', 'gui.', 'menu.', 'tile.',
                'minecraft:', 'forge:', 'fabric:', 'create:', 'thermal:'
            ],
            'en_us': [
                # 英文常见词汇  
                '"key":', '"src_text":', '"dst_text":', '"status":', '"locale":',
                'item', 'block', 'entity', 'recipe', 'advancement', 'gui', 'menu',
                'description', 'title', 'name', 'type', 'version', 'mod', 'pack',
                'translation', 'entry', 'language', 'file', 'update', 'create', 'delete',
                # JSON结构
                '{"', '":"', '","', '"}', '[{', '}]', 'true', 'false', 'null',
                # MC相关
                'item.', 'block.', 'entity.', 'gui.', 'menu.', 'tile.',
                'minecraft:', 'forge:', 'fabric:', 'create:', 'thermal:'
            ]
        }
        
        patterns = common_patterns.get(locale, common_patterns['en_us'])
        
        # 构建字典内容
        dict_content = '\n'.join(patterns).encode('utf-8')
        
        # 限制字典大小
        if len(dict_content) > self.max_dict_size:
            dict_content = dict_content[:self.max_dict_size]
        
        return dict_content
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        return {
            "zstd_available": ZSTD_AVAILABLE,
            "compression_level": self.compression_level,
            "min_response_size": self.min_response_size,
            "dictionary_enabled": self.enable_dictionary,
            "locale_dictionaries": list(self.locale_dictionaries.keys()),
            "max_dict_size": self.max_dict_size
        }
    
    def clear_dictionaries(self):
        """清理压缩字典缓存"""
        cleared_count = len(self.locale_dictionaries)
        self.locale_dictionaries.clear()
        logger.info("清理压缩字典缓存", cleared_count=cleared_count)