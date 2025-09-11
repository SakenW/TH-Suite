"""
MOD 加载器支持系统
支持 Forge、Fabric、Quilt、NeoForge 等多种加载器的检测和处理
"""

import json
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Union
from enum import Enum
import structlog
import re
from packaging import version

logger = structlog.get_logger(__name__)


class ModLoaderType(Enum):
    """MOD 加载器类型"""
    FORGE = "forge"
    NEOFORGE = "neoforge" 
    FABRIC = "fabric"
    QUILT = "quilt"
    VANILLA = "vanilla"
    UNKNOWN = "unknown"


class VersionRequirement:
    """版本需求"""
    
    def __init__(self, min_version: Optional[str] = None, max_version: Optional[str] = None):
        self.min_version = version.parse(min_version) if min_version else None
        self.max_version = version.parse(max_version) if max_version else None
    
    def is_compatible(self, target_version: str) -> bool:
        """检查版本兼容性"""
        try:
            target = version.parse(target_version)
            
            if self.min_version and target < self.min_version:
                return False
            if self.max_version and target > self.max_version:
                return False
            return True
        except Exception:
            return False


@dataclass
class ModLoaderInfo:
    """MOD 加载器信息"""
    loader_type: ModLoaderType
    version: str
    minecraft_version: str
    loader_name: str = ""
    api_version: Optional[str] = None
    capabilities: Set[str] = None
    metadata_files: List[str] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = set()
        if self.metadata_files is None:
            self.metadata_files = []
        if not self.loader_name:
            self.loader_name = self.loader_type.value.title()


@dataclass 
class ModDependency:
    """MOD 依赖"""
    mod_id: str
    version_requirement: Optional[VersionRequirement] = None
    required: bool = True
    side: str = "both"  # client, server, both


@dataclass
class ModMetadata:
    """MOD 元数据"""
    mod_id: str
    name: str
    version: str
    description: str = ""
    authors: List[str] = None
    license: str = ""
    homepage: str = ""
    source_url: str = ""
    issue_tracker: str = ""
    icon_path: str = ""
    dependencies: List[ModDependency] = None
    supported_sides: Set[str] = None
    supported_versions: List[str] = None
    loader_info: Optional[ModLoaderInfo] = None
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.dependencies is None:
            self.dependencies = []
        if self.supported_sides is None:
            self.supported_sides = {"client", "server"}
        if self.supported_versions is None:
            self.supported_versions = []


class ModLoaderDetector(ABC):
    """MOD 加载器检测器抽象基类"""
    
    @property
    @abstractmethod
    def loader_type(self) -> ModLoaderType:
        pass
    
    @property 
    @abstractmethod
    def metadata_files(self) -> List[str]:
        """元数据文件列表"""
        pass
    
    @property
    @abstractmethod
    def signature_patterns(self) -> List[str]:
        """加载器特征模式"""
        pass
    
    @abstractmethod
    async def detect_in_jar(self, jar_path: Path) -> Optional[ModLoaderInfo]:
        """在 JAR 文件中检测加载器"""
        pass
    
    @abstractmethod
    async def extract_mod_metadata(self, jar_path: Path) -> Optional[ModMetadata]:
        """提取 MOD 元数据"""
        pass
    
    @abstractmethod
    def validate_mod_structure(self, jar_path: Path) -> bool:
        """验证 MOD 结构"""
        pass


