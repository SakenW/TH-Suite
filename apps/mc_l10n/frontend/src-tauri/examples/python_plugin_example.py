#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python插件示例 - 高级Minecraft数据包提取器
演示如何创建Python子进程插件，通过JSON-RPC与Rust进程通信
"""

import asyncio
import json
import sys
import os
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JsonRpcServer:
    """JSON-RPC 2.0 服务器"""
    
    def __init__(self):
        self.methods = {}
        self.running = True
    
    def register_method(self, name: str, func):
        """注册RPC方法"""
        self.methods[name] = func
    
    async def handle_request(self, request_data: str) -> str:
        """处理RPC请求"""
        try:
            request = json.loads(request_data)
            
            if not isinstance(request, dict) or request.get('jsonrpc') != '2.0':
                return self.error_response(None, -32600, "Invalid Request")
            
            method = request.get('method')
            params = request.get('params', {})
            request_id = request.get('id')
            
            if method not in self.methods:
                return self.error_response(request_id, -32601, "Method not found")
            
            try:
                result = await self.methods[method](params)
                return self.success_response(request_id, result)
            except Exception as e:
                logger.error(f"方法执行错误 {method}: {e}")
                return self.error_response(request_id, -32603, str(e))
                
        except json.JSONDecodeError:
            return self.error_response(None, -32700, "Parse error")
        except Exception as e:
            logger.error(f"请求处理错误: {e}")
            return self.error_response(None, -32603, str(e))
    
    def success_response(self, request_id, result):
        """成功响应"""
        return json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        })
    
    def error_response(self, request_id, code: int, message: str):
        """错误响应"""
        return json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        })

class AdvancedMinecraftDatapackExtractor:
    """高级Minecraft数据包提取器"""
    
    def __init__(self):
        self.plugin_info = {
            "name": "Advanced Minecraft Datapack Extractor",
            "version": "1.0.0",
            "author": "TH-Suite Python Plugin",
            "description": "高级Minecraft数据包提取器，支持函数、进度、配方等的本地化",
            "supported_formats": ["zip", "jar", "mcpack"]
        }
        logger.info(f"初始化插件: {self.plugin_info['name']}")
    
    async def supports(self, params: Dict[str, Any]) -> bool:
        """检查是否支持指定文件"""
        file_path = Path(params.get("file_path", ""))
        
        if not file_path.exists():
            return False
        
        # 检查文件扩展名
        if file_path.suffix.lower() not in ['.zip', '.jar', '.mcpack']:
            return False
        
        # 检查是否为有效的ZIP文件
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # 检查是否包含数据包标识
                if self._is_datapack(zip_file):
                    return True
                
                # 检查是否包含可本地化的内容
                return self._has_localizable_content(zip_file)
        except (zipfile.BadZipFile, PermissionError):
            return False
    
    def _is_datapack(self, zip_file: zipfile.ZipFile) -> bool:
        """检查是否为Minecraft数据包"""
        # 检查pack.mcmeta文件
        if 'pack.mcmeta' in zip_file.namelist():
            try:
                with zip_file.open('pack.mcmeta') as f:
                    pack_meta = json.load(f)
                    return 'pack' in pack_meta and 'pack_format' in pack_meta['pack']
            except (json.JSONDecodeError, KeyError):
                pass
        
        # 检查data目录结构
        file_list = zip_file.namelist()
        return any(path.startswith('data/') for path in file_list)
    
    def _has_localizable_content(self, zip_file: zipfile.ZipFile) -> bool:
        """检查是否包含可本地化的内容"""
        localizable_patterns = [
            'data/',  # 数据包内容
            'assets/',  # 资源包内容
            '/lang/',  # 语言文件
            '/advancement/',  # 进度文件
            '/recipes/',  # 配方文件
            '.json',  # JSON文件
        ]
        
        file_list = zip_file.namelist()
        return any(
            any(pattern in path for pattern in localizable_patterns)
            for path in file_list
        )
    
    async def extract(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """提取文件内容"""
        file_path = Path(params.get("file_path", ""))
        start_time = datetime.now()
        
        logger.info(f"开始提取文件: {file_path}")
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # 提取基本信息
                metadata = await self._extract_metadata(file_path, zip_file)
                
                # 提取语言文件
                language_files = await self._extract_language_files(zip_file)
                
                # 提取可本地化的JSON文件
                localizable_files = await self._extract_localizable_json(zip_file)
                
                # 合并语言文件信息
                all_language_files = language_files + localizable_files
                
                # 计算统计信息
                total_entries = sum(lf.get('entry_count', 0) for lf in all_language_files)
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return {
                    "success": True,
                    "file_type": "minecraft_datapack",
                    "language_files": all_language_files,
                    "metadata": metadata,
                    "error": None,
                    "warnings": [],
                    "stats": {
                        "processing_time_ms": int(processing_time),
                        "files_scanned": len(zip_file.namelist()),
                        "language_files_found": len(all_language_files),
                        "total_entries": total_entries,
                        "memory_used": file_path.stat().st_size
                    }
                }
                
        except Exception as e:
            logger.error(f"提取失败: {e}")
            return {
                "success": False,
                "file_type": "unknown",
                "language_files": [],
                "metadata": {"name": file_path.name, "size": 0, "hash": "", "uida_compatible": False},
                "error": str(e),
                "warnings": [],
                "stats": {"processing_time_ms": 0, "files_scanned": 0, "language_files_found": 0, "total_entries": 0, "memory_used": 0}
            }
    
    async def _extract_metadata(self, file_path: Path, zip_file: zipfile.ZipFile) -> Dict[str, Any]:
        """提取文件元数据"""
        # 计算文件哈希
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # 尝试读取pack.mcmeta
        pack_info = None
        if 'pack.mcmeta' in zip_file.namelist():
            try:
                with zip_file.open('pack.mcmeta') as f:
                    pack_data = json.load(f)
                    pack_info = {
                        "pack_format": pack_data.get('pack', {}).get('pack_format', 0),
                        "description": pack_data.get('pack', {}).get('description', ''),
                        "supported_versions": self._get_supported_versions(pack_data.get('pack', {}).get('pack_format', 0))
                    }
            except (json.JSONDecodeError, KeyError):
                logger.warning("无法解析pack.mcmeta文件")
        
        return {
            "name": file_path.name,
            "size": file_path.stat().st_size,
            "hash": file_hash,
            "mod_info": None,
            "pack_info": pack_info,
            "uida_compatible": True
        }
    
    def _get_supported_versions(self, pack_format: int) -> List[str]:
        """根据pack_format获取支持的Minecraft版本"""
        version_map = {
            1: ["1.6.1", "1.8.9"],
            2: ["1.9", "1.10.2"],
            3: ["1.11", "1.12.2"],
            4: ["1.13", "1.14.4"],
            5: ["1.15", "1.16.1"],
            6: ["1.16.2", "1.16.5"],
            7: ["1.17", "1.17.1"],
            8: ["1.18", "1.18.2"],
            9: ["1.19", "1.19.2"],
            10: ["1.19.3", "1.19.4"],
            11: ["1.20", "1.20.1"],
            12: ["1.20.2", "1.20.4"],
            13: ["1.20.5", "1.20.6"],
            14: ["1.21"],
        }
        return version_map.get(pack_format, ["unknown"])
    
    async def _extract_language_files(self, zip_file: zipfile.ZipFile) -> List[Dict[str, Any]]:
        """提取标准语言文件"""
        language_files = []
        
        for file_path in zip_file.namelist():
            if '/lang/' in file_path and file_path.endswith('.json'):
                try:
                    with zip_file.open(file_path) as f:
                        content = f.read().decode('utf-8')
                        lang_data = json.loads(content)
                    
                    # 提取语言代码
                    lang_code = Path(file_path).stem
                    
                    # 提取命名空间
                    namespace = self._extract_namespace(file_path)
                    
                    # 分析翻译条目
                    entries = []
                    for key, value in lang_data.items():
                        entries.append({
                            "key": key,
                            "value": value,
                            "category": self._categorize_key(key)
                        })
                    
                    language_files.append({
                        "language_code": lang_code,
                        "path": file_path,
                        "entry_count": len(entries),
                        "format": "json",
                        "namespace": namespace,
                        "sample_entries": entries[:5]  # 取前5个作为示例
                    })
                    
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"无法解析语言文件 {file_path}: {e}")
        
        return language_files
    
    async def _extract_localizable_json(self, zip_file: zipfile.ZipFile) -> List[Dict[str, Any]]:
        """提取可本地化的JSON文件（进度、配方等）"""
        localizable_files = []
        
        # 定义可本地化的文件类型
        localizable_types = {
            '/advancements/': 'advancement',
            '/recipes/': 'recipe',
            '/loot_tables/': 'loot_table',
            '/functions/': 'function',
        }
        
        for file_path in zip_file.namelist():
            if not file_path.endswith('.json'):
                continue
            
            # 检查是否为可本地化类型
            file_type = None
            for pattern, ftype in localizable_types.items():
                if pattern in file_path:
                    file_type = ftype
                    break
            
            if not file_type:
                continue
            
            try:
                with zip_file.open(file_path) as f:
                    content = f.read().decode('utf-8')
                    json_data = json.loads(content)
                
                # 提取可本地化的字符串
                localizable_entries = self._extract_localizable_strings(json_data, file_type)
                
                if localizable_entries:
                    namespace = self._extract_namespace(file_path)
                    
                    localizable_files.append({
                        "language_code": "localizable_content",
                        "path": file_path,
                        "entry_count": len(localizable_entries),
                        "format": f"json_{file_type}",
                        "namespace": namespace,
                        "sample_entries": localizable_entries[:3]
                    })
                    
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"无法解析JSON文件 {file_path}: {e}")
        
        return localizable_files
    
    def _extract_localizable_strings(self, json_data: Any, file_type: str) -> List[Dict[str, Any]]:
        """从JSON数据中提取可本地化的字符串"""
        entries = []
        
        def extract_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # 检查是否为可本地化的字段
                    if self._is_localizable_field(key, value, file_type):
                        entries.append({
                            "key": current_path,
                            "value": str(value),
                            "category": file_type
                        })
                    elif isinstance(value, (dict, list)):
                        extract_recursive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_recursive(item, f"{path}[{i}]")
        
        extract_recursive(json_data)
        return entries
    
    def _is_localizable_field(self, key: str, value: Any, file_type: str) -> bool:
        """判断字段是否可本地化"""
        if not isinstance(value, str):
            return False
        
        # 常见的可本地化字段名
        localizable_fields = {
            'title', 'description', 'name', 'text', 'value',
            'display_name', 'tooltip', 'lore', 'message'
        }
        
        # 根据文件类型的特殊字段
        type_specific_fields = {
            'advancement': {'title', 'description'},
            'recipe': {'description'},
            'loot_table': {'display_name', 'lore'},
            'function': {'comment', 'description'}
        }
        
        check_fields = localizable_fields | type_specific_fields.get(file_type, set())
        
        return key.lower() in check_fields and len(value.strip()) > 0
    
    def _extract_namespace(self, file_path: str) -> Optional[str]:
        """提取命名空间"""
        if file_path.startswith('data/'):
            parts = file_path.split('/')
            if len(parts) > 1:
                return parts[1]
        elif file_path.startswith('assets/'):
            parts = file_path.split('/')
            if len(parts) > 1:
                return parts[1]
        return None
    
    def _categorize_key(self, key: str) -> Optional[str]:
        """分类翻译键"""
        categories = {
            'advancements.': 'advancement',
            'block.': 'block',
            'item.': 'item',
            'entity.': 'entity',
            'gui.': 'gui',
            'menu.': 'menu',
            'key.': 'key',
            'subtitle.': 'sound',
            'death.': 'death',
            'commands.': 'command',
        }
        
        for prefix, category in categories.items():
            if key.startswith(prefix):
                return category
        
        return 'other'

class PythonPluginHost:
    """Python插件主机"""
    
    def __init__(self):
        self.server = JsonRpcServer()
        self.extractor = AdvancedMinecraftDatapackExtractor()
        self.initialized = False
        
        # 注册RPC方法
        self.server.register_method('initialize', self.initialize)
        self.server.register_method('supports', self.extractor.supports)
        self.server.register_method('extract', self.extractor.extract)
        self.server.register_method('get_info', self.get_info)
        self.server.register_method('shutdown', self.shutdown)
    
    async def initialize(self, params: Dict[str, Any]) -> Dict[str, str]:
        """初始化插件"""
        logger.info("初始化Python插件")
        self.initialized = True
        return {"status": "initialized", "version": "1.0.0"}
    
    async def get_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取插件信息"""
        return self.extractor.plugin_info
    
    async def shutdown(self, params: Dict[str, Any]) -> Dict[str, str]:
        """关闭插件"""
        logger.info("关闭Python插件")
        self.server.running = False
        return {"status": "shutdown"}
    
    async def run(self):
        """运行插件主循环"""
        logger.info("启动Python插件RPC服务器")
        
        try:
            while self.server.running:
                # 从stdin读取请求
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # 处理请求
                response = await self.server.handle_request(line)
                
                # 发送响应到stdout
                print(response, flush=True)
                
        except KeyboardInterrupt:
            logger.info("接收到中断信号，正在关闭...")
        except Exception as e:
            logger.error(f"运行时错误: {e}")
        finally:
            logger.info("Python插件已关闭")

def main():
    """主函数"""
    # 检查是否在沙箱模式下运行
    if os.environ.get('TH_PLUGIN_SANDBOX') == '1':
        logger.info("在沙箱模式下运行")
        
        # 限制可访问的模块
        restricted_modules = ['subprocess', 'os.system', 'eval', 'exec']
        for module in restricted_modules:
            if module in sys.modules:
                del sys.modules[module]
    
    # 创建并运行插件主机
    host = PythonPluginHost()
    
    try:
        asyncio.run(host.run())
    except Exception as e:
        logger.error(f"插件启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()