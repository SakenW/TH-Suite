"""
安全模块测试

测试安全管理器、完整性验证、权限控制等功能
"""

import asyncio
import pytest
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from ..security import (
    SecurityManager, SecurityContext, SecurityResource, AccessControl,
    SecurityLevel, ActionType, PermissionLevel, DefaultSecurityPolicy
)
from ..security.config import SecurityConfig, SecurityConfigTemplates
from ..security.integrity import (
    IntegrityVerifier, HashCalculator, ChecksumValidator, 
    FileIntegrityChecker, HashAlgorithm
)
from ..security.errors import (
    SecurityError, AuthenticationError, AuthorizationError, IntegrityError
)


class TestSecurityConfig:
    """测试安全配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = SecurityConfig()
        
        assert config.default_session_timeout == 3600
        assert config.enable_authentication is True
        assert config.verify_file_integrity is True
        assert config.default_hash_algorithm == "blake3"
    
    def test_config_templates(self):
        """测试配置模板"""
        # 开发环境配置
        dev_config = SecurityConfigTemplates.development()
        assert dev_config.security_level == "low"
        assert dev_config.require_strong_passwords is False
        assert dev_config.enforce_https is False
        
        # 生产环境配置
        prod_config = SecurityConfigTemplates.production()
        assert prod_config.security_level == "high"
        assert prod_config.require_strong_passwords is True
        assert prod_config.enforce_https is True
        
        # 高安全级别配置
        high_sec_config = SecurityConfigTemplates.high_security()
        assert high_sec_config.security_level == "critical"
        assert high_sec_config.max_login_attempts == 3
        assert high_sec_config.enable_intrusion_detection is True


class TestSecurityContext:
    """测试安全上下文"""
    
    def test_context_creation(self):
        """测试上下文创建"""
        context = SecurityContext(
            user_id="test_user",
            session_id="session_123",
            ip_address="192.168.1.100",
            user_agent="test-agent",
            permissions={"read", "write"},
            roles={"user"}
        )
        
        assert context.user_id == "test_user"
        assert context.session_id == "session_123"
        assert "read" in context.permissions
        assert "user" in context.roles
        assert not context.is_expired
        assert not context.is_admin
    
    def test_context_expiration(self):
        """测试上下文过期"""
        past_time = datetime.now() - timedelta(hours=1)
        context = SecurityContext(
            user_id="test_user",
            session_id="session_123",
            ip_address="192.168.1.100",
            user_agent="test-agent",
            expires_at=past_time
        )
        
        assert context.is_expired
    
    def test_admin_permissions(self):
        """测试管理员权限"""
        admin_context = SecurityContext(
            user_id="admin_user",
            session_id="admin_session",
            ip_address="192.168.1.100",
            user_agent="admin-agent",
            roles={"admin"}
        )
        
        assert admin_context.is_admin
        assert admin_context.has_permission("any_permission")
    
    def test_permission_checking(self):
        """测试权限检查"""
        context = SecurityContext(
            user_id="test_user",
            session_id="session_123",
            ip_address="192.168.1.100",
            user_agent="test-agent",
            permissions={"read", "write"}
        )
        
        assert context.has_permission("read")
        assert context.has_permission("write")
        assert not context.has_permission("delete")
    
    def test_role_checking(self):
        """测试角色检查"""
        context = SecurityContext(
            user_id="test_user",
            session_id="session_123",
            ip_address="192.168.1.100",
            user_agent="test-agent",
            roles={"user", "editor"}
        )
        
        assert context.has_role("user")
        assert context.has_role("editor")
        assert not context.has_role("admin")


class TestSecurityResource:
    """测试安全资源"""
    
    def test_resource_creation(self):
        """测试资源创建"""
        resource = SecurityResource(
            resource_id="file_123",
            resource_type="file",
            owner_id="user_456",
            security_level=SecurityLevel.HIGH,
            required_permissions={"file:read", "file:write"},
            allowed_roles={"editor", "admin"}
        )
        
        assert resource.resource_id == "file_123"
        assert resource.resource_type == "file"
        assert resource.owner_id == "user_456"
        assert resource.security_level == SecurityLevel.HIGH
    
    def test_resource_permission_check(self):
        """测试资源权限检查"""
        resource = SecurityResource(
            resource_id="test_resource",
            resource_type="file",
            owner_id="owner",
            required_permissions={"file:read", "file:write"}
        )
        
        assert resource.requires_permission("file:read")
        assert resource.requires_permission("file:write")
        assert not resource.requires_permission("file:delete")
    
    def test_resource_role_check(self):
        """测试资源角色检查"""
        resource = SecurityResource(
            resource_id="test_resource",
            resource_type="file",
            owner_id="owner",
            allowed_roles={"editor", "admin"}
        )
        
        assert resource.allows_role("editor")
        assert resource.allows_role("admin")
        assert not resource.allows_role("viewer")
        
        # 空角色列表表示允许所有角色
        open_resource = SecurityResource(
            resource_id="open_resource",
            resource_type="file",
            owner_id="owner"
        )
        assert open_resource.allows_role("anyone")


class TestDefaultSecurityPolicy:
    """测试默认安全策略"""
    
    @pytest.mark.asyncio
    async def test_expired_session(self):
        """测试过期会话"""
        policy = DefaultSecurityPolicy()
        
        expired_context = SecurityContext(
            user_id="test_user",
            session_id="session_123",
            ip_address="192.168.1.100",
            user_agent="test-agent",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        
        resource = SecurityResource(
            resource_id="test_resource",
            resource_type="file",
            owner_id="other_user"
        )
        
        result = await policy.evaluate(expired_context, resource, ActionType.READ)
        assert not result
    
    @pytest.mark.asyncio
    async def test_admin_access(self):
        """测试管理员访问"""
        policy = DefaultSecurityPolicy()
        
        admin_context = SecurityContext(
            user_id="admin_user",
            session_id="admin_session",
            ip_address="192.168.1.100",
            user_agent="admin-agent",
            roles={"admin"}
        )
        
        resource = SecurityResource(
            resource_id="test_resource",
            resource_type="file",
            owner_id="other_user"
        )
        
        result = await policy.evaluate(admin_context, resource, ActionType.DELETE)
        assert result
    
    @pytest.mark.asyncio
    async def test_owner_access(self):
        """测试所有者访问"""
        policy = DefaultSecurityPolicy()
        
        context = SecurityContext(
            user_id="owner_user",
            session_id="session_123",
            ip_address="192.168.1.100",
            user_agent="test-agent"
        )
        
        resource = SecurityResource(
            resource_id="test_resource",
            resource_type="file",
            owner_id="owner_user"
        )
        
        result = await policy.evaluate(context, resource, ActionType.WRITE)
        assert result
    
    @pytest.mark.asyncio
    async def test_role_based_access(self):
        """测试基于角色的访问"""
        policy = DefaultSecurityPolicy()
        
        context = SecurityContext(
            user_id="editor_user",
            session_id="session_123",
            ip_address="192.168.1.100",
            user_agent="test-agent",
            roles={"editor"}
        )
        
        resource = SecurityResource(
            resource_id="test_resource",
            resource_type="file",
            owner_id="other_user",
            allowed_roles={"editor", "admin"}
        )
        
        result = await policy.evaluate(context, resource, ActionType.READ)
        assert result
        
        # 角色不匹配
        viewer_context = SecurityContext(
            user_id="viewer_user",
            session_id="session_456",
            ip_address="192.168.1.100",
            user_agent="test-agent",
            roles={"viewer"}
        )
        
        result = await policy.evaluate(viewer_context, resource, ActionType.READ)
        assert not result
    
    @pytest.mark.asyncio
    async def test_permission_based_access(self):
        """测试基于权限的访问"""
        policy = DefaultSecurityPolicy()
        
        context = SecurityContext(
            user_id="test_user",
            session_id="session_123",
            ip_address="192.168.1.100",
            user_agent="test-agent",
            permissions={"file:read"}
        )
        
        resource = SecurityResource(
            resource_id="test_resource",
            resource_type="file",
            owner_id="other_user",
            required_permissions={"file:read"}
        )
        
        result = await policy.evaluate(context, resource, ActionType.READ)
        assert result
        
        # 权限不足
        result = await policy.evaluate(context, resource, ActionType.WRITE)
        assert not result


@pytest.fixture
def temp_file():
    """创建临时文件"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        test_data = b"Hello, Security Test! " * 50
        f.write(test_data)
        temp_path = Path(f.name)
    
    yield temp_path, test_data
    
    # 清理
    if temp_path.exists():
        temp_path.unlink()


