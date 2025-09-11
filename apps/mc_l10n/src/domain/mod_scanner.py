"""
Minecraft MOD扫描器 - Core-First架构
负责扫描和识别Minecraft MOD、资源包和数据包
"""

import asyncio
import json
import zipfile
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, AsyncIterator
import structlog

from .mod_loaders import (
    ModLoaderRegistry, 
    ModLoaderInfo, 
    ModMetadata, 
    ModLoaderType,
    get_mod_loader_registry
)

logger = structlog.get_logger(__name__)


class ScanType(Enum):
    """扫描类型枚举"""
    MODPACK = "modpack"
    SINGLE_MOD = "single_mod"
    RESOURCE_PACK = "resource_pack"
    DATA_PACK = "data_pack"
    MIXED_DIRECTORY = "mixed_directory"


# 使用新的 ModLoaderType 替代原有的 LoaderType
# 为了兼容性保留别名
LoaderType = ModLoaderType


@dataclass
class ModInfo:
    """MOD信息数据类 - 增强版本"""
    mod_id: str
    name: str
    version: str
    loader_type: ModLoaderType
    minecraft_version: Optional[str] = None
    authors: List[str] = None
    description: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    dependencies: List[str] = None
    # 新增字段
    loader_info: Optional[ModLoaderInfo] = None
    metadata: Optional[ModMetadata] = None
    homepage: Optional[str] = None
    license: Optional[str] = None
    supported_sides: Optional[set] = None
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.dependencies is None:
            self.dependencies = []
        if self.supported_sides is None:
            self.supported_sides = {"client", "server"}
    
    @classmethod
    def from_metadata(cls, metadata: ModMetadata, file_path: str, file_size: int) -> 'ModInfo':
        """从元数据创建 ModInfo"""
        return cls(
            mod_id=metadata.mod_id,
            name=metadata.name,
            version=metadata.version,
            loader_type=metadata.loader_info.loader_type if metadata.loader_info else ModLoaderType.UNKNOWN,
            minecraft_version=metadata.loader_info.minecraft_version if metadata.loader_info else None,
            authors=metadata.authors,
            description=metadata.description,
            file_path=file_path,
            file_size=file_size,
            dependencies=[dep.mod_id for dep in metadata.dependencies],
            loader_info=metadata.loader_info,
            metadata=metadata,
            homepage=metadata.homepage,
            license=metadata.license,
            supported_sides=metadata.supported_sides
        )


@dataclass
class LanguageFileInfo:
    """语言文件信息"""
    file_path: str
    locale: str
    format: str  # json, lang, properties
    entries_count: int
    file_size: int


@dataclass
class ScanProgress:
    """扫描进度信息"""
    current_file: str
    processed_files: int
    total_files: int
    current_phase: str
    progress_percentage: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScanResult:
    """扫描结果"""
    scan_id: str
    scan_type: ScanType
    target_path: str
    mods_found: List[ModInfo]
    language_files: List[LanguageFileInfo]
    scan_statistics: Dict[str, Any]
    is_success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'scan_id': self.scan_id,
            'scan_type': self.scan_type.value,
            'target_path': self.target_path,
            'mods_found': [asdict(mod) for mod in self.mods_found],
            'language_files': [asdict(lf) for lf in self.language_files],
            'scan_statistics': self.scan_statistics,
            'is_success': self.is_success,
            'error_message': self.error_message
        }


