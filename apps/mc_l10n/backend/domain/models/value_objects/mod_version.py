"""模组版本值对象"""

import re

from packages.core.data.models import ValueObject


class ModVersion(ValueObject):
    """模组版本值对象"""

    def __init__(self, version_string: str):
        if not version_string:
            raise ValueError("版本号不能为空")
        self._version_string = version_string
        self._parsed = self._parse_version(version_string)

    def _parse_version(self, version: str) -> dict:
        """解析版本号"""
        # 尝试解析语义化版本号 (major.minor.patch)
        semver_pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?(?:\+(.+))?$"
        match = re.match(semver_pattern, version)

        if match:
            return {
                "major": int(match.group(1)),
                "minor": int(match.group(2)),
                "patch": int(match.group(3)),
                "pre_release": match.group(4),
                "build": match.group(5),
                "type": "semver",
            }

        # 如果不是标准语义化版本，作为普通字符串处理
        return {"raw": version, "type": "string"}

    def is_newer_than(self, other: "ModVersion") -> bool:
        """比较版本新旧"""
        if self._parsed["type"] == "semver" and other._parsed["type"] == "semver":
            # 语义化版本比较
            for field in ["major", "minor", "patch"]:
                if self._parsed[field] > other._parsed[field]:
                    return True
                elif self._parsed[field] < other._parsed[field]:
                    return False
            return False

        # 字符串比较
        return self._version_string > other._version_string

    @property
    def version_string(self) -> str:
        return self._version_string

    @property
    def is_semver(self) -> bool:
        return self._parsed["type"] == "semver"

    @property
    def major(self) -> int | None:
        return self._parsed.get("major")

    @property
    def minor(self) -> int | None:
        return self._parsed.get("minor")

    @property
    def patch(self) -> int | None:
        return self._parsed.get("patch")

    def __str__(self) -> str:
        return self._version_string

    def __eq__(self, other) -> bool:
        if not isinstance(other, ModVersion):
            return False
        return self._version_string == other._version_string

    def __hash__(self) -> int:
        return hash(self._version_string)
