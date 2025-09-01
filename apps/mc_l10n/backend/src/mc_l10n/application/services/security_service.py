"""安全服务模块 - 提供完整性校验、签名验证、许可记录、审计日志和OS安全存储功能。"""

import base64
import hashlib
import json
import os
import platform
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from packages.core.database import SQLCipherDatabase
from packages.core.errors import SecurityError, ValidationError


@dataclass
class IntegrityCheck:
    """完整性检查结果。"""

    file_path: str
    expected_hash: str
    actual_hash: str
    algorithm: str = "sha256"
    is_valid: bool = field(init=False)
    checked_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self.is_valid = self.expected_hash == self.actual_hash


@dataclass
class SignatureVerification:
    """签名验证结果。"""

    data_hash: str
    signature: str
    public_key_id: str
    is_valid: bool
    algorithm: str = "RSA-PSS"
    verified_at: datetime = field(default_factory=datetime.now)


@dataclass
class LicenseRecord:
    """许可记录。"""

    asset_id: str
    source_platform: str  # "curseforge", "modrinth", "github", etc.
    project_id: str
    file_id: str
    license_type: str
    license_url: str | None = None
    attribution_required: bool = False
    commercial_use_allowed: bool = True
    modification_allowed: bool = True
    redistribution_allowed: bool = True
    recorded_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditLogEntry:
    """审计日志条目。"""

    event_id: str
    event_type: str  # "upload", "download", "build", "access", "modify", etc.
    user_id: str | None
    project_id: str | None
    resource_type: str  # "project", "asset", "build", etc.
    resource_id: str
    action: str
    result: str  # "success", "failure", "partial"
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    signature: str | None = None