class ForgeModLoader(ModLoaderDetector):
    """Forge MOD 加载器检测器"""
    
    @property
    def loader_type(self) -> ModLoaderType:
        return ModLoaderType.FORGE
    
    @property
    def metadata_files(self) -> List[str]:
        return ["META-INF/mods.toml", "mcmod.info"]
    
    @property
    def signature_patterns(self) -> List[str]:
        return [
            r"net/minecraftforge/.*",
            r"META-INF/mods\.toml",
            r"mcmod\.info"
        ]
    
    async def detect_in_jar(self, jar_path: Path) -> Optional[ModLoaderInfo]:
        """检测 Forge 加载器"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 检查特征文件
                has_mods_toml = "META-INF/mods.toml" in file_list
                has_mcmod_info = "mcmod.info" in file_list
                has_forge_classes = any(f.startswith("net/minecraftforge/") for f in file_list)
                
                if not (has_mods_toml or has_mcmod_info or has_forge_classes):
                    return None
                
                # 提取版本信息
                loader_version = "unknown"
                minecraft_version = "unknown"
                api_version = None
                
                if has_mods_toml:
                    try:
                        import toml
                        mods_toml_content = jar.read("META-INF/mods.toml").decode('utf-8')
                        mods_data = toml.loads(mods_toml_content)
                        
                        loader_version = mods_data.get("loaderVersion", "unknown")
                        minecraft_version = mods_data.get("minecraftVersion", "unknown")
                        
                        # 尝试从依赖中获取更多信息
                        if "dependencies" in mods_data:
                            for mod_id, deps in mods_data["dependencies"].items():
                                for dep in deps:
                                    if dep.get("modId") == "forge":
                                        api_version = dep.get("versionRange", "")
                    except Exception as e:
                        logger.warning("解析 mods.toml 失败", error=str(e))
                
                elif has_mcmod_info:
                    try:
                        mcmod_content = jar.read("mcmod.info").decode('utf-8')
                        mcmod_data = json.loads(mcmod_content)
                        
                        if isinstance(mcmod_data, list) and mcmod_data:
                            mod_info = mcmod_data[0]
                            minecraft_version = mod_info.get("mcversion", "unknown")
                    except Exception as e:
                        logger.warning("解析 mcmod.info 失败", error=str(e))
                
                return ModLoaderInfo(
                    loader_type=ModLoaderType.FORGE,
                    version=loader_version,
                    minecraft_version=minecraft_version,
                    loader_name="Forge",
                    api_version=api_version,
                    capabilities={"mods", "coremods", "resources"},
                    metadata_files=[f for f in self.metadata_files if f in file_list]
                )
        
        except Exception as e:
            logger.error("Forge 检测失败", jar_path=str(jar_path), error=str(e))
            return None
    
    async def extract_mod_metadata(self, jar_path: Path) -> Optional[ModMetadata]:
        """提取 Forge MOD 元数据"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 优先使用 mods.toml
                if "META-INF/mods.toml" in file_list:
                    return await self._extract_from_mods_toml(jar)
                elif "mcmod.info" in file_list:
                    return await self._extract_from_mcmod_info(jar)
                
        except Exception as e:
            logger.error("提取 Forge 元数据失败", jar_path=str(jar_path), error=str(e))
        
        return None
    
    async def _extract_from_mods_toml(self, jar: zipfile.ZipFile) -> Optional[ModMetadata]:
        """从 mods.toml 提取元数据"""
        try:
            import toml
            content = jar.read("META-INF/mods.toml").decode('utf-8')
            data = toml.loads(content)
            
            # 获取第一个 MOD 信息
            mods = data.get("mods", [])
            if not mods:
                return None
            
            mod = mods[0]
            
            # 提取依赖信息
            dependencies = []
            deps_data = data.get("dependencies", {})
            mod_id = mod.get("modId", "unknown")
            
            if mod_id in deps_data:
                for dep in deps_data[mod_id]:
                    version_range = dep.get("versionRange", "")
                    version_req = self._parse_forge_version_range(version_range)
                    
                    dependencies.append(ModDependency(
                        mod_id=dep.get("modId", ""),
                        version_requirement=version_req,
                        required=dep.get("mandatory", True),
                        side=dep.get("side", "both")
                    ))
            
            return ModMetadata(
                mod_id=mod_id,
                name=mod.get("displayName", mod_id),
                version=mod.get("version", "unknown"),
                description=mod.get("description", ""),
                authors=[mod.get("authors", "")],
                license=mod.get("license", ""),
                homepage=mod.get("displayURL", ""),
                dependencies=dependencies,
                loader_info=await self.detect_in_jar(Path(jar.filename))
            )
            
        except Exception as e:
            logger.error("解析 mods.toml 失败", error=str(e))
            return None
    
    async def _extract_from_mcmod_info(self, jar: zipfile.ZipFile) -> Optional[ModMetadata]:
        """从 mcmod.info 提取元数据"""
        try:
            content = jar.read("mcmod.info").decode('utf-8')
            data = json.loads(content)
            
            if isinstance(data, list) and data:
                mod = data[0]
            elif isinstance(data, dict):
                mod = data
            else:
                return None
            
            return ModMetadata(
                mod_id=mod.get("modid", "unknown"),
                name=mod.get("name", ""),
                version=mod.get("version", "unknown"),
                description=mod.get("description", ""),
                authors=mod.get("authorList", []),
                homepage=mod.get("url", ""),
                loader_info=await self.detect_in_jar(Path(jar.filename))
            )
            
        except Exception as e:
            logger.error("解析 mcmod.info 失败", error=str(e))
            return None
    
    def _parse_forge_version_range(self, version_range: str) -> Optional[VersionRequirement]:
        """解析 Forge 版本范围"""
        if not version_range:
            return None
        
        try:
            # 简化版本范围解析
            if "," in version_range:
                parts = version_range.strip("[]()").split(",")
                min_ver = parts[0].strip() if parts[0].strip() else None
                max_ver = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
                return VersionRequirement(min_ver, max_ver)
            else:
                return VersionRequirement(min_version=version_range)
        except Exception:
            return None
    
    def validate_mod_structure(self, jar_path: Path) -> bool:
        """验证 Forge MOD 结构"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 必须有元数据文件或 Forge 类
                has_metadata = any(f in file_list for f in self.metadata_files)
                has_forge_classes = any(f.startswith("net/minecraftforge/") for f in file_list)
                
                return has_metadata or has_forge_classes
        except Exception:
            return False


class FabricModLoader(ModLoaderDetector):
    """Fabric MOD 加载器检测器"""
    
    @property
    def loader_type(self) -> ModLoaderType:
        return ModLoaderType.FABRIC
    
    @property
    def metadata_files(self) -> List[str]:
        return ["fabric.mod.json"]
    
    @property
    def signature_patterns(self) -> List[str]:
        return [
            r"fabric\.mod\.json",
            r"net/fabricmc/.*",
            r"assets/.*/lang/.*\.json"
        ]
    
    async def detect_in_jar(self, jar_path: Path) -> Optional[ModLoaderInfo]:
        """检测 Fabric 加载器"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                if "fabric.mod.json" not in file_list:
                    return None
                
                # 解析 fabric.mod.json
                fabric_json_content = jar.read("fabric.mod.json").decode('utf-8')
                fabric_data = json.loads(fabric_json_content)
                
                # 提取版本信息
                schema_version = fabric_data.get("schemaVersion", 1)
                minecraft_version = "unknown"
                fabric_version = "unknown"
                
                # 从依赖中获取 Minecraft 版本
                depends = fabric_data.get("depends", {})
                if "minecraft" in depends:
                    minecraft_version = depends["minecraft"]
                if "fabricloader" in depends:
                    fabric_version = depends["fabricloader"]
                
                return ModLoaderInfo(
                    loader_type=ModLoaderType.FABRIC,
                    version=fabric_version,
                    minecraft_version=minecraft_version,
                    loader_name="Fabric",
                    api_version=f"schema-{schema_version}",
                    capabilities={"mods", "mixins", "resources", "data"},
                    metadata_files=["fabric.mod.json"]
                )
        
        except Exception as e:
            logger.error("Fabric 检测失败", jar_path=str(jar_path), error=str(e))
            return None
    
    async def extract_mod_metadata(self, jar_path: Path) -> Optional[ModMetadata]:
        """提取 Fabric MOD 元数据"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                if "fabric.mod.json" not in jar.namelist():
                    return None
                
                content = jar.read("fabric.mod.json").decode('utf-8')
                data = json.loads(content)
                
                # 提取基本信息
                mod_id = data.get("id", "unknown")
                name = data.get("name", mod_id)
                version_str = data.get("version", "unknown")
                description = data.get("description", "")
                
                # 提取作者信息
                authors = []
                authors_data = data.get("authors", [])
                for author in authors_data:
                    if isinstance(author, str):
                        authors.append(author)
                    elif isinstance(author, dict):
                        authors.append(author.get("name", ""))
                
                # 提取联系信息
                contact = data.get("contact", {})
                homepage = contact.get("homepage", "")
                source_url = contact.get("sources", "")
                issue_tracker = contact.get("issues", "")
                
                # 提取依赖
                dependencies = []
                depends = data.get("depends", {})
                for dep_id, dep_version in depends.items():
                    if dep_id not in ["minecraft", "fabricloader"]:  # 排除系统依赖
                        version_req = VersionRequirement(min_version=dep_version) if dep_version else None
                        dependencies.append(ModDependency(
                            mod_id=dep_id,
                            version_requirement=version_req,
                            required=True
                        ))
                
                # 可选依赖
                suggests = data.get("suggests", {})
                for dep_id, dep_version in suggests.items():
                    version_req = VersionRequirement(min_version=dep_version) if dep_version else None
                    dependencies.append(ModDependency(
                        mod_id=dep_id,
                        version_requirement=version_req,
                        required=False
                    ))
                
                # 支持的环境
                environment = data.get("environment", "*")
                if environment == "client":
                    supported_sides = {"client"}
                elif environment == "server":
                    supported_sides = {"server"}
                else:
                    supported_sides = {"client", "server"}
                
                return ModMetadata(
                    mod_id=mod_id,
                    name=name,
                    version=version_str,
                    description=description,
                    authors=authors,
                    license=data.get("license", ""),
                    homepage=homepage,
                    source_url=source_url,
                    issue_tracker=issue_tracker,
                    icon_path=data.get("icon", ""),
                    dependencies=dependencies,
                    supported_sides=supported_sides,
                    loader_info=await self.detect_in_jar(jar_path)
                )
        
        except Exception as e:
            logger.error("提取 Fabric 元数据失败", jar_path=str(jar_path), error=str(e))
            return None
    
    def validate_mod_structure(self, jar_path: Path) -> bool:
        """验证 Fabric MOD 结构"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                return "fabric.mod.json" in jar.namelist()
        except Exception:
            return False


