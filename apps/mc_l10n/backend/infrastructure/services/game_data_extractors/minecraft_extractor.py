"""
Minecraft数据提取器
支持JSON(1.13+)和lang(1.12-)格式的语言文件提取
集成MOD检测和命名空间处理
"""

import asyncio
import json
import re
import structlog
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .base_extractor import (
    BaseGameDataExtractor, GameType, FileFormat, 
    TranslationEntry, LanguageFile, ExtractionResult
)

logger = structlog.get_logger(__name__)


class MinecraftDataExtractor(BaseGameDataExtractor):
    """Minecraft专用数据提取器"""
    
    def _get_game_type(self) -> GameType:
        return GameType.MINECRAFT
    
    def _get_supported_formats(self) -> List[FileFormat]:
        return [FileFormat.JSON, FileFormat.LANG, FileFormat.PROPERTIES]
    
    async def extract_from_discovered_items(
        self, 
        discovered_items: List[Dict[str, Any]]
    ) -> ExtractionResult:
        """从扫描发现的Minecraft项目中提取翻译数据"""
        start_time = time.time()
        
        language_files = []
        errors = []
        
        for item in discovered_items:
            try:
                if item.get("type") == "mod":
                    # 处理MOD中的语言文件
                    mod_lang_files = await self._extract_from_mod(item)
                    language_files.extend(mod_lang_files)
                    
                elif item.get("type") == "standalone_language_file":
                    # 处理独立的语言文件
                    standalone_file = await self._extract_from_standalone_file(item)
                    if standalone_file:
                        language_files.append(standalone_file)
                        
            except Exception as e:
                error_msg = f"提取失败 {item.get('path', 'unknown')}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return ExtractionResult(
            success=len(errors) == 0,
            language_files=language_files,
            statistics={},
            errors=errors,
            duration_ms=duration_ms
        )
    
    async def extract_from_file(
        self, 
        file_path: Path, 
        carrier_info: Dict[str, Any]
    ) -> List[LanguageFile]:
        """从单个文件提取翻译数据"""
        language_files = []
        
        if file_path.suffix.lower() in ['.jar', '.zip']:
            # JAR文件处理
            language_files = await self._extract_from_jar(file_path, carrier_info)
        else:
            # 单个语言文件处理
            lang_file = await self._extract_single_language_file(file_path, carrier_info)
            if lang_file:
                language_files.append(lang_file)
        
        return language_files
    
    async def _extract_from_mod(self, mod_item: Dict[str, Any]) -> List[LanguageFile]:
        """从MOD项目中提取语言文件"""
        language_files = []
        mod_path = Path(mod_item["path"])
        
        if not mod_path.exists():
            logger.warning(f"MOD文件不存在: {mod_path}")
            return language_files
        
        try:
            # 构建载体信息
            carrier_info = {
                "mod_id": mod_item.get("mod_id", mod_path.stem),
                "name": mod_item.get("name", mod_path.stem),
                "version": mod_item.get("version", "unknown"),
                "loader_type": mod_item.get("loader_type", "unknown")
            }
            
            # 使用JAR提取逻辑
            if mod_path.suffix.lower() in ['.jar', '.zip']:
                language_files = await self._extract_from_jar(mod_path, carrier_info)
            
            # 处理已发现的语言文件信息
            for lang_file_info in mod_item.get("language_files", []):
                if lang_file_info.get("type") == "language_file":
                    entries = await self._parse_language_content(
                        lang_file_info.get("translations", {}),
                        FileFormat.JSON,
                        mod_item.get("mod_id", "minecraft")
                    )
                    
                    lang_file = LanguageFile(
                        uid="",  # 将自动生成
                        path=str(mod_path),
                        relative_path=lang_file_info.get("file_path", ""),
                        locale=lang_file_info.get("language_code", "en_us"),
                        format=FileFormat.JSON,
                        size=len(str(lang_file_info.get("translations", {}))),
                        carrier_type="mod",
                        carrier_uid=mod_item.get("mod_id", mod_path.stem),
                        entries=entries
                    )
                    language_files.append(lang_file)
        
        except Exception as e:
            logger.error(f"MOD语言文件提取失败 {mod_path}: {e}")
        
        return language_files
    
    async def _extract_from_jar(
        self, 
        jar_path: Path, 
        carrier_info: Dict[str, Any]
    ) -> List[LanguageFile]:
        """从JAR文件提取语言文件"""
        language_files = []
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # 查找语言文件路径模式
                lang_file_patterns = [
                    r'assets/[^/]+/lang/[^/]+\.json$',  # 1.13+ JSON格式
                    r'assets/[^/]+/lang/[^/]+\.lang$',  # 1.12- lang格式
                    r'lang/[^/]+\.properties$'          # 一些特殊MOD使用
                ]
                
                for file_path in jar.namelist():
                    # 检查是否匹配语言文件模式
                    if any(re.match(pattern, file_path) for pattern in lang_file_patterns):
                        try:
                            # 提取语言文件内容
                            with jar.open(file_path) as lang_file:
                                content = lang_file.read().decode('utf-8')
                                
                                # 检测格式和解析内容
                                file_format = self._detect_file_format(Path(file_path))
                                namespace = self._extract_namespace_from_path(file_path)
                                locale = self._detect_locale_from_path(Path(file_path))
                                
                                # 解析翻译条目
                                entries = await self._parse_content_by_format(
                                    content, file_format, namespace
                                )
                                
                                if entries:  # 只有包含条目的文件才创建记录
                                    lang_file_obj = LanguageFile(
                                        uid="",  # 自动生成
                                        path=str(jar_path),
                                        relative_path=file_path,
                                        locale=locale,
                                        format=file_format,
                                        size=len(content),
                                        carrier_type="mod",
                                        carrier_uid=carrier_info.get("mod_id", jar_path.stem),
                                        entries=entries
                                    )
                                    language_files.append(lang_file_obj)
                                    
                                    logger.debug(
                                        f"提取语言文件: {file_path} "
                                        f"({locale}, {len(entries)} 条目)"
                                    )
                        
                        except (UnicodeDecodeError, json.JSONDecodeError) as e:
                            logger.warning(f"解析语言文件失败 {file_path}: {e}")
                            continue
                        except Exception as e:
                            logger.error(f"处理语言文件异常 {file_path}: {e}")
                            continue
        
        except zipfile.BadZipFile:
            logger.error(f"无效的ZIP/JAR文件: {jar_path}")
        except Exception as e:
            logger.error(f"JAR语言文件提取失败 {jar_path}: {e}")
        
        return language_files
    
    async def _extract_from_standalone_file(
        self, 
        file_item: Dict[str, Any]
    ) -> Optional[LanguageFile]:
        """从独立语言文件项目提取数据"""
        file_path = Path(file_item["path"])
        
        if not file_path.exists():
            return None
        
        try:
            carrier_info = {
                "mod_id": file_item.get("mod_id", "unknown"),
                "type": "standalone"
            }
            
            return await self._extract_single_language_file(file_path, carrier_info)
            
        except Exception as e:
            logger.error(f"独立语言文件提取失败 {file_path}: {e}")
            return None
    
    async def _extract_single_language_file(
        self, 
        file_path: Path, 
        carrier_info: Dict[str, Any]
    ) -> Optional[LanguageFile]:
        """提取单个语言文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_format = self._detect_file_format(file_path)
            namespace = carrier_info.get("mod_id", "minecraft")
            locale = self._detect_locale_from_path(file_path)
            
            entries = await self._parse_content_by_format(content, file_format, namespace)
            
            if not entries:
                return None
            
            return LanguageFile(
                uid="",  # 自动生成
                path=str(file_path),
                relative_path=file_path.name,
                locale=locale,
                format=file_format,
                size=len(content),
                carrier_type="standalone",
                carrier_uid=carrier_info.get("mod_id", "unknown"),
                entries=entries
            )
            
        except Exception as e:
            logger.error(f"单个语言文件提取失败 {file_path}: {e}")
            return None
    
    async def _parse_content_by_format(
        self, 
        content: str, 
        file_format: FileFormat, 
        namespace: str
    ) -> List[TranslationEntry]:
        """根据格式解析文件内容"""
        if file_format == FileFormat.JSON:
            return await self._parse_json_content(content, namespace)
        elif file_format == FileFormat.LANG:
            return await self._parse_lang_content(content, namespace)
        elif file_format == FileFormat.PROPERTIES:
            return await self._parse_properties_content(content, namespace)
        else:
            return []
    
    async def _parse_json_content(
        self, 
        content: str, 
        namespace: str
    ) -> List[TranslationEntry]:
        """解析JSON格式语言文件"""
        try:
            data = json.loads(content)
            entries = []
            
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str):
                        entries.append(TranslationEntry(
                            key=key,
                            source_text=value,
                            namespace=namespace,
                            format=FileFormat.JSON
                        ))
            
            return entries
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}")
            return []
    
    async def _parse_lang_content(
        self, 
        content: str, 
        namespace: str
    ) -> List[TranslationEntry]:
        """解析.lang格式语言文件（Minecraft 1.12-）"""
        entries = []
        
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            
            # 解析键值对
            if '=' in line:
                key, value = line.split('=', 1)
                entries.append(TranslationEntry(
                    key=key.strip(),
                    source_text=value.strip(),
                    namespace=namespace,
                    format=FileFormat.LANG,
                    metadata={"line_number": line_num}
                ))
        
        return entries
    
    async def _parse_properties_content(
        self, 
        content: str, 
        namespace: str
    ) -> List[TranslationEntry]:
        """解析Properties格式语言文件"""
        entries = []
        
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('#') or line.startswith('!'):
                continue
            
            # 处理转义的等号和冒号
            if '=' in line or ':' in line:
                # 简化处理：使用第一个=或:作为分隔符
                separator = '=' if '=' in line else ':'
                key, value = line.split(separator, 1)
                
                entries.append(TranslationEntry(
                    key=key.strip(),
                    source_text=value.strip(),
                    namespace=namespace,
                    format=FileFormat.PROPERTIES,
                    metadata={"line_number": line_num}
                ))
        
        return entries
    
    async def _parse_language_content(
        self, 
        content: Dict[str, Any], 
        file_format: FileFormat, 
        namespace: str
    ) -> List[TranslationEntry]:
        """解析已加载的语言内容字典"""
        entries = []
        
        if isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, str):
                    entries.append(TranslationEntry(
                        key=key,
                        source_text=value,
                        namespace=namespace,
                        format=file_format
                    ))
        
        return entries
    
    def _detect_file_format(self, file_path: Path) -> FileFormat:
        """检测文件格式"""
        suffix = file_path.suffix.lower()
        
        format_mapping = {
            '.json': FileFormat.JSON,
            '.lang': FileFormat.LANG,
            '.properties': FileFormat.PROPERTIES
        }
        
        return format_mapping.get(suffix, FileFormat.JSON)
    
    def _extract_namespace_from_path(self, file_path: str) -> str:
        """从文件路径提取命名空间"""
        # assets/modid/lang/locale.json -> modid
        path_parts = file_path.split('/')
        
        if len(path_parts) >= 3 and path_parts[0] == 'assets':
            return path_parts[1]
        
        # 默认命名空间
        return "minecraft"
    
    async def _extract_keyset_preview(
        self, 
        item: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """快速提取键集信息用于增量比较"""
        preview_items = []
        
        try:
            if item.get("type") == "mod":
                # 从已扫描的语言文件信息中提取键集
                for lang_file_info in item.get("language_files", []):
                    translations = lang_file_info.get("translations", {})
                    if translations:
                        keys = sorted(translations.keys())
                        keyset_hash = self._calculate_keyset_hash(keys)
                        
                        preview_items.append({
                            "carrier_uid": item.get("mod_id", "unknown"),
                            "relative_path": lang_file_info.get("file_path", ""),
                            "keyset_hash": keyset_hash,
                            "path": item["path"],
                            "carrier_info": {
                                "mod_id": item.get("mod_id"),
                                "type": "mod"
                            }
                        })
        
        except Exception as e:
            logger.warning(f"键集预览提取失败: {e}")
        
        return preview_items
    
    def _calculate_keyset_hash(self, keys: List[str]) -> str:
        """计算键集哈希"""
        import hashlib
        key_string = '|'.join(keys)
        return hashlib.blake3(key_string.encode('utf-8')).hexdigest()[:16]
    
    async def _extract_resource_pack_files(
        self, 
        pack_path: Path, 
        carrier_info: Dict[str, Any]
    ) -> List[LanguageFile]:
        """提取资源包中的语言文件"""
        language_files = []
        
        try:
            if pack_path.is_dir():
                # 目录形式的资源包
                lang_dir = pack_path / "assets"
                if lang_dir.exists():
                    for namespace_dir in lang_dir.iterdir():
                        if namespace_dir.is_dir():
                            namespace_lang_dir = namespace_dir / "lang"
                            if namespace_lang_dir.exists():
                                for lang_file in namespace_lang_dir.glob("*.json"):
                                    lang_file_obj = await self._extract_single_language_file(
                                        lang_file, 
                                        {**carrier_info, "mod_id": namespace_dir.name}
                                    )
                                    if lang_file_obj:
                                        lang_file_obj.carrier_type = "resource_pack"
                                        language_files.append(lang_file_obj)
            
            elif pack_path.suffix.lower() == '.zip':
                # ZIP形式的资源包
                language_files = await self._extract_from_jar(pack_path, carrier_info)
                # 更新载体类型
                for lf in language_files:
                    lf.carrier_type = "resource_pack"
        
        except Exception as e:
            logger.error(f"资源包语言文件提取失败 {pack_path}: {e}")
        
        return language_files