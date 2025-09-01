"""
MC模组分析领域服务

负责分析模组文件，提取基本信息、检测格式、解析依赖关系等核心业务逻辑
"""

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from packages.core.framework.logging import get_logger
from packages.core.framework.validation import ValidationRule, Validator

from domain.models.enums import FileType, ModLoader
from domain.models.value_objects.file_path import FilePath
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.mod_id import ModId
from domain.models.value_objects.mod_version import ModVersion

logger = get_logger(__name__)


@dataclass
class ModMetadata:
    """模组元数据"""

    mod_id: ModId
    name: str
    version: ModVersion
    description: str | None = None
    authors: list[str] = None
    homepage: str | None = None
    mod_loader: ModLoader | None = None
    minecraft_versions: list[str] = None
    dependencies: list["ModDependency"] = None

    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.dependencies is None:
            self.dependencies = []
        if self.minecraft_versions is None:
            self.minecraft_versions = []


@dataclass
class ModDependency:
    """模组依赖信息"""

    mod_id: ModId
    version_requirement: str
    is_required: bool = True
    side: str = "both"  # both, client, server


@dataclass
class LanguageFileInfo:
    """语言文件信息"""

    language_code: LanguageCode
    file_path: str
    file_type: FileType
    entry_count: int
    file_size: int


@dataclass
class ModScanResult:
    """模组扫描结果"""

    metadata: ModMetadata
    language_files: list[LanguageFileInfo]
    has_assets: bool
    assets_structure: dict[str, list[str]]
    scan_errors: list[str]

    def __post_init__(self):
        if self.scan_errors is None:
            self.scan_errors = []


