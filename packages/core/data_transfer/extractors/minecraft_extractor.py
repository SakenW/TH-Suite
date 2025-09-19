"""
Minecraft翻译数据提取器

专门处理Minecraft MOD和资源包的翻译数据提取
"""

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import structlog
import toml

from ..models import (
    GameType,
    MinecraftModInfo,
    ModLoader,
    TranslationEntry,
    TranslationProject,
    TranslationStatus,
    generate_entry_id,
    generate_project_id,
)
from .interfaces import BaseTranslationExtractor

logger = structlog.get_logger(__name__)


class MinecraftFileScanner:
    """Minecraft文件扫描器"""
    
    def __init__(self):
        self.language_file_patterns = [
            r'assets/[^/]+/lang/[^/]+\.json$',  # 1.13+ JSON格式
            r'assets/[^/]+/lang/[^/]+\.lang$',  # 1.12- Properties格式
        ]
        
        self.mod_metadata_files = [
            'mods.toml',              # Forge
            'fabric.mod.json',        # Fabric
            'quilt.mod.json',         # Quilt
            'mcmod.info',             # 旧版Forge
            'META-INF/mods.toml',     # Forge (在JAR中)
            'META-INF/MANIFEST.MF',   # 通用清单
        ]
    
    async def scan_directory(
        self, 
        root_path: Path,
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None
    ) -> List[Path]:
        """扫描Minecraft项目目录"""
        
        files = []
        
        try:
            for item in root_path.rglob('*'):
                if item.is_file():
                    # 检查是否匹配包含模式
                    if includes and not any(pattern in str(item) for pattern in includes):
                        continue
                    
                    # 检查是否匹配排除模式
                    if excludes and any(pattern in str(item) for pattern in excludes):
                        continue
                    
                    # 检查是否是相关文件
                    if self._is_relevant_file(item):
                        files.append(item)
        
        except Exception as e:
            logger.error("Failed to scan directory", path=str(root_path), error=str(e))
        
        return files
    
    async def find_language_files(self, mod_path: Path) -> List[Path]:
        """查找MOD中的语言文件"""
        
        lang_files = []
        
        try:
            if mod_path.suffix.lower() == '.jar':
                # 处理JAR文件
                lang_files.extend(await self._scan_jar_language_files(mod_path))
            else:
                # 处理目录
                lang_files.extend(await self._scan_directory_language_files(mod_path))
        
        except Exception as e:
            logger.error("Failed to find language files", mod_path=str(mod_path), error=str(e))
        
        return lang_files
    
    async def find_mod_metadata(self, mod_path: Path) -> Optional[Path]:
        """查找MOD元数据文件"""
        
        try:
            if mod_path.suffix.lower() == '.jar':
                return await self._find_jar_metadata(mod_path)
            else:
                return await self._find_directory_metadata(mod_path)
        
        except Exception as e:
            logger.error("Failed to find mod metadata", mod_path=str(mod_path), error=str(e))
            return None
    
    def _is_relevant_file(self, file_path: Path) -> bool:
        """检查文件是否相关"""
        
        # 语言文件
        if any(re.search(pattern, str(file_path)) for pattern in self.language_file_patterns):
            return True
        
        # MOD元数据文件
        if file_path.name in self.mod_metadata_files:
            return True
        
        # JAR文件
        if file_path.suffix.lower() == '.jar':
            return True
        
        return False
    
    async def _scan_jar_language_files(self, jar_path: Path) -> List[Path]:
        """扫描JAR文件中的语言文件"""
        
        lang_files = []
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as zf:
                for file_info in zf.filelist:
                    if any(re.search(pattern, file_info.filename) for pattern in self.language_file_patterns):
                        # 创建虚拟路径表示JAR中的文件
                        virtual_path = jar_path / file_info.filename
                        lang_files.append(virtual_path)
        
        except Exception as e:
            logger.warning("Failed to scan JAR file", jar_path=str(jar_path), error=str(e))
        
        return lang_files
    
    async def _scan_directory_language_files(self, dir_path: Path) -> List[Path]:
        """扫描目录中的语言文件"""
        
        lang_files = []
        
        try:
            for pattern in self.language_file_patterns:
                # 将正则表达式转换为glob模式（简化版）
                glob_pattern = pattern.replace(r'[^/]+', '*').replace('$', '')
                
                for file_path in dir_path.glob(glob_pattern):
                    if file_path.is_file():
                        lang_files.append(file_path)
        
        except Exception as e:
            logger.warning("Failed to scan directory", dir_path=str(dir_path), error=str(e))
        
        return lang_files
    
    async def _find_jar_metadata(self, jar_path: Path) -> Optional[Path]:
        """查找JAR文件中的元数据"""
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as zf:
                for metadata_file in self.mod_metadata_files:
                    if metadata_file in zf.namelist():
                        # 返回虚拟路径
                        return jar_path / metadata_file
        
        except Exception as e:
            logger.warning("Failed to scan JAR metadata", jar_path=str(jar_path), error=str(e))
        
        return None
    
    async def _find_directory_metadata(self, dir_path: Path) -> Optional[Path]:
        """查找目录中的元数据"""
        
        for metadata_file in self.mod_metadata_files:
            metadata_path = dir_path / metadata_file
            if metadata_path.exists():
                return metadata_path
        
        return None