class QuiltModLoader(FabricModLoader):
    """Quilt MOD 加载器检测器（继承 Fabric 检测器）"""
    
    @property
    def loader_type(self) -> ModLoaderType:
        return ModLoaderType.QUILT
    
    @property
    def metadata_files(self) -> List[str]:
        return ["quilt.mod.json", "fabric.mod.json"]
    
    @property
    def signature_patterns(self) -> List[str]:
        return [
            r"quilt\.mod\.json",
            r"fabric\.mod\.json",
            r"org/quiltmc/.*",
            r"net/fabricmc/.*"
        ]
    
    async def detect_in_jar(self, jar_path: Path) -> Optional[ModLoaderInfo]:
        """检测 Quilt 加载器"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 优先检查 quilt.mod.json
                if "quilt.mod.json" in file_list:
                    return await self._detect_quilt_metadata(jar)
                # 检查 Quilt 特有的类
                elif any(f.startswith("org/quiltmc/") for f in file_list):
                    # 如果有 fabric.mod.json，可能是兼容模式
                    if "fabric.mod.json" in file_list:
                        loader_info = await super().detect_in_jar(jar_path)
                        if loader_info:
                            loader_info.loader_type = ModLoaderType.QUILT
                            loader_info.loader_name = "Quilt"
                            return loader_info
        
        except Exception as e:
            logger.error("Quilt 检测失败", jar_path=str(jar_path), error=str(e))
        
        return None
    
    async def _detect_quilt_metadata(self, jar: zipfile.ZipFile) -> Optional[ModLoaderInfo]:
        """检测 Quilt 元数据"""
        try:
            content = jar.read("quilt.mod.json").decode('utf-8')
            data = json.loads(content)
            
            schema_version = data.get("schema_version", 1)
            minecraft_version = "unknown"
            quilt_version = "unknown"
            
            # 从依赖中获取版本信息
            quilt_loader = data.get("quilt_loader", {})
            depends = quilt_loader.get("depends", [])
            
            for dep in depends:
                if isinstance(dep, dict):
                    dep_id = dep.get("id", "")
                    if dep_id == "minecraft":
                        minecraft_version = dep.get("versions", "unknown")
                    elif dep_id == "quilt_loader":
                        quilt_version = dep.get("versions", "unknown")
            
            return ModLoaderInfo(
                loader_type=ModLoaderType.QUILT,
                version=quilt_version,
                minecraft_version=minecraft_version,
                loader_name="Quilt",
                api_version=f"schema-{schema_version}",
                capabilities={"mods", "mixins", "resources", "data", "quilt_api"},
                metadata_files=["quilt.mod.json"]
            )
            
        except Exception as e:
            logger.error("解析 quilt.mod.json 失败", error=str(e))
            return None


class NeoForgeModLoader(ModLoaderDetector):
    """NeoForge MOD 加载器检测器"""
    
    @property
    def loader_type(self) -> ModLoaderType:
        return ModLoaderType.NEOFORGE
    
    @property
    def metadata_files(self) -> List[str]:
        return ["META-INF/neoforge.mods.toml", "META-INF/mods.toml"]
    
    @property
    def signature_patterns(self) -> List[str]:
        return [
            r"net/neoforged/.*",
            r"META-INF/neoforge\.mods\.toml"
        ]
    
    async def detect_in_jar(self, jar_path: Path) -> Optional[ModLoaderInfo]:
        """检测 NeoForge 加载器"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 检查特征文件和类
                has_neoforge_toml = "META-INF/neoforge.mods.toml" in file_list
                has_neoforge_classes = any(f.startswith("net/neoforged/") for f in file_list)
                
                if not (has_neoforge_toml or has_neoforge_classes):
                    return None
                
                loader_version = "unknown"
                minecraft_version = "unknown"
                api_version = None
                
                # 解析 neoforge.mods.toml
                if has_neoforge_toml:
                    try:
                        import toml
                        content = jar.read("META-INF/neoforge.mods.toml").decode('utf-8')
                        data = toml.loads(content)
                        
                        loader_version = data.get("neoForgeVersion", "unknown")
                        minecraft_version = data.get("minecraftVersion", "unknown")
                        
                        # 从依赖中获取 API 版本
                        if "dependencies" in data:
                            for mod_id, deps in data["dependencies"].items():
                                for dep in deps:
                                    if dep.get("modId") == "neoforge":
                                        api_version = dep.get("versionRange", "")
                    except Exception as e:
                        logger.warning("解析 neoforge.mods.toml 失败", error=str(e))
                
                return ModLoaderInfo(
                    loader_type=ModLoaderType.NEOFORGE,
                    version=loader_version,
                    minecraft_version=minecraft_version,
                    loader_name="NeoForge",
                    api_version=api_version,
                    capabilities={"mods", "coremods", "resources", "data_generation"},
                    metadata_files=[f for f in self.metadata_files if f in file_list]
                )
        
        except Exception as e:
            logger.error("NeoForge 检测失败", jar_path=str(jar_path), error=str(e))
            return None
    
    async def extract_mod_metadata(self, jar_path: Path) -> Optional[ModMetadata]:
        """提取 NeoForge MOD 元数据"""
        # NeoForge 的元数据格式与 Forge 类似，可以复用 Forge 的逻辑
        forge_detector = ForgeModLoader()
        metadata = await forge_detector.extract_mod_metadata(jar_path)
        
        if metadata:
            # 更新加载器信息为 NeoForge
            metadata.loader_info = await self.detect_in_jar(jar_path)
        
        return metadata
    
    def validate_mod_structure(self, jar_path: Path) -> bool:
        """验证 NeoForge MOD 结构"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 检查 NeoForge 特征
                has_neoforge_toml = "META-INF/neoforge.mods.toml" in file_list
                has_neoforge_classes = any(f.startswith("net/neoforged/") for f in file_list)
                
                return has_neoforge_toml or has_neoforge_classes
        except Exception:
            return False


class ModLoaderRegistry:
    """MOD 加载器注册表"""
    
    def __init__(self):
        self.detectors: Dict[ModLoaderType, ModLoaderDetector] = {
            ModLoaderType.FORGE: ForgeModLoader(),
            ModLoaderType.NEOFORGE: NeoForgeModLoader(),
            ModLoaderType.FABRIC: FabricModLoader(),
            ModLoaderType.QUILT: QuiltModLoader()
        }
        
        # 检测优先级（按常见程度排序）
        self.detection_order = [
            ModLoaderType.FABRIC,
            ModLoaderType.FORGE,
            ModLoaderType.QUILT,
            ModLoaderType.NEOFORGE
        ]
        
        logger.info("MOD 加载器注册表已初始化", 
                   detectors=list(self.detectors.keys()))
    
    def register_detector(self, detector: ModLoaderDetector):
        """注册检测器"""
        self.detectors[detector.loader_type] = detector
        logger.info("注册 MOD 加载器检测器", 
                   loader_type=detector.loader_type.value)
    
    async def detect_loader(self, jar_path: Path) -> Optional[ModLoaderInfo]:
        """检测 JAR 文件的加载器类型"""
        if not jar_path.exists() or not jar_path.suffix.lower() == '.jar':
            return None
        
        # 按优先级检测
        for loader_type in self.detection_order:
            detector = self.detectors.get(loader_type)
            if detector:
                try:
                    loader_info = await detector.detect_in_jar(jar_path)
                    if loader_info:
                        logger.info("检测到 MOD 加载器",
                                  jar_path=str(jar_path),
                                  loader_type=loader_type.value,
                                  version=loader_info.version)
                        return loader_info
                except Exception as e:
                    logger.warning("检测器执行失败",
                                 loader_type=loader_type.value,
                                 jar_path=str(jar_path),
                                 error=str(e))
        
        logger.debug("未检测到已知的 MOD 加载器", jar_path=str(jar_path))
        return None
    
    async def extract_metadata(self, jar_path: Path, loader_type: Optional[ModLoaderType] = None) -> Optional[ModMetadata]:
        """提取 MOD 元数据"""
        if not jar_path.exists():
            return None
        
        # 如果未指定加载器类型，先检测
        if loader_type is None:
            loader_info = await self.detect_loader(jar_path)
            if loader_info:
                loader_type = loader_info.loader_type
        
        if loader_type and loader_type in self.detectors:
            detector = self.detectors[loader_type]
            try:
                return await detector.extract_mod_metadata(jar_path)
            except Exception as e:
                logger.error("提取元数据失败",
                           jar_path=str(jar_path),
                           loader_type=loader_type.value,
                           error=str(e))
        
        return None
    
    def validate_mod(self, jar_path: Path, loader_type: Optional[ModLoaderType] = None) -> bool:
        """验证 MOD 结构"""
        if not jar_path.exists():
            return False
        
        if loader_type and loader_type in self.detectors:
            detector = self.detectors[loader_type]
            return detector.validate_mod_structure(jar_path)
        else:
            # 尝试所有检测器
            for detector in self.detectors.values():
                if detector.validate_mod_structure(jar_path):
                    return True
        
        return False
    
    def get_supported_loaders(self) -> List[ModLoaderType]:
        """获取支持的加载器列表"""
        return list(self.detectors.keys())
    
    def get_detector(self, loader_type: ModLoaderType) -> Optional[ModLoaderDetector]:
        """获取指定类型的检测器"""
        return self.detectors.get(loader_type)
    
    async def batch_detect(self, jar_paths: List[Path]) -> Dict[Path, Optional[ModLoaderInfo]]:
        """批量检测加载器"""
        results = {}
        
        for jar_path in jar_paths:
            try:
                loader_info = await self.detect_loader(jar_path)
                results[jar_path] = loader_info
            except Exception as e:
                logger.error("批量检测失败", jar_path=str(jar_path), error=str(e))
                results[jar_path] = None
        
        logger.info("批量检测完成",
                   total=len(jar_paths),
                   detected=sum(1 for info in results.values() if info))
        
        return results
    
    def get_statistics(self, jar_paths: List[Path]) -> Dict[str, Any]:
        """获取检测统计信息"""
        stats = {
            "total_files": len(jar_paths),
            "loader_distribution": {},
            "minecraft_versions": set(),
            "unsupported": 0
        }
        
        for loader_type in ModLoaderType:
            stats["loader_distribution"][loader_type.value] = 0
        
        return stats


# ==================== 工厂函数和便捷接口 ====================

_registry_instance: Optional[ModLoaderRegistry] = None

def get_mod_loader_registry() -> ModLoaderRegistry:
    """获取 MOD 加载器注册表单例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModLoaderRegistry()
    return _registry_instance


async def detect_mod_loader(jar_path: Union[str, Path]) -> Optional[ModLoaderInfo]:
    """便捷函数：检测 MOD 加载器"""
    registry = get_mod_loader_registry()
    return await registry.detect_loader(Path(jar_path))


async def extract_mod_metadata(jar_path: Union[str, Path]) -> Optional[ModMetadata]:
    """便捷函数：提取 MOD 元数据"""
    registry = get_mod_loader_registry()
    return await registry.extract_metadata(Path(jar_path))


def validate_mod_file(jar_path: Union[str, Path]) -> bool:
    """便捷函数：验证 MOD 文件"""
    registry = get_mod_loader_registry()
    return registry.validate_mod(Path(jar_path))


async def scan_directory_for_loaders(directory: Path) -> Dict[Path, Optional[ModLoaderInfo]]:
    """扫描目录中的所有 MOD 加载器"""
    if not directory.exists() or not directory.is_dir():
        return {}
    
    jar_files = list(directory.glob("*.jar"))
    if not jar_files:
        return {}
    
    registry = get_mod_loader_registry()
    return await registry.batch_detect(jar_files)