"""
JAR文件解压助手
解决直接在内存中读取JAR内容导致的性能问题
实现方案：解压到临时目录 → 读取文件 → 清理临时文件
"""

import tempfile
import shutil
import asyncio
import structlog
import glob
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager
from zipfile import ZipFile, BadZipFile

logger = structlog.get_logger(__name__)


class JarExtractionHelper:
    """JAR文件解压助手"""
    
    def __init__(self, temp_base_dir: Optional[str] = None):
        """
        初始化
        
        Args:
            temp_base_dir: 临时目录基础路径，None则使用系统默认
        """
        self.temp_base_dir = temp_base_dir
        self._cleanup_paths: List[Path] = []
        self._workspace_prefix = "mc_l10n_"
    
    @asynccontextmanager
    async def extract_jar(self, jar_path: Path) -> AsyncGenerator[Path, None]:
        """
        异步上下文管理器：解压JAR文件到临时目录
        
        Args:
            jar_path: JAR文件路径
            
        Yields:
            Path: 解压后的临时目录路径
            
        Usage:
            async with helper.extract_jar(jar_path) as temp_dir:
                # 在temp_dir中处理解压后的文件
                pass
            # 自动清理临时目录
        """
        temp_dir = None
        try:
            # 创建临时目录
            temp_dir = await self._create_temp_dir(jar_path.name)
            
            # 解压JAR文件
            await self._extract_jar_to_dir(jar_path, temp_dir)
            
            logger.info("JAR文件解压完成", 
                       jar=str(jar_path), 
                       temp_dir=str(temp_dir),
                       size=self._get_dir_size(temp_dir))
            
            yield temp_dir
            
        finally:
            # 清理临时目录
            if temp_dir and temp_dir.exists():
                await self._cleanup_temp_dir(temp_dir)
    
    async def _create_temp_dir(self, jar_name: str) -> Path:
        """创建临时目录"""
        # 使用JAR文件名作为临时目录前缀
        prefix = f"mc_l10n_jar_{jar_name.replace('.', '_')}_"
        
        # 创建临时目录
        temp_dir = Path(tempfile.mkdtemp(
            prefix=prefix,
            dir=self.temp_base_dir
        ))
        
        self._cleanup_paths.append(temp_dir)
        return temp_dir
    
    async def _extract_jar_to_dir(self, jar_path: Path, temp_dir: Path):
        """将JAR文件解压到指定目录"""
        if not jar_path.exists():
            raise FileNotFoundError(f"JAR文件不存在: {jar_path}")
        
        def _extract_sync():
            """同步解压操作"""
            try:
                with ZipFile(jar_path, 'r') as zip_file:
                    # 检查ZIP文件完整性
                    if zip_file.testzip() is not None:
                        raise BadZipFile(f"ZIP文件损坏: {jar_path}")
                    
                    # 安全解压：检查路径遍历攻击
                    for member in zip_file.namelist():
                        if member.startswith('/') or '..' in member:
                            logger.warning("跳过不安全的路径", path=member)
                            continue
                        
                        # 提取文件
                        zip_file.extract(member, temp_dir)
                        
            except BadZipFile as e:
                raise BadZipFile(f"无法解压JAR文件 {jar_path}: {e}")
            except Exception as e:
                raise RuntimeError(f"解压过程中发生错误 {jar_path}: {e}")
        
        # 在线程池中执行同步解压操作
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _extract_sync)
    
    async def _cleanup_temp_dir(self, temp_dir: Path):
        """清理临时目录"""
        def _cleanup_sync():
            """同步清理操作"""
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    logger.debug("临时目录已清理", path=str(temp_dir))
            except Exception as e:
                logger.warning("清理临时目录失败", path=str(temp_dir), error=str(e))
        
        # 在线程池中执行同步清理操作
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _cleanup_sync)
        
        # 从清理列表中移除
        if temp_dir in self._cleanup_paths:
            self._cleanup_paths.remove(temp_dir)
    
    def _get_dir_size(self, dir_path: Path) -> int:
        """获取目录大小（字节）"""
        total_size = 0
        try:
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception:
            pass
        return total_size
    
    async def cleanup_all(self):
        """清理所有创建的临时目录"""
        cleanup_tasks = []
        for temp_dir in self._cleanup_paths.copy():
            if temp_dir.exists():
                cleanup_tasks.append(self._cleanup_temp_dir(temp_dir))
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            logger.info("已清理所有临时目录", count=len(cleanup_tasks))
    
    async def cleanup_workspace(self):
        """清理工作区中所有相关的临时目录
        
        扫描前调用此方法清理可能遗留的解压文件
        """
        if self.temp_base_dir:
            workspace_dir = Path(self.temp_base_dir)
        else:
            workspace_dir = Path(tempfile.gettempdir())
        
        if not workspace_dir.exists():
            return
        
        # 查找所有匹配前缀的临时目录
        cleanup_tasks = []
        cleanup_count = 0
        
        try:
            for temp_path in workspace_dir.iterdir():
                if (temp_path.is_dir() and 
                    temp_path.name.startswith(self._workspace_prefix)):
                    cleanup_tasks.append(self._cleanup_temp_dir(temp_path))
                    cleanup_count += 1
                    
                    # 也从清理列表中移除（如果存在）
                    if temp_path in self._cleanup_paths:
                        self._cleanup_paths.remove(temp_path)
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                logger.info("工作区清理完成", 
                           workspace=str(workspace_dir),
                           cleaned_dirs=cleanup_count)
            else:
                logger.debug("工作区无需清理", workspace=str(workspace_dir))
                
        except Exception as e:
            logger.warning("工作区清理失败", 
                         workspace=str(workspace_dir), 
                         error=str(e))