class TestHashCalculator:
    """测试哈希计算器"""
    
    @pytest.mark.asyncio
    async def test_data_hash_calculation(self):
        """测试数据哈希计算"""
        calculator = HashCalculator(HashAlgorithm.BLAKE3)
        test_data = b"Hello, World!"
        
        hash_value = await calculator.calculate_data_hash(test_data)
        
        assert isinstance(hash_value, str)
        assert len(hash_value) > 0
        
        # 相同数据应该产生相同哈希
        hash_value2 = await calculator.calculate_data_hash(test_data)
        assert hash_value == hash_value2
    
    @pytest.mark.asyncio
    async def test_file_hash_calculation(self, temp_file):
        """测试文件哈希计算"""
        temp_path, test_data = temp_file
        calculator = HashCalculator(HashAlgorithm.BLAKE3)
        
        hash_value = await calculator.calculate_file_hash(temp_path)
        
        assert isinstance(hash_value, str)
        assert len(hash_value) > 0
    
    @pytest.mark.asyncio
    async def test_nonexistent_file_hash(self):
        """测试不存在文件的哈希计算"""
        calculator = HashCalculator(HashAlgorithm.BLAKE3)
        nonexistent_path = Path("/nonexistent/file.txt")
        
        with pytest.raises(IntegrityError, match="文件不存在"):
            await calculator.calculate_file_hash(nonexistent_path)
    
    def test_unsupported_algorithm(self):
        """测试不支持的算法"""
        with pytest.raises(IntegrityError, match="不支持的哈希算法"):
            HashCalculator("unsupported_algorithm")
    
    @pytest.mark.asyncio
    async def test_stream_hash_calculation(self):
        """测试流哈希计算"""
        calculator = HashCalculator(HashAlgorithm.BLAKE3)
        
        async def test_stream():
            yield b"Hello, "
            yield b"World!"
        
        hash_value = await calculator.calculate_stream_hash(test_stream())
        
        assert isinstance(hash_value, str)
        assert len(hash_value) > 0
    
    @pytest.mark.asyncio
    async def test_incremental_hash(self):
        """测试增量哈希"""
        calculator = HashCalculator(HashAlgorithm.BLAKE3)
        initial_data = b"Initial data "
        
        async def additional_chunks():
            yield b"chunk 1 "
            yield b"chunk 2"
        
        hash_value = await calculator.calculate_incremental_hash(
            initial_data, additional_chunks()
        )
        
        assert isinstance(hash_value, str)
        assert len(hash_value) > 0


