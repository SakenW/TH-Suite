"""
Minecraft模组扫描器
实现具体的模组文件扫描逻辑
"""

import json
import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import toml

logger = logging.getLogger(__name__)


@dataclass
class ModScanResult:
    """模组扫描结果"""

    mod_id: str
    name: str
    version: str
    authors: list[str]
    description: str | None
    minecraft_version: str | None
    loader_type: str  # forge, fabric, quilt
    translations: dict[str, dict[str, str]]  # language -> key -> value
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "mod_id": self.mod_id,
            "name": self.name,
            "version": self.version,
            "authors": self.authors,
            "description": self.description,
            "minecraft_version": self.minecraft_version,
            "loader_type": self.loader_type,
            "translations": self.translations,
            "metadata": self.metadata,
        }


class MinecraftModScanner:
    """Minecraft模组扫描器"""

    def __init__(self):
        self.supported_extensions = [".jar", ".zip"]
        self.language_file_patterns = [
            "assets/*/lang/*.json",
            "assets/*/lang/*.lang",
            "data/*/lang/*.json",
        ]

    def _extract_version_from_filename(self, filename: str) -> str:
        """从文件名中提取版本号"""
        # 移除文件扩展名
        name = Path(filename).stem
        
        # 按优先级排序的版本号模式 - 优先匹配更具体的模式
        version_patterns = [
            # modname-mc1.20.1-1.2.3.jar (提取第二个版本号)
            r"-mc\d+(?:\.\d+)*-(\d+(?:\.\d+)*)",
            # modname-1.20.1-1.2.3.jar (提取最后一个版本号)
            r"-\d+(?:\.\d+)*-(\d+(?:\.\d+)*)",
            # modname_v1.2.3.jar
            r"[_-]v(\d+(?:\.\d+)*(?:[.-](?:alpha|beta|rc|snapshot|SNAPSHOT)\d*)?)",
            # modname-1.2.3.jar (最后匹配，避免匹配到MC版本)
            r"-(\d+(?:\.\d+)*(?:[.-](?:alpha|beta|rc|snapshot|SNAPSHOT)\d*)?)$",
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # 如果没有找到版本号，返回 "unknown"
        return "unknown"

    def _resolve_template_variables(self, template_str: str, file_path: str) -> str:
        """解析模板变量"""
        if not isinstance(template_str, str):
            return str(template_str)
            
        result = template_str
        
        # 解析 ${file.jarVersion}
        if "${file.jarVersion}" in result:
            version = self._extract_version_from_filename(file_path)
            result = result.replace("${file.jarVersion}", version)
            
        # 可以添加更多模板变量的解析
        # ${file.name}, ${file.baseName} 等
        
        return result

    def scan(self, file_path: str) -> ModScanResult:
        """扫描模组文件"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        logger.info(f"Scanning mod file: {file_path}")

        try:
            with zipfile.ZipFile(file_path, "r") as zip_file:
                # 检测加载器类型
                loader_type = self._detect_loader_type(zip_file)

                # 提取模组信息
                mod_info = self._extract_mod_info(zip_file, loader_type, file_path)

                # 提取翻译文件
                translations = self._extract_translations(zip_file)

                return ModScanResult(
                    mod_id=mod_info.get("mod_id", path.stem),
                    name=mod_info.get("name", path.stem),
                    version=mod_info.get("version", "1.0.0"),
                    authors=mod_info.get("authors", []),
                    description=mod_info.get("description"),
                    minecraft_version=mod_info.get("minecraft_version"),
                    loader_type=loader_type,
                    translations=translations,
                    metadata=mod_info,
                )

        except Exception as e:
            logger.error(f"Failed to scan {file_path}: {e}")
            raise

    def _detect_loader_type(self, zip_file: zipfile.ZipFile) -> str:
        """检测模组加载器类型"""
        file_list = zip_file.namelist()

        if "META-INF/mods.toml" in file_list:
            return "forge"
        elif "fabric.mod.json" in file_list:
            return "fabric"
        elif "quilt.mod.json" in file_list:
            return "quilt"
        else:
            # 默认为Forge
            return "forge"

    def _extract_mod_info(
        self, zip_file: zipfile.ZipFile, loader_type: str, file_path: str
    ) -> dict[str, Any]:
        """提取模组信息"""
        try:
            if loader_type == "forge":
                return self._extract_forge_info(zip_file, file_path)
            elif loader_type == "fabric":
                return self._extract_fabric_info(zip_file)
            elif loader_type == "quilt":
                return self._extract_quilt_info(zip_file)
            else:
                return {}
        except Exception as e:
            logger.warning(f"Failed to extract mod info: {e}")
            return {}

    def _extract_forge_info(self, zip_file: zipfile.ZipFile, file_path: str) -> dict[str, Any]:
        """提取Forge模组信息"""
        try:
            with zip_file.open("META-INF/mods.toml") as f:
                data = toml.load(f)

                # 获取第一个mod的信息
                mod = data.get("mods", [{}])[0]

                # 获取版本号并解析模板变量
                version = mod.get("version", "${file.jarVersion}")
                resolved_version = self._resolve_template_variables(version, file_path)

                return {
                    "mod_id": mod.get("modId", ""),
                    "name": mod.get("displayName", ""),
                    "version": resolved_version,
                    "authors": [mod.get("authors", "")],
                    "description": mod.get("description", ""),
                    "minecraft_version": self._extract_forge_mc_version(data),
                }
        except Exception as e:
            logger.error(f"Failed to parse mods.toml: {e}")
            return {}

    def _extract_fabric_info(self, zip_file: zipfile.ZipFile) -> dict[str, Any]:
        """提取Fabric模组信息"""
        try:
            with zip_file.open("fabric.mod.json") as f:
                data = json.load(f)

                authors = data.get("authors", [])
                if isinstance(authors, list):
                    authors = [
                        a if isinstance(a, str) else a.get("name", "") for a in authors
                    ]

                return {
                    "mod_id": data.get("id", ""),
                    "name": data.get("name", ""),
                    "version": data.get("version", ""),
                    "authors": authors,
                    "description": data.get("description", ""),
                    "minecraft_version": self._extract_fabric_mc_version(data),
                }
        except Exception as e:
            logger.error(f"Failed to parse fabric.mod.json: {e}")
            return {}

    def _extract_quilt_info(self, zip_file: zipfile.ZipFile) -> dict[str, Any]:
        """提取Quilt模组信息"""
        try:
            with zip_file.open("quilt.mod.json") as f:
                data = json.load(f)

                quilt_loader = data.get("quilt_loader", {})
                metadata = quilt_loader.get("metadata", {})

                return {
                    "mod_id": quilt_loader.get("id", ""),
                    "name": metadata.get("name", ""),
                    "version": quilt_loader.get("version", ""),
                    "authors": metadata.get("contributors", {}).keys(),
                    "description": metadata.get("description", ""),
                    "minecraft_version": self._extract_quilt_mc_version(data),
                }
        except Exception as e:
            logger.error(f"Failed to parse quilt.mod.json: {e}")
            return {}

    def _extract_forge_mc_version(self, data: dict) -> str | None:
        """提取Forge的Minecraft版本"""
        dependencies = data.get("dependencies", {})
        minecraft = dependencies.get("minecraft", "")

        # 解析版本范围，如 "[1.20,1.21)"
        if minecraft and "[" in minecraft:
            parts = minecraft.strip("[]()").split(",")
            if parts:
                return parts[0]

        return minecraft

    def _extract_fabric_mc_version(self, data: dict) -> str | None:
        """提取Fabric的Minecraft版本"""
        depends = data.get("depends", {})
        minecraft = depends.get("minecraft", "")

        # 解析版本，如 ">=1.20"
        if minecraft:
            minecraft = minecraft.replace(">=", "").replace("~", "").replace("^", "")

        return minecraft

    def _extract_quilt_mc_version(self, data: dict) -> str | None:
        """提取Quilt的Minecraft版本"""
        quilt_loader = data.get("quilt_loader", {})
        depends = quilt_loader.get("depends", [])

        for dep in depends:
            if dep.get("id") == "minecraft":
                versions = dep.get("versions", "")
                if isinstance(versions, str):
                    return versions.replace(">=", "").replace("~", "")

        return None

    def _extract_translations(
        self, zip_file: zipfile.ZipFile
    ) -> dict[str, dict[str, str]]:
        """提取翻译文件"""
        translations = {}

        for file_name in zip_file.namelist():
            # 检查是否是语言文件
            if "/lang/" in file_name and (
                file_name.endswith(".json") or file_name.endswith(".lang")
            ):
                try:
                    # 提取语言代码
                    parts = file_name.split("/")
                    lang_file = parts[-1]
                    language = lang_file.split(".")[0]

                    # 读取翻译内容
                    with zip_file.open(file_name) as f:
                        if file_name.endswith(".json"):
                            content = json.load(f)
                            if isinstance(content, dict):
                                if language not in translations:
                                    translations[language] = {}
                                translations[language].update(content)
                        elif file_name.endswith(".lang"):
                            # 解析.lang格式（key=value）
                            content = f.read().decode("utf-8", errors="ignore")
                            if language not in translations:
                                translations[language] = {}

                            for line in content.splitlines():
                                line = line.strip()
                                if line and not line.startswith("#") and "=" in line:
                                    key, value = line.split("=", 1)
                                    translations[language][key.strip()] = value.strip()

                except Exception as e:
                    logger.warning(f"Failed to parse language file {file_name}: {e}")

        return translations
