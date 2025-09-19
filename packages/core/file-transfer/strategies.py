"""
文件传输策略实现

实现不同的传输策略：HTTP、WebSocket、流式传输等
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import aiohttp
import websockets
from urllib.parse import urljoin, urlparse

from .core import TransferStrategy, ChunkInfo, TransferTask
from .errors import NetworkError, ValidationError, TimeoutError, AuthenticationError


class BaseTransferStrategy(TransferStrategy, ABC):
    """传输策略基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
    
    async def initialize(self) -> None:
        """初始化策略"""
        connector = aiohttp.TCPConnector(
            limit=self.config.get('max_connections', 100),
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=self.config.get('total_timeout', 300),
            connect=self.config.get('connect_timeout', 10),
            sock_read=self.config.get('read_timeout', 30)
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self._get_default_headers()
        )
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _get_default_headers(self) -> Dict[str, str]:
        """获取默认请求头"""
        headers = {
            'User-Agent': 'TH-Suite-FileTransfer/1.0',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        }
        
        # 添加认证头
        if 'auth_token' in self.config:
            headers['Authorization'] = f"Bearer {self.config['auth_token']}"
        elif 'api_key' in self.config:
            headers['X-API-Key'] = self.config['api_key']
        
        return headers
    
    def _get_chunk_url(self, task: TransferTask, chunk: ChunkInfo) -> str:
        """获取分块上传URL"""
        base_url = task.target_url
        return urljoin(base_url, f"chunks/{chunk.index}")
    
    async def _handle_response_error(self, response: aiohttp.ClientResponse) -> None:
        """处理响应错误"""
        if response.status == 401:
            raise AuthenticationError("认证失败")
        elif response.status == 403:
            raise AuthenticationError("权限不足")
        elif response.status == 404:
            raise NetworkError("资源不存在", status_code=response.status)
        elif response.status >= 500:
            raise NetworkError("服务器内部错误", status_code=response.status)
        elif response.status >= 400:
            error_text = await response.text()
            raise NetworkError(f"请求错误: {error_text}", status_code=response.status)