class MinecraftModParser:
    """Minecraft MOD解析器"""
    
    async def parse_language_file(self, file_path: Path) -> Dict[str, str]:
        """解析语言文件"""
        
        try:
            if file_path.suffix == '.json':
                return await self._parse_json_lang_file(file_path)
            elif file_path.suffix == '.lang':
                return await self._parse_properties_lang_file(file_path)
            else:
                logger.warning("Unsupported language file format", file_path=str(file_path))
                return {}
        
        except Exception as e:
            logger.error("Failed to parse language file", file_path=str(file_path), error=str(e))
            return {}
    
    async def extract_mod_info(self, mod_path: Path, metadata_path: Optional[Path] = None) -> MinecraftModInfo:
        """提取MOD信息"""
        
        try:
            if metadata_path:
                return await self._parse_mod_metadata(metadata_path)
            else:
                # 尝试从路径推断MOD信息
                return await self._infer_mod_info(mod_path)
        
        except Exception as e:
            logger.error("Failed to extract mod info", mod_path=str(mod_path), error=str(e))
            return await self._create_default_mod_info(mod_path)
    
    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        return ['.json', '.lang']
    
    def detect_language_code(self, file_path: Path) -> str:
        """检测语言代码"""
        
        # 从文件名提取语言代码
        stem = file_path.stem
        
        # 常见的语言代码模式
        if stem in ['en_us', 'zh_cn', 'zh_tw', 'ja_jp', 'ko_kr']:
            return stem
        
        # 默认返回英文
        return 'en_us'
    
    async def _parse_json_lang_file(self, file_path: Path) -> Dict[str, str]:
        """解析JSON格式语言文件"""
        
        try:
            content = await self._read_file_content(file_path)
            if not content:
                return {}
            
            data = json.loads(content)
            
            # 确保所有值都是字符串
            return {k: str(v) for k, v in data.items() if isinstance(k, str)}
        
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in language file", file_path=str(file_path), error=str(e))
            return {}
    
    async def _parse_properties_lang_file(self, file_path: Path) -> Dict[str, str]:
        """解析Properties格式语言文件"""
        
        try:
            content = await self._read_file_content(file_path)
            if not content:
                return {}
            
            data = {}
            
            for line in content.splitlines():
                line = line.strip()
                
                # 跳过注释和空行
                if not line or line.startswith('#'):
                    continue
                
                # 解析键值对
                if '=' in line:
                    key, value = line.split('=', 1)
                    data[key.strip()] = value.strip()
            
            return data
        
        except Exception as e:
            logger.error("Failed to parse properties file", file_path=str(file_path), error=str(e))
            return {}
    
    async def _parse_mod_metadata(self, metadata_path: Path) -> MinecraftModInfo:
        """解析MOD元数据"""
        
        try:
            filename = metadata_path.name
            
            if filename == 'mods.toml':
                return await self._parse_forge_metadata(metadata_path)
            elif filename in ['fabric.mod.json', 'quilt.mod.json']:
                return await self._parse_fabric_metadata(metadata_path)
            elif filename == 'mcmod.info':
                return await self._parse_legacy_forge_metadata(metadata_path)
            else:
                return await self._create_default_mod_info(metadata_path.parent)
        
        except Exception as e:
            logger.error("Failed to parse metadata", metadata_path=str(metadata_path), error=str(e))
            return await self._create_default_mod_info(metadata_path.parent)
    
    async def _parse_forge_metadata(self, metadata_path: Path) -> MinecraftModInfo:
        """解析Forge mods.toml文件"""
        
        try:
            content = await self._read_file_content(metadata_path)
            if not content:
                return await self._create_default_mod_info(metadata_path.parent)
            
            data = toml.loads(content)
            
            # 获取第一个MOD的信息
            mods = data.get('mods', [])
            if not mods:
                return await self._create_default_mod_info(metadata_path.parent)
            
            mod_data = mods[0]
            
            return MinecraftModInfo(
                mod_id=mod_data.get('modId', 'unknown'),
                name=mod_data.get('displayName', 'Unknown Mod'),
                version=mod_data.get('version', '1.0.0'),
                description=mod_data.get('description', ''),
                author=mod_data.get('authors', ''),
                loader_type=ModLoader.FORGE,
                mc_version=data.get('loaderVersion', ''),
                dependencies=self._extract_dependencies(data.get('dependencies', {}))
            )
        
        except Exception as e:
            logger.error("Failed to parse Forge metadata", error=str(e))
            return await self._create_default_mod_info(metadata_path.parent)
    
    async def _parse_fabric_metadata(self, metadata_path: Path) -> MinecraftModInfo:
        """解析Fabric/Quilt mod.json文件"""
        
        try:
            content = await self._read_file_content(metadata_path)
            if not content:
                return await self._create_default_mod_info(metadata_path.parent)
            
            data = json.loads(content)
            
            # 检测加载器类型
            loader_type = ModLoader.FABRIC
            if 'quilt_loader' in data:
                loader_type = ModLoader.QUILT
            
            return MinecraftModInfo(
                mod_id=data.get('id', 'unknown'),
                name=data.get('name', 'Unknown Mod'),
                version=data.get('version', '1.0.0'),
                description=data.get('description', ''),
                author=self._format_authors(data.get('authors', [])),
                loader_type=loader_type,
                mc_version=self._extract_mc_version(data.get('depends', {})),
                dependencies=list(data.get('depends', {}).keys())
            )
        
        except Exception as e:
            logger.error("Failed to parse Fabric metadata", error=str(e))
            return await self._create_default_mod_info(metadata_path.parent)
    
    async def _parse_legacy_forge_metadata(self, metadata_path: Path) -> MinecraftModInfo:
        """解析旧版Forge mcmod.info文件"""
        
        try:
            content = await self._read_file_content(metadata_path)
            if not content:
                return await self._create_default_mod_info(metadata_path.parent)
            
            data = json.loads(content)
            
            # mcmod.info是一个数组
            if isinstance(data, list) and data:
                mod_data = data[0]
            else:
                mod_data = data
            
            return MinecraftModInfo(
                mod_id=mod_data.get('modid', 'unknown'),
                name=mod_data.get('name', 'Unknown Mod'),
                version=mod_data.get('version', '1.0.0'),
                description=mod_data.get('description', ''),
                author=self._format_authors(mod_data.get('authorList', [])),
                loader_type=ModLoader.FORGE,
                mc_version=mod_data.get('mcversion', ''),
                dependencies=mod_data.get('requiredMods', [])
            )
        
        except Exception as e:
            logger.error("Failed to parse legacy Forge metadata", error=str(e))
            return await self._create_default_mod_info(metadata_path.parent)
    
    async def _infer_mod_info(self, mod_path: Path) -> MinecraftModInfo:
        """从路径推断MOD信息"""
        
        mod_name = mod_path.name
        
        # 移除文件扩展名
        if mod_path.is_file():
            mod_name = mod_path.stem
        
        # 尝试从文件名提取版本信息
        version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', mod_name)
        version = version_match.group(1) if version_match else '1.0.0'
        
        # 清理MOD名称
        clean_name = re.sub(r'[-_]\d+\.\d+.*', '', mod_name)
        clean_name = clean_name.replace('_', ' ').replace('-', ' ').title()
        
        return MinecraftModInfo(
            mod_id=mod_name.lower().replace(' ', '_'),
            name=clean_name,
            version=version,
            description=f"Inferred from path: {mod_path}",
            loader_type=ModLoader.UNKNOWN
        )
    
    async def _create_default_mod_info(self, mod_path: Path) -> MinecraftModInfo:
        """创建默认MOD信息"""
        
        return MinecraftModInfo(
            mod_id='unknown',
            name=mod_path.name,
            version='1.0.0',
            description='Unknown mod',
            loader_type=ModLoader.UNKNOWN
        )
    
    async def _read_file_content(self, file_path: Path) -> str:
        """读取文件内容（支持JAR中的文件）"""
        
        # 检查是否是JAR中的虚拟路径
        if len(file_path.parts) > 1 and file_path.parts[0].endswith('.jar'):
            jar_path = Path(file_path.parts[0])
            internal_path = '/'.join(file_path.parts[1:])
            
            try:
                with zipfile.ZipFile(jar_path, 'r') as zf:
                    with zf.open(internal_path) as f:
                        content = f.read()
                        # 尝试解码
                        for encoding in ['utf-8', 'latin-1', 'cp1252']:
                            try:
                                return content.decode(encoding)
                            except UnicodeDecodeError:
                                continue
                        return content.decode('utf-8', errors='ignore')
            except Exception:
                return ""
        else:
            # 普通文件
            try:
                return file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    return file_path.read_text(encoding='latin-1')
                except Exception:
                    return ""
            except Exception:
                return ""
    
    def _extract_dependencies(self, deps_data: Dict) -> List[str]:
        """提取依赖列表"""
        
        dependencies = []
        
        for mod_id, dep_info in deps_data.items():
            if mod_id not in ['minecraft', 'forge', 'fabric', 'quilt']:
                dependencies.append(mod_id)
        
        return dependencies
    
    def _extract_mc_version(self, deps_data: Dict) -> str:
        """提取Minecraft版本"""
        
        mc_dep = deps_data.get('minecraft')
        if isinstance(mc_dep, str):
            return mc_dep
        elif isinstance(mc_dep, dict):
            return mc_dep.get('version', '')
        
        return ''
    
    def _format_authors(self, authors) -> str:
        """格式化作者信息"""
        
        if isinstance(authors, list):
            return ', '.join(str(author) for author in authors)
        elif isinstance(authors, str):
            return authors
        else:
            return ''


