"""
文件系统缓存提供者

基于文件系统的缓存实现，提供持久化存储
"""

import fnmatch
import hashlib
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..cache_manager import ICacheProvider


class FileCacheProvider(ICacheProvider):
    """文件系统缓存提供者"""

    def __init__(self, cache_dir: Path, serialization: str = "pickle"):
        self.cache_dir = Path(cache_dir)
        self.serialization = serialization  # "pickle" or "json"

        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 创建元数据目录
        self.metadata_dir = self.cache_dir / ".metadata"
        self.metadata_dir.mkdir(exist_ok=True)

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        entry_path = self._get_entry_path(key)
        metadata_path = self._get_metadata_path(key)

        if not entry_path.exists() or not metadata_path.exists():
            return None

        try:
            # 读取元数据
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)

            # 检查是否过期
            if self._is_expired(metadata):
                self._delete_files(key)
                return None

            # 读取数据
            if self.serialization == "json":
                with open(entry_path, encoding="utf-8") as f:
                    return json.load(f)
            else:  # pickle
                with open(entry_path, "rb") as f:
                    return pickle.load(f)

        except Exception:
            # 如果读取失败，删除损坏的文件
            self._delete_files(key)
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存值"""
        entry_path = self._get_entry_path(key)
        metadata_path = self._get_metadata_path(key)

        try:
            # 写入数据
            if self.serialization == "json":
                with open(entry_path, "w", encoding="utf-8") as f:
                    json.dump(value, f, ensure_ascii=False, indent=2)
            else:  # pickle
                with open(entry_path, "wb") as f:
                    pickle.dump(value, f)

            # 写入元数据
            metadata = {
                "key": key,
                "created_at": datetime.now().isoformat(),
                "ttl": ttl,
                "access_count": 0,
                "last_accessed": datetime.now().isoformat(),
            }

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

        except Exception:
            # 如果写入失败，清理可能的部分文件
            self._delete_files(key)
            raise

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        entry_path = self._get_entry_path(key)
        metadata_path = self._get_metadata_path(key)

        existed = entry_path.exists() or metadata_path.exists()
        self._delete_files(key)

        return existed

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        entry_path = self._get_entry_path(key)
        metadata_path = self._get_metadata_path(key)

        if not entry_path.exists() or not metadata_path.exists():
            return False

        try:
            # 检查是否过期
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)

            if self._is_expired(metadata):
                self._delete_files(key)
                return False

            return True

        except Exception:
            # 如果元数据损坏，删除文件
            self._delete_files(key)
            return False

    def clear(self) -> None:
        """清空所有缓存"""
        try:
            # 删除所有缓存文件
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file() and file_path.name != ".metadata":
                    file_path.unlink()

            # 删除所有元数据文件
            for file_path in self.metadata_dir.glob("*"):
                if file_path.is_file():
                    file_path.unlink()

        except Exception as e:
            print(f"清空文件缓存失败: {e}")

    def keys(self, pattern: str | None = None) -> list[str]:
        """获取所有键"""
        keys = []

        try:
            # 从元数据文件中读取键
            for metadata_file in self.metadata_dir.glob("*.json"):
                try:
                    with open(metadata_file, encoding="utf-8") as f:
                        metadata = json.load(f)

                    # 检查是否过期
                    if not self._is_expired(metadata):
                        key = metadata.get("key", "")
                        if key and (pattern is None or fnmatch.fnmatch(key, pattern)):
                            keys.append(key)
                    else:
                        # 清理过期文件
                        self._delete_files(metadata.get("key", ""))

                except Exception:
                    # 如果读取失败，删除损坏的元数据文件
                    metadata_file.unlink()

        except Exception as e:
            print(f"读取缓存键列表失败: {e}")

        return keys

    def _get_entry_path(self, key: str) -> Path:
        """获取缓存条目文件路径"""
        safe_key = self._get_safe_filename(key)
        extension = ".json" if self.serialization == "json" else ".pkl"
        return self.cache_dir / f"{safe_key}{extension}"

    def _get_metadata_path(self, key: str) -> Path:
        """获取元数据文件路径"""
        safe_key = self._get_safe_filename(key)
        return self.metadata_dir / f"{safe_key}.json"

    def _get_safe_filename(self, key: str) -> str:
        """生成安全的文件名"""
        # 使用SHA256生成文件名，避免特殊字符问题
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _is_expired(self, metadata: dict[str, Any]) -> bool:
        """检查是否过期"""
        ttl = metadata.get("ttl")
        if ttl is None:
            return False

        created_at = datetime.fromisoformat(metadata["created_at"])
        return datetime.now() > created_at + timedelta(seconds=ttl)

    def _delete_files(self, key: str) -> None:
        """删除缓存相关的所有文件"""
        entry_path = self._get_entry_path(key)
        metadata_path = self._get_metadata_path(key)

        try:
            if entry_path.exists():
                entry_path.unlink()
        except Exception:
            pass

        try:
            if metadata_path.exists():
                metadata_path.unlink()
        except Exception:
            pass