class HttpUploadStrategy(BaseTransferStrategy):
    """HTTP上传策略"""
    
    async def upload_chunk(
        self,
        chunk_data: bytes,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """上传单个分块"""
        if not self.session:
            await self.initialize()
        
        url = self._get_chunk_url(task, chunk_info)
        
        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Length': str(len(chunk_data)),
            'X-Chunk-Index': str(chunk_info.index),
            'X-Chunk-Size': str(chunk_info.size),
            'X-Chunk-Start': str(chunk_info.start),
            'X-Chunk-End': str(chunk_info.end),
            'X-Task-Id': task.id
        }
        
        if chunk_info.hash:
            headers['X-Chunk-Hash'] = chunk_info.hash
        
        try:
            async with self.session.put(url, data=chunk_data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('success', False)
                else:
                    await self._handle_response_error(response)
                    return False
                    
        except asyncio.TimeoutError:
            raise TimeoutError(f"上传分块 {chunk_info.index} 超时")
        except aiohttp.ClientError as e:
            raise NetworkError(f"上传分块 {chunk_info.index} 失败: {e}")
    
    async def verify_chunk(
        self,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """验证分块完整性"""
        if not self.session:
            await self.initialize()
        
        url = self._get_chunk_url(task, chunk_info)
        
        try:
            async with self.session.head(url) as response:
                if response.status == 200:
                    remote_hash = response.headers.get('X-Chunk-Hash')
                    if remote_hash and chunk_info.hash:
                        return remote_hash == chunk_info.hash
                    return True
                else:
                    return False
                    
        except (asyncio.TimeoutError, aiohttp.ClientError):
            return False


class MultipartUploadStrategy(BaseTransferStrategy):
    """分段上传策略"""
    
    async def upload_chunk(
        self,
        chunk_data: bytes,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """使用multipart/form-data上传分块"""
        if not self.session:
            await self.initialize()
        
        url = task.target_url
        
        # 创建multipart数据
        data = aiohttp.FormData()
        data.add_field('chunk_index', str(chunk_info.index))
        data.add_field('chunk_start', str(chunk_info.start))
        data.add_field('chunk_end', str(chunk_info.end))
        data.add_field('task_id', task.id)
        
        if chunk_info.hash:
            data.add_field('chunk_hash', chunk_info.hash)
        
        data.add_field(
            'chunk_data',
            chunk_data,
            filename=f'chunk_{chunk_info.index}',
            content_type='application/octet-stream'
        )
        
        try:
            async with self.session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('success', False)
                else:
                    await self._handle_response_error(response)
                    return False
                    
        except asyncio.TimeoutError:
            raise TimeoutError(f"上传分块 {chunk_info.index} 超时")
        except aiohttp.ClientError as e:
            raise NetworkError(f"上传分块 {chunk_info.index} 失败: {e}")
    
    async def verify_chunk(
        self,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """验证分块"""
        # multipart上传通常在上传时就验证
        return True


class WebSocketStrategy(BaseTransferStrategy):
    """WebSocket传输策略"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.chunk_responses: Dict[int, bool] = {}
    
    async def initialize(self) -> None:
        """初始化WebSocket连接"""
        await super().initialize()
        
        # 建立WebSocket连接
        ws_url = self.config.get('websocket_url', 'ws://localhost:8000/ws/upload')
        try:
            self.websocket = await websockets.connect(
                ws_url,
                extra_headers=self._get_default_headers()
            )
            
            # 启动响应监听器
            asyncio.create_task(self._response_listener())
            
        except Exception as e:
            raise NetworkError(f"WebSocket连接失败: {e}")
    
    async def cleanup(self) -> None:
        """清理WebSocket连接"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        await super().cleanup()
    
    async def _response_listener(self) -> None:
        """监听WebSocket响应"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                if data.get('type') == 'chunk_response':
                    chunk_index = data.get('chunk_index')
                    success = data.get('success', False)
                    self.chunk_responses[chunk_index] = success
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket连接已关闭")
        except Exception as e:
            self.logger.error(f"WebSocket响应监听错误: {e}")
    
    async def upload_chunk(
        self,
        chunk_data: bytes,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """通过WebSocket上传分块"""
        if not self.websocket:
            raise NetworkError("WebSocket未连接")
        
        # 发送分块元数据
        metadata = {
            'type': 'chunk_upload',
            'task_id': task.id,
            'chunk_index': chunk_info.index,
            'chunk_size': chunk_info.size,
            'chunk_start': chunk_info.start,
            'chunk_end': chunk_info.end,
            'chunk_hash': chunk_info.hash
        }
        
        try:
            # 发送元数据
            await self.websocket.send(json.dumps(metadata))
            
            # 发送分块数据
            await self.websocket.send(chunk_data)
            
            # 等待响应
            timeout = self.config.get('response_timeout', 30)
            for _ in range(int(timeout * 10)):  # 100ms检查间隔
                if chunk_info.index in self.chunk_responses:
                    return self.chunk_responses.pop(chunk_info.index)
                await asyncio.sleep(0.1)
            
            raise TimeoutError(f"等待分块 {chunk_info.index} 响应超时")
            
        except websockets.exceptions.ConnectionClosed:
            raise NetworkError("WebSocket连接已断开")
        except Exception as e:
            raise NetworkError(f"WebSocket上传失败: {e}")
    
    async def verify_chunk(
        self,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """验证分块"""
        if not self.websocket:
            return False
        
        verify_request = {
            'type': 'chunk_verify',
            'task_id': task.id,
            'chunk_index': chunk_info.index,
            'chunk_hash': chunk_info.hash
        }
        
        try:
            await self.websocket.send(json.dumps(verify_request))
            
            # 等待验证响应
            timeout = self.config.get('verify_timeout', 10)
            for _ in range(int(timeout * 10)):
                if chunk_info.index in self.chunk_responses:
                    return self.chunk_responses.pop(chunk_info.index)
                await asyncio.sleep(0.1)
            
            return False
            
        except Exception as e:
            self.logger.error(f"分块验证失败: {e}")
            return False


class StreamingStrategy(BaseTransferStrategy):
    """流式传输策略"""
    
    async def upload_chunk(
        self,
        chunk_data: bytes,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """流式上传分块"""
        if not self.session:
            await self.initialize()
        
        url = self._get_chunk_url(task, chunk_info)
        
        headers = {
            'Transfer-Encoding': 'chunked',
            'X-Chunk-Index': str(chunk_info.index),
            'X-Task-Id': task.id
        }
        
        if chunk_info.hash:
            headers['X-Chunk-Hash'] = chunk_info.hash
        
        try:
            # 创建流式数据生成器
            async def data_generator():
                chunk_size = self.config.get('stream_chunk_size', 8192)
                for i in range(0, len(chunk_data), chunk_size):
                    yield chunk_data[i:i + chunk_size]
                    # 添加小延迟以避免过度占用带宽
                    await asyncio.sleep(0.001)
            
            async with self.session.put(
                url,
                data=data_generator(),
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('success', False)
                else:
                    await self._handle_response_error(response)
                    return False
                    
        except asyncio.TimeoutError:
            raise TimeoutError(f"流式上传分块 {chunk_info.index} 超时")
        except aiohttp.ClientError as e:
            raise NetworkError(f"流式上传分块 {chunk_info.index} 失败: {e}")
    
    async def verify_chunk(
        self,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """验证分块"""
        return await HttpUploadStrategy.verify_chunk(self, chunk_info, task)


class ResumeUploadStrategy(BaseTransferStrategy):
    """断点续传策略"""
    
    async def upload_chunk(
        self,
        chunk_data: bytes,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """支持断点续传的分块上传"""
        if not self.session:
            await self.initialize()
        
        url = self._get_chunk_url(task, chunk_info)
        
        # 首先检查服务器上已有的数据
        uploaded_size = await self._get_uploaded_size(chunk_info, task)
        
        if uploaded_size >= chunk_info.size:
            # 分块已完全上传
            return True
        elif uploaded_size > 0:
            # 部分上传，继续上传剩余部分
            remaining_data = chunk_data[uploaded_size:]
            start_byte = chunk_info.start + uploaded_size
        else:
            # 全新上传
            remaining_data = chunk_data
            start_byte = chunk_info.start
        
        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Range': f'bytes {start_byte}-{chunk_info.end - 1}/{chunk_info.size}',
            'X-Chunk-Index': str(chunk_info.index),
            'X-Task-Id': task.id
        }
        
        if chunk_info.hash:
            headers['X-Chunk-Hash'] = chunk_info.hash
        
        try:
            async with self.session.put(url, data=remaining_data, headers=headers) as response:
                if response.status in (200, 201, 206):  # 206 Partial Content
                    result = await response.json()
                    return result.get('success', False)
                else:
                    await self._handle_response_error(response)
                    return False
                    
        except asyncio.TimeoutError:
            raise TimeoutError(f"断点续传分块 {chunk_info.index} 超时")
        except aiohttp.ClientError as e:
            raise NetworkError(f"断点续传分块 {chunk_info.index} 失败: {e}")
    
    async def _get_uploaded_size(self, chunk_info: ChunkInfo, task: TransferTask) -> int:
        """获取已上传的大小"""
        if not self.session:
            return 0
        
        url = self._get_chunk_url(task, chunk_info)
        
        try:
            async with self.session.head(url) as response:
                if response.status == 200:
                    content_length = response.headers.get('Content-Length')
                    return int(content_length) if content_length else 0
                elif response.status == 206:  # Partial Content
                    content_range = response.headers.get('Content-Range', '')
                    # 解析 Content-Range: bytes 0-1023/2048
                    if content_range.startswith('bytes '):
                        range_part = content_range[6:].split('/')[0]
                        if '-' in range_part:
                            end_byte = int(range_part.split('-')[1])
                            return end_byte + 1
                return 0
        except (asyncio.TimeoutError, aiohttp.ClientError):
            return 0
    
    async def verify_chunk(
        self,
        chunk_info: ChunkInfo,
        task: TransferTask
    ) -> bool:
        """验证分块完整性"""
        return await HttpUploadStrategy.verify_chunk(self, chunk_info, task)


class StrategyFactory:
    """传输策略工厂"""
    
    _strategies = {
        'http': HttpUploadStrategy,
        'multipart': MultipartUploadStrategy,
        'websocket': WebSocketStrategy,
        'streaming': StreamingStrategy,
        'resume': ResumeUploadStrategy
    }
    
    @classmethod
    def create_strategy(
        self,
        strategy_type: str,
        config: Dict[str, Any] = None
    ) -> BaseTransferStrategy:
        """创建传输策略"""
        if strategy_type not in self._strategies:
            raise ValueError(f"不支持的传输策略: {strategy_type}")
        
        strategy_class = self._strategies[strategy_type]
        return strategy_class(config or {})
    
    @classmethod
    def register_strategy(
        self,
        name: str,
        strategy_class: type
    ) -> None:
        """注册自定义传输策略"""
        if not issubclass(strategy_class, BaseTransferStrategy):
            raise ValueError("策略类必须继承自BaseTransferStrategy")
        
        self._strategies[name] = strategy_class
    
    @classmethod
    def list_strategies(self) -> List[str]:
        """列出可用的传输策略"""
        return list(self._strategies.keys())


# 策略选择器
class StrategySelector:
    """智能策略选择器"""
    
    @staticmethod
    def select_strategy(
        file_size: int,
        network_condition: Dict[str, Any],
        server_capabilities: Dict[str, Any] = None
    ) -> str:
        """根据条件智能选择传输策略"""
        server_capabilities = server_capabilities or {}
        
        # 检查服务器支持的功能
        supports_websocket = server_capabilities.get('websocket', False)
        supports_resume = server_capabilities.get('resume', False)
        supports_streaming = server_capabilities.get('streaming', False)
        
        # 网络条件
        bandwidth = network_condition.get('bandwidth_mbps', 10)
        latency = network_condition.get('latency_ms', 100)
        stability = network_condition.get('stability', 0.9)  # 0-1
        
        # 根据文件大小选择
        if file_size > 100 * 1024 * 1024:  # 大文件 (>100MB)
            if supports_resume and stability < 0.8:
                return 'resume'  # 网络不稳定时使用断点续传
            elif supports_streaming and bandwidth > 50:
                return 'streaming'  # 高带宽时使用流式传输
            else:
                return 'http'
        
        # 根据网络条件选择
        if latency > 300 or stability < 0.7:  # 高延迟或不稳定网络
            if supports_websocket:
                return 'websocket'  # WebSocket对不稳定网络友好
            elif supports_resume:
                return 'resume'
            else:
                return 'http'
        
        # 小文件或良好网络条件
        if file_size < 10 * 1024 * 1024:  # 小文件 (<10MB)
            return 'multipart'  # 小文件使用multipart
        else:
            return 'http'  # 默认HTTP策略