"""
Factorio数据提取器
支持locale CFG格式的翻译文件提取
处理类别管理和插值占位符
"""

import configparser
import re
import structlog
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional

from .base_extractor import (
    BaseGameDataExtractor, GameType, FileFormat, 
    TranslationEntry, LanguageFile, ExtractionResult
)

logger = structlog.get_logger(__name__)


class FactorioDataExtractor(BaseGameDataExtractor):
    """Factorio专用数据提取器"""
    
    def _get_game_type(self) -> GameType:
        return GameType.FACTORIO
    
    def _get_supported_formats(self) -> List[FileFormat]:
        return [FileFormat.CFG]
    
    async def extract_from_discovered_items(
        self, 
        discovered_items: List[Dict[str, Any]]
    ) -> ExtractionResult:
        """从扫描发现的Factorio项目中提取翻译数据"""
        import time
        start_time = time.time()
        
        language_files = []
        errors = []
        
        for item in discovered_items:
            try:
                if item.get("type") == "mod":
                    # 处理Factorio MOD
                    mod_lang_files = await self._extract_from_mod(item)
                    language_files.extend(mod_lang_files)
                    
                elif item.get("type") == "locale_file":
                    # 处理locale文件
                    locale_file = await self._extract_from_locale_file(item)
                    if locale_file:
                        language_files.append(locale_file)
                        
            except Exception as e:
                error_msg = f"Factorio提取失败 {item.get('path', 'unknown')}: {e}"
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
        """从单个Factorio文件提取翻译数据"""
        language_files = []
        
        if file_path.is_dir():
            # 处理MOD目录
            language_files = await self._extract_from_mod_directory(file_path, carrier_info)
        elif file_path.suffix.lower() == '.zip':
            # 处理ZIP形式的MOD
            language_files = await self._extract_from_mod_zip(file_path, carrier_info)
        elif file_path.suffix.lower() == '.cfg':
            # 处理单个locale文件
            lang_file = await self._extract_single_locale_file(file_path, carrier_info)
            if lang_file:
                language_files.append(lang_file)
        
        return language_files
    
    async def _extract_from_mod(self, mod_item: Dict[str, Any]) -> List[LanguageFile]:
        """从Factorio MOD项目中提取locale文件"""
        mod_path = Path(mod_item["path"])
        
        if not mod_path.exists():
            logger.warning(f"Factorio MOD路径不存在: {mod_path}")
            return []
        
        # 解析info.json获取MOD信息
        mod_info = await self._parse_info_json(mod_path)
        
        carrier_info = {
            "mod_id": mod_info.get("name", mod_path.name),
            "title": mod_info.get("title", mod_path.name),
            "version": mod_info.get("version", "unknown"),
            "author": mod_info.get("author", "Unknown"),
            "dependencies": mod_info.get("dependencies", [])
        }
        
        if mod_path.is_dir():
            return await self._extract_from_mod_directory(mod_path, carrier_info)
        elif mod_path.suffix.lower() == '.zip':
            return await self._extract_from_mod_zip(mod_path, carrier_info)
        
        return []
    
    async def _extract_from_mod_directory(
        self, 
        mod_path: Path, 
        carrier_info: Dict[str, Any]
    ) -> List[LanguageFile]:
        """从MOD目录中提取locale文件"""
        language_files = []
        
        # 查找locale目录
        locale_dir = mod_path / "locale"
        if not locale_dir.exists():
            logger.debug(f"Factorio MOD无locale目录: {mod_path}")
            return language_files
        
        # 遍历语言目录
        for lang_dir in locale_dir.iterdir():
            if not lang_dir.is_dir():
                continue
            
            locale_code = lang_dir.name.lower()
            
            # 处理该语言目录下的所有cfg文件
            for cfg_file in lang_dir.glob("*.cfg"):
                try:
                    lang_file = await self._extract_locale_cfg(
                        cfg_file, locale_code, carrier_info
                    )
                    if lang_file:
                        language_files.append(lang_file)
                except Exception as e:
                    logger.warning(f"locale文件处理失败 {cfg_file}: {e}")
        
        return language_files
    
    async def _extract_from_mod_zip(
        self, 
        zip_path: Path, 
        carrier_info: Dict[str, Any]
    ) -> List[LanguageFile]:
        """从ZIP形式的MOD中提取locale文件"""
        language_files = []
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                # 查找locale文件路径模式
                locale_pattern = re.compile(r'^[^/]+/locale/([^/]+)/([^/]+\.cfg)$')
                
                for file_path in zip_file.namelist():
                    match = locale_pattern.match(file_path)
                    if match:
                        locale_code = match.group(1).lower()
                        cfg_name = match.group(2)
                        
                        try:
                            # 读取cfg文件内容
                            with zip_file.open(file_path) as cfg_file:
                                content = cfg_file.read().decode('utf-8')
                            
                            # 解析locale内容
                            entries = await self._parse_cfg_content(
                                content, cfg_name, carrier_info.get("mod_id", "unknown")
                            )
                            
                            if entries:
                                relative_path = f"locale/{locale_code}/{cfg_name}"
                                
                                lang_file = LanguageFile(
                                    uid="",  # 自动生成
                                    path=str(zip_path),
                                    relative_path=relative_path,
                                    locale=locale_code,
                                    format=FileFormat.CFG,
                                    size=len(content),
                                    carrier_type="mod",
                                    carrier_uid=carrier_info.get("mod_id", "unknown"),
                                    entries=entries
                                )
                                language_files.append(lang_file)
                                
                        except (UnicodeDecodeError, Exception) as e:
                            logger.warning(f"ZIP内locale文件处理失败 {file_path}: {e}")
        
        except zipfile.BadZipFile:
            logger.error(f"无效的ZIP文件: {zip_path}")
        except Exception as e:
            logger.error(f"ZIP MOD处理失败 {zip_path}: {e}")
        
        return language_files
    
    async def _extract_locale_cfg(
        self, 
        cfg_file: Path, 
        locale_code: str, 
        carrier_info: Dict[str, Any]
    ) -> Optional[LanguageFile]:
        """提取单个locale CFG文件"""
        try:
            with open(cfg_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            entries = await self._parse_cfg_content(
                content, cfg_file.name, carrier_info.get("mod_id", "unknown")
            )
            
            if not entries:
                return None
            
            relative_path = f"locale/{locale_code}/{cfg_file.name}"
            
            return LanguageFile(
                uid="",  # 自动生成
                path=str(cfg_file),
                relative_path=relative_path,
                locale=locale_code,
                format=FileFormat.CFG,
                size=cfg_file.stat().st_size,
                carrier_type="mod",
                carrier_uid=carrier_info.get("mod_id", "unknown"),
                entries=entries
            )
            
        except Exception as e:
            logger.error(f"locale CFG处理失败 {cfg_file}: {e}")
            return None
    
    async def _parse_cfg_content(
        self, 
        content: str, 
        file_name: str, 
        mod_id: str
    ) -> List[TranslationEntry]:
        """解析CFG格式的locale内容"""
        entries = []
        
        try:
            # 使用configparser解析INI/CFG格式
            config = configparser.ConfigParser(
                interpolation=None,  # 禁用插值以保留__1__等占位符
                allow_no_value=True
            )
            
            # 处理特殊字符和编码
            config.read_string(content)
            
            for section_name in config.sections():
                section = config[section_name]
                
                for key, value in section.items():
                    if value is not None:
                        # 处理Factorio特有的插值占位符
                        processed_value = self._process_factorio_interpolation(value)
                        
                        # 构建完整的键名
                        full_key = f"{section_name}.{key}"
                        
                        entries.append(TranslationEntry(
                            key=full_key,
                            source_text=processed_value,
                            namespace=mod_id,
                            context=section_name,
                            format=FileFormat.CFG,
                            metadata={
                                "section": section_name,
                                "file": file_name,
                                "has_placeholders": self._has_placeholders(value)
                            }
                        ))
            
        except configparser.Error as e:
            logger.warning(f"CFG解析失败: {e}")
            # 尝试手动解析
            entries = await self._manual_parse_cfg(content, file_name, mod_id)
        except Exception as e:
            logger.error(f"CFG内容处理失败: {e}")
        
        return entries
    
    async def _manual_parse_cfg(
        self, 
        content: str, 
        file_name: str, 
        mod_id: str
    ) -> List[TranslationEntry]:
        """手动解析CFG内容（备用方法）"""
        entries = []
        current_section = "general"
        
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            
            # 检测节（section）
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                continue
            
            # 解析键值对
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key and value:
                    full_key = f"{current_section}.{key}"
                    processed_value = self._process_factorio_interpolation(value)
                    
                    entries.append(TranslationEntry(
                        key=full_key,
                        source_text=processed_value,
                        namespace=mod_id,
                        context=current_section,
                        format=FileFormat.CFG,
                        metadata={
                            "section": current_section,
                            "file": file_name,
                            "line_number": line_num,
                            "has_placeholders": self._has_placeholders(value)
                        }
                    ))
        
        return entries
    
    def _process_factorio_interpolation(self, text: str) -> str:
        """处理Factorio的插值占位符"""
        # Factorio使用__1__, __2__等作为占位符
        # 这里保持原样，不做特殊处理
        return text
    
    def _has_placeholders(self, text: str) -> bool:
        """检查文本是否包含占位符"""
        placeholder_pattern = r'__\d+__'
        return bool(re.search(placeholder_pattern, text))
    
    async def _extract_from_locale_file(
        self, 
        file_item: Dict[str, Any]
    ) -> Optional[LanguageFile]:
        """从locale文件项目提取数据"""
        file_path = Path(file_item["path"])
        
        if not file_path.exists():
            return None
        
        carrier_info = {
            "mod_id": file_item.get("mod_id", "unknown"),
            "type": "locale"
        }
        
        return await self._extract_single_locale_file(file_path, carrier_info)
    
    async def _extract_single_locale_file(
        self, 
        file_path: Path, 
        carrier_info: Dict[str, Any]
    ) -> Optional[LanguageFile]:
        """提取单个locale文件"""
        try:
            # 从路径推断语言代码
            path_parts = file_path.parts
            locale_code = "unknown"
            
            # 查找locale目录和语言代码
            for i, part in enumerate(path_parts):
                if part == "locale" and i + 1 < len(path_parts):
                    locale_code = path_parts[i + 1].lower()
                    break
            
            return await self._extract_locale_cfg(file_path, locale_code, carrier_info)
                
        except Exception as e:
            logger.error(f"单个locale文件处理失败 {file_path}: {e}")
            return None
    
    async def _parse_info_json(self, mod_path: Path) -> Dict[str, Any]:
        """解析Factorio MOD的info.json文件"""
        if mod_path.is_dir():
            info_file = mod_path / "info.json"
        else:
            # ZIP文件中的info.json
            try:
                with zipfile.ZipFile(mod_path, 'r') as zip_file:
                    for file_path in zip_file.namelist():
                        if file_path.endswith('/info.json') or file_path == 'info.json':
                            with zip_file.open(file_path) as info_file:
                                import json
                                return json.loads(info_file.read().decode('utf-8'))
            except Exception as e:
                logger.warning(f"ZIP中info.json读取失败: {e}")
            return {}
        
        mod_info = {}
        
        if not info_file.exists():
            return mod_info
        
        try:
            import json
            with open(info_file, 'r', encoding='utf-8') as f:
                mod_info = json.load(f)
                
        except json.JSONDecodeError as e:
            logger.warning(f"info.json解析失败 {info_file}: {e}")
        except Exception as e:
            logger.warning(f"info.json处理失败 {info_file}: {e}")
        
        return mod_info
    
    async def _extract_keyset_preview(
        self, 
        item: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """快速提取Factorio键集信息用于增量比较"""
        preview_items = []
        
        try:
            if item.get("type") == "mod":
                mod_path = Path(item["path"])
                
                if mod_path.is_dir():
                    locale_dir = mod_path / "locale"
                    if locale_dir.exists():
                        for lang_dir in locale_dir.iterdir():
                            if lang_dir.is_dir():
                                locale_code = lang_dir.name.lower()
                                for cfg_file in lang_dir.glob("*.cfg"):
                                    keys = await self._quick_extract_cfg_keys(cfg_file)
                                    if keys:
                                        keyset_hash = self._calculate_keyset_hash(keys)
                                        
                                        relative_path = f"locale/{locale_code}/{cfg_file.name}"
                                        preview_items.append({
                                            "carrier_uid": item.get("mod_id", mod_path.name),
                                            "relative_path": relative_path,
                                            "keyset_hash": keyset_hash,
                                            "path": str(cfg_file),
                                            "carrier_info": {"mod_id": item.get("mod_id"), "type": "mod"}
                                        })
                
                elif mod_path.suffix.lower() == '.zip':
                    # 处理ZIP文件的快速键集提取
                    with zipfile.ZipFile(mod_path, 'r') as zip_file:
                        locale_pattern = re.compile(r'^[^/]+/locale/([^/]+)/([^/]+\.cfg)$')
                        
                        for file_path in zip_file.namelist():
                            match = locale_pattern.match(file_path)
                            if match:
                                locale_code = match.group(1).lower()
                                cfg_name = match.group(2)
                                
                                try:
                                    with zip_file.open(file_path) as cfg_file:
                                        content = cfg_file.read().decode('utf-8')
                                    
                                    keys = await self._quick_extract_cfg_keys_from_content(content)
                                    if keys:
                                        keyset_hash = self._calculate_keyset_hash(keys)
                                        
                                        relative_path = f"locale/{locale_code}/{cfg_name}"
                                        preview_items.append({
                                            "carrier_uid": item.get("mod_id", mod_path.name),
                                            "relative_path": relative_path,
                                            "keyset_hash": keyset_hash,
                                            "path": str(mod_path),
                                            "carrier_info": {"mod_id": item.get("mod_id"), "type": "mod"}
                                        })
                                except Exception:
                                    continue
        
        except Exception as e:
            logger.warning(f"Factorio键集预览失败: {e}")
        
        return preview_items
    
    async def _quick_extract_cfg_keys(self, cfg_file: Path) -> List[str]:
        """快速提取CFG文件的键名（用于键集比较）"""
        try:
            with open(cfg_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return await self._quick_extract_cfg_keys_from_content(content)
        except Exception:
            return []
    
    async def _quick_extract_cfg_keys_from_content(self, content: str) -> List[str]:
        """从CFG内容快速提取键名"""
        keys = []
        current_section = "general"
        
        for line in content.splitlines():
            line = line.strip()
            
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                continue
            
            if '=' in line:
                key, _ = line.split('=', 1)
                key = key.strip()
                if key:
                    full_key = f"{current_section}.{key}"
                    keys.append(full_key)
        
        return sorted(keys)
    
    def _calculate_keyset_hash(self, keys: List[str]) -> str:
        """计算键集哈希"""
        import hashlib
        key_string = '|'.join(keys)
        return hashlib.blake3(key_string.encode('utf-8')).hexdigest()[:16]