class ModAnalyzerService:
    """模组分析领域服务"""

    def __init__(self):
        self._validator = Validator()
        self._setup_validation_rules()

    def _setup_validation_rules(self):
        """设置验证规则"""
        # 添加模组文件验证规则
        self._validator.add_rule(
            "mod_file_exists",
            ValidationRule(lambda path: Path(path).exists(), "模组文件不存在"),
        )
        self._validator.add_rule(
            "mod_file_readable",
            ValidationRule(lambda path: Path(path).is_file(), "路径不是文件"),
        )

    async def analyze_mod(self, file_path: FilePath) -> ModScanResult:
        """
        分析模组文件，返回完整的扫描结果

        Args:
            file_path: 模组文件路径 (JAR文件或文件夹)

        Returns:
            ModScanResult: 完整的模组分析结果

        Raises:
            ValueError: 文件路径无效或文件不存在
            ModAnalysisError: 模组分析过程中的错误
        """
        logger.info(f"开始分析模组: {file_path}")

        # 验证文件路径
        validation_result = self._validator.validate(
            {"mod_file_exists": file_path.value, "mod_file_readable": file_path.value}
        )

        if not validation_result.is_valid:
            raise ValueError(f"无效的模组文件: {validation_result.errors}")

        try:
            path = Path(file_path.value)

            if path.is_file() and path.suffix.lower() == ".jar":
                # 分析JAR文件
                return await self._analyze_jar_mod(path)
            elif path.is_dir():
                # 分析文件夹模组
                return await self._analyze_folder_mod(path)
            else:
                raise ValueError(f"不支持的文件类型: {path}")

        except Exception as e:
            logger.error(f"模组分析失败: {file_path} - {str(e)}")
            raise ModAnalysisError(f"分析模组失败: {str(e)}") from e

    async def _analyze_jar_mod(self, jar_path: Path) -> ModScanResult:
        """分析JAR格式的模组"""
        scan_errors = []

        try:
            with zipfile.ZipFile(jar_path, "r") as jar_file:
                # 提取模组元数据
                metadata = self._extract_mod_metadata_from_jar(jar_file)

                # 扫描语言文件
                language_files = self._scan_language_files_in_jar(
                    jar_file, metadata.mod_id
                )

                # 分析assets结构
                assets_structure = self._analyze_assets_structure_in_jar(jar_file)

                return ModScanResult(
                    metadata=metadata,
                    language_files=language_files,
                    has_assets=bool(assets_structure),
                    assets_structure=assets_structure,
                    scan_errors=scan_errors,
                )

        except zipfile.BadZipFile:
            raise ModAnalysisError("无效的JAR文件格式")
        except Exception as e:
            scan_errors.append(f"JAR分析错误: {str(e)}")
            raise

    async def _analyze_folder_mod(self, folder_path: Path) -> ModScanResult:
        """分析文件夹格式的模组"""
        scan_errors = []

        try:
            # 提取模组元数据
            metadata = self._extract_mod_metadata_from_folder(folder_path)

            # 扫描语言文件
            language_files = self._scan_language_files_in_folder(
                folder_path, metadata.mod_id
            )

            # 分析assets结构
            assets_structure = self._analyze_assets_structure_in_folder(folder_path)

            return ModScanResult(
                metadata=metadata,
                language_files=language_files,
                has_assets=bool(assets_structure),
                assets_structure=assets_structure,
                scan_errors=scan_errors,
            )

        except Exception as e:
            scan_errors.append(f"文件夹分析错误: {str(e)}")
            raise

    def _extract_mod_metadata_from_jar(self, jar_file: zipfile.ZipFile) -> ModMetadata:
        """从JAR文件提取模组元数据"""

        # 尝试读取 mods.toml (Forge 1.13+)
        if "META-INF/mods.toml" in jar_file.namelist():
            return self._parse_mods_toml(jar_file.read("META-INF/mods.toml"))

        # 尝试读取 mcmod.info (Forge 1.12.2-)
        if "mcmod.info" in jar_file.namelist():
            return self._parse_mcmod_info(jar_file.read("mcmod.info"))

        # 尝试读取 fabric.mod.json (Fabric)
        if "fabric.mod.json" in jar_file.namelist():
            return self._parse_fabric_mod_json(jar_file.read("fabric.mod.json"))

        # 如果没找到元数据文件，尝试从文件名推断
        logger.warning("未找到模组元数据文件，尝试从文件名推断")
        return self._infer_metadata_from_filename(Path(jar_file.filename))

    def _extract_mod_metadata_from_folder(self, folder_path: Path) -> ModMetadata:
        """从文件夹提取模组元数据"""

        # 检查各种可能的元数据文件
        metadata_files = [
            ("META-INF/mods.toml", self._parse_mods_toml),
            ("mcmod.info", self._parse_mcmod_info),
            ("fabric.mod.json", self._parse_fabric_mod_json),
        ]

        for file_path, parser in metadata_files:
            full_path = folder_path / file_path
            if full_path.exists():
                try:
                    with open(full_path, "rb") as f:
                        return parser(f.read())
                except Exception as e:
                    logger.warning(f"解析元数据文件失败 {file_path}: {e}")
                    continue

        # 从文件夹名称推断
        return self._infer_metadata_from_filename(folder_path)

    def _parse_mods_toml(self, content: bytes) -> ModMetadata:
        """解析mods.toml格式 (Forge 1.13+)"""
        import tomllib

        try:
            toml_data = tomllib.loads(content.decode("utf-8"))

            # mods.toml可能包含多个模组
            mods_list = toml_data.get("mods", [])
            if not mods_list:
                raise ValueError("mods.toml中没有找到模组信息")

            # 取第一个模组的信息
            mod_info = mods_list[0]

            return ModMetadata(
                mod_id=ModId(mod_info["modId"]),
                name=mod_info.get("displayName", mod_info["modId"]),
                version=ModVersion(mod_info["version"]),
                description=mod_info.get("description"),
                authors=mod_info.get("authors", "").split(",")
                if mod_info.get("authors")
                else [],
                homepage=mod_info.get("displayURL"),
                mod_loader=ModLoader.FORGE,
                minecraft_versions=self._extract_mc_versions_from_toml(toml_data),
            )

        except Exception as e:
            raise ModAnalysisError(f"解析mods.toml失败: {str(e)}")

    def _parse_mcmod_info(self, content: bytes) -> ModMetadata:
        """解析mcmod.info格式 (Forge 1.12.2-)"""
        try:
            json_data = json.loads(content.decode("utf-8"))

            # mcmod.info可能是数组或单个对象
            if isinstance(json_data, list):
                if not json_data:
                    raise ValueError("mcmod.info为空数组")
                mod_info = json_data[0]
            else:
                mod_info = json_data

            return ModMetadata(
                mod_id=ModId(mod_info["modid"]),
                name=mod_info.get("name", mod_info["modid"]),
                version=ModVersion(mod_info["version"]),
                description=mod_info.get("description"),
                authors=mod_info.get("authorList", []) or [mod_info.get("authors", "")],
                homepage=mod_info.get("url"),
                mod_loader=ModLoader.FORGE,
                minecraft_versions=mod_info.get("mcversion", "").split(",")
                if mod_info.get("mcversion")
                else [],
            )

        except Exception as e:
            raise ModAnalysisError(f"解析mcmod.info失败: {str(e)}")

    def _parse_fabric_mod_json(self, content: bytes) -> ModMetadata:
        """解析fabric.mod.json格式 (Fabric)"""
        try:
            json_data = json.loads(content.decode("utf-8"))

            return ModMetadata(
                mod_id=ModId(json_data["id"]),
                name=json_data.get("name", json_data["id"]),
                version=ModVersion(json_data["version"]),
                description=json_data.get("description"),
                authors=self._extract_authors_from_fabric_json(json_data),
                homepage=json_data.get("contact", {}).get("homepage"),
                mod_loader=ModLoader.FABRIC,
                minecraft_versions=self._extract_mc_versions_from_fabric_json(
                    json_data
                ),
            )

        except Exception as e:
            raise ModAnalysisError(f"解析fabric.mod.json失败: {str(e)}")

    def _infer_metadata_from_filename(self, path: Path) -> ModMetadata:
        """从文件名推断模组信息"""
        filename = path.stem

        # 尝试从文件名解析模组ID和版本
        # 常见格式: modid-1.2.3.jar, modid_1.2.3.jar
        parts = filename.replace("-", "_").split("_")

        if len(parts) >= 2:
            mod_id = parts[0]
            version = parts[1]
        else:
            mod_id = filename
            version = "unknown"

        logger.info(f"从文件名推断模组信息: {mod_id} v{version}")

        return ModMetadata(
            mod_id=ModId(mod_id.lower()),
            name=mod_id,
            version=ModVersion(version),
            description=f"从文件名推断的模组: {filename}",
        )

    def _scan_language_files_in_jar(
        self, jar_file: zipfile.ZipFile, mod_id: ModId
    ) -> list[LanguageFileInfo]:
        """扫描JAR文件中的语言文件"""
        language_files = []

        # 构建可能的语言文件路径模式
        lang_patterns = [
            f"assets/{mod_id.value}/lang/",
            "assets/minecraft/lang/",  # 某些模组可能修改原版语言
        ]

        for file_path in jar_file.namelist():
            for pattern in lang_patterns:
                if file_path.startswith(pattern) and file_path.endswith(
                    (".json", ".lang")
                ):
                    try:
                        # 提取语言代码
                        filename = Path(file_path).name
                        lang_code = filename.split(".")[0]

                        # 验证语言代码
                        language_code = LanguageCode(lang_code)

                        # 获取文件信息
                        file_info = jar_file.getinfo(file_path)

                        # 尝试计算条目数量
                        entry_count = self._count_entries_in_lang_file(
                            jar_file.read(file_path),
                            FileType.JSON
                            if filename.endswith(".json")
                            else FileType.PROPERTIES,
                        )

                        language_files.append(
                            LanguageFileInfo(
                                language_code=language_code,
                                file_path=file_path,
                                file_type=FileType.JSON
                                if filename.endswith(".json")
                                else FileType.PROPERTIES,
                                entry_count=entry_count,
                                file_size=file_info.file_size,
                            )
                        )

                    except Exception as e:
                        logger.warning(f"处理语言文件失败 {file_path}: {e}")
                        continue

        return language_files

    def _scan_language_files_in_folder(
        self, folder_path: Path, mod_id: ModId
    ) -> list[LanguageFileInfo]:
        """扫描文件夹中的语言文件"""
        language_files = []

        # 可能的语言文件目录
        lang_dirs = [
            folder_path / "assets" / mod_id.value / "lang",
            folder_path / "assets" / "minecraft" / "lang",
            folder_path
            / "src"
            / "main"
            / "resources"
            / "assets"
            / mod_id.value
            / "lang",
        ]

        for lang_dir in lang_dirs:
            if not lang_dir.exists():
                continue

            for lang_file_path in lang_dir.glob("*"):
                if lang_file_path.suffix.lower() in [".json", ".lang"]:
                    try:
                        # 提取语言代码
                        lang_code = lang_file_path.stem
                        language_code = LanguageCode(lang_code)

                        # 读取文件内容并计算条目数量
                        with open(lang_file_path, "rb") as f:
                            content = f.read()

                        entry_count = self._count_entries_in_lang_file(
                            content,
                            FileType.JSON
                            if lang_file_path.suffix == ".json"
                            else FileType.PROPERTIES,
                        )

                        language_files.append(
                            LanguageFileInfo(
                                language_code=language_code,
                                file_path=str(lang_file_path.relative_to(folder_path)),
                                file_type=FileType.JSON
                                if lang_file_path.suffix == ".json"
                                else FileType.PROPERTIES,
                                entry_count=entry_count,
                                file_size=lang_file_path.stat().st_size,
                            )
                        )

                    except Exception as e:
                        logger.warning(f"处理语言文件失败 {lang_file_path}: {e}")
                        continue

        return language_files

    def _count_entries_in_lang_file(self, content: bytes, file_type: FileType) -> int:
        """计算语言文件中的条目数量"""
        try:
            if file_type == FileType.JSON:
                data = json.loads(content.decode("utf-8"))
                return len(data) if isinstance(data, dict) else 0
            elif file_type == FileType.PROPERTIES:
                # 简单计算非空行和非注释行
                lines = content.decode("utf-8", errors="ignore").split("\n")
                count = 0
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        count += 1
                return count
            else:
                return 0
        except Exception:
            return 0

    def _analyze_assets_structure_in_jar(
        self, jar_file: zipfile.ZipFile
    ) -> dict[str, list[str]]:
        """分析JAR文件中的assets结构"""
        structure = {}

        for file_path in jar_file.namelist():
            if file_path.startswith("assets/"):
                parts = file_path.split("/")
                if len(parts) >= 3:
                    mod_id = parts[1]
                    asset_type = parts[2]

                    if mod_id not in structure:
                        structure[mod_id] = {}
                    if asset_type not in structure[mod_id]:
                        structure[mod_id][asset_type] = []

                    if len(parts) > 3:
                        structure[mod_id][asset_type].append("/".join(parts[3:]))

        return structure

    def _analyze_assets_structure_in_folder(
        self, folder_path: Path
    ) -> dict[str, list[str]]:
        """分析文件夹中的assets结构"""
        structure = {}
        assets_path = folder_path / "assets"

        if not assets_path.exists():
            return structure

        for mod_dir in assets_path.iterdir():
            if mod_dir.is_dir():
                mod_id = mod_dir.name
                structure[mod_id] = {}

                for asset_type_dir in mod_dir.iterdir():
                    if asset_type_dir.is_dir():
                        asset_type = asset_type_dir.name
                        structure[mod_id][asset_type] = []

                        for asset_file in asset_type_dir.rglob("*"):
                            if asset_file.is_file():
                                relative_path = asset_file.relative_to(asset_type_dir)
                                structure[mod_id][asset_type].append(str(relative_path))

        return structure

    def _extract_authors_from_fabric_json(self, json_data: dict) -> list[str]:
        """从Fabric模组JSON中提取作者信息"""
        authors = []

        # authors字段可能是字符串、列表或对象
        authors_field = json_data.get("authors", [])

        if isinstance(authors_field, str):
            authors.append(authors_field)
        elif isinstance(authors_field, list):
            for author in authors_field:
                if isinstance(author, str):
                    authors.append(author)
                elif isinstance(author, dict) and "name" in author:
                    authors.append(author["name"])

        return authors

    def _extract_mc_versions_from_fabric_json(self, json_data: dict) -> list[str]:
        """从Fabric模组JSON中提取Minecraft版本信息"""
        depends = json_data.get("depends", {})
        minecraft_dep = depends.get("minecraft", "")

        if minecraft_dep:
            # Fabric使用版本范围，如 ">=1.18", "~1.18.2"
            return [minecraft_dep]

        return []

    def _extract_mc_versions_from_toml(self, toml_data: dict) -> list[str]:
        """从mods.toml中提取Minecraft版本信息"""
        dependencies = toml_data.get("dependencies", {})

        for mod_id, deps in dependencies.items():
            for dep in deps:
                if dep.get("modId") == "minecraft":
                    return [dep.get("versionRange", "")]

        return []


class ModAnalysisError(Exception):
    """模组分析异常"""

    pass