class AsyncJarReader:
    """异步JAR文件读取器
    
    结合JarExtractionHelper提供便捷的JAR文件读取接口
    """
    
    def __init__(self, temp_base_dir: Optional[str] = None):
        self.helper = JarExtractionHelper(temp_base_dir)
    
    async def find_language_files(self, jar_path: Path, language_patterns: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        查找JAR文件中的语言文件
        
        Args:
            jar_path: JAR文件路径
            language_patterns: 语言文件模式 {'json': r'pattern', 'properties': r'pattern'}
            
        Returns:
            List[Dict]: 语言文件信息列表
        """
        language_files = []
        
        async with self.helper.extract_jar(jar_path) as temp_dir:
            # 在解压后的目录中查找语言文件
            for pattern_type, pattern in language_patterns.items():
                import re
                pattern_regex = re.compile(pattern)
                
                for file_path in temp_dir.rglob('*'):
                    if not file_path.is_file():
                        continue
                    
                    rel_path = file_path.relative_to(temp_dir)
                    if pattern_regex.search(str(rel_path)):
                        try:
                            # 读取文件内容
                            content = file_path.read_text(encoding='utf-8')
                            
                            language_files.append({
                                'rel_path': str(rel_path),
                                'format': pattern_type,
                                'size': file_path.stat().st_size,
                                'content': content,
                                'file_path': file_path  # 临时文件路径，仅在上下文内有效
                            })
                            
                        except Exception as e:
                            logger.debug("无法读取语言文件", 
                                       file=str(rel_path), 
                                       error=str(e))
        
        return language_files
    
    async def find_manifest_files(self, jar_path: Path) -> Dict[str, Any]:
        """
        查找JAR文件中的manifest文件
        
        Args:
            jar_path: JAR文件路径
            
        Returns:
            Dict: manifest信息
        """
        manifest_info = {}
        
        async with self.helper.extract_jar(jar_path) as temp_dir:
            # 查找各种manifest文件
            manifest_files = {
                'mods.toml': temp_dir / 'META-INF' / 'mods.toml',  # Forge
                'fabric.mod.json': temp_dir / 'fabric.mod.json',  # Fabric
                'mcmod.info': temp_dir / 'mcmod.info',  # Legacy
                'pack.mcmeta': temp_dir / 'pack.mcmeta'  # Resource Pack
            }
            
            for manifest_type, manifest_path in manifest_files.items():
                if manifest_path.exists():
                    try:
                        content = manifest_path.read_text(encoding='utf-8')
                        manifest_info[manifest_type] = {
                            'content': content[:1000],  # 限制内容长度
                            'size': manifest_path.stat().st_size
                        }
                    except Exception as e:
                        logger.debug("无法读取manifest文件", 
                                   file=manifest_type, 
                                   error=str(e))
        
        return manifest_info
    
    async def cleanup(self):
        """清理所有临时文件"""
        await self.helper.cleanup_all()


# 全局实例（可选）
_global_jar_reader: Optional[AsyncJarReader] = None

def get_jar_reader(temp_base_dir: Optional[str] = None) -> AsyncJarReader:
    """获取全局JAR读取器实例"""
    global _global_jar_reader
    if _global_jar_reader is None:
        _global_jar_reader = AsyncJarReader(temp_base_dir)
    return _global_jar_reader

async def cleanup_global_jar_reader():
    """清理全局JAR读取器"""
    global _global_jar_reader
    if _global_jar_reader:
        await _global_jar_reader.cleanup()
        _global_jar_reader = None