"""
文件验证领域服务

负责验证模组文件、语言文件的完整性、格式正确性等
"""

import json
import zipfile
from dataclasses import dataclass
from typing import Any

from packages.core.framework.logging import get_logger

from domain.models.enums import FileType
from domain.models.value_objects.file_path import FilePath
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.translation_key import TranslationKey

logger = get_logger(__name__)


@dataclass
class ValidationIssue:
    """验证问题"""

    severity: str  # "error", "warning", "info"
    category: str  # "format", "content", "structure", "security"
    message: str
    line_number: int | None = None
    suggestion: str | None = None


@dataclass
class FileValidationResult:
    """文件验证结果"""

    is_valid: bool
    file_path: str
    file_type: FileType
    issues: list[ValidationIssue]
    metadata: dict[str, Any]

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TranslationConsistencyResult:
    """翻译一致性检查结果"""

    missing_keys: list[TranslationKey]
    extra_keys: list[TranslationKey]
    format_inconsistencies: list[ValidationIssue]
    placeholder_mismatches: list[ValidationIssue]


class FileValidatorService:
    """文件验证领域服务"""

    def __init__(self):
        self._supported_formats = {
            ".jar": FileType.JSON,  # JAR文件内部包含JSON
            ".json": FileType.JSON,
            ".properties": FileType.PROPERTIES,
            ".lang": FileType.PROPERTIES,
            ".yml": FileType.YAML,
            ".yaml": FileType.YAML,
        }

        # 常见的Minecraft格式化占位符
        self._mc_placeholders = [
            r"%s",
            r"%d",
            r"%f",
            r"%c",  # Java String.format
            r"\{[0-9]+\}",  # {0}, {1}, etc.
            r"\{[a-zA-Z_][a-zA-Z0-9_]*\}",  # {player}, {item}, etc.
            r"§[0-9a-fk-or]",  # Minecraft color codes
        ]

    async def validate_mod_file(self, file_path: FilePath) -> FileValidationResult:
        """
        验证模组文件的完整性和格式

        Args:
            file_path: 模组文件路径

        Returns:
            FileValidationResult: 验证结果
        """
        logger.info(f"开始验证模组文件: {file_path}")

        issues = []
        metadata = {}

        try:
            # 基础文件检查
            basic_issues = await self._validate_basic_file_properties(file_path)
            issues.extend(basic_issues)

            # 根据文件类型进行具体验证
            if file_path.extension == ".jar":
                jar_issues, jar_metadata = await self._validate_jar_file(file_path)
                issues.extend(jar_issues)
                metadata.update(jar_metadata)
                file_type = FileType.JSON
            else:
                # 文件夹模组验证
                folder_issues, folder_metadata = await self._validate_mod_folder(
                    file_path
                )
                issues.extend(folder_issues)
                metadata.update(folder_metadata)
                file_type = FileType.JSON

            # 安全检查
            security_issues = await self._perform_security_checks(file_path)
            issues.extend(security_issues)

            # 判断是否通过验证
            error_count = len([issue for issue in issues if issue.severity == "error"])
            is_valid = error_count == 0

            return FileValidationResult(
                is_valid=is_valid,
                file_path=str(file_path),
                file_type=file_type,
                issues=issues,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"文件验证失败: {file_path} - {str(e)}")
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="system",
                    message=f"验证过程中发生错误: {str(e)}",
                )
            )

            return FileValidationResult(
                is_valid=False,
                file_path=str(file_path),
                file_type=FileType.UNKNOWN,
                issues=issues,
                metadata={},
            )

    async def validate_language_file(
        self,
        file_content: bytes,
        file_path: str,
        file_type: FileType,
        language_code: LanguageCode,
    ) -> FileValidationResult:
        """
        验证语言文件的格式和内容

        Args:
            file_content: 文件内容
            file_path: 文件路径
            file_type: 文件类型
            language_code: 语言代码

        Returns:
            FileValidationResult: 验证结果
        """
        logger.info(f"验证语言文件: {file_path} ({language_code.code})")

        issues = []
        metadata = {
            "language_code": language_code.code,
            "file_size": len(file_content),
            "encoding": "utf-8",
        }

        try:
            # 编码验证
            try:
                text_content = file_content.decode("utf-8")
            except UnicodeDecodeError as e:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="format",
                        message=f"文件编码不是UTF-8: {str(e)}",
                        suggestion="请将文件转换为UTF-8编码",
                    )
                )
                return FileValidationResult(
                    False, file_path, file_type, issues, metadata
                )

            # 格式特定验证
            if file_type == FileType.JSON:
                format_issues, entries = await self._validate_json_language_file(
                    text_content
                )
            elif file_type == FileType.PROPERTIES:
                format_issues, entries = await self._validate_properties_language_file(
                    text_content
                )
            elif file_type == FileType.YAML:
                format_issues, entries = await self._validate_yaml_language_file(
                    text_content
                )
            else:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="format",
                        message=f"不支持的文件类型: {file_type}",
                    )
                )
                return FileValidationResult(
                    False, file_path, file_type, issues, metadata
                )

            issues.extend(format_issues)

            if entries:
                # 内容验证
                content_issues = await self._validate_translation_content(
                    entries, language_code
                )
                issues.extend(content_issues)

                # 更新元数据
                metadata.update(
                    {
                        "entry_count": len(entries),
                        "empty_entries": len(
                            [v for v in entries.values() if not v.strip()]
                        ),
                        "has_placeholders": any(
                            self._has_placeholders(v) for v in entries.values()
                        ),
                    }
                )

            # 判断验证结果
            error_count = len([issue for issue in issues if issue.severity == "error"])
            is_valid = error_count == 0

            return FileValidationResult(
                is_valid=is_valid,
                file_path=file_path,
                file_type=file_type,
                issues=issues,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"语言文件验证失败: {file_path} - {str(e)}")
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="system",
                    message=f"验证过程中发生错误: {str(e)}",
                )
            )

            return FileValidationResult(
                is_valid=False,
                file_path=file_path,
                file_type=file_type,
                issues=issues,
                metadata=metadata,
            )

    async def check_translation_consistency(
        self,
        source_entries: dict[str, str],
        target_entries: dict[str, str],
        source_language: LanguageCode,
        target_language: LanguageCode,
    ) -> TranslationConsistencyResult:
        """
        检查翻译一致性（缺失的键、多余的键、格式问题等）

        Args:
            source_entries: 源语言条目
            target_entries: 目标语言条目
            source_language: 源语言代码
            target_language: 目标语言代码

        Returns:
            TranslationConsistencyResult: 一致性检查结果
        """
        logger.info(f"检查翻译一致性: {source_language.code} -> {target_language.code}")

        source_keys = set(source_entries.keys())
        target_keys = set(target_entries.keys())

        # 找出缺失和多余的键
        missing_keys = [TranslationKey(key) for key in source_keys - target_keys]
        extra_keys = [TranslationKey(key) for key in target_keys - source_keys]

        format_issues = []
        placeholder_issues = []

        # 检查共同键的格式一致性
        common_keys = source_keys & target_keys
        for key in common_keys:
            source_value = source_entries[key]
            target_value = target_entries[key]

            # 检查占位符一致性
            source_placeholders = self._extract_placeholders(source_value)
            target_placeholders = self._extract_placeholders(target_value)

            if source_placeholders != target_placeholders:
                placeholder_issues.append(
                    ValidationIssue(
                        severity="warning",
                        category="content",
                        message=f"键 '{key}' 的占位符不匹配",
                        suggestion=f"源: {source_placeholders}, 目标: {target_placeholders}",
                    )
                )

            # 检查格式代码一致性
            source_formatting = self._extract_formatting_codes(source_value)
            target_formatting = self._extract_formatting_codes(target_value)

            if len(source_formatting) != len(target_formatting):
                format_issues.append(
                    ValidationIssue(
                        severity="info",
                        category="format",
                        message=f"键 '{key}' 的格式代码数量不匹配",
                        suggestion="请检查颜色代码和格式代码是否正确",
                    )
                )

        return TranslationConsistencyResult(
            missing_keys=missing_keys,
            extra_keys=extra_keys,
            format_inconsistencies=format_issues,
            placeholder_mismatches=placeholder_issues,
        )

    async def _validate_basic_file_properties(
        self, file_path: FilePath
    ) -> list[ValidationIssue]:
        """验证基本文件属性"""
        issues = []

        if not file_path.exists:
            issues.append(
                ValidationIssue(
                    severity="error", category="structure", message="文件不存在"
                )
            )
            return issues

        # 文件大小检查
        try:
            file_size = file_path.resolved_path.stat().st_size
            if file_size == 0:
                issues.append(
                    ValidationIssue(
                        severity="warning", category="structure", message="文件为空"
                    )
                )
            elif file_size > 100 * 1024 * 1024:  # 100MB
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        category="structure",
                        message="文件过大，可能影响处理性能",
                    )
                )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="system",
                    message=f"无法获取文件信息: {str(e)}",
                )
            )

        return issues

    async def _validate_jar_file(
        self, file_path: FilePath
    ) -> tuple[list[ValidationIssue], dict[str, Any]]:
        """验证JAR文件"""
        issues = []
        metadata = {"type": "jar", "contains_assets": False}

        try:
            with zipfile.ZipFile(file_path.resolved_path, "r") as jar:
                # 检查基本JAR结构
                file_list = jar.namelist()
                metadata["file_count"] = len(file_list)

                # 检查模组元数据文件
                has_metadata = False
                metadata_files = ["META-INF/mods.toml", "mcmod.info", "fabric.mod.json"]
                for meta_file in metadata_files:
                    if meta_file in file_list:
                        has_metadata = True
                        metadata["metadata_file"] = meta_file
                        break

                if not has_metadata:
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            category="structure",
                            message="未找到模组元数据文件",
                            suggestion="JAR文件应包含 mods.toml、mcmod.info 或 fabric.mod.json",
                        )
                    )

                # 检查assets目录
                assets_files = [f for f in file_list if f.startswith("assets/")]
                if assets_files:
                    metadata["contains_assets"] = True
                    metadata["assets_count"] = len(assets_files)

                    # 检查语言文件
                    lang_files = [
                        f
                        for f in assets_files
                        if "/lang/" in f and f.endswith((".json", ".lang"))
                    ]
                    metadata["language_files"] = len(lang_files)
                else:
                    issues.append(
                        ValidationIssue(
                            severity="info",
                            category="structure",
                            message="JAR文件中未找到assets目录",
                        )
                    )

        except zipfile.BadZipFile:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="format",
                    message="文件不是有效的ZIP/JAR格式",
                )
            )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="system",
                    message=f"JAR文件验证失败: {str(e)}",
                )
            )

        return issues, metadata

    async def _validate_mod_folder(
        self, folder_path: FilePath
    ) -> tuple[list[ValidationIssue], dict[str, Any]]:
        """验证模组文件夹"""
        issues = []
        metadata = {"type": "folder"}

        if not folder_path.is_directory:
            issues.append(
                ValidationIssue(
                    severity="error", category="structure", message="路径不是目录"
                )
            )
            return issues, metadata

        folder = folder_path.resolved_path

        # 检查assets目录
        assets_dir = folder / "assets"
        if assets_dir.exists():
            metadata["contains_assets"] = True

            # 统计资源文件
            asset_files = list(assets_dir.rglob("*"))
            metadata["assets_count"] = len([f for f in asset_files if f.is_file()])

            # 统计语言文件
            lang_files = list(assets_dir.rglob("lang/*"))
            metadata["language_files"] = len([f for f in lang_files if f.is_file()])
        else:
            metadata["contains_assets"] = False
            issues.append(
                ValidationIssue(
                    severity="info",
                    category="structure",
                    message="文件夹中未找到assets目录",
                )
            )

        return issues, metadata

    async def _validate_json_language_file(
        self, content: str
    ) -> tuple[list[ValidationIssue], dict[str, str]]:
        """验证JSON语言文件"""
        issues = []
        entries = {}

        try:
            data = json.loads(content)

            if not isinstance(data, dict):
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="format",
                        message="JSON根元素必须是对象",
                    )
                )
                return issues, {}

            # 验证每个条目
            for key, value in data.items():
                if not isinstance(key, str):
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            category="format",
                            message=f"键必须是字符串: {type(key)}",
                        )
                    )
                    continue

                if not isinstance(value, str):
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            category="format",
                            message=f"键 '{key}' 的值不是字符串: {type(value)}",
                            suggestion="值将被转换为字符串",
                        )
                    )
                    value = str(value)

                entries[key] = value

        except json.JSONDecodeError as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="format",
                    message=f"JSON格式错误: {str(e)}",
                    line_number=getattr(e, "lineno", None),
                )
            )

        return issues, entries

    async def _validate_properties_language_file(
        self, content: str
    ) -> tuple[list[ValidationIssue], dict[str, str]]:
        """验证Properties语言文件"""
        issues = []
        entries = {}

        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            original_line = line
            line = line.strip()

            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="format",
                        message="缺少等号分隔符",
                        line_number=i,
                        suggestion=f"行内容: '{original_line}'",
                    )
                )
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if not key:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="format",
                        message="键不能为空",
                        line_number=i,
                    )
                )
                continue

            if key in entries:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        category="content",
                        message=f"重复的键: '{key}'",
                        line_number=i,
                    )
                )

            entries[key] = value

        return issues, entries

    async def _validate_yaml_language_file(
        self, content: str
    ) -> tuple[list[ValidationIssue], dict[str, str]]:
        """验证YAML语言文件"""
        issues = []
        entries = {}

        try:
            import yaml

            data = yaml.safe_load(content)

            if not isinstance(data, dict):
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="format",
                        message="YAML根元素必须是对象",
                    )
                )
                return issues, {}

            # 递归展开嵌套结构
            entries = self._flatten_dict(data)

        except ImportError:
            issues.append(
                ValidationIssue(
                    severity="error", category="system", message="YAML支持未安装"
                )
            )
        except yaml.YAMLError as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="format",
                    message=f"YAML格式错误: {str(e)}",
                )
            )

        return issues, entries

    def _flatten_dict(self, data: dict, prefix: str = "") -> dict[str, str]:
        """递归展开嵌套字典"""
        result = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, full_key))
            else:
                result[full_key] = str(value)
        return result

    async def _validate_translation_content(
        self, entries: dict[str, str], language_code: LanguageCode
    ) -> list[ValidationIssue]:
        """验证翻译内容"""
        issues = []

        for key, value in entries.items():
            # 检查空值
            if not value.strip():
                issues.append(
                    ValidationIssue(
                        severity="info",
                        category="content",
                        message=f"键 '{key}' 的值为空",
                    )
                )
                continue

            # 检查可疑的未翻译内容（英文键在非英文语言文件中）
            if not language_code.is_english() and self._appears_untranslated(
                value, language_code
            ):
                issues.append(
                    ValidationIssue(
                        severity="info",
                        category="content",
                        message=f"键 '{key}' 可能未翻译",
                        suggestion="请检查是否需要翻译此内容",
                    )
                )

            # 检查过长的文本（可能导致UI问题）
            if len(value) > 200:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        category="content",
                        message=f"键 '{key}' 的文本过长（{len(value)}字符）",
                        suggestion="长文本可能导致界面显示问题",
                    )
                )

        return issues

    def _appears_untranslated(self, value: str, target_language: LanguageCode) -> bool:
        """检查文本是否看起来未翻译"""
        # 简单的启发式检查
        if target_language.is_chinese():
            # 中文翻译应该包含中文字符
            chinese_chars = sum(1 for c in value if "\u4e00" <= c <= "\u9fff")
            return chinese_chars < len(value) * 0.3  # 至少30%是中文字符

        # 对于其他语言，暂时不做检查
        return False

    def _has_placeholders(self, text: str) -> bool:
        """检查文本是否包含占位符"""
        import re

        for pattern in self._mc_placeholders:
            if re.search(pattern, text):
                return True
        return False

    def _extract_placeholders(self, text: str) -> set[str]:
        """提取文本中的占位符"""
        import re

        placeholders = set()
        for pattern in self._mc_placeholders:
            matches = re.findall(pattern, text)
            placeholders.update(matches)
        return placeholders

    def _extract_formatting_codes(self, text: str) -> list[str]:
        """提取Minecraft格式代码"""
        import re

        return re.findall(r"§[0-9a-fk-or]", text)

    async def _perform_security_checks(
        self, file_path: FilePath
    ) -> list[ValidationIssue]:
        """执行安全检查"""
        issues = []

        # 检查文件大小（防止过大的文件）
        try:
            file_size = file_path.resolved_path.stat().st_size
            if file_size > 500 * 1024 * 1024:  # 500MB
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="security",
                        message="文件过大，可能存在安全风险",
                    )
                )
        except Exception:
            pass

        # 对于JAR文件，检查可疑的路径
        if file_path.extension == ".jar":
            try:
                with zipfile.ZipFile(file_path.resolved_path, "r") as jar:
                    for file_info in jar.infolist():
                        filename = file_info.filename

                        # 检查路径遍历攻击
                        if ".." in filename or filename.startswith("/"):
                            issues.append(
                                ValidationIssue(
                                    severity="error",
                                    category="security",
                                    message=f"检测到可疑的文件路径: {filename}",
                                )
                            )

                        # 检查过深的目录结构
                        if filename.count("/") > 10:
                            issues.append(
                                ValidationIssue(
                                    severity="warning",
                                    category="security",
                                    message=f"文件路径过深: {filename}",
                                )
                            )
            except Exception:
                pass

        return issues
