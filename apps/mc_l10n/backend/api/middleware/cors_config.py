"""
CORS跨域配置

配置API的跨域访问策略
"""

import os

from fastapi.middleware.cors import CORSMiddleware


class CORSConfig:
    """CORS配置管理"""

    def __init__(self):
        # 从环境变量获取配置，开发环境和生产环境使用不同的配置
        self.environment = os.getenv("ENVIRONMENT", "production").lower()

        # 允许的源地址
        self.allowed_origins = self._get_allowed_origins()

        # 允许的方法
        self.allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]

        # 允许的请求头
        self.allowed_headers = [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Request-ID",
            "X-API-Key",
            "Cache-Control",
            "Pragma",
        ]

        # 暴露给前端的响应头
        self.exposed_headers = [
            "X-Request-ID",
            "X-Total-Count",
            "X-Page-Count",
            "Content-Disposition",
        ]

        # 是否允许凭据（cookies等）
        self.allow_credentials = True

        # 预检请求的缓存时间（秒）
        self.max_age = 3600

    def _get_allowed_origins(self) -> list[str]:
        """获取允许的源地址列表"""
        # 从环境变量读取配置
        origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")

        if origins_env:
            # 环境变量中配置了具体的源地址
            return [
                origin.strip() for origin in origins_env.split(",") if origin.strip()
            ]

        # 根据环境返回默认配置
        if self.environment in ["development", "dev", "local"]:
            # 开发环境：允许本地开发服务器
            return [
                "http://localhost:3000",  # React开发服务器
                "http://localhost:5173",  # Vite开发服务器
                "http://localhost:8080",  # 其他开发服务器
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:8080",
                "tauri://localhost",  # Tauri应用
                "http://tauri.localhost",  # Tauri开发环境
                "https://tauri.localhost",
            ]
        elif self.environment == "testing":
            # 测试环境：允许测试相关的源
            return ["http://localhost:*", "http://127.0.0.1:*", "tauri://localhost"]
        else:
            # 生产环境：只允许特定的生产域名
            return [
                "tauri://localhost",  # Tauri应用（必须）
                # 这里可以添加生产环境的web域名
                # "https://your-production-domain.com",
            ]

    def apply_to_app(self, app):
        """将CORS配置应用到FastAPI应用"""
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.allowed_origins,
            allow_credentials=self.allow_credentials,
            allow_methods=self.allowed_methods,
            allow_headers=self.allowed_headers,
            expose_headers=self.exposed_headers,
            max_age=self.max_age,
        )

    def get_config_summary(self) -> dict:
        """获取CORS配置摘要"""
        return {
            "environment": self.environment,
            "allowed_origins": self.allowed_origins,
            "allowed_methods": self.allowed_methods,
            "allowed_headers": self.allowed_headers,
            "exposed_headers": self.exposed_headers,
            "allow_credentials": self.allow_credentials,
            "max_age": self.max_age,
        }


# 创建全局CORS配置实例
cors_config = CORSConfig()


def setup_cors(app):
    """设置CORS中间件的便捷函数"""
    cors_config.apply_to_app(app)

    # 记录CORS配置
    from packages.core.framework.logging import get_logger

    logger = get_logger(__name__)

    config_summary = cors_config.get_config_summary()
    logger.info(
        f"CORS配置已应用: 环境={config_summary['environment']}, 允许源={len(config_summary['allowed_origins'])}个"
    )

    # 在开发环境中显示详细配置
    if cors_config.environment in ["development", "dev", "local"]:
        logger.debug(f"CORS详细配置: {config_summary}")


def validate_cors_origin(origin: str) -> bool:
    """验证请求源是否被允许"""
    if not origin:
        return False

    allowed_origins = cors_config.allowed_origins

    # 精确匹配
    if origin in allowed_origins:
        return True

    # 通配符匹配（仅在开发/测试环境）
    if cors_config.environment in ["development", "dev", "local", "testing"]:
        import re

        for allowed_origin in allowed_origins:
            if "*" in allowed_origin:
                # 将通配符转换为正则表达式
                pattern = allowed_origin.replace("*", ".*")
                if re.match(f"^{pattern}$", origin):
                    return True

    return False


def get_cors_headers_for_origin(origin: str) -> dict:
    """为指定源获取CORS响应头"""
    headers = {}

    if validate_cors_origin(origin):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = str(
            cors_config.allow_credentials
        ).lower()
        headers["Access-Control-Allow-Methods"] = ", ".join(cors_config.allowed_methods)
        headers["Access-Control-Allow-Headers"] = ", ".join(cors_config.allowed_headers)
        headers["Access-Control-Expose-Headers"] = ", ".join(
            cors_config.exposed_headers
        )
        headers["Access-Control-Max-Age"] = str(cors_config.max_age)

    return headers


def is_cors_preflight_request(request) -> bool:
    """检查是否为CORS预检请求"""
    return (
        request.method == "OPTIONS"
        and request.headers.get("access-control-request-method") is not None
    )
