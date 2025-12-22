"""
存储管理器

提供统一的存储接口，支持多种存储实现
"""

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any


class IStorageProvider(ABC):
    """存储提供者接口"""

    @abstractmethod
    async def put(self, key: str, data: bytes, metadata: dict[str, Any] = None) -> str:
        """存储数据"""
        pass

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        """获取数据"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查是否存在"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除数据"""
        pass

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """列出键"""
        pass

    @abstractmethod
    async def get_metadata(self, key: str) -> dict[str, Any] | None:
        """获取元数据"""
        pass


class LocalStorageProvider(IStorageProvider):
    """本地文件系统存储提供者"""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 元数据目录
        self.metadata_path = self.base_path / ".metadata"
        self.metadata_path.mkdir(exist_ok=True)

    async def put(self, key: str, data: bytes, metadata: dict[str, Any] = None) -> str:
        """存储数据到本地文件"""
        file_path = self._get_file_path(key)

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入数据
        with open(file_path, "wb") as f:
            f.write(data)

        # 保存元数据
        if metadata:
            await self._save_metadata(key, metadata)

        return str(file_path)

    async def get(self, key: str) -> bytes | None:
        """从本地文件获取数据"""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return None

        with open(file_path, "rb") as f:
            return f.read()

    async def exists(self, key: str) -> bool:
        """检查文件是否存在"""
        return self._get_file_path(key).exists()

    async def delete(self, key: str) -> bool:
        """删除文件"""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return False

        # 删除数据文件
        file_path.unlink()

        # 删除元数据
        await self._delete_metadata(key)

        return True

    async def list_keys(self, prefix: str = "") -> list[str]:
        """列出所有键"""
        keys = []

        for file_path in self.base_path.rglob("*"):
            if file_path.is_file() and not file_path.parent.name.startswith("."):
                # 计算相对键
                rel_path = file_path.relative_to(self.base_path)
                key = str(rel_path).replace("\\", "/")

                if key.startswith(prefix):
                    keys.append(key)

        return sorted(keys)

    async def get_metadata(self, key: str) -> dict[str, Any] | None:
        """获取元数据"""
        metadata_file = self._get_metadata_path(key)

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _get_file_path(self, key: str) -> Path:
        """获取文件路径"""
        # 处理路径分隔符
        key = key.replace("/", "\\") if "\\" in str(self.base_path) else key
        return self.base_path / key

    def _get_metadata_path(self, key: str) -> Path:
        """获取元数据文件路径"""
        # 使用键的哈希作为元数据文件名
        key_hash = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self.metadata_path / f"{key_hash}.json"

    async def _save_metadata(self, key: str, metadata: dict[str, Any]) -> None:
        """保存元数据"""
        metadata_file = self._get_metadata_path(key)

        # 添加系统元数据
        full_metadata = {
            "key": key,
            "created_at": metadata.get("created_at") or str(datetime.now()),
            **metadata,
        }

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(full_metadata, f, indent=2)

    async def _delete_metadata(self, key: str) -> None:
        """删除元数据"""
        metadata_file = self._get_metadata_path(key)
        if metadata_file.exists():
            metadata_file.unlink()


class StorageManager:
    """存储管理器"""

    def __init__(self):
        self._providers: dict[str, IStorageProvider] = {}
        self._default_provider: str | None = None

    def register_provider(
        self, name: str, provider: IStorageProvider, is_default: bool = False
    ) -> None:
        """注册存储提供者"""
        self._providers[name] = provider

        if is_default or self._default_provider is None:
            self._default_provider = name

    def get_provider(self, name: str | None = None) -> IStorageProvider:
        """获取存储提供者"""
        provider_name = name or self._default_provider

        if provider_name is None:
            raise ValueError("没有可用的存储提供者")

        if provider_name not in self._providers:
            raise ValueError(f"存储提供者 '{provider_name}' 不存在")

        return self._providers[provider_name]

    async def put(
        self,
        key: str,
        data: bytes,
        provider: str = None,
        metadata: dict[str, Any] = None,
    ) -> str:
        """存储数据"""
        storage_provider = self.get_provider(provider)
        return await storage_provider.put(key, data, metadata)

    async def put_text(
        self,
        key: str,
        text: str,
        encoding: str = "utf-8",
        provider: str = None,
        metadata: dict[str, Any] = None,
    ) -> str:
        """存储文本数据"""
        data = text.encode(encoding)
        return await self.put(key, data, provider, metadata)

    async def put_json(
        self, key: str, obj: Any, provider: str = None, metadata: dict[str, Any] = None
    ) -> str:
        """存储JSON数据"""
        json_text = json.dumps(obj, ensure_ascii=False, indent=2)
        return await self.put_text(key, json_text, provider=provider, metadata=metadata)

    async def get(self, key: str, provider: str = None) -> bytes | None:
        """获取数据"""
        storage_provider = self.get_provider(provider)
        return await storage_provider.get(key)

    async def get_text(
        self, key: str, encoding: str = "utf-8", provider: str = None
    ) -> str | None:
        """获取文本数据"""
        data = await self.get(key, provider)
        if data is None:
            return None
        return data.decode(encoding)

    async def get_json(self, key: str, provider: str = None) -> Any | None:
        """获取JSON数据"""
        text = await self.get_text(key, provider=provider)
        if text is None:
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    async def exists(self, key: str, provider: str = None) -> bool:
        """检查是否存在"""
        storage_provider = self.get_provider(provider)
        return await storage_provider.exists(key)

    async def delete(self, key: str, provider: str = None) -> bool:
        """删除数据"""
        storage_provider = self.get_provider(provider)
        return await storage_provider.delete(key)

    async def list_keys(self, prefix: str = "", provider: str = None) -> list[str]:
        """列出键"""
        storage_provider = self.get_provider(provider)
        return await storage_provider.list_keys(prefix)

    async def get_metadata(
        self, key: str, provider: str = None
    ) -> dict[str, Any] | None:
        """获取元数据"""
        storage_provider = self.get_provider(provider)
        return await storage_provider.get_metadata(key)

    async def copy(
        self,
        source_key: str,
        dest_key: str,
        source_provider: str = None,
        dest_provider: str = None,
    ) -> bool:
        """复制数据"""
        # 获取源数据
        data = await self.get(source_key, source_provider)
        if data is None:
            return False

        # 获取元数据
        metadata = await self.get_metadata(source_key, source_provider)

        # 存储到目标
        await self.put(dest_key, data, dest_provider, metadata)

        return True

    async def move(
        self,
        source_key: str,
        dest_key: str,
        source_provider: str = None,
        dest_provider: str = None,
    ) -> bool:
        """移动数据"""
        # 先复制
        success = await self.copy(source_key, dest_key, source_provider, dest_provider)

        if success:
            # 删除源文件
            await self.delete(source_key, source_provider)

        return success