class MinecraftTranslationExtractor(BaseTranslationExtractor):
    """Minecraft翻译数据提取器"""
    
    def __init__(self):
        super().__init__(GameType.MINECRAFT)
        self.scanner = MinecraftFileScanner()
        self.parser = MinecraftModParser()
    
    async def extract_project(self, project_path: str) -> TranslationProject:
        """提取Minecraft项目信息"""
        
        path = Path(project_path)
        
        # 扫描MOD文件
        mod_files = await self._scan_mods(path)
        
        # 统计翻译条目（快速估算）
        total_entries = await self._estimate_translation_entries(mod_files)
        
        return TranslationProject(
            project_id=generate_project_id(path.name, GameType.MINECRAFT),
            name=path.name,
            game_type=GameType.MINECRAFT,
            source_language="en_us",
            target_languages=["zh_cn"],
            root_path=str(path),
            total_entries=total_entries,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    async def extract_entries(
        self, 
        project: TranslationProject,
        incremental: bool = True,
        target_languages: Optional[List[str]] = None
    ) -> List[TranslationEntry]:
        """提取Minecraft翻译条目"""
        
        if target_languages is None:
            target_languages = project.target_languages
        
        entries = []
        root_path = Path(project.root_path)
        
        # 扫描所有MOD
        mod_files = await self._scan_mods(root_path)
        
        for mod_file in mod_files:
            try:
                # 提取MOD信息
                metadata_path = await self.scanner.find_mod_metadata(mod_file)
                mod_info = await self.parser.extract_mod_info(mod_file, metadata_path)
                
                # 查找语言文件
                lang_files = await self.scanner.find_language_files(mod_file)
                
                # 处理每个语言文件
                for lang_file in lang_files:
                    lang_entries = await self._extract_language_file(
                        lang_file, mod_info, target_languages
                    )
                    entries.extend(lang_entries)
            
            except Exception as e:
                logger.error("Failed to process mod", mod_file=str(mod_file), error=str(e))
                continue
        
        logger.info(
            "Extraction completed",
            project_id=project.project_id,
            total_entries=len(entries),
            total_mods=len(mod_files)
        )
        
        return entries
    
    async def _scan_mods(self, root_path: Path) -> List[Path]:
        """扫描目录中的MOD文件"""
        
        mods = []
        
        try:
            # 查找JAR文件
            for jar_file in root_path.glob('**/*.jar'):
                if jar_file.is_file():
                    mods.append(jar_file)
            
            # 查找MOD目录（包含mods.toml等元数据文件的目录）
            for item in root_path.rglob('*'):
                if item.is_dir():
                    metadata_path = await self.scanner.find_mod_metadata(item)
                    if metadata_path:
                        mods.append(item)
        
        except Exception as e:
            logger.error("Failed to scan mods", root_path=str(root_path), error=str(e))
        
        return mods
    
    async def _estimate_translation_entries(self, mod_files: List[Path]) -> int:
        """估算翻译条目总数"""
        
        total = 0
        
        for mod_file in mod_files[:10]:  # 只采样前10个MOD
            try:
                lang_files = await self.scanner.find_language_files(mod_file)
                for lang_file in lang_files:
                    lang_data = await self.parser.parse_language_file(lang_file)
                    total += len(lang_data)
            except Exception:
                continue
        
        # 根据采样结果估算
        if len(mod_files) > 10:
            total = total * len(mod_files) // min(10, len(mod_files))
        
        return total
    
    async def _extract_language_file(
        self, 
        lang_file: Path,
        mod_info: MinecraftModInfo,
        target_languages: List[str]
    ) -> List[TranslationEntry]:
        """提取单个语言文件的翻译条目"""
        
        entries = []
        
        try:
            # 解析语言文件
            lang_data = await self.parser.parse_language_file(lang_file)
            if not lang_data:
                return entries
            
            # 检测语言代码
            language = self.parser.detect_language_code(lang_file)
            
            # 只处理目标语言
            if language not in target_languages and language != 'en_us':
                return entries
            
            # 转换为翻译条目
            for key, value in lang_data.items():
                entry = TranslationEntry(
                    entry_id=generate_entry_id(mod_info.mod_id, key, language),
                    namespace=mod_info.mod_id,
                    key=key,
                    source_text=value if language == "en_us" else "",
                    target_text=value if language != "en_us" else None,
                    target_language=language,
                    game_type=GameType.MINECRAFT,
                    mod_info=mod_info,
                    file_path=str(lang_file),
                    category=self._categorize_key(key),
                    version=1,
                    last_modified=self._get_file_mtime(lang_file),
                    status=TranslationStatus.TRANSLATED if language != "en_us" else TranslationStatus.SOURCE
                )
                entries.append(entry)
        
        except Exception as e:
            logger.error(
                "Failed to extract language file",
                lang_file=str(lang_file),
                mod_id=mod_info.mod_id,
                error=str(e)
            )
        
        return entries
    
    def _get_file_mtime(self, file_path: Path) -> datetime:
        """获取文件修改时间"""
        
        try:
            # 如果是JAR中的虚拟路径，使用JAR文件的修改时间
            if len(file_path.parts) > 1 and file_path.parts[0].endswith('.jar'):
                jar_path = Path(file_path.parts[0])
                return datetime.fromtimestamp(jar_path.stat().st_mtime)
            else:
                return datetime.fromtimestamp(file_path.stat().st_mtime)
        except Exception:
            return datetime.now()