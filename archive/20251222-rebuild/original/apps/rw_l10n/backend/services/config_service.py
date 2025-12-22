from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from packages.core.logging import get_logger
from packages.parsers.json_parser import JSONParser
from packages.parsers.toml_parser import TOMLParser
from packages.protocol.schemas import AppConfig, ConfigBackup, GameConfig, ModLoadOrder

logger = get_logger(__name__)


class ConfigService:
    """配置管理服务"""

    def __init__(self):
        self.toml_parser = TOMLParser()
        self.json_parser = JSONParser()
        self.config_cache: dict[str, Any] = {}
        self.config_file = Path("config/app_config.toml")
        self.game_config_file = Path("config/game_config.json")
        self.backup_dir = Path("config/backups")

        # 确保配置目录存在
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def get_config(self, config_type: str = "app") -> dict[str, Any]:
        """获取配置"""
        try:
            logger.info(f"Getting config: {config_type}")

            if config_type == "app":
                return await self._load_app_config()
            elif config_type == "game":
                return await self._load_game_config()
            else:
                raise ValueError(f"Unknown config type: {config_type}")

        except Exception as e:
            logger.error(f"Failed to get config {config_type}: {e}")
            raise

    async def set_config(
        self, config_type: str, config_data: dict[str, Any], create_backup: bool = True
    ):
        """设置配置"""
        try:
            logger.info(f"Setting config: {config_type}")

            # 创建备份
            if create_backup:
                await self.create_backup(config_type)

            if config_type == "app":
                await self._save_app_config(config_data)
            elif config_type == "game":
                await self._save_game_config(config_data)
            else:
                raise ValueError(f"Unknown config type: {config_type}")

            # 更新缓存
            self.config_cache[config_type] = config_data

        except Exception as e:
            logger.error(f"Failed to set config {config_type}: {e}")
            raise

    async def update_config(
        self, config_type: str, updates: dict[str, Any], create_backup: bool = True
    ):
        """更新配置（部分更新）"""
        try:
            logger.info(f"Updating config: {config_type}")

            # 获取当前配置
            current_config = await self.get_config(config_type)

            # 合并更新
            updated_config = self._deep_merge(current_config, updates)

            # 保存更新后的配置
            await self.set_config(config_type, updated_config, create_backup)

        except Exception as e:
            logger.error(f"Failed to update config {config_type}: {e}")
            raise

    async def reset_config(self, config_type: str, create_backup: bool = True):
        """重置配置为默认值"""
        try:
            logger.info(f"Resetting config: {config_type}")

            # 创建备份
            if create_backup:
                await self.create_backup(config_type)

            # 获取默认配置
            default_config = await self._get_default_config(config_type)

            # 保存默认配置
            await self.set_config(config_type, default_config, False)

        except Exception as e:
            logger.error(f"Failed to reset config {config_type}: {e}")
            raise

    async def import_config(
        self,
        config_type: str,
        file_path: str,
        merge: bool = False,
        create_backup: bool = True,
    ):
        """导入配置"""
        try:
            logger.info(f"Importing config: {config_type} from {file_path}")

            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"Config file not found: {file_path}")

            # 根据文件扩展名选择解析器
            if file_path_obj.suffix.lower() == ".toml":
                imported_config = await self.toml_parser.parse_file(file_path)
            elif file_path_obj.suffix.lower() == ".json":
                imported_config = await self.json_parser.parse_file(file_path)
            else:
                raise ValueError(
                    f"Unsupported config file format: {file_path_obj.suffix}"
                )

            if merge:
                # 合并配置
                current_config = await self.get_config(config_type)
                final_config = self._deep_merge(current_config, imported_config)
            else:
                # 完全替换
                final_config = imported_config

            # 验证配置
            await self._validate_config(config_type, final_config)

            # 保存配置
            await self.set_config(config_type, final_config, create_backup)

        except Exception as e:
            logger.error(f"Failed to import config {config_type}: {e}")
            raise

    async def export_config(
        self, config_type: str, file_path: str, format: str = "toml"
    ) -> str:
        """导出配置"""
        try:
            logger.info(f"Exporting config: {config_type} to {file_path}")

            config_data = await self.get_config(config_type)

            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() == "toml":
                await self.toml_parser.write_file(str(file_path_obj), config_data)
            elif format.lower() == "json":
                await self.json_parser.write_file(str(file_path_obj), config_data)
            else:
                raise ValueError(f"Unsupported export format: {format}")

            return str(file_path_obj)

        except Exception as e:
            logger.error(f"Failed to export config {config_type}: {e}")
            raise

    async def validate_config(
        self, config_type: str, config_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """验证配置"""
        try:
            logger.info(f"Validating config: {config_type}")

            if config_data is None:
                config_data = await self.get_config(config_type)

            validation_result = {"valid": True, "errors": [], "warnings": []}

            try:
                await self._validate_config(config_type, config_data)
            except ValidationError as e:
                validation_result["valid"] = False
                validation_result["errors"] = [str(error) for error in e.errors()]
            except Exception as e:
                validation_result["valid"] = False
                validation_result["errors"] = [str(e)]

            return validation_result

        except Exception as e:
            logger.error(f"Failed to validate config {config_type}: {e}")
            raise

    async def get_config_schema(self, config_type: str) -> dict[str, Any]:
        """获取配置模式"""
        try:
            logger.info(f"Getting config schema: {config_type}")

            if config_type == "app":
                return AppConfig.model_json_schema()
            elif config_type == "game":
                return GameConfig.model_json_schema()
            else:
                raise ValueError(f"Unknown config type: {config_type}")

        except Exception as e:
            logger.error(f"Failed to get config schema {config_type}: {e}")
            raise

    async def get_game_paths(self) -> dict[str, str]:
        """获取游戏路径配置"""
        try:
            logger.info("Getting game paths")

            game_config = await self.get_config("game")
            return {
                "game_path": game_config.get("game_path", ""),
                "saves_path": game_config.get("saves_path", ""),
                "mods_path": game_config.get("mods_path", ""),
                "config_path": game_config.get("config_path", ""),
            }

        except Exception as e:
            logger.error(f"Failed to get game paths: {e}")
            raise

    async def set_game_paths(self, paths: dict[str, str]):
        """设置游戏路径配置"""
        try:
            logger.info("Setting game paths")

            # 验证路径
            for path_type, path_value in paths.items():
                if path_value and not Path(path_value).exists():
                    logger.warning(f"Path does not exist: {path_type} = {path_value}")

            # 更新配置
            await self.update_config("game", paths)

        except Exception as e:
            logger.error(f"Failed to set game paths: {e}")
            raise

    async def get_mod_load_order(self) -> ModLoadOrder:
        """获取模组加载顺序"""
        try:
            logger.info("Getting mod load order")

            game_config = await self.get_config("game")
            mod_order = game_config.get("mod_load_order", [])

            return ModLoadOrder(
                mods=mod_order,
                auto_sort=game_config.get("auto_sort_mods", False),
                last_updated=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Failed to get mod load order: {e}")
            raise

    async def set_mod_load_order(self, load_order: ModLoadOrder):
        """设置模组加载顺序"""
        try:
            logger.info("Setting mod load order")

            updates = {
                "mod_load_order": load_order.mods,
                "auto_sort_mods": load_order.auto_sort,
                "mod_order_last_updated": load_order.last_updated.isoformat(),
            }

            await self.update_config("game", updates)

        except Exception as e:
            logger.error(f"Failed to set mod load order: {e}")
            raise

    async def create_backup(
        self, config_type: str, backup_name: str | None = None
    ) -> str:
        """创建配置备份"""
        try:
            logger.info(f"Creating config backup: {config_type}")

            if backup_name is None:
                backup_name = (
                    f"{config_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )

            # 获取当前配置
            config_data = await self.get_config(config_type)

            # 创建备份文件
            backup_file = self.backup_dir / f"{backup_name}.json"
            await self.json_parser.write_file(
                str(backup_file),
                {
                    "config_type": config_type,
                    "created_time": datetime.now().isoformat(),
                    "data": config_data,
                },
            )

            return backup_name

        except Exception as e:
            logger.error(f"Failed to create config backup {config_type}: {e}")
            raise

    async def restore_backup(self, backup_name: str, create_backup: bool = True):
        """恢复配置备份"""
        try:
            logger.info(f"Restoring config backup: {backup_name}")

            backup_file = self.backup_dir / f"{backup_name}.json"
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup not found: {backup_name}")

            # 读取备份数据
            backup_data = await self.json_parser.parse_file(str(backup_file))
            config_type = backup_data["config_type"]
            config_data = backup_data["data"]

            # 恢复配置
            await self.set_config(config_type, config_data, create_backup)

        except Exception as e:
            logger.error(f"Failed to restore config backup {backup_name}: {e}")
            raise

    async def list_backups(self) -> list[ConfigBackup]:
        """列出配置备份"""
        try:
            logger.info("Listing config backups")

            backups = []
            for backup_file in self.backup_dir.glob("*.json"):
                try:
                    backup_data = await self.json_parser.parse_file(str(backup_file))
                    backup = ConfigBackup(
                        name=backup_file.stem,
                        config_type=backup_data["config_type"],
                        created_time=datetime.fromisoformat(
                            backup_data["created_time"]
                        ),
                        file_size=backup_file.stat().st_size,
                        file_path=str(backup_file),
                    )
                    backups.append(backup)
                except Exception as e:
                    logger.warning(f"Failed to read backup {backup_file}: {e}")

            # 按创建时间排序
            backups.sort(key=lambda x: x.created_time, reverse=True)

            return backups

        except Exception as e:
            logger.error(f"Failed to list config backups: {e}")
            raise

    async def delete_backup(self, backup_name: str):
        """删除配置备份"""
        try:
            logger.info(f"Deleting config backup: {backup_name}")

            backup_file = self.backup_dir / f"{backup_name}.json"
            if backup_file.exists():
                backup_file.unlink()
            else:
                raise FileNotFoundError(f"Backup not found: {backup_name}")

        except Exception as e:
            logger.error(f"Failed to delete config backup {backup_name}: {e}")
            raise

    async def _load_app_config(self) -> dict[str, Any]:
        """加载应用配置"""
        try:
            if "app" in self.config_cache:
                return self.config_cache["app"]

            if self.config_file.exists():
                config = await self.toml_parser.parse_file(str(self.config_file))
            else:
                config = await self._get_default_config("app")
                await self._save_app_config(config)

            self.config_cache["app"] = config
            return config

        except Exception as e:
            logger.error(f"Failed to load app config: {e}")
            raise

    async def _load_game_config(self) -> dict[str, Any]:
        """加载游戏配置"""
        try:
            if "game" in self.config_cache:
                return self.config_cache["game"]

            if self.game_config_file.exists():
                config = await self.json_parser.parse_file(str(self.game_config_file))
            else:
                config = await self._get_default_config("game")
                await self._save_game_config(config)

            self.config_cache["game"] = config
            return config

        except Exception as e:
            logger.error(f"Failed to load game config: {e}")
            raise

    async def _save_app_config(self, config: dict[str, Any]):
        """保存应用配置"""
        try:
            await self.toml_parser.write_file(str(self.config_file), config)

        except Exception as e:
            logger.error(f"Failed to save app config: {e}")
            raise

    async def _save_game_config(self, config: dict[str, Any]):
        """保存游戏配置"""
        try:
            await self.json_parser.write_file(str(self.game_config_file), config)

        except Exception as e:
            logger.error(f"Failed to save game config: {e}")
            raise

    async def _get_default_config(self, config_type: str) -> dict[str, Any]:
        """获取默认配置"""
        if config_type == "app":
            return {
                "app_name": "RW Studio",
                "version": "1.0.0",
                "language": "zh-CN",
                "theme": "dark",
                "auto_backup": True,
                "backup_interval": 24,
                "max_backups": 10,
                "log_level": "INFO",
                "enable_notifications": True,
                "check_updates": True,
            }
        elif config_type == "game":
            return {
                "game_path": "",
                "saves_path": "",
                "mods_path": "",
                "config_path": "",
                "auto_detect_paths": True,
                "mod_load_order": [],
                "auto_sort_mods": False,
                "enable_dev_mode": False,
                "max_memory": 4096,
                "launch_options": [],
            }
        else:
            raise ValueError(f"Unknown config type: {config_type}")

    async def _validate_config(self, config_type: str, config_data: dict[str, Any]):
        """验证配置数据"""
        try:
            if config_type == "app":
                AppConfig(**config_data)
            elif config_type == "game":
                GameConfig(**config_data)
            else:
                raise ValueError(f"Unknown config type: {config_type}")

        except Exception as e:
            logger.error(f"Config validation failed for {config_type}: {e}")
            raise

    def _deep_merge(
        self, base: dict[str, Any], updates: dict[str, Any]
    ) -> dict[str, Any]:
        """深度合并字典"""
        result = base.copy()

        for key, value in updates.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result
