"""
加密器

提供加密和哈希功能
"""

import hashlib


class Encryptor:
    """加密器"""

    @staticmethod
    def hash_md5(data: str) -> str:
        """MD5哈希"""
        return hashlib.md5(data.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_sha256(data: str) -> str:
        """SHA256哈希"""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