class MinecraftModScanner:
    """Minecraft MOD扫描器 - Core-First架构实现，集成多MOD加载器支持"""
    
    def __init__(self, mod_loader_registry: Optional[ModLoaderRegistry] = None):
        self.supported_extensions = ['.jar', '.zip']
        self.language_file_patterns = [
            'assets/*/lang/*.json',
            'assets/*/lang/*.lang',
            'data/*/lang/*.json'
        ]
        self.active_scans: Dict[str, ScanResult] = {}
        
        # 集成 MOD 加载器注册表
        self.mod_loader_registry = mod_loader_registry or get_mod_loader_registry()
        
        logger.info("Minecraft MOD扫描器已初始化", 
                   supported_loaders=[lt.value for lt in self.mod_loader_registry.get_supported_loaders()])
    
    async def scan_async(
        self,
        target_path: str,
        scan_type: Optional[ScanType] = None,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None
    ) -> ScanResult:
        """异步扫描目标路径
        
        Args:
            target_path: 扫描目标路径
            scan_type: 扫描类型，如果不指定则自动检测
            progress_callback: 进度回调函数
            
        Returns:
            ScanResult: 扫描结果
        """
        import uuid
        scan_id = str(uuid.uuid4())[:16]
        
        logger.info("开始MOD扫描", 
                   scan_id=scan_id, 
                   target_path=target_path,
                   scan_type=scan_type)
        
        try:
            # 验证目标路径
            path = Path(target_path)
            if not path.exists():
                raise FileNotFoundError(f"扫描目标不存在: {target_path}")
            
            # 自动检测扫描类型
            if scan_type is None:
                scan_type = await self._detect_scan_type(path)
                
            logger.debug("检测到扫描类型", scan_type=scan_type.value)
            
            # 执行扫描
            scan_result = ScanResult(
                scan_id=scan_id,
                scan_type=scan_type,
                target_path=target_path,
                mods_found=[],
                language_files=[],
                scan_statistics={},
                is_success=False
            )
            
            # 保存到活动扫描列表
            self.active_scans[scan_id] = scan_result
            
            # 根据扫描类型执行不同的扫描策略
            if scan_type == ScanType.MODPACK:
                await self._scan_modpack(path, scan_result, progress_callback)
            elif scan_type == ScanType.SINGLE_MOD:
                await self._scan_single_mod(path, scan_result, progress_callback)
            elif scan_type == ScanType.RESOURCE_PACK:
                await self._scan_resource_pack(path, scan_result, progress_callback)
            elif scan_type == ScanType.DATA_PACK:
                await self._scan_data_pack(path, scan_result, progress_callback)
            else:
                await self._scan_mixed_directory(path, scan_result, progress_callback)
            
            # 生成统计信息
            scan_result.scan_statistics = self._generate_statistics(scan_result)
            scan_result.is_success = True
            
            logger.info("MOD扫描完成", 
                       scan_id=scan_id,
                       mods_count=len(scan_result.mods_found),
                       language_files_count=len(scan_result.language_files))
            
            return scan_result
            
        except Exception as e:
            logger.error("MOD扫描失败", scan_id=scan_id, error=str(e))
            scan_result = ScanResult(
                scan_id=scan_id,
                scan_type=scan_type or ScanType.MIXED_DIRECTORY,
                target_path=target_path,
                mods_found=[],
                language_files=[],
                scan_statistics={},
                is_success=False,
                error_message=str(e)
            )
            self.active_scans[scan_id] = scan_result
            return scan_result
    
    async def _detect_scan_type(self, path: Path) -> ScanType:
        """自动检测扫描类型"""
        if path.is_file():
            if path.suffix in self.supported_extensions:
                # 检查是否为MOD还是资源包
                if await self._is_resource_pack(path):
                    return ScanType.RESOURCE_PACK
                else:
                    return ScanType.SINGLE_MOD
            else:
                raise ValueError(f"不支持的文件类型: {path.suffix}")
        
        elif path.is_dir():
            # 检查目录特征
            if (path / "mods").exists():
                return ScanType.MODPACK
            elif (path / "pack.mcmeta").exists():
                return ScanType.RESOURCE_PACK
            elif (path / "data").exists() and not (path / "assets").exists():
                return ScanType.DATA_PACK
            else:
                return ScanType.MIXED_DIRECTORY
        
        else:
            raise ValueError(f"无效的扫描目标: {path}")
    
    async def _is_resource_pack(self, jar_path: Path) -> bool:
        """判断JAR文件是否为资源包"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as zf:
                # 资源包通常包含 pack.mcmeta 而不包含 META-INF/mods.toml 等
                has_pack_mcmeta = "pack.mcmeta" in zf.namelist()
                has_mod_files = any(
                    name in zf.namelist() 
                    for name in ["META-INF/mods.toml", "fabric.mod.json", "quilt.mod.json"]
                )
                return has_pack_mcmeta and not has_mod_files
        except:
            return False
    
    async def _scan_modpack(
        self, 
        modpack_path: Path, 
        scan_result: ScanResult,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None
    ):
        """扫描整合包"""
        logger.debug("开始扫描整合包", path=str(modpack_path))
        
        # 查找mods目录
        mods_dir = modpack_path / "mods"
        if not mods_dir.exists():
            logger.warning("整合包中未找到mods目录")
            return
        
        # 收集所有MOD文件
        mod_files = []
        for ext in self.supported_extensions:
            mod_files.extend(mods_dir.glob(f"**/*{ext}"))
        
        logger.debug("发现MOD文件", count=len(mod_files))
        
        # 扫描每个MOD文件
        for i, mod_file in enumerate(mod_files):
            if progress_callback:
                progress = ScanProgress(
                    current_file=mod_file.name,
                    processed_files=i,
                    total_files=len(mod_files),
                    current_phase="扫描MOD文件",
                    progress_percentage=(i / len(mod_files)) * 100 if mod_files else 0
                )
                progress_callback(progress)
            
            try:
                mod_info = await self._extract_mod_info(mod_file)
                if mod_info:
                    scan_result.mods_found.append(mod_info)
                
                # 提取语言文件信息
                language_files = await self._extract_language_files_info(mod_file)
                scan_result.language_files.extend(language_files)
                
            except Exception as e:
                logger.warning("扫描MOD文件失败", 
                             mod_file=str(mod_file), 
                             error=str(e))
                continue
            
            # 允许异步中断
            await asyncio.sleep(0.001)
    
    async def _scan_single_mod(
        self, 
        mod_path: Path, 
        scan_result: ScanResult,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None
    ):
        """扫描单个MOD"""
        logger.debug("开始扫描单个MOD", path=str(mod_path))
        
        if progress_callback:
            progress = ScanProgress(
                current_file=mod_path.name,
                processed_files=0,
                total_files=1,
                current_phase="扫描MOD信息",
                progress_percentage=0
            )
            progress_callback(progress)
        
        try:
            mod_info = await self._extract_mod_info(mod_path)
            if mod_info:
                scan_result.mods_found.append(mod_info)
            
            if progress_callback:
                progress.current_phase = "提取语言文件"
                progress.progress_percentage = 50
                progress_callback(progress)
            
            # 提取语言文件信息
            language_files = await self._extract_language_files_info(mod_path)
            scan_result.language_files.extend(language_files)
            
            if progress_callback:
                progress.current_phase = "完成"
                progress.progress_percentage = 100
                progress.processed_files = 1
                progress_callback(progress)
                
        except Exception as e:
            logger.error("扫描单个MOD失败", 
                        mod_path=str(mod_path), 
                        error=str(e))
            raise
    
    async def _scan_resource_pack(
        self, 
        pack_path: Path, 
        scan_result: ScanResult,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None
    ):
        """扫描资源包"""
        logger.debug("开始扫描资源包", path=str(pack_path))
        
        if progress_callback:
            progress = ScanProgress(
                current_file=pack_path.name,
                processed_files=0,
                total_files=1,
                current_phase="扫描资源包",
                progress_percentage=0
            )
            progress_callback(progress)
        
        try:
            # 资源包信息提取（简化版MOD信息）
            pack_info = await self._extract_resource_pack_info(pack_path)
            if pack_info:
                scan_result.mods_found.append(pack_info)
            
            # 提取语言文件信息
            language_files = await self._extract_language_files_info(pack_path)
            scan_result.language_files.extend(language_files)
            
            if progress_callback:
                progress.progress_percentage = 100
                progress.processed_files = 1
                progress.current_phase = "完成"
                progress_callback(progress)
                
        except Exception as e:
            logger.error("扫描资源包失败", 
                        pack_path=str(pack_path), 
                        error=str(e))
            raise
    
    async def _scan_data_pack(
        self, 
        pack_path: Path, 
        scan_result: ScanResult,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None
    ):
        """扫描数据包"""
        logger.debug("开始扫描数据包", path=str(pack_path))
        
        # 数据包通常不包含语言文件，但可能包含一些翻译相关的数据
        # 这里实现基础的数据包信息提取
        if progress_callback:
            progress = ScanProgress(
                current_file=pack_path.name,
                processed_files=0,
                total_files=1,
                current_phase="扫描数据包",
                progress_percentage=0
            )
            progress_callback(progress)
        
        try:
            # 提取数据包基础信息
            pack_info = await self._extract_data_pack_info(pack_path)
            if pack_info:
                scan_result.mods_found.append(pack_info)
            
            if progress_callback:
                progress.progress_percentage = 100
                progress.processed_files = 1
                progress.current_phase = "完成"
                progress_callback(progress)
                
        except Exception as e:
            logger.error("扫描数据包失败", 
                        pack_path=str(pack_path), 
                        error=str(e))
            raise
    
    async def _scan_mixed_directory(
        self, 
        dir_path: Path, 
        scan_result: ScanResult,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None
    ):
        """扫描混合目录（包含多种文件类型）"""
        logger.debug("开始扫描混合目录", path=str(dir_path))
        
        # 递归查找所有支持的文件
        all_files = []
        for ext in self.supported_extensions:
            all_files.extend(dir_path.glob(f"**/*{ext}"))
        
        logger.debug("发现文件", count=len(all_files))
        
        for i, file_path in enumerate(all_files):
            if progress_callback:
                progress = ScanProgress(
                    current_file=file_path.name,
                    processed_files=i,
                    total_files=len(all_files),
                    current_phase="扫描文件",
                    progress_percentage=(i / len(all_files)) * 100 if all_files else 0
                )
                progress_callback(progress)
            
            try:
                # 判断文件类型并相应处理
                if await self._is_resource_pack(file_path):
                    pack_info = await self._extract_resource_pack_info(file_path)
                    if pack_info:
                        scan_result.mods_found.append(pack_info)
                else:
                    mod_info = await self._extract_mod_info(file_path)
                    if mod_info:
                        scan_result.mods_found.append(mod_info)
                
                # 提取语言文件信息
                language_files = await self._extract_language_files_info(file_path)
                scan_result.language_files.extend(language_files)
                
            except Exception as e:
                logger.warning("处理文件失败", 
                             file_path=str(file_path), 
                             error=str(e))
                continue
            
            # 允许异步中断
            await asyncio.sleep(0.001)
    
    async def _extract_mod_info(self, jar_path: Path) -> Optional[ModInfo]:
        """从JAR文件中提取MOD信息 - 使用新的 MOD 加载器系统"""
        try:
            # 首先检测 MOD 加载器类型
            loader_info = await self.mod_loader_registry.detect_loader(jar_path)
            
            if loader_info:
                # 提取完整的元数据
                metadata = await self.mod_loader_registry.extract_metadata(jar_path, loader_info.loader_type)
                
                if metadata:
                    # 使用元数据创建 ModInfo
                    return ModInfo.from_metadata(metadata, str(jar_path), jar_path.stat().st_size)
            
            # 如果无法识别，尝试基础信息提取
            logger.debug("无法识别 MOD 加载器类型，尝试基础信息提取", jar_path=str(jar_path))
            return await self._extract_unknown_mod_info(jar_path)
                    
        except Exception as e:
            logger.warning("提取MOD信息失败", 
                          jar_path=str(jar_path), 
                          error=str(e))
            return None
    
    async def _extract_fabric_info(self, zf: zipfile.ZipFile, jar_path: Path) -> ModInfo:
        """提取Fabric MOD信息"""
        with zf.open("fabric.mod.json") as f:
            data = json.load(f)
        
        authors = data.get("authors", [])
        if isinstance(authors, list):
            authors = [
                author if isinstance(author, str) else author.get("name", "")
                for author in authors
            ]
        
        # 提取Minecraft版本
        depends = data.get("depends", {})
        minecraft_version = depends.get("minecraft", "")
        if minecraft_version:
            # 清理版本字符串
            minecraft_version = minecraft_version.replace(">=", "").replace("~", "").replace("^", "")
        
        return ModInfo(
            mod_id=data.get("id", jar_path.stem),
            name=data.get("name", jar_path.stem),
            version=data.get("version", "unknown"),
            loader_type=LoaderType.FABRIC,
            minecraft_version=minecraft_version or None,
            authors=authors,
            description=data.get("description", ""),
            file_path=str(jar_path),
            file_size=jar_path.stat().st_size
        )
    
    async def _extract_quilt_info(self, zf: zipfile.ZipFile, jar_path: Path) -> ModInfo:
        """提取Quilt MOD信息"""
        with zf.open("quilt.mod.json") as f:
            data = json.load(f)
        
        quilt_loader = data.get("quilt_loader", {})
        metadata = quilt_loader.get("metadata", {})
        
        return ModInfo(
            mod_id=quilt_loader.get("id", jar_path.stem),
            name=metadata.get("name", jar_path.stem),
            version=quilt_loader.get("version", "unknown"),
            loader_type=LoaderType.QUILT,
            authors=list(metadata.get("contributors", {}).keys()),
            description=metadata.get("description", ""),
            file_path=str(jar_path),
            file_size=jar_path.stat().st_size
        )
    
    async def _extract_forge_info(self, zf: zipfile.ZipFile, jar_path: Path) -> ModInfo:
        """提取现代Forge MOD信息"""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                logger.warning("缺少TOML解析库，无法解析mods.toml")
                return await self._extract_unknown_mod_info(jar_path)
        
        with zf.open("META-INF/mods.toml") as f:
            content = f.read().decode("utf-8")
            data = tomllib.loads(content)
        
        # 获取第一个mod的信息
        mods = data.get("mods", [{}])
        if not mods:
            return await self._extract_unknown_mod_info(jar_path)
            
        mod = mods[0]
        
        # 解析版本模板变量
        version = mod.get("version", "${file.jarVersion}")
        if "${" in version:
            version = self._resolve_version_template(version, jar_path)
        
        # 提取Minecraft版本
        minecraft_version = self._extract_forge_mc_version(data)
        
        return ModInfo(
            mod_id=mod.get("modId", jar_path.stem),
            name=mod.get("displayName", jar_path.stem),
            version=version,
            loader_type=LoaderType.FORGE,
            minecraft_version=minecraft_version,
            authors=[mod.get("authors", "")],
            description=mod.get("description", ""),
            file_path=str(jar_path),
            file_size=jar_path.stat().st_size
        )
    
    async def _extract_legacy_forge_info(self, zf: zipfile.ZipFile, jar_path: Path) -> ModInfo:
        """提取旧版Forge MOD信息"""
        with zf.open("mcmod.info") as f:
            data = json.load(f)
        
        if isinstance(data, list) and len(data) > 0:
            mod_data = data[0]
        else:
            return await self._extract_unknown_mod_info(jar_path)
        
        return ModInfo(
            mod_id=mod_data.get("modid", jar_path.stem),
            name=mod_data.get("name", jar_path.stem),
            version=mod_data.get("version", "unknown"),
            loader_type=LoaderType.FORGE,
            authors=[mod_data.get("authorList", [])],
            description=mod_data.get("description", ""),
            file_path=str(jar_path),
            file_size=jar_path.stat().st_size
        )
    
    async def _extract_unknown_mod_info(self, jar_path: Path) -> ModInfo:
        """提取未知MOD的基础信息"""
        # 从文件名推测信息
        clean_name, version = self._parse_filename_intelligently(jar_path.stem)
        
        return ModInfo(
            mod_id=clean_name,
            name=clean_name,
            version=version or "unknown",
            loader_type=LoaderType.UNKNOWN,
            file_path=str(jar_path),
            file_size=jar_path.stat().st_size
        )
    
    async def _extract_resource_pack_info(self, pack_path: Path) -> Optional[ModInfo]:
        """提取资源包信息"""
        try:
            if pack_path.is_file():
                with zipfile.ZipFile(pack_path, 'r') as zf:
                    if "pack.mcmeta" in zf.namelist():
                        with zf.open("pack.mcmeta") as f:
                            data = json.load(f)
                            pack_info = data.get("pack", {})
                            
                            return ModInfo(
                                mod_id=pack_path.stem,
                                name=pack_path.stem,
                                version=str(pack_info.get("pack_format", "unknown")),
                                loader_type=LoaderType.UNKNOWN,
                                description=pack_info.get("description", ""),
                                file_path=str(pack_path),
                                file_size=pack_path.stat().st_size
                            )
            else:
                # 目录形式的资源包
                pack_mcmeta = pack_path / "pack.mcmeta"
                if pack_mcmeta.exists():
                    with open(pack_mcmeta, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        pack_info = data.get("pack", {})
                        
                        return ModInfo(
                            mod_id=pack_path.name,
                            name=pack_path.name,
                            version=str(pack_info.get("pack_format", "unknown")),
                            loader_type=LoaderType.UNKNOWN,
                            description=pack_info.get("description", ""),
                            file_path=str(pack_path)
                        )
        except Exception as e:
            logger.warning("提取资源包信息失败", 
                          pack_path=str(pack_path), 
                          error=str(e))
        
        return None
    
    async def _extract_data_pack_info(self, pack_path: Path) -> Optional[ModInfo]:
        """提取数据包信息"""
        try:
            pack_mcmeta = pack_path / "pack.mcmeta" if pack_path.is_dir() else None
            
            if pack_path.is_file():
                with zipfile.ZipFile(pack_path, 'r') as zf:
                    if "pack.mcmeta" in zf.namelist():
                        with zf.open("pack.mcmeta") as f:
                            data = json.load(f)
                            pack_info = data.get("pack", {})
                            
                            return ModInfo(
                                mod_id=pack_path.stem,
                                name=pack_path.stem,
                                version=str(pack_info.get("pack_format", "unknown")),
                                loader_type=LoaderType.UNKNOWN,
                                description=pack_info.get("description", "数据包"),
                                file_path=str(pack_path),
                                file_size=pack_path.stat().st_size
                            )
            elif pack_mcmeta and pack_mcmeta.exists():
                with open(pack_mcmeta, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    pack_info = data.get("pack", {})
                    
                    return ModInfo(
                        mod_id=pack_path.name,
                        name=pack_path.name,
                        version=str(pack_info.get("pack_format", "unknown")),
                        loader_type=LoaderType.UNKNOWN,
                        description=pack_info.get("description", "数据包"),
                        file_path=str(pack_path)
                    )
        except Exception as e:
            logger.warning("提取数据包信息失败", 
                          pack_path=str(pack_path), 
                          error=str(e))
        
        return None
    
    async def _extract_language_files_info(self, jar_path: Path) -> List[LanguageFileInfo]:
        """提取语言文件信息"""
        language_files = []
        
        try:
            if jar_path.is_file():
                with zipfile.ZipFile(jar_path, 'r') as zf:
                    for file_info in zf.filelist:
                        file_path = file_info.filename
                        
                        # 检查是否是语言文件
                        if "/lang/" in file_path and (
                            file_path.endswith(".json") or 
                            file_path.endswith(".lang") or
                            file_path.endswith(".properties")
                        ):
                            try:
                                # 提取语言代码
                                locale = self._extract_language_code(file_path)
                                if not locale:
                                    continue
                                
                                # 读取文件内容以计算条目数
                                content = zf.read(file_info).decode("utf-8", errors='ignore')
                                entries_count = self._count_language_entries(content, file_path)
                                
                                # 确定文件格式
                                file_format = Path(file_path).suffix[1:]  # 去掉点号
                                
                                language_files.append(LanguageFileInfo(
                                    file_path=file_path,
                                    locale=locale,
                                    format=file_format,
                                    entries_count=entries_count,
                                    file_size=file_info.file_size
                                ))
                                
                            except Exception as e:
                                logger.debug("处理语言文件失败", 
                                           file_path=file_path, 
                                           error=str(e))
                                continue
            
            else:
                # 目录扫描
                for lang_file in jar_path.glob("**/lang/*"):
                    if lang_file.is_file() and lang_file.suffix in ['.json', '.lang', '.properties']:
                        try:
                            locale = self._extract_language_code(str(lang_file))
                            if not locale:
                                continue
                            
                            content = lang_file.read_text(encoding='utf-8', errors='ignore')
                            entries_count = self._count_language_entries(content, str(lang_file))
                            
                            language_files.append(LanguageFileInfo(
                                file_path=str(lang_file.relative_to(jar_path)),
                                locale=locale,
                                format=lang_file.suffix[1:],
                                entries_count=entries_count,
                                file_size=lang_file.stat().st_size
                            ))
                            
                        except Exception as e:
                            logger.debug("处理语言文件失败", 
                                       file_path=str(lang_file), 
                                       error=str(e))
                            continue
                            
        except Exception as e:
            logger.warning("提取语言文件信息失败", 
                          jar_path=str(jar_path), 
                          error=str(e))
        
        return language_files
    
    def _extract_language_code(self, file_path: str) -> Optional[str]:
        """从文件路径中提取语言代码"""
        import re
        # 匹配如 "assets/mod/lang/zh_cn.json" 中的 "zh_cn"
        match = re.search(r'/lang/([^/]+)\.(json|lang|properties)$', file_path)
        return match.group(1) if match else None
    
    def _count_language_entries(self, content: str, file_path: str) -> int:
        """计算语言文件中的条目数量"""
        try:
            if file_path.endswith('.json'):
                data = json.loads(content)
                return len(data) if isinstance(data, dict) else 0
            elif file_path.endswith('.lang') or file_path.endswith('.properties'):
                lines = content.splitlines()
                entries = [
                    line for line in lines 
                    if line.strip() and '=' in line and not line.strip().startswith('#')
                ]
                return len(entries)
        except:
            pass
        
        return 0
    
    def _parse_filename_intelligently(self, filename: str) -> tuple[str, str]:
        """智能解析文件名，提取名称和版本"""
        import re
        
        # 尝试各种版本号模式
        patterns = [
            r'^(.+?)-mc(\d+\.\d+(?:\.\d+)?)-(.+)$',  # name-mc1.18.2-version
            r'^(.+?)-(\d+\.\d+(?:\.\d+)?(?:-\d+\.\d+(?:\.\d+)?)*)$',  # name-version
            r'^(.+?)_(\d+\.\d+(?:\.\d+)?)$',  # name_version
            r'^(.+?)[_-]v?(\d+\.\d+.*?)$',  # name-v1.0 or name_v1.0
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return groups[0], groups[1]
                elif len(groups) == 3:  # mc版本模式
                    return groups[0], f"{groups[1]}-{groups[2]}"
        
        # 如果没有匹配到，返回原文件名和空版本
        return filename, ""
    
    def _resolve_version_template(self, template: str, jar_path: Path) -> str:
        """解析版本模板变量"""
        if "${file.jarVersion}" in template:
            _, version = self._parse_filename_intelligently(jar_path.stem)
            return template.replace("${file.jarVersion}", version or "unknown")
        
        return template
    
    def _extract_forge_mc_version(self, toml_data: dict) -> Optional[str]:
        """从Forge mods.toml中提取Minecraft版本"""
        dependencies = toml_data.get("dependencies", {})
        minecraft = dependencies.get("minecraft", "")
        
        if isinstance(minecraft, dict) and "versionRange" in minecraft:
            version_range = minecraft["versionRange"]
        elif isinstance(minecraft, str):
            version_range = minecraft
        else:
            return None
        
        # 解析版本范围，如 "[1.20,1.21)" -> "1.20"
        if version_range and "[" in version_range:
            import re
            match = re.search(r'\[([^,\]]+)', version_range)
            return match.group(1) if match else None
        
        return version_range
    
    def _generate_statistics(self, scan_result: ScanResult) -> Dict[str, Any]:
        """生成扫描统计信息 - 增强版本"""
        loader_counts = {}
        minecraft_versions = set()
        supported_sides = {"client": 0, "server": 0, "both": 0}
        total_file_size = 0
        dependencies_count = 0
        
        for mod in scan_result.mods_found:
            loader_type = mod.loader_type.value
            loader_counts[loader_type] = loader_counts.get(loader_type, 0) + 1
            
            # 收集 Minecraft 版本
            if mod.minecraft_version:
                minecraft_versions.add(mod.minecraft_version)
            
            # 统计文件大小
            if mod.file_size:
                total_file_size += mod.file_size
            
            # 统计依赖数量
            dependencies_count += len(mod.dependencies)
            
            # 统计支持的环境
            if mod.supported_sides:
                if mod.supported_sides == {"client"}:
                    supported_sides["client"] += 1
                elif mod.supported_sides == {"server"}:
                    supported_sides["server"] += 1
                else:
                    supported_sides["both"] += 1
        
        locale_counts = {}
        total_entries = 0
        for lang_file in scan_result.language_files:
            locale_counts[lang_file.locale] = locale_counts.get(lang_file.locale, 0) + 1
            total_entries += lang_file.entries_count
        
        return {
            'total_mods': len(scan_result.mods_found),
            'total_language_files': len(scan_result.language_files),
            'total_translation_entries': total_entries,
            'total_file_size': total_file_size,
            'total_dependencies': dependencies_count,
            'loader_distribution': loader_counts,
            'locale_distribution': locale_counts,
            'minecraft_versions': sorted(list(minecraft_versions)),
            'supported_sides': supported_sides,
            'scan_type': scan_result.scan_type.value,
            'supported_loaders': [lt.value for lt in self.mod_loader_registry.get_supported_loaders()]
        }
    
    def get_scan_result(self, scan_id: str) -> Optional[ScanResult]:
        """获取扫描结果"""
        return self.active_scans.get(scan_id)
    
    def get_active_scans(self) -> List[str]:
        """获取所有活跃的扫描ID"""
        return list(self.active_scans.keys())
    
    def clear_scan_result(self, scan_id: str) -> bool:
        """清除扫描结果"""
        if scan_id in self.active_scans:
            del self.active_scans[scan_id]
            return True
        return False
    
    async def validate_mod_files(self, jar_paths: List[Path]) -> Dict[Path, bool]:
        """批量验证 MOD 文件"""
        results = {}
        for jar_path in jar_paths:
            try:
                results[jar_path] = self.mod_loader_registry.validate_mod(jar_path)
            except Exception as e:
                logger.warning("验证 MOD 文件失败", jar_path=str(jar_path), error=str(e))
                results[jar_path] = False
        return results
    
    async def detect_mod_loaders_batch(self, jar_paths: List[Path]) -> Dict[Path, Optional[ModLoaderInfo]]:
        """批量检测 MOD 加载器类型"""
        return await self.mod_loader_registry.batch_detect(jar_paths)
    
    def get_supported_loaders(self) -> List[ModLoaderType]:
        """获取支持的加载器列表"""
        return self.mod_loader_registry.get_supported_loaders()
    
    def get_loader_capabilities(self, loader_type: ModLoaderType) -> Set[str]:
        """获取加载器能力"""
        detector = self.mod_loader_registry.get_detector(loader_type)
        if detector:
            # 模拟获取能力集合
            if loader_type == ModLoaderType.FORGE:
                return {"mods", "coremods", "resources"}
            elif loader_type == ModLoaderType.FABRIC:
                return {"mods", "mixins", "resources", "data"}
            elif loader_type == ModLoaderType.QUILT:
                return {"mods", "mixins", "resources", "data", "quilt_api"}
            elif loader_type == ModLoaderType.NEOFORGE:
                return {"mods", "coremods", "resources", "data_generation"}
        return set()
    
    async def analyze_mod_dependencies(self, scan_result: ScanResult) -> Dict[str, Any]:
        """分析 MOD 依赖关系"""
        dependency_graph = {}
        dependency_conflicts = []
        missing_dependencies = set()
        
        # 构建依赖图
        for mod in scan_result.mods_found:
            if mod.metadata:
                mod_deps = [dep.mod_id for dep in mod.metadata.dependencies if dep.required]
                dependency_graph[mod.mod_id] = mod_deps
                
                # 检查缺失依赖
                for dep in mod.metadata.dependencies:
                    if dep.required:
                        dep_found = any(m.mod_id == dep.mod_id for m in scan_result.mods_found)
                        if not dep_found:
                            missing_dependencies.add(dep.mod_id)
        
        return {
            "dependency_graph": dependency_graph,
            "missing_dependencies": list(missing_dependencies),
            "dependency_conflicts": dependency_conflicts,
            "total_dependencies": sum(len(deps) for deps in dependency_graph.values())
        }


# 全局扫描器实例
_scanner_instance: Optional[MinecraftModScanner] = None


def get_scanner() -> MinecraftModScanner:
    """获取全局扫描器实例"""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = MinecraftModScanner()
    return _scanner_instance


async def scan_minecraft_content(
    target_path: str,
    scan_type: Optional[ScanType] = None,
    progress_callback: Optional[Callable[[ScanProgress], None]] = None
) -> ScanResult:
    """便捷函数：扫描Minecraft内容"""
    scanner = get_scanner()
    return await scanner.scan_async(target_path, scan_type, progress_callback)