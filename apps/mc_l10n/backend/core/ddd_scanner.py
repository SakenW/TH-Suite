"""
DDD扫描器模块 - 使用统一数据库的最优实现
提供目录扫描、JAR文件解析和语言文件提取功能
"""

import asyncio
import json
import logging
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .mc_database import Database, LanguageFile, ModInfo, TranslationEntry

logger = logging.getLogger(__name__)

# 全局扫描服务实例
_scanner_instance: Optional["DDDScanner"] = None


class DDDScanner:
    """DDD扫描器 - 使用统一数据库系统"""

    def __init__(self, database_path: str):
        """
        初始化扫描器

        Args:
            database_path: 数据库文件路径
        """
        self.database_path = database_path
        self.active_scans = {}
        logger.info(f"DDD扫描器已初始化，数据库路径: {database_path}")

    def _extract_version_from_filename(self, filename: str) -> str:
        """从文件名中提取版本号"""
        # 移除文件扩展名
        name = Path(filename).stem
        
        # 按优先级排序的版本号模式 - 优先匹配更具体的模式
        version_patterns = [
            # modname-mc1.20.1-1.2.3.jar (提取第二个版本号)
            r"-mc\d+(?:\.\d+)*-(\d+(?:\.\d+)*)",
            # modname-1.20.1-1.2.3.jar (提取最后一个版本号)
            r"-\d+(?:\.\d+)*-(\d+(?:\.\d+)*)",
            # modname_v1.2.3.jar
            r"[_-]v(\d+(?:\.\d+)*(?:[.-](?:alpha|beta|rc|snapshot|SNAPSHOT)\d*)?)",
            # modname-1.2.3.jar (最后匹配，避免匹配到MC版本)
            r"-(\d+(?:\.\d+)*(?:[.-](?:alpha|beta|rc|snapshot|SNAPSHOT)\d*)?)$",
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # 如果没有找到版本号，返回 "unknown"
        return "unknown"

    def _resolve_template_variables(self, template_str: str, file_path: str) -> str:
        """解析模板变量"""
        if not isinstance(template_str, str):
            return str(template_str)
            
        result = template_str
        
        # 解析 ${file.jarVersion}
        if "${file.jarVersion}" in result:
            version = self._extract_version_from_filename(file_path)
            result = result.replace("${file.jarVersion}", version)
            
        # 可以添加更多模板变量的解析
        # ${file.name}, ${file.baseName} 等
        
        return result

    async def start_scan(
        self, target_path: str, incremental: bool = True, options: dict[str, Any] = None
    ) -> dict[str, Any]:
        """
        启动扫描任务

        Args:
            target_path: 要扫描的目录路径
            incremental: 是否增量扫描
            options: 扫描选项

        Returns:
            包含scan_id的字典
        """
        try:
            # 检查路径是否存在
            if not os.path.exists(target_path):
                raise ValueError(f"路径不存在: {target_path}")

            # 创建扫描会话
            db = Database(self.database_path)
            scan_id = db.create_scan_session(
                project_path=target_path,
                scan_type="incremental" if incremental else "full",
            )

            # 初始化扫描状态
            self.active_scans[scan_id] = {
                "scan_id": scan_id,
                "target_path": target_path,
                "incremental": incremental,
                "status": "started",
                "progress": 0.0,
                "processed_files": 0,
                "total_files": 0,
                "current_file": "",
                "statistics": {
                    "total_mods": 0,
                    "total_language_files": 0,
                    "total_keys": 0,
                },
                "started_at": datetime.now().isoformat(),
                "errors": [],
                "warnings": [],
            }

            logger.info(
                f"启动扫描任务: {scan_id}, 路径: {target_path}, 增量: {incremental}"
            )

            # 启动后台扫描任务
            asyncio.create_task(self._execute_scan(scan_id))

            return {"scan_id": scan_id}

        except Exception as e:
            logger.error(f"启动扫描失败: {e}")
            raise

    async def _execute_scan(self, scan_id: str):
        """
        执行扫描任务（后台任务）
        """
        db = None
        try:
            scan_data = self.active_scans[scan_id]
            scan_data["status"] = "scanning"
            target_path = Path(scan_data["target_path"])

            # 打开数据库连接
            db = Database(self.database_path)

            # 收集所有JAR文件
            jar_files = []
            logger.info(f"开始搜索JAR文件: {target_path}")

            for root, dirs, files in os.walk(target_path):
                for file in files:
                    if file.endswith(".jar"):
                        jar_files.append(Path(root) / file)

            scan_data["total_files"] = len(jar_files)
            logger.info(f"找到 {len(jar_files)} 个JAR文件")

            # 处理每个JAR文件
            total_mods = 0
            total_language_files = 0
            total_keys = 0

            # 批次处理设置
            batch_size = 20
            start_time = datetime.now()

            for idx, jar_path in enumerate(jar_files):
                if scan_id not in self.active_scans:
                    return  # 扫描被取消

                # 计算进度和批次信息
                current_progress = ((idx + 1) / len(jar_files)) * 100
                current_batch = (idx // batch_size) + 1
                total_batches = (len(jar_files) + batch_size - 1) // batch_size
                batch_progress = (
                    ((idx % batch_size) + 1)
                    / min(batch_size, len(jar_files) - (current_batch - 1) * batch_size)
                    * 100
                )

                # 计算性能指标
                elapsed_time = (datetime.now() - start_time).total_seconds()
                files_per_second = (idx + 1) / max(elapsed_time, 1)
                estimated_remaining_time = (len(jar_files) - idx - 1) / max(
                    files_per_second, 0.1
                )

                # 确定扫描阶段
                if idx < 10:
                    scan_phase = "discovering"
                    phase_text = "正在发现模组文件..."
                elif current_progress < 95:
                    scan_phase = "processing"
                    phase_text = f"正在处理第 {current_batch}/{total_batches} 批"
                else:
                    scan_phase = "finalizing"
                    phase_text = "正在完成扫描..."

                # 更新进度
                scan_data["processed_files"] = idx + 1
                scan_data["progress"] = current_progress
                scan_data["current_file"] = jar_path.name
                scan_data["scan_phase"] = scan_phase
                scan_data["phase_text"] = phase_text
                scan_data["current_batch"] = current_batch
                scan_data["total_batches"] = total_batches
                scan_data["batch_progress"] = batch_progress
                scan_data["files_per_second"] = round(files_per_second, 1)
                scan_data["estimated_remaining_seconds"] = round(
                    estimated_remaining_time
                )
                scan_data["elapsed_seconds"] = round(elapsed_time)

                # 处理JAR文件
                try:
                    stats = await self._process_jar_file(jar_path, scan_id, db)

                    if stats:
                        total_mods += stats["mods"]
                        total_language_files += stats["language_files"]
                        total_keys += stats["keys"]

                    # 更新统计信息
                    scan_data["statistics"]["total_mods"] = total_mods
                    scan_data["statistics"]["total_language_files"] = (
                        total_language_files
                    )
                    scan_data["statistics"]["total_keys"] = total_keys

                except Exception as e:
                    error_msg = f"处理文件失败 {jar_path.name}: {e}"
                    logger.error(error_msg)
                    scan_data["errors"].append(error_msg)

                # 每10个文件休息一下，避免阻塞
                if idx % 10 == 0:
                    await asyncio.sleep(0.1)

            # 完成扫描
            scan_data["status"] = "completed"
            scan_data["progress"] = 100.0
            scan_data["completed_at"] = datetime.now().isoformat()

            # 更新数据库中的扫描会话
            db.complete_scan_session(scan_id, scan_data["statistics"])

            logger.info(
                f"扫描任务完成: {scan_id}, 找到 {total_mods} 个模组, {total_language_files} 个语言文件, {total_keys} 个翻译键"
            )

        except Exception as e:
            logger.error(f"执行扫描失败 {scan_id}: {e}")
            if scan_id in self.active_scans:
                self.active_scans[scan_id]["status"] = "failed"
                self.active_scans[scan_id]["error"] = str(e)

            if db:
                db.complete_scan_session(scan_id, {"error": str(e)})

        finally:
            # Database 使用单例模式，不需要手动关闭
            pass

    async def _process_jar_file(
        self, jar_path: Path, scan_id: str, db: Database
    ) -> dict | None:
        """
        处理单个JAR文件

        Returns:
            处理统计信息
        """
        stats = {"mods": 0, "language_files": 0, "keys": 0}

        try:
            with zipfile.ZipFile(jar_path, "r") as jar:
                # 解析模组信息
                mod_info = self._extract_mod_info(jar, jar_path)

                if mod_info:
                    # 保存模组到数据库
                    mod_info_obj = ModInfo(
                        mod_id=mod_info.get("mod_id"),
                        display_name=mod_info.get("name", ""),
                        version=mod_info.get("version", ""),
                        description=mod_info.get("description", ""),
                        mod_loader=mod_info.get("mod_loader", ""),
                        authors=json.dumps(mod_info.get("authors", []))
                        if isinstance(mod_info.get("authors"), list)
                        else mod_info.get("authors", ""),
                        file_path=mod_info.get("file_path", ""),
                        file_size=mod_info.get("file_size", 0),
                        file_hash="",
                    )
                    mod_id = db.save_mod(mod_info_obj, scan_id)
                    stats["mods"] = 1

                    # 提取并保存语言文件
                    for file_info in jar.filelist:
                        file_path = file_info.filename

                        # 检查是否是语言文件
                        if "/lang/" in file_path and (
                            file_path.endswith(".json") or file_path.endswith(".lang")
                        ):
                            lang_data = self._extract_language_file(
                                jar, file_info, mod_id
                            )
                            if lang_data:
                                # 保存语言文件
                                lang_file_obj = LanguageFile(
                                    language_code=lang_data.get("locale", "en_us"),
                                    file_path=lang_data.get("file_path", ""),
                                    format=lang_data.get("format", "json"),
                                    entry_count=len(lang_data.get("entries", {})),
                                )
                                file_id = db.save_language_file(mod_id, lang_file_obj)
                                stats["language_files"] += 1

                                # 保存翻译条目
                                if "entries" in lang_data and lang_data["entries"]:
                                    entries = []
                                    for key, value in lang_data["entries"].items():
                                        entries.append(
                                            TranslationEntry(
                                                key=key,
                                                source_text=value,
                                                target_text="",
                                                status="pending",
                                            )
                                        )
                                    db.save_translation_entries(file_id, entries)
                                    stats["keys"] += len(entries)

        except Exception as e:
            logger.warning(f"处理JAR文件失败 {jar_path}: {e}")

        return stats

    def _extract_mod_info(self, jar: zipfile.ZipFile, jar_path: Path) -> dict:
        """
        从JAR文件中提取模组信息
        """
        mod_info = {
            "mod_id": jar_path.stem,
            "name": jar_path.stem,
            "file_path": str(jar_path),
            "file_size": jar_path.stat().st_size,
        }

        # 尝试读取fabric.mod.json (Fabric模组)
        try:
            with jar.open("fabric.mod.json") as f:
                data = json.load(f)
                mod_info["mod_id"] = data.get("id", mod_info["mod_id"])
                mod_info["name"] = data.get("name", mod_info["name"])
                raw_version = data.get("version", "unknown")
                # 解析模板变量
                mod_info["version"] = self._resolve_template_variables(raw_version, str(jar_path))
                mod_info["description"] = data.get("description", "")
                mod_info["mod_loader"] = "fabric"

                # 提取作者信息
                authors = data.get("authors", [])
                if authors:
                    author_names = []
                    for author in authors:
                        if isinstance(author, str):
                            author_names.append(author)
                        elif isinstance(author, dict):
                            author_names.append(author.get("name", ""))
                    mod_info["authors"] = author_names

        except (KeyError, json.JSONDecodeError):
            pass

        # 尝试读取mods.toml (Forge模组)
        try:
            with jar.open("META-INF/mods.toml") as f:
                content = f.read().decode("utf-8")
                # 简单解析TOML（这里只提取基本信息）
                for line in content.split("\n"):
                    if "modId=" in line:
                        mod_info["mod_id"] = (
                            line.split('"')[1] if '"' in line else mod_info["mod_id"]
                        )
                    elif "displayName=" in line:
                        mod_info["name"] = (
                            line.split('"')[1] if '"' in line else mod_info["name"]
                        )
                    elif "version=" in line:
                        raw_version = line.split('"')[1] if '"' in line else "unknown"
                        # 解析模板变量
                        mod_info["version"] = self._resolve_template_variables(raw_version, str(jar_path))
                mod_info["mod_loader"] = "forge"
        except (KeyError, UnicodeDecodeError):
            pass

        # 尝试读取mcmod.info (旧版Forge)
        try:
            with jar.open("mcmod.info") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    mod_data = data[0]
                    mod_info["mod_id"] = mod_data.get("modid", mod_info["mod_id"])
                    mod_info["name"] = mod_data.get("name", mod_info["name"])
                    raw_version = mod_data.get("version", "unknown")
                    # 解析模板变量
                    mod_info["version"] = self._resolve_template_variables(raw_version, str(jar_path))
                    mod_info["description"] = mod_data.get("description", "")
                    mod_info["mod_loader"] = "forge"
                    mod_info["authors"] = mod_data.get("authorList", [])

        except (KeyError, json.JSONDecodeError):
            pass

        return mod_info

    def _extract_language_file(
        self, jar: zipfile.ZipFile, file_info: zipfile.ZipInfo, mod_id: str
    ) -> dict | None:
        """
        提取并解析语言文件
        """
        try:
            file_path = file_info.filename

            # 提取语言代码和命名空间
            parts = file_path.split("/")
            locale = "en_us"
            namespace = "minecraft"

            # 从路径中提取信息
            if "/lang/" in file_path:
                lang_idx = parts.index("lang") if "lang" in parts else -1
                if lang_idx > 0:
                    namespace = parts[lang_idx - 1] if lang_idx > 0 else "minecraft"
                if lang_idx < len(parts) - 1:
                    locale_file = parts[lang_idx + 1]
                    locale = locale_file.replace(".json", "").replace(".lang", "")

            # 读取文件内容
            with jar.open(file_info) as f:
                content = f.read()

                # 解析内容
                entries = {}
                if file_path.endswith(".json"):
                    # JSON格式
                    entries = json.loads(content)
                else:
                    # Properties格式 (.lang文件)
                    for line in content.decode("utf-8", errors="ignore").split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            entries[key.strip()] = value.strip()

                if entries:
                    return {
                        "file_path": file_path,
                        "locale": locale,
                        "namespace": namespace,
                        "key_count": len(entries),
                        "entries": entries,
                    }

        except Exception as e:
            logger.debug(f"无法解析语言文件 {file_info.filename}: {e}")

        return None

    async def get_scan_status(self, scan_id: str) -> dict[str, Any]:
        """
        获取扫描状态

        Args:
            scan_id: 扫描ID

        Returns:
            扫描状态信息
        """
        if scan_id not in self.active_scans:
            # 尝试从数据库获取历史扫描信息
            with Database(self.database_path) as db:
                stats = db.get_statistics()
                for scan in stats.get("recent_scans", []):
                    if scan["scan_id"] == scan_id:
                        return {
                            "scan_id": scan_id,
                            "status": scan["status"],
                            "progress": 100.0 if scan["status"] == "completed" else 0.0,
                            "statistics": {
                                "total_mods": scan.get("total_mods", 0),
                                "total_language_files": scan.get(
                                    "total_language_files", 0
                                ),
                                "total_keys": scan.get("total_keys", 0),
                            },
                        }

            raise ValueError(f"扫描任务不存在: {scan_id}")

        return self.active_scans[scan_id]

    async def cancel_scan(self, scan_id: str) -> bool:
        """
        取消扫描任务

        Args:
            scan_id: 扫描ID

        Returns:
            是否成功取消
        """
        if scan_id in self.active_scans:
            scan_data = self.active_scans[scan_id]
            scan_data["status"] = "cancelled"

            # 更新数据库
            with Database(self.database_path) as db:
                db.complete_scan_session(scan_id, error="User cancelled")

            # 从活动列表中移除
            del self.active_scans[scan_id]

            logger.info(f"扫描任务已取消: {scan_id}")
            return True

        return False

    def get_active_scans(self) -> list[str]:
        """
        获取所有活动的扫描任务ID
        """
        return list(self.active_scans.keys())


def get_scanner_instance(database_path: str = None) -> DDDScanner:
    """
    获取扫描器实例（单例模式）

    Args:
        database_path: 数据库路径

    Returns:
        扫描器实例
    """
    global _scanner_instance

    if database_path is None:
        database_path = str(Path(__file__).parent / "mc_l10n.db")

    if _scanner_instance is None:
        _scanner_instance = DDDScanner(database_path)

    return _scanner_instance


# 向后兼容的函数
async def start_scan(
    target_path: str, incremental: bool = True, options: dict[str, Any] = None
) -> dict[str, Any]:
    """启动扫描（向后兼容）"""
    scanner = get_scanner_instance()
    return await scanner.start_scan(target_path, incremental, options)


async def get_scan_status(scan_id: str) -> dict[str, Any]:
    """获取扫描状态（向后兼容）"""
    scanner = get_scanner_instance()
    return await scanner.get_scan_status(scan_id)


async def cancel_scan(scan_id: str) -> bool:
    """取消扫描（向后兼容）"""
    scanner = get_scanner_instance()
    return await scanner.cancel_scan(scan_id)
