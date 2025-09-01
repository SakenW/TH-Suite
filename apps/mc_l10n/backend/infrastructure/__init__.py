"""
MC工具基础设施层初始化

注册所有扫描器、解析器和基础设施组件
"""

from packages.core.framework.logging import get_logger

# 导入解析器
from .parsers.base_parser import parser_registry
from .parsers.json_parser import JsonParser
from .parsers.properties_parser import PropertiesParser

# 导入扫描器
from .scanners.base_scanner import scanner_registry
from .scanners.folder_scanner import FolderScanner
from .scanners.jar_scanner import JarScanner

logger = get_logger(__name__)


def initialize_infrastructure():
    """初始化基础设施组件"""
    logger.info("开始初始化MC工具基础设施组件...")

    try:
        # 注册扫描器
        _register_scanners()

        # 注册解析器
        _register_parsers()

        # 验证注册结果
        _validate_registrations()

        logger.info("MC工具基础设施组件初始化完成")

    except Exception as e:
        logger.error(f"基础设施组件初始化失败: {str(e)}")
        raise


def _register_scanners():
    """注册所有扫描器"""
    logger.info("注册扫描器...")

    # JAR文件扫描器
    jar_scanner = JarScanner()
    scanner_registry.register(jar_scanner)

    # 文件夹扫描器
    folder_scanner = FolderScanner()
    scanner_registry.register(folder_scanner)

    logger.info(f"已注册 {len(scanner_registry.get_registered_scanners())} 个扫描器")


def _register_parsers():
    """注册所有解析器"""
    logger.info("注册解析器...")

    # JSON解析器
    json_parser = JsonParser()
    parser_registry.register(json_parser)

    # Properties解析器
    properties_parser = PropertiesParser()
    parser_registry.register(properties_parser)

    supported_types = parser_registry.get_supported_file_types()
    logger.info(f"已注册解析器，支持文件类型: {[ft.value for ft in supported_types]}")


def _validate_registrations():
    """验证注册结果"""
    logger.info("验证组件注册...")

    # 验证扫描器
    registered_scanners = scanner_registry.get_registered_scanners()
    if not registered_scanners:
        raise RuntimeError("没有注册任何扫描器")

    # 验证解析器
    supported_types = parser_registry.get_supported_file_types()
    if not supported_types:
        raise RuntimeError("没有注册任何解析器")

    # 确保覆盖了主要文件类型
    from domain.models.enums import FileType

    required_types = {FileType.JSON, FileType.PROPERTIES}
    missing_types = required_types - supported_types

    if missing_types:
        logger.warning(
            f"缺少以下文件类型的解析器: {[ft.value for ft in missing_types]}"
        )

    logger.info("组件注册验证通过")


def get_scanner_registry():
    """获取扫描器注册表"""
    return scanner_registry


def get_parser_registry():
    """获取解析器注册表"""
    return parser_registry


# 导出主要组件
__all__ = [
    "initialize_infrastructure",
    "get_scanner_registry",
    "get_parser_registry",
    "scanner_registry",
    "parser_registry",
]
