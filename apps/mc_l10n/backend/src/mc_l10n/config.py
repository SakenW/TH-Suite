# apps/mc-l10n/backend/src/mc_l10n/config.py
"""
MC L10n 应用配置

基于TH-Suite核心配置系统的应用特定配置
"""

from pathlib import Path

from packages.core import THSuiteConfig


class MCL10nConfig(THSuiteConfig):
    """MC L10n 特定配置"""

    # 应用特定配置
    app_name: str = "MC L10n"

    # 端口配置
    server_host: str = "127.0.0.1"
    server_port: int = 8000

    # Minecraft特定配置
    minecraft_versions: list[str] = ["1.20.1", "1.19.4", "1.18.2"]
    supported_loaders: list[str] = ["forge", "fabric", "quilt", "neoforge"]

    # 扫描配置
    max_mod_file_size: int = 500 * 1024 * 1024  # 500MB
    language_file_patterns: list[str] = [
        "assets/*/lang/*.json",
        "assets/*/lang/*.lang",
        "data/*/lang/*.json",
    ]

    # 构建配置
    build_output_dir: Path = Path("./build")
    temp_extract_dir: Path = Path("./temp")


def get_mc_l10n_config(env_file: str | None = None, **overrides) -> MCL10nConfig:
    """获取MC L10n配置实例"""
    config_overrides = {"app_name": "MC L10n", **overrides}

    if env_file:
        config = MCL10nConfig(_env_file=env_file, **config_overrides)
    else:
        config = MCL10nConfig(**config_overrides)

    return config


# 全局配置实例
_mc_l10n_config: MCL10nConfig | None = None


def get_config() -> MCL10nConfig:
    """获取全局MC L10n配置"""
    global _mc_l10n_config
    if _mc_l10n_config is None:
        _mc_l10n_config = get_mc_l10n_config()
    return _mc_l10n_config
