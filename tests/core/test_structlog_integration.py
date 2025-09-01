"""
测试 Trans-Hub 日志系统集成

验证 structlog + rich 日志系统是否正确集成到 Core Platform 中
"""

from unittest.mock import patch

import pytest

from packages.core.framework.logging import StructLogFactory, StructLogLogger
from packages.core.framework.logging.logging_config import setup_logging
from packages.core.platform import CorePlatform


class TestStructLogIntegration:
    """测试 StructLog 集成"""

    def test_structlog_factory_initialization(self):
        """测试 StructLog 工厂初始化"""
        # 重置工厂状态
        StructLogFactory.reset()

        # 测试初始化
        StructLogFactory.initialize_logging(
            log_level="DEBUG", log_format="console", service="test-service"
        )

        # 验证可以获取日志器
        logger = StructLogFactory.get_logger("test.logger")
        assert isinstance(logger, StructLogLogger)
        assert logger.name == "test.logger"

    def test_structlog_logger_methods(self):
        """测试 StructLog 日志器方法"""
        # 重置工厂状态
        StructLogFactory.reset()
        StructLogFactory.initialize_logging(
            log_format="json"
        )  # 使用 JSON 格式避免 rich 依赖问题

        logger = StructLogFactory.get_logger("test")

        # 测试各种日志级别方法不会抛出异常
        logger.debug("调试消息", key="value")
        logger.info("信息消息", user_id=123)
        logger.warning("警告消息", count=5)
        logger.error("错误消息", error_code="E001")
        logger.critical("严重错误", system="auth")

        # 测试带异常的日志
        try:
            raise ValueError("测试异常")
        except ValueError as e:
            logger.error("捕获异常", exception=e)

    def test_structlog_logger_bind(self):
        """测试 StructLog 日志器上下文绑定"""
        StructLogFactory.reset()
        StructLogFactory.initialize_logging(log_format="json")

        logger = StructLogFactory.get_logger("test")

        # 测试绑定上下文
        bound_logger = logger.bind(user_id=123, session_id="abc")
        assert isinstance(bound_logger, StructLogLogger)

        # 测试绑定后的日志器工作正常
        bound_logger.info("用户操作", action="login")

    @pytest.mark.asyncio
    async def test_core_platform_with_structlog(self):
        """测试 Core Platform 使用 StructLog"""
        # 创建平台实例
        platform = CorePlatform("test-app")

        # 验证日志器类型
        assert isinstance(platform.logger, StructLogLogger)
        assert platform.logger.name == "core_platform"

        try:
            # 初始化平台
            await platform.initialize()

            # 测试日志记录
            platform.logger.info("平台初始化测试", test_mode=True)
            platform.logger.debug("调试信息", component="test")

            # 测试绑定上下文的日志器
            contextual_logger = platform.logger.bind(operation="test")
            contextual_logger.info("上下文日志测试", status="success")

        finally:
            # 清理
            await platform.shutdown()

    def test_logging_config_validation(self):
        """测试日志配置验证"""
        # 测试无效的日志级别
        with pytest.raises(ValueError, match="Invalid log level"):
            setup_logging(log_level="INVALID")

        # 测试无效的日志格式
        with pytest.raises(ValueError, match="Invalid format type"):
            setup_logging(log_format="invalid")

        # 测试无效的面板内边距
        with pytest.raises(ValueError, match="panel_padding must be a tuple"):
            setup_logging(panel_padding=(1,))  # 只有一个元素

        with pytest.raises(ValueError, match="panel_padding must be a tuple"):
            setup_logging(panel_padding=(1, -1))  # 负数

    @patch("packages.core.framework.logging.logging_config.Console", None)
    def test_missing_rich_dependency(self):
        """测试缺少 Rich 依赖时的处理"""
        with pytest.raises(
            ImportError, match="要使用 'console' 日志格式，请先安装 rich"
        ):
            setup_logging(log_format="console")

        # JSON 格式不应该受影响
        setup_logging(log_format="json")

    def test_logging_levels_conversion(self):
        """测试日志级别转换"""
        from packages.core.framework.logging.logger import LogLevel as FrameworkLogLevel

        StructLogFactory.reset()
        StructLogFactory.initialize_logging(log_format="json")

        logger = StructLogFactory.get_logger("test")

        # 测试各种级别转换
        logger.log(FrameworkLogLevel.TRACE, "TRACE 消息")
        logger.log(FrameworkLogLevel.DEBUG, "DEBUG 消息")
        logger.log(FrameworkLogLevel.INFO, "INFO 消息")
        logger.log(FrameworkLogLevel.WARNING, "WARNING 消息")
        logger.log(FrameworkLogLevel.ERROR, "ERROR 消息")
        logger.log(FrameworkLogLevel.CRITICAL, "CRITICAL 消息")

    def test_noisy_loggers_silencing(self):
        """测试噪声日志器静音功能"""
        import logging

        # 设置日志系统
        setup_logging(log_level="DEBUG", log_format="json", silence_noisy_libs=True)

        # 验证噪声日志器级别被设置为 WARNING
        noisy_logger = logging.getLogger("urllib3")
        assert noisy_logger.level >= logging.WARNING

        httpcore_logger = logging.getLogger("httpcore")
        assert httpcore_logger.level >= logging.WARNING