class TestChecksumValidator:
    """测试校验和验证器"""
    
    @pytest.fixture
    def validator(self):
        config = SecurityConfig()
        return ChecksumValidator(config)
    
    @pytest.mark.asyncio
    async def test_data_validation(self, validator):
        """测试数据验证"""
        test_data = b"Hello, World!"
        
        # 计算正确的哈希
        calculator = HashCalculator(HashAlgorithm.BLAKE3)
        expected_hash = await calculator.calculate_data_hash(test_data)
        
        # 验证应该通过
        is_valid = await validator.validate_data(test_data, expected_hash)
        assert is_valid
        
        # 错误的哈希应该失败
        wrong_hash = "wrong_hash_value"
        is_valid = await validator.validate_data(test_data, wrong_hash)
        assert not is_valid
    
    @pytest.mark.asyncio
    async def test_file_validation(self, validator, temp_file):
        """测试文件验证"""
        temp_path, test_data = temp_file
        
        # 计算正确的哈希
        calculator = HashCalculator(HashAlgorithm.BLAKE3)
        expected_hash = await calculator.calculate_file_hash(temp_path)
        
        # 验证应该通过
        is_valid = await validator.validate_file(temp_path, expected_hash)
        assert is_valid
        
        # 错误的哈希应该失败
        wrong_hash = "wrong_hash_value"
        is_valid = await validator.validate_file(temp_path, wrong_hash)
        assert not is_valid
    
    @pytest.mark.asyncio
    async def test_multiple_files_validation(self, validator, temp_file):
        """测试多文件验证"""
        temp_path, test_data = temp_file
        
        # 创建另一个临时文件
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"Another test file")
            temp_path2 = Path(f.name)
        
        try:
            # 计算哈希
            calculator = HashCalculator(HashAlgorithm.BLAKE3)
            hash1 = await calculator.calculate_file_hash(temp_path)
            hash2 = await calculator.calculate_file_hash(temp_path2)
            
            file_hashes = {
                temp_path: hash1,
                temp_path2: hash2
            }
            
            results = await validator.validate_multiple_files(file_hashes)
            
            assert len(results) == 2
            assert results[temp_path] is True
            assert results[temp_path2] is True
            
        finally:
            if temp_path2.exists():
                temp_path2.unlink()


class TestFileIntegrityChecker:
    """测试文件完整性检查器"""
    
    @pytest.fixture
    def integrity_checker(self):
        config = SecurityConfig()
        return FileIntegrityChecker(config)
    
    @pytest.mark.asyncio
    async def test_create_manifest(self, integrity_checker, temp_file):
        """测试创建清单"""
        temp_path, test_data = temp_file
        temp_dir = temp_path.parent
        
        manifest = await integrity_checker.create_manifest(temp_dir)
        
        assert isinstance(manifest, dict)
        assert len(manifest) > 0
        
        # 检查是否包含我们的测试文件
        relative_path = temp_path.relative_to(temp_dir)
        assert str(relative_path) in manifest
    
    @pytest.mark.asyncio
    async def test_verify_manifest(self, integrity_checker, temp_file):
        """测试验证清单"""
        temp_path, test_data = temp_file
        temp_dir = temp_path.parent
        
        # 创建清单
        manifest = await integrity_checker.create_manifest(temp_dir)
        
        # 验证清单
        results = await integrity_checker.verify_manifest(temp_dir, manifest=manifest)
        
        assert isinstance(results, dict)
        
        # 我们的测试文件应该验证通过
        relative_path = str(temp_path.relative_to(temp_dir))
        if relative_path in results:
            assert results[relative_path] is True


class TestAccessControl:
    """测试访问控制"""
    
    @pytest.fixture
    def access_control(self):
        config = SecurityConfig()
        return AccessControl(config)
    
    @pytest.mark.asyncio
    async def test_check_access_with_policy(self, access_control):
        """测试带策略的访问检查"""
        # 添加默认策略
        access_control.add_policy(DefaultSecurityPolicy())
        
        # 创建上下文和资源
        context = SecurityContext(
            user_id="test_user",
            session_id="session_123",
            ip_address="192.168.1.100",
            user_agent="test-agent",
            roles={"admin"}
        )
        
        resource = SecurityResource(
            resource_id="test_resource",
            resource_type="file",
            owner_id="other_user"
        )
        
        # 管理员应该有访问权限
        has_access = await access_control.check_access(
            context, resource, ActionType.READ
        )
        assert has_access
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """测试速率限制"""
        config = SecurityConfig()
        config.enable_rate_limiting = True
        config.rate_limit_requests = 2
        config.rate_limit_window = 1  # 1秒窗口
        
        access_control = AccessControl(config)
        
        context = SecurityContext(
            user_id="test_user",
            session_id="session_123",
            ip_address="192.168.1.100",
            user_agent="test-agent"
        )
        
        # 前两次请求应该通过
        assert await access_control._check_rate_limit(context)
        assert await access_control._check_rate_limit(context)
        
        # 第三次请求应该被限制
        assert not await access_control._check_rate_limit(context)


class TestSecurityManager:
    """测试安全管理器"""
    
    @pytest.fixture
    def security_manager(self):
        config = SecurityConfig()
        config.session_cleanup_interval = 0  # 禁用自动清理
        return SecurityManager(config)
    
    @pytest.mark.asyncio
    async def test_create_session(self, security_manager):
        """测试创建会话"""
        context = await security_manager.create_session(
            user_id="test_user",
            ip_address="192.168.1.100",
            user_agent="test-agent",
            permissions={"read", "write"},
            roles={"user"}
        )
        
        assert context.user_id == "test_user"
        assert context.session_id is not None
        assert "read" in context.permissions
        assert "user" in context.roles
    
    def test_get_session(self, security_manager):
        """测试获取会话"""
        # 这个测试需要先创建会话
        async def create_and_test():
            context = await security_manager.create_session(
                user_id="test_user",
                ip_address="192.168.1.100",
                user_agent="test-agent"
            )
            
            # 获取会话
            retrieved = security_manager.get_session(context.session_id)
            assert retrieved is not None
            assert retrieved.user_id == "test_user"
            
            # 不存在的会话
            nonexistent = security_manager.get_session("nonexistent_session")
            assert nonexistent is None
        
        asyncio.get_event_loop().run_until_complete(create_and_test())
    
    @pytest.mark.asyncio
    async def test_revoke_session(self, security_manager):
        """测试撤销会话"""
        context = await security_manager.create_session(
            user_id="test_user",
            ip_address="192.168.1.100",
            user_agent="test-agent"
        )
        
        # 撤销会话
        revoked = await security_manager.revoke_session(context.session_id)
        assert revoked
        
        # 会话应该不再存在
        retrieved = security_manager.get_session(context.session_id)
        assert retrieved is None
    
    def test_register_resource(self, security_manager):
        """测试注册资源"""
        resource = security_manager.register_resource(
            resource_id="test_file",
            resource_type="file",
            owner_id="test_user",
            security_level=SecurityLevel.HIGH
        )
        
        assert resource.resource_id == "test_file"
        assert resource.resource_type == "file"
        assert resource.security_level == SecurityLevel.HIGH
        
        # 获取资源
        retrieved = security_manager.get_resource("test_file")
        assert retrieved is not None
        assert retrieved.resource_id == "test_file"
    
    @pytest.mark.asyncio
    async def test_check_permission(self, security_manager):
        """测试检查权限"""
        # 创建会话
        context = await security_manager.create_session(
            user_id="owner_user",
            ip_address="192.168.1.100",
            user_agent="test-agent"
        )
        
        # 注册资源
        security_manager.register_resource(
            resource_id="test_file",
            resource_type="file",
            owner_id="owner_user"
        )
        
        # 检查权限（所有者应该有权限）
        has_permission = await security_manager.check_permission(
            context.session_id, "test_file", ActionType.READ
        )
        assert has_permission
    
    @pytest.mark.asyncio
    async def test_require_permission(self, security_manager):
        """测试要求权限"""
        # 创建会话
        context = await security_manager.create_session(
            user_id="test_user",
            ip_address="192.168.1.100",
            user_agent="test-agent"
        )
        
        # 注册资源（不同所有者）
        security_manager.register_resource(
            resource_id="restricted_file",
            resource_type="file",
            owner_id="other_user"
        )
        
        # 要求权限应该抛出异常
        with pytest.raises(AuthorizationError):
            await security_manager.require_permission(
                context.session_id, "restricted_file", ActionType.WRITE
            )
    
    def test_security_stats(self, security_manager):
        """测试安全统计"""
        stats = security_manager.get_security_stats()
        
        assert 'active_sessions' in stats
        assert 'registered_resources' in stats
        assert 'security_policies' in stats
        assert isinstance(stats['active_sessions'], int)


@pytest.mark.asyncio
async def test_integration_security_workflow(temp_file):
    """集成测试：完整的安全工作流程"""
    temp_path, test_data = temp_file
    
    # 创建安全配置
    config = SecurityConfig(
        verify_file_integrity=True,
        enable_rate_limiting=True,
        rate_limit_requests=10
    )
    
    # 创建安全管理器
    security_manager = SecurityManager(config)
    
    # 创建完整性验证器
    integrity_verifier = IntegrityVerifier(config)
    
    # 1. 创建用户会话
    user_context = await security_manager.create_session(
        user_id="test_user",
        ip_address="192.168.1.100",
        user_agent="test-client",
        permissions={"file:read", "file:write"},
        roles={"user"}
    )
    
    # 2. 计算文件哈希
    calculator = HashCalculator(HashAlgorithm.BLAKE3)
    file_hash = await calculator.calculate_file_hash(temp_path)
    
    # 3. 注册文件资源
    file_resource = security_manager.register_resource(
        resource_id=str(temp_path),
        resource_type="file",
        owner_id="test_user",
        security_level=SecurityLevel.MEDIUM,
        required_permissions={"file:read"},
        path=str(temp_path)
    )
    file_resource.metadata['hash'] = file_hash
    
    # 4. 验证文件完整性
    integrity_valid = await integrity_verifier.verify_file_integrity(
        temp_path, file_hash
    )
    assert integrity_valid
    
    # 5. 检查访问权限
    can_read = await security_manager.check_permission(
        user_context.session_id, str(temp_path), ActionType.READ
    )
    assert can_read
    
    can_write = await security_manager.check_permission(
        user_context.session_id, str(temp_path), ActionType.WRITE
    )
    assert can_write  # 用户是所有者
    
    # 6. 创建另一个用户测试权限
    other_context = await security_manager.create_session(
        user_id="other_user",
        ip_address="192.168.1.101",
        user_agent="other-client",
        permissions={"file:read"},
        roles={"viewer"}
    )
    
    # 其他用户应该可以读取但不能写入
    other_can_read = await security_manager.check_permission(
        other_context.session_id, str(temp_path), ActionType.READ
    )
    assert other_can_read  # 默认策略允许读取
    
    other_can_write = await security_manager.check_permission(
        other_context.session_id, str(temp_path), ActionType.WRITE
    )
    assert not other_can_write  # 不是所有者且没有写权限
    
    # 7. 创建目录完整性报告
    temp_dir = temp_path.parent
    integrity_report = await integrity_verifier.create_integrity_report(temp_dir)
    
    assert integrity_report['total_files'] >= 1
    assert str(temp_path.name) in str(integrity_report['manifest'])
    
    # 8. 验证报告
    verification_results = await integrity_verifier.verify_integrity_report(
        integrity_report
    )
    
    assert isinstance(verification_results, dict)
    
    # 9. 获取安全统计
    security_stats = security_manager.get_security_stats()
    assert security_stats['active_sessions'] >= 2
    assert security_stats['registered_resources'] >= 1


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])