@dataclass
class SecureCredential:
    """安全凭证。"""

    credential_id: str
    service_name: str
    encrypted_data: bytes
    salt: bytes
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SecurityService:
    """安全服务类。

    提供完整性校验、签名验证、许可记录、审计日志和OS安全存储功能。
    """

    def __init__(
        self, database: SQLCipherDatabase, logger: structlog.BoundLogger | None = None
    ):
        self.database = database
        self.logger = logger or structlog.get_logger()
        self._master_key: bytes | None = None
        self._signing_key: rsa.RSAPrivateKey | None = None
        self._public_key: rsa.RSAPublicKey | None = None

    async def initialize_security(self, master_password: str | None = None) -> None:
        """初始化安全服务。

        Args:
            master_password: 主密码（可选，用于额外加密）
        """
        try:
            # 初始化主密钥
            await self._initialize_master_key(master_password)

            # 初始化签名密钥对
            await self._initialize_signing_keys()

            # 创建安全相关表
            await self._create_security_tables()

            self.logger.info("安全服务初始化完成")

        except Exception as e:
            self.logger.error("安全服务初始化失败", error=str(e))
            raise SecurityError(f"安全服务初始化失败: {str(e)}")

    async def verify_file_integrity(
        self, file_path: str | Path, expected_hash: str, algorithm: str = "sha256"
    ) -> IntegrityCheck:
        """验证文件完整性。

        Args:
            file_path: 文件路径
            expected_hash: 期望的哈希值
            algorithm: 哈希算法

        Returns:
            IntegrityCheck: 完整性检查结果
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ValidationError(f"文件不存在: {file_path}")

        # 计算文件哈希
        actual_hash = await self._calculate_file_hash(file_path, algorithm)

        result = IntegrityCheck(
            file_path=str(file_path),
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            algorithm=algorithm,
        )

        # 记录审计日志
        await self._log_audit_event(
            event_type="integrity_check",
            resource_type="file",
            resource_id=str(file_path),
            action="verify_integrity",
            result="success" if result.is_valid else "failure",
            details={
                "algorithm": algorithm,
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
                "is_valid": result.is_valid,
            },
        )

        return result

    async def sign_data(self, data: str | bytes, key_id: str | None = None) -> str:
        """对数据进行数字签名。

        Args:
            data: 要签名的数据
            key_id: 密钥ID（可选）

        Returns:
            str: Base64编码的签名
        """
        if isinstance(data, str):
            data = data.encode("utf-8")

        if not self._signing_key:
            raise SecurityError("签名密钥未初始化")

        try:
            # 使用RSA-PSS签名
            signature = self._signing_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )

            signature_b64 = base64.b64encode(signature).decode("utf-8")

            # 记录审计日志
            await self._log_audit_event(
                event_type="cryptographic",
                resource_type="data",
                resource_id=hashlib.sha256(data).hexdigest()[:16],
                action="sign_data",
                result="success",
                details={
                    "algorithm": "RSA-PSS",
                    "key_id": key_id or "default",
                    "data_size": len(data),
                },
            )

            return signature_b64

        except Exception as e:
            self.logger.error("数据签名失败", error=str(e))
            raise SecurityError(f"数据签名失败: {str(e)}")

    async def verify_signature(
        self, data: str | bytes, signature: str, public_key_id: str | None = None
    ) -> SignatureVerification:
        """验证数字签名。

        Args:
            data: 原始数据
            signature: Base64编码的签名
            public_key_id: 公钥ID（可选）

        Returns:
            SignatureVerification: 签名验证结果
        """
        if isinstance(data, str):
            data = data.encode("utf-8")

        if not self._public_key:
            raise SecurityError("公钥未初始化")

        try:
            signature_bytes = base64.b64decode(signature)
            data_hash = hashlib.sha256(data).hexdigest()

            # 验证RSA-PSS签名
            self._public_key.verify(
                signature_bytes,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )

            result = SignatureVerification(
                data_hash=data_hash,
                signature=signature,
                public_key_id=public_key_id or "default",
                is_valid=True,
            )

        except Exception as e:
            self.logger.warning("签名验证失败", error=str(e))
            result = SignatureVerification(
                data_hash=hashlib.sha256(data).hexdigest(),
                signature=signature,
                public_key_id=public_key_id or "default",
                is_valid=False,
            )

        # 记录审计日志
        await self._log_audit_event(
            event_type="cryptographic",
            resource_type="signature",
            resource_id=result.data_hash[:16],
            action="verify_signature",
            result="success" if result.is_valid else "failure",
            details={
                "algorithm": "RSA-PSS",
                "public_key_id": result.public_key_id,
                "is_valid": result.is_valid,
            },
        )

        return result

    async def record_license(
        self,
        asset_id: str,
        source_platform: str,
        project_id: str,
        file_id: str,
        license_info: dict[str, Any],
    ) -> LicenseRecord:
        """记录许可信息。

        Args:
            asset_id: 资产ID
            source_platform: 来源平台
            project_id: 项目ID
            file_id: 文件ID
            license_info: 许可信息

        Returns:
            LicenseRecord: 许可记录
        """
        record = LicenseRecord(
            asset_id=asset_id,
            source_platform=source_platform,
            project_id=project_id,
            file_id=file_id,
            license_type=license_info.get("type", "unknown"),
            license_url=license_info.get("url"),
            attribution_required=license_info.get("attribution_required", False),
            commercial_use_allowed=license_info.get("commercial_use_allowed", True),
            modification_allowed=license_info.get("modification_allowed", True),
            redistribution_allowed=license_info.get("redistribution_allowed", True),
            metadata=license_info.get("metadata", {}),
        )

        # 保存到数据库
        await self._save_license_record(record)

        # 记录审计日志
        await self._log_audit_event(
            event_type="license",
            resource_type="asset",
            resource_id=asset_id,
            action="record_license",
            result="success",
            details={
                "source_platform": source_platform,
                "license_type": record.license_type,
                "project_id": project_id,
                "file_id": file_id,
            },
        )

        return record

    async def get_license_records(
        self, asset_id: str | None = None, source_platform: str | None = None
    ) -> list[LicenseRecord]:
        """获取许可记录。

        Args:
            asset_id: 资产ID（可选）
            source_platform: 来源平台（可选）

        Returns:
            List[LicenseRecord]: 许可记录列表
        """
        query = "SELECT * FROM license_records WHERE 1=1"
        params = []

        if asset_id:
            query += " AND asset_id = ?"
            params.append(asset_id)

        if source_platform:
            query += " AND source_platform = ?"
            params.append(source_platform)

        query += " ORDER BY recorded_at DESC"

        rows = await self.database.fetch_all(query, *params)

        records = []
        for row in rows:
            record = LicenseRecord(
                asset_id=row["asset_id"],
                source_platform=row["source_platform"],
                project_id=row["project_id"],
                file_id=row["file_id"],
                license_type=row["license_type"],
                license_url=row["license_url"],
                attribution_required=bool(row["attribution_required"]),
                commercial_use_allowed=bool(row["commercial_use_allowed"]),
                modification_allowed=bool(row["modification_allowed"]),
                redistribution_allowed=bool(row["redistribution_allowed"]),
                recorded_at=datetime.fromisoformat(row["recorded_at"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )
            records.append(record)

        return records

    async def log_audit_event(
        self,
        event_type: str,
        resource_type: str,
        resource_id: str,
        action: str,
        result: str,
        user_id: str | None = None,
        project_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        """记录审计事件。

        Args:
            event_type: 事件类型
            resource_type: 资源类型
            resource_id: 资源ID
            action: 操作
            result: 结果
            user_id: 用户ID（可选）
            project_id: 项目ID（可选）
            details: 详细信息（可选）

        Returns:
            AuditLogEntry: 审计日志条目
        """
        return await self._log_audit_event(
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            user_id=user_id,
            project_id=project_id,
            details=details or {},
        )

    async def get_audit_logs(
        self,
        event_type: str | None = None,
        resource_type: str | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        """获取审计日志。

        Args:
            event_type: 事件类型（可选）
            resource_type: 资源类型（可选）
            user_id: 用户ID（可选）
            project_id: 项目ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            limit: 返回数量限制

        Returns:
            List[AuditLogEntry]: 审计日志列表
        """
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = await self.database.fetch_all(query, *params)

        logs = []
        for row in rows:
            log = AuditLogEntry(
                event_id=row["event_id"],
                event_type=row["event_type"],
                user_id=row["user_id"],
                project_id=row["project_id"],
                resource_type=row["resource_type"],
                resource_id=row["resource_id"],
                action=row["action"],
                result=row["result"],
                ip_address=row["ip_address"],
                user_agent=row["user_agent"],
                details=json.loads(row["details"]) if row["details"] else {},
                timestamp=datetime.fromisoformat(row["timestamp"]),
                signature=row["signature"],
            )
            logs.append(log)

        return logs

    async def store_secure_credential(
        self, credential_id: str, service_name: str, credential_data: dict[str, Any]
    ) -> SecureCredential:
        """安全存储凭证。

        Args:
            credential_id: 凭证ID
            service_name: 服务名称
            credential_data: 凭证数据

        Returns:
            SecureCredential: 安全凭证
        """
        if not self._master_key:
            raise SecurityError("主密钥未初始化")

        # 生成随机盐
        salt = os.urandom(32)

        # 使用主密钥和盐生成加密密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._master_key))

        # 加密凭证数据
        fernet = Fernet(key)
        credential_json = json.dumps(credential_data)
        encrypted_data = fernet.encrypt(credential_json.encode("utf-8"))

        credential = SecureCredential(
            credential_id=credential_id,
            service_name=service_name,
            encrypted_data=encrypted_data,
            salt=salt,
        )

        # 保存到数据库
        await self._save_secure_credential(credential)

        # 记录审计日志
        await self._log_audit_event(
            event_type="credential",
            resource_type="credential",
            resource_id=credential_id,
            action="store_credential",
            result="success",
            details={
                "service_name": service_name,
                "encrypted_size": len(encrypted_data),
            },
        )

        return credential

    async def retrieve_secure_credential(
        self, credential_id: str
    ) -> dict[str, Any] | None:
        """检索安全凭证。

        Args:
            credential_id: 凭证ID

        Returns:
            Optional[Dict[str, Any]]: 凭证数据（如果存在）
        """
        if not self._master_key:
            raise SecurityError("主密钥未初始化")

        # 从数据库获取凭证
        credential = await self._get_secure_credential(credential_id)
        if not credential:
            return None

        try:
            # 使用主密钥和盐生成解密密钥
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=credential.salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self._master_key))

            # 解密凭证数据
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(credential.encrypted_data)
            credential_data = json.loads(decrypted_data.decode("utf-8"))

            # 更新最后访问时间
            await self._update_credential_access_time(credential_id)

            # 记录审计日志
            await self._log_audit_event(
                event_type="credential",
                resource_type="credential",
                resource_id=credential_id,
                action="retrieve_credential",
                result="success",
                details={"service_name": credential.service_name},
            )

            return credential_data

        except Exception as e:
            self.logger.error("凭证解密失败", credential_id=credential_id, error=str(e))

            # 记录审计日志
            await self._log_audit_event(
                event_type="credential",
                resource_type="credential",
                resource_id=credential_id,
                action="retrieve_credential",
                result="failure",
                details={"error": str(e)},
            )

            return None

    async def delete_secure_credential(self, credential_id: str) -> bool:
        """删除安全凭证。

        Args:
            credential_id: 凭证ID

        Returns:
            bool: 是否成功删除
        """
        try:
            query = "DELETE FROM secure_credentials WHERE credential_id = ?"
            await self.database.execute(query, credential_id)

            # 记录审计日志
            await self._log_audit_event(
                event_type="credential",
                resource_type="credential",
                resource_id=credential_id,
                action="delete_credential",
                result="success",
            )

            return True

        except Exception as e:
            self.logger.error("凭证删除失败", credential_id=credential_id, error=str(e))

            # 记录审计日志
            await self._log_audit_event(
                event_type="credential",
                resource_type="credential",
                resource_id=credential_id,
                action="delete_credential",
                result="failure",
                details={"error": str(e)},
            )

            return False

    # 私有方法

    async def _initialize_master_key(self, master_password: str | None = None) -> None:
        """初始化主密钥。"""
        if master_password:
            # 使用用户提供的密码生成主密钥
            self._master_key = hashlib.pbkdf2_hmac(
                "sha256",
                master_password.encode("utf-8"),
                b"transhub_salt",  # 固定盐值
                100000,
            )
        else:
            # 使用OS安全存储或生成随机密钥
            self._master_key = await self._get_or_create_os_key()

    async def _get_or_create_os_key(self) -> bytes:
        """从OS安全存储获取或创建密钥。"""
        system = platform.system()

        if system == "Windows":
            return await self._get_or_create_windows_key()
        elif system == "Darwin":
            return await self._get_or_create_macos_key()
        elif system == "Linux":
            return await self._get_or_create_linux_key()
        else:
            # 回退到文件存储（不推荐）
            return await self._get_or_create_file_key()

    async def _get_or_create_windows_key(self) -> bytes:
        """Windows DPAPI密钥管理。"""
        try:
            import win32crypt

            key_file = Path.home() / ".transhub" / "master.key"

            if key_file.exists():
                # 读取并解密现有密钥
                with open(key_file, "rb") as f:
                    encrypted_key = f.read()
                return win32crypt.CryptUnprotectData(
                    encrypted_key, None, None, None, 0
                )[1]
            else:
                # 生成新密钥并加密存储
                key = os.urandom(32)
                encrypted_key = win32crypt.CryptProtectData(
                    key, None, None, None, None, 0
                )

                key_file.parent.mkdir(exist_ok=True)
                with open(key_file, "wb") as f:
                    f.write(encrypted_key)

                return key

        except ImportError:
            self.logger.warning("Windows DPAPI不可用，回退到文件存储")
            return await self._get_or_create_file_key()

    async def _get_or_create_macos_key(self) -> bytes:
        """macOS Keychain密钥管理。"""
        # 这里应该使用macOS Keychain API
        # 由于复杂性，暂时回退到文件存储
        self.logger.warning("macOS Keychain集成待实现，回退到文件存储")
        return await self._get_or_create_file_key()

    async def _get_or_create_linux_key(self) -> bytes:
        """Linux密钥管理（使用libsecret或文件存储）。"""
        # 这里应该使用libsecret或其他Linux密钥管理系统
        # 由于复杂性，暂时回退到文件存储
        self.logger.warning("Linux密钥管理集成待实现，回退到文件存储")
        return await self._get_or_create_file_key()

    async def _get_or_create_file_key(self) -> bytes:
        """文件密钥存储（回退方案）。"""
        key_file = Path.home() / ".transhub" / "master.key"

        if key_file.exists():
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = os.urandom(32)
            key_file.parent.mkdir(exist_ok=True)
            with open(key_file, "wb") as f:
                f.write(key)

            # 设置文件权限（仅所有者可读写）
            if hasattr(os, "chmod"):
                os.chmod(key_file, 0o600)

            return key

    async def _initialize_signing_keys(self) -> None:
        """初始化签名密钥对。"""
        # 检查是否已有密钥对
        private_key_data = await self._get_stored_private_key()

        if private_key_data:
            # 加载现有密钥对
            self._signing_key = serialization.load_pem_private_key(
                private_key_data, password=None
            )
            self._public_key = self._signing_key.public_key()
        else:
            # 生成新密钥对
            self._signing_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048
            )
            self._public_key = self._signing_key.public_key()

            # 存储密钥对
            await self._store_signing_keys()

    async def _calculate_file_hash(
        self, file_path: Path, algorithm: str = "sha256"
    ) -> str:
        """计算文件哈希。"""
        if algorithm == "sha256":
            hash_obj = hashlib.sha256()
        elif algorithm == "sha1":
            hash_obj = hashlib.sha1()
        elif algorithm == "md5":
            hash_obj = hashlib.md5()
        else:
            raise ValidationError(f"不支持的哈希算法: {algorithm}")

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    async def _log_audit_event(
        self,
        event_type: str,
        resource_type: str,
        resource_id: str,
        action: str,
        result: str,
        user_id: str | None = None,
        project_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        """内部审计日志记录方法。"""
        event_id = hashlib.sha256(
            f"{datetime.now().isoformat()}_{resource_type}_{resource_id}_{action}".encode()
        ).hexdigest()[:16]

        entry = AuditLogEntry(
            event_id=event_id,
            event_type=event_type,
            user_id=user_id,
            project_id=project_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details=details or {},
        )

        # 对审计日志进行签名
        if self._signing_key:
            log_data = json.dumps(
                {
                    "event_id": entry.event_id,
                    "event_type": entry.event_type,
                    "resource_type": entry.resource_type,
                    "resource_id": entry.resource_id,
                    "action": entry.action,
                    "result": entry.result,
                    "timestamp": entry.timestamp.isoformat(),
                },
                sort_keys=True,
            )

            entry.signature = await self.sign_data(log_data)

        # 保存到数据库
        await self._save_audit_log(entry)

        return entry

    async def _create_security_tables(self) -> None:
        """创建安全相关表。"""
        # 许可记录表
        await self.database.execute("""
        CREATE TABLE IF NOT EXISTS license_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            source_platform TEXT NOT NULL,
            project_id TEXT NOT NULL,
            file_id TEXT NOT NULL,
            license_type TEXT NOT NULL,
            license_url TEXT,
            attribution_required INTEGER DEFAULT 0,
            commercial_use_allowed INTEGER DEFAULT 1,
            modification_allowed INTEGER DEFAULT 1,
            redistribution_allowed INTEGER DEFAULT 1,
            recorded_at TEXT NOT NULL,
            metadata TEXT,
            UNIQUE(asset_id, source_platform)
        )
        """)

        # 审计日志表
        await self.database.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            event_type TEXT NOT NULL,
            user_id TEXT,
            project_id TEXT,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            action TEXT NOT NULL,
            result TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            details TEXT,
            timestamp TEXT NOT NULL,
            signature TEXT
        )
        """)

        # 安全凭证表
        await self.database.execute("""
        CREATE TABLE IF NOT EXISTS secure_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credential_id TEXT UNIQUE NOT NULL,
            service_name TEXT NOT NULL,
            encrypted_data BLOB NOT NULL,
            salt BLOB NOT NULL,
            created_at TEXT NOT NULL,
            last_accessed TEXT,
            metadata TEXT
        )
        """)

        # 密钥存储表
        await self.database.execute("""
        CREATE TABLE IF NOT EXISTS key_storage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_id TEXT UNIQUE NOT NULL,
            key_type TEXT NOT NULL,
            key_data BLOB NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT
        )
        """)

    async def _save_license_record(self, record: LicenseRecord) -> None:
        """保存许可记录。"""
        query = """
        INSERT OR REPLACE INTO license_records (
            asset_id, source_platform, project_id, file_id, license_type,
            license_url, attribution_required, commercial_use_allowed,
            modification_allowed, redistribution_allowed, recorded_at, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        await self.database.execute(
            query,
            record.asset_id,
            record.source_platform,
            record.project_id,
            record.file_id,
            record.license_type,
            record.license_url,
            int(record.attribution_required),
            int(record.commercial_use_allowed),
            int(record.modification_allowed),
            int(record.redistribution_allowed),
            record.recorded_at.isoformat(),
            json.dumps(record.metadata),
        )

    async def _save_audit_log(self, entry: AuditLogEntry) -> None:
        """保存审计日志。"""
        query = """
        INSERT INTO audit_logs (
            event_id, event_type, user_id, project_id, resource_type,
            resource_id, action, result, ip_address, user_agent,
            details, timestamp, signature
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        await self.database.execute(
            query,
            entry.event_id,
            entry.event_type,
            entry.user_id,
            entry.project_id,
            entry.resource_type,
            entry.resource_id,
            entry.action,
            entry.result,
            entry.ip_address,
            entry.user_agent,
            json.dumps(entry.details),
            entry.timestamp.isoformat(),
            entry.signature,
        )

    async def _save_secure_credential(self, credential: SecureCredential) -> None:
        """保存安全凭证。"""
        query = """
        INSERT OR REPLACE INTO secure_credentials (
            credential_id, service_name, encrypted_data, salt,
            created_at, metadata
        ) VALUES (?, ?, ?, ?, ?, ?)
        """

        await self.database.execute(
            query,
            credential.credential_id,
            credential.service_name,
            credential.encrypted_data,
            credential.salt,
            credential.created_at.isoformat(),
            json.dumps(credential.metadata),
        )

    async def _get_secure_credential(
        self, credential_id: str
    ) -> SecureCredential | None:
        """获取安全凭证。"""
        query = "SELECT * FROM secure_credentials WHERE credential_id = ?"
        row = await self.database.fetch_one(query, credential_id)

        if not row:
            return None

        return SecureCredential(
            credential_id=row["credential_id"],
            service_name=row["service_name"],
            encrypted_data=row["encrypted_data"],
            salt=row["salt"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"])
            if row["last_accessed"]
            else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    async def _update_credential_access_time(self, credential_id: str) -> None:
        """更新凭证访问时间。"""
        query = (
            "UPDATE secure_credentials SET last_accessed = ? WHERE credential_id = ?"
        )
        await self.database.execute(query, datetime.now().isoformat(), credential_id)

    async def _get_stored_private_key(self) -> bytes | None:
        """获取存储的私钥。"""
        query = "SELECT key_data FROM key_storage WHERE key_id = ? AND key_type = ?"
        row = await self.database.fetch_one(query, "default", "rsa_private")

        return row["key_data"] if row else None

    async def _store_signing_keys(self) -> None:
        """存储签名密钥对。"""
        # 存储私钥
        private_pem = self._signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # 存储公钥
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # 保存到数据库
        query = """
        INSERT OR REPLACE INTO key_storage (
            key_id, key_type, key_data, created_at, metadata
        ) VALUES (?, ?, ?, ?, ?)
        """

        now = datetime.now().isoformat()

        await self.database.execute(
            query, "default", "rsa_private", private_pem, now, "{}"
        )

        await self.database.execute(
            query, "default", "rsa_public", public_pem, now, "{}"
        )
