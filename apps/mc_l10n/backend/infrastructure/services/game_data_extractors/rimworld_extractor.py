"""
RimWorld数据提取器
支持DefInjection XML格式的翻译文件提取
处理Def路径映射和模组依赖关系
"""

import xml.etree.ElementTree as ET
import re
import structlog
from pathlib import Path
from typing import Dict, List, Any, Optional

from .base_extractor import (
    BaseGameDataExtractor, GameType, FileFormat, 
    TranslationEntry, LanguageFile, ExtractionResult
)

logger = structlog.get_logger(__name__)


class RimWorldDataExtractor(BaseGameDataExtractor):
    """RimWorld专用数据提取器"""
    
    def _get_game_type(self) -> GameType:
        return GameType.RIMWORLD
    
    def _get_supported_formats(self) -> List[FileFormat]:
        return [FileFormat.XML]
    
    async def extract_from_discovered_items(
        self, 
        discovered_items: List[Dict[str, Any]]
    ) -> ExtractionResult:
        """从扫描发现的RimWorld项目中提取翻译数据"""
        import time
        start_time = time.time()
        
        language_files = []
        errors = []
        
        for item in discovered_items:
            try:
                if item.get("type") == "mod":
                    # 处理RimWorld MOD
                    mod_lang_files = await self._extract_from_mod(item)
                    language_files.extend(mod_lang_files)
                    
                elif item.get("type") == "definjection_file":
                    # 处理DefInjection文件
                    def_file = await self._extract_from_definjection_file(item)
                    if def_file:
                        language_files.append(def_file)
                        
            except Exception as e:
                error_msg = f"RimWorld提取失败 {item.get('path', 'unknown')}: {e}"
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
        """从单个RimWorld文件提取翻译数据"""
        language_files = []
        
        if file_path.is_dir():
            # 处理MOD目录
            language_files = await self._extract_from_mod_directory(file_path, carrier_info)
        elif file_path.suffix.lower() == '.xml':
            # 处理单个XML文件
            lang_file = await self._extract_single_definjection_file(file_path, carrier_info)
            if lang_file:
                language_files.append(lang_file)
        
        return language_files
    
    async def _extract_from_mod(self, mod_item: Dict[str, Any]) -> List[LanguageFile]:
        """从RimWorld MOD项目中提取语言文件"""
        mod_path = Path(mod_item["path"])
        
        if not mod_path.exists():
            logger.warning(f"RimWorld MOD路径不存在: {mod_path}")
            return []
        
        # 解析About.xml获取MOD信息
        about_info = await self._parse_about_xml(mod_path)
        
        carrier_info = {
            "mod_id": about_info.get("packageId", mod_path.name),
            "name": about_info.get("name", mod_path.name),
            "author": about_info.get("author", "Unknown"),
            "dependencies": about_info.get("dependencies", [])
        }
        
        return await self._extract_from_mod_directory(mod_path, carrier_info)
    
    async def _extract_from_mod_directory(
        self, 
        mod_path: Path, 
        carrier_info: Dict[str, Any]
    ) -> List[LanguageFile]:
        """从MOD目录中提取DefInjection文件"""
        language_files = []
        
        # 查找Languages目录
        languages_dir = mod_path / "Languages"
        if not languages_dir.exists():
            logger.debug(f"RimWorld MOD无Languages目录: {mod_path}")
            return language_files
        
        # 遍历语言目录
        for lang_dir in languages_dir.iterdir():
            if not lang_dir.is_dir():
                continue
            
            locale = lang_dir.name.lower()
            
            # 查找DefInjected目录
            definjected_dir = lang_dir / "DefInjected"
            if definjected_dir.exists():
                lang_files = await self._extract_definjected_directory(
                    definjected_dir, locale, carrier_info
                )
                language_files.extend(lang_files)
            
            # 查找Keyed目录（键值对翻译）
            keyed_dir = lang_dir / "Keyed"
            if keyed_dir.exists():
                keyed_files = await self._extract_keyed_directory(
                    keyed_dir, locale, carrier_info
                )
                language_files.extend(keyed_files)
        
        return language_files
    
    async def _extract_definjected_directory(
        self, 
        definjected_dir: Path, 
        locale: str, 
        carrier_info: Dict[str, Any]
    ) -> List[LanguageFile]:
        """提取DefInjected目录中的文件"""
        language_files = []
        
        # 遍历DefInjected的子目录（如Buildings, Items等）
        for def_category_dir in definjected_dir.iterdir():
            if not def_category_dir.is_dir():
                continue
            
            category_name = def_category_dir.name
            
            # 处理该类别下的所有XML文件
            for xml_file in def_category_dir.glob("*.xml"):
                try:
                    lang_file = await self._extract_definjection_xml(
                        xml_file, locale, category_name, carrier_info
                    )
                    if lang_file:
                        language_files.append(lang_file)
                except Exception as e:
                    logger.warning(f"DefInjection文件处理失败 {xml_file}: {e}")
        
        return language_files
    
    async def _extract_keyed_directory(
        self, 
        keyed_dir: Path, 
        locale: str, 
        carrier_info: Dict[str, Any]
    ) -> List[LanguageFile]:
        """提取Keyed目录中的键值对文件"""
        language_files = []
        
        for xml_file in keyed_dir.glob("*.xml"):
            try:
                lang_file = await self._extract_keyed_xml(
                    xml_file, locale, carrier_info
                )
                if lang_file:
                    language_files.append(lang_file)
            except Exception as e:
                logger.warning(f"Keyed文件处理失败 {xml_file}: {e}")
        
        return language_files
    
    async def _extract_definjection_xml(
        self, 
        xml_file: Path, 
        locale: str, 
        category: str, 
        carrier_info: Dict[str, Any]
    ) -> Optional[LanguageFile]:
        """提取DefInjection XML文件"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            entries = []
            
            # 解析DefInjection结构
            for language_data in root.findall('LanguageData'):
                for def_node in language_data:
                    def_name = def_node.tag
                    
                    # 处理简单文本节点
                    if def_node.text and def_node.text.strip():
                        entries.append(TranslationEntry(
                            key=f"{category}.{def_name}",
                            source_text=def_node.text.strip(),
                            namespace=carrier_info.get("mod_id", "core"),
                            context=f"DefInjection/{category}",
                            format=FileFormat.XML,
                            metadata={
                                "category": category,
                                "def_name": def_name,
                                "injection_type": "simple"
                            }
                        ))
                    
                    # 处理子节点（如label、description等）
                    for field_node in def_node:
                        if field_node.text and field_node.text.strip():
                            field_key = f"{category}.{def_name}.{field_node.tag}"
                            entries.append(TranslationEntry(
                                key=field_key,
                                source_text=field_node.text.strip(),
                                namespace=carrier_info.get("mod_id", "core"),
                                context=f"DefInjection/{category}",
                                format=FileFormat.XML,
                                metadata={
                                    "category": category,
                                    "def_name": def_name,
                                    "field": field_node.tag,
                                    "injection_type": "field"
                                }
                            ))
                        
                        # 处理列表项（如cost、ingredients等）
                        if len(field_node) > 0:
                            for i, list_item in enumerate(field_node):
                                if list_item.text and list_item.text.strip():
                                    list_key = f"{category}.{def_name}.{field_node.tag}.{i}"
                                    entries.append(TranslationEntry(
                                        key=list_key,
                                        source_text=list_item.text.strip(),
                                        namespace=carrier_info.get("mod_id", "core"),
                                        context=f"DefInjection/{category}",
                                        format=FileFormat.XML,
                                        metadata={
                                            "category": category,
                                            "def_name": def_name,
                                            "field": field_node.tag,
                                            "index": i,
                                            "injection_type": "list"
                                        }
                                    ))
            
            if not entries:
                return None
            
            relative_path = f"Languages/{locale}/DefInjected/{category}/{xml_file.name}"
            
            return LanguageFile(
                uid="",  # 自动生成
                path=str(xml_file),
                relative_path=relative_path,
                locale=locale,
                format=FileFormat.XML,
                size=xml_file.stat().st_size,
                carrier_type="mod",
                carrier_uid=carrier_info.get("mod_id", "unknown"),
                entries=entries
            )
            
        except ET.ParseError as e:
            logger.error(f"XML解析失败 {xml_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"DefInjection处理失败 {xml_file}: {e}")
            return None
    
    async def _extract_keyed_xml(
        self, 
        xml_file: Path, 
        locale: str, 
        carrier_info: Dict[str, Any]
    ) -> Optional[LanguageFile]:
        """提取Keyed XML文件（键值对翻译）"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            entries = []
            
            # 解析Keyed结构
            for language_data in root.findall('LanguageData'):
                for key_node in language_data:
                    key = key_node.tag
                    text = key_node.text
                    
                    if text and text.strip():
                        entries.append(TranslationEntry(
                            key=key,
                            source_text=text.strip(),
                            namespace=carrier_info.get("mod_id", "core"),
                            context="Keyed",
                            format=FileFormat.XML,
                            metadata={
                                "file": xml_file.stem,
                                "translation_type": "keyed"
                            }
                        ))
            
            if not entries:
                return None
            
            relative_path = f"Languages/{locale}/Keyed/{xml_file.name}"
            
            return LanguageFile(
                uid="",  # 自动生成
                path=str(xml_file),
                relative_path=relative_path,
                locale=locale,
                format=FileFormat.XML,
                size=xml_file.stat().st_size,
                carrier_type="mod",
                carrier_uid=carrier_info.get("mod_id", "unknown"),
                entries=entries
            )
            
        except ET.ParseError as e:
            logger.error(f"Keyed XML解析失败 {xml_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"Keyed处理失败 {xml_file}: {e}")
            return None
    
    async def _extract_from_definjection_file(
        self, 
        file_item: Dict[str, Any]
    ) -> Optional[LanguageFile]:
        """从DefInjection文件项目提取数据"""
        file_path = Path(file_item["path"])
        
        if not file_path.exists():
            return None
        
        carrier_info = {
            "mod_id": file_item.get("mod_id", "unknown"),
            "type": "definjection"
        }
        
        return await self._extract_single_definjection_file(file_path, carrier_info)
    
    async def _extract_single_definjection_file(
        self, 
        file_path: Path, 
        carrier_info: Dict[str, Any]
    ) -> Optional[LanguageFile]:
        """提取单个DefInjection文件"""
        try:
            # 从路径推断语言和类别
            path_parts = file_path.parts
            
            locale = "unknown"
            category = "unknown"
            
            # 查找Languages目录和语言代码
            for i, part in enumerate(path_parts):
                if part == "Languages" and i + 1 < len(path_parts):
                    locale = path_parts[i + 1].lower()
                    break
            
            # 查找DefInjected目录和类别
            for i, part in enumerate(path_parts):
                if part == "DefInjected" and i + 1 < len(path_parts):
                    category = path_parts[i + 1]
                    break
            
            if "Keyed" in str(file_path):
                # 处理Keyed文件
                return await self._extract_keyed_xml(file_path, locale, carrier_info)
            else:
                # 处理DefInjection文件
                return await self._extract_definjection_xml(
                    file_path, locale, category, carrier_info
                )
                
        except Exception as e:
            logger.error(f"单个DefInjection文件处理失败 {file_path}: {e}")
            return None
    
    async def _parse_about_xml(self, mod_path: Path) -> Dict[str, Any]:
        """解析RimWorld MOD的About.xml文件"""
        about_file = mod_path / "About" / "About.xml"
        about_info = {}
        
        if not about_file.exists():
            return about_info
        
        try:
            tree = ET.parse(about_file)
            root = tree.getroot()
            
            # 解析基本信息
            name_elem = root.find('name')
            if name_elem is not None and name_elem.text:
                about_info['name'] = name_elem.text.strip()
            
            author_elem = root.find('author')
            if author_elem is not None and author_elem.text:
                about_info['author'] = author_elem.text.strip()
            
            package_id_elem = root.find('packageId')
            if package_id_elem is not None and package_id_elem.text:
                about_info['packageId'] = package_id_elem.text.strip()
            
            # 解析依赖关系
            dependencies = []
            for dep_elem in root.findall('.//li'):
                if dep_elem.text and dep_elem.text.strip():
                    dependencies.append(dep_elem.text.strip())
            
            about_info['dependencies'] = dependencies
            
        except ET.ParseError as e:
            logger.warning(f"About.xml解析失败 {about_file}: {e}")
        except Exception as e:
            logger.warning(f"About.xml处理失败 {about_file}: {e}")
        
        return about_info
    
    async def _extract_keyset_preview(
        self, 
        item: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """快速提取RimWorld键集信息用于增量比较"""
        preview_items = []
        
        try:
            if item.get("type") == "mod":
                mod_path = Path(item["path"])
                languages_dir = mod_path / "Languages"
                
                if languages_dir.exists():
                    for lang_dir in languages_dir.iterdir():
                        if not lang_dir.is_dir():
                            continue
                        
                        locale = lang_dir.name.lower()
                        
                        # 快速扫描DefInjected文件
                        definjected_dir = lang_dir / "DefInjected"
                        if definjected_dir.exists():
                            for category_dir in definjected_dir.iterdir():
                                if category_dir.is_dir():
                                    for xml_file in category_dir.glob("*.xml"):
                                        keys = await self._quick_extract_xml_keys(xml_file)
                                        if keys:
                                            keyset_hash = self._calculate_keyset_hash(keys)
                                            
                                            relative_path = f"Languages/{locale}/DefInjected/{category_dir.name}/{xml_file.name}"
                                            preview_items.append({
                                                "carrier_uid": item.get("mod_id", mod_path.name),
                                                "relative_path": relative_path,
                                                "keyset_hash": keyset_hash,
                                                "path": str(xml_file),
                                                "carrier_info": {"mod_id": item.get("mod_id"), "type": "mod"}
                                            })
        
        except Exception as e:
            logger.warning(f"RimWorld键集预览失败: {e}")
        
        return preview_items
    
    async def _quick_extract_xml_keys(self, xml_file: Path) -> List[str]:
        """快速提取XML文件的键名（用于键集比较）"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            keys = []
            
            for language_data in root.findall('LanguageData'):
                for def_node in language_data:
                    def_name = def_node.tag
                    
                    if def_node.text and def_node.text.strip():
                        keys.append(def_name)
                    
                    for field_node in def_node:
                        field_key = f"{def_name}.{field_node.tag}"
                        keys.append(field_key)
            
            return sorted(keys)
            
        except Exception:
            return []
    
    def _calculate_keyset_hash(self, keys: List[str]) -> str:
        """计算键集哈希"""
        import hashlib
        key_string = '|'.join(keys)
        return hashlib.blake3(key_string.encode('utf-8')).hexdigest()[:16]