"""
DDD扫描器模块 - V6架构简化版本
只提供扫描功能，不依赖旧数据库
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
import uuid

from database.core.manager import get_database_manager
from utils.path_converter import PathConverter

logger = logging.getLogger(__name__)

# 全局扫描服务实例
_scanner_instance: Optional["DDDScanner"] = None


class DDDScanner:
    """DDD扫描器 - 简化版本，只提供扫描统计功能"""

    def __init__(self, database_path: str):
        self.database_path = database_path
        self.active_scans = {}
        logger.info(f"DDD扫描器已初始化，数据库路径: {database_path}")

    async def start_scan(
        self, target_path: str, incremental: bool = True, options: dict[str, Any] = None
    ) -> dict[str, Any]:
        """启动扫描任务"""
        try:
            # 智能路径转换
            original_path = target_path
            converted_path, path_exists, status_msg = PathConverter.validate_and_convert_path(target_path)
            
            if converted_path != original_path:
                logger.info(f"路径智能转换: {original_path} -> {converted_path}")
            
            if not path_exists:
                error_msg = f"路径不存在: {converted_path}"
                if converted_path != original_path:
                    error_msg += f" (原路径: {original_path})"
                # 提供建议路径
                suggestions = PathConverter.suggest_minecraft_paths()
                if suggestions:
                    error_msg += f". 建议路径: {', '.join(suggestions[:3])}"
                raise ValueError(error_msg)

            # 使用转换后的路径
            target_path = converted_path
            
            # 生成扫描ID
            scan_id = str(uuid.uuid4())[:16]

            # 初始化扫描状态
            self.active_scans[scan_id] = {
                "scan_id": scan_id,
                "target_path": target_path,
                "incremental": incremental,
                "status": "started",
                "progress": 0.0,
                "statistics": {
                    "total_mods": 0,
                    "total_language_files": 0,
                    "total_keys": 0,
                },
            }

            logger.info(f"启动扫描任务: {scan_id}, 路径: {target_path}, 增量: {incremental}")

            # 在后台执行扫描
            asyncio.create_task(self._execute_scan(scan_id))

            return {"scan_id": scan_id, "status": "started"}

        except Exception as e:
            logger.error(f"启动扫描失败: {e}")
            raise

    async def _execute_scan(self, scan_id: str):
        """执行扫描任务"""
        try:
            scan_data = self.active_scans[scan_id]
            scan_data["status"] = "scanning"
            target_path = Path(scan_data["target_path"])

            # 搜索JAR文件
            jar_files = []
            logger.info(f"开始搜索JAR文件: {target_path}")
            for root, dirs, files in os.walk(target_path):
                for file in files:
                    if file.endswith(".jar"):
                        jar_files.append(Path(root) / file)

            logger.info(f"找到 {len(jar_files)} 个JAR文件")

            total_mods = 0
            total_language_files = 0
            total_keys = 0

            for i, jar_path in enumerate(jar_files):
                # 更新进度
                progress = (i / len(jar_files)) * 100 if jar_files else 100
                scan_data["progress"] = progress
                scan_data["current_file"] = str(jar_path.name)

                # 处理JAR文件
                try:
                    stats = await self._process_jar_file(jar_path)
                    if stats:
                        total_mods += stats["mods"]
                        total_language_files += stats["language_files"]
                        total_keys += stats["keys"]
                except Exception as e:
                    logger.warning(f"处理JAR文件失败: {jar_path}, 错误: {e}")

            # 完成扫描
            scan_data["status"] = "completed"
            scan_data["progress"] = 100.0
            scan_data["statistics"] = {
                "total_mods": total_mods,
                "total_language_files": total_language_files,
                "total_keys": total_keys,
            }

            logger.info(f"扫描任务完成: {scan_id}, 找到 {total_mods} 个模组, {total_language_files} 个语言文件, {total_keys} 个翻译键")
            
            # 保存扫描结果到数据库
            try:
                await self._save_scan_results_to_database(jar_files, scan_id)
                logger.info(f"扫描结果已保存到数据库: {scan_id}")
            except Exception as e:
                logger.error(f"保存扫描结果到数据库失败: {scan_id}, 错误: {e}")

        except Exception as e:
            logger.error(f"扫描任务失败: {scan_id}, 错误: {e}")
            if scan_id in self.active_scans:
                self.active_scans[scan_id]["status"] = "failed"
                self.active_scans[scan_id]["error"] = str(e)

    async def _process_jar_file(self, jar_path: Path) -> dict | None:
        """处理单个JAR文件"""
        stats = {"mods": 0, "language_files": 0, "keys": 0}

        try:
            with zipfile.ZipFile(jar_path, "r") as jar:
                # 解析模组信息
                mod_info = self._extract_mod_info(jar, jar_path)

                if mod_info:
                    stats["mods"] = 1

                    # 统计语言文件
                    for file_info in jar.filelist:
                        file_path = file_info.filename

                        # 检查是否是语言文件
                        if "/lang/" in file_path and (
                            file_path.endswith(".json") or file_path.endswith(".lang")
                        ):
                            try:
                                # 读取语言文件内容
                                lang_content = jar.read(file_info).decode("utf-8")
                                if file_path.endswith(".json"):
                                    lang_entries = json.loads(lang_content)
                                    if isinstance(lang_entries, dict):
                                        stats["language_files"] += 1
                                        stats["keys"] += len(lang_entries)
                                elif file_path.endswith(".lang"):
                                    # 简单的 .lang 文件解析
                                    lines = lang_content.split('\n')
                                    entries = [line for line in lines if '=' in line and not line.strip().startswith('#')]
                                    if entries:
                                        stats["language_files"] += 1
                                        stats["keys"] += len(entries)
                            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                                logger.debug(f"解析语言文件失败: {file_path}, 错误: {e}")
                                continue

        except Exception as e:
            logger.error(f"处理JAR文件失败: {jar_path}, 错误: {e}")
            return None

        return stats

    def _extract_mod_info(self, jar: zipfile.ZipFile, jar_path: Path) -> dict:
        """从JAR文件中提取模组信息"""
        # 智能解析文件名，提取基础模组名和版本号
        clean_name, extracted_version = self._parse_filename_intelligently(jar_path.stem)
        
        mod_info = {
            "mod_id": clean_name,  # 使用清理后的名称作为默认mod_id
            "name": clean_name,    # 使用清理后的名称作为默认name
            "version": extracted_version,
            "file_path": str(jar_path),
            "file_size": jar_path.stat().st_size,
        }

        # 尝试读取fabric.mod.json (Fabric模组)
        try:
            with jar.open("fabric.mod.json") as f:
                data = json.load(f)
                mod_info["mod_id"] = data.get("id", mod_info["mod_id"])
                mod_info["name"] = data.get("name", mod_info["name"])
                raw_version = data.get("version", mod_info["version"])
                mod_info["version"] = self._resolve_template_variables(raw_version, str(jar_path))
                mod_info["description"] = data.get("description", "")
                mod_info["mod_loader"] = "fabric"
                return mod_info
        except:
            pass

        # 尝试读取META-INF/mods.toml (现代Forge模组)
        try:
            with jar.open("META-INF/mods.toml") as f:
                content = f.read().decode("utf-8")
                mod_info.update(self._parse_mods_toml(content, jar_path))
                mod_info["mod_loader"] = "forge"
                return mod_info
        except:
            pass

        # 尝试读取mcmod.info (旧版Forge模组)
        try:
            with jar.open("mcmod.info") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    mod_data = data[0]
                    mod_info["mod_id"] = mod_data.get("modid", mod_info["mod_id"])
                    mod_info["name"] = mod_data.get("name", mod_info["name"])
                    raw_version = mod_data.get("version", mod_info["version"])
                    mod_info["version"] = self._resolve_template_variables(raw_version, str(jar_path))
                    mod_info["description"] = mod_data.get("description", "")
                    mod_info["mod_loader"] = "forge"
                    return mod_info
        except:
            pass

        # 如果所有解析都失败，使用智能文件名解析结果
        mod_info["mod_loader"] = "unknown"
        return mod_info

    async def get_scan_status(self, scan_id: str) -> dict[str, Any]:
        """获取扫描状态"""
        if scan_id not in self.active_scans:
            raise ValueError(f"扫描任务不存在: {scan_id}")

        return self.active_scans[scan_id]

    async def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        if scan_id in self.active_scans:
            scan_data = self.active_scans[scan_id]
            scan_data["status"] = "cancelled"
            del self.active_scans[scan_id]
            logger.info(f"扫描任务已取消: {scan_id}")
            return True
        return False

    async def get_content_items(self, content_type: str, limit: int = 100) -> list:
        """获取内容项 - 简化实现"""
        return []

    def get_active_scans(self) -> list[str]:
        """获取所有活动的扫描任务ID"""
        return list(self.active_scans.keys())

    async def _save_scan_results_to_database(self, jar_files: list[Path], scan_id: str) -> None:
        """将扫描结果保存到V6数据库"""
        try:
            db_manager = get_database_manager()
            
            for jar_path in jar_files:
                try:
                    with zipfile.ZipFile(jar_path, "r") as jar:
                        # 解析模组信息
                        mod_info = self._extract_mod_info(jar, jar_path)
                        
                        if mod_info:
                            # 保存模组信息到数据库
                            mod_data = {
                                'mod_id': mod_info['mod_id'],
                                'display_name': mod_info['name'],
                                'version': mod_info.get('version', 'unknown'),
                                'description': mod_info.get('description', ''),
                                'mod_loader': mod_info.get('mod_loader', 'unknown'),
                                'file_path': str(jar_path),
                                'file_size': mod_info['file_size'],
                                'scan_id': scan_id
                            }
                            
                            # 使用数据库管理器保存模组数据，获取mod_uid
                            mod_uid = await self._save_mod_to_database(db_manager, mod_data)
                            
                            # 处理语言文件，传入mod_uid
                            await self._save_language_files_to_database(db_manager, jar, mod_info, scan_id, mod_uid)
                            
                except Exception as e:
                    logger.warning(f"保存JAR文件数据失败: {jar_path}, 错误: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"数据库保存过程失败: {e}")
            raise

    async def _save_mod_to_database(self, db_manager, mod_data: dict) -> str:
        """保存模组数据到V6数据库，返回mod_uid"""
        try:
            # 使用数据库管理器的连接执行SQL
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # V6架构使用core_mods表
                # 检查模组是否已存在（根据modid查找）
                cursor.execute(
                    "SELECT uid FROM core_mods WHERE modid = ?",
                    (mod_data['mod_id'],)
                )
                
                existing = cursor.fetchone()
                
                if existing:
                    # 更新现有模组
                    mod_uid = existing['uid']
                    cursor.execute("""
                        UPDATE core_mods SET 
                            name = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE uid = ?
                    """, (
                        mod_data.get('name', mod_data.get('display_name', 'Unknown')), mod_uid
                    ))
                    logger.debug(f"更新模组: {mod_data['mod_id']} (uid: {mod_uid})")
                    
                    # 也为更新的MOD保存版本信息
                    self._save_mod_version_to_db(cursor, mod_uid, mod_data)
                else:
                    # 插入新模组，生成UUID
                    import uuid
                    mod_uid = str(uuid.uuid4())
                    
                    cursor.execute("""
                        INSERT INTO core_mods (
                            uid, modid, name, created_at, updated_at
                        ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (
                        mod_uid, mod_data['mod_id'], mod_data.get('name', mod_data.get('display_name', 'Unknown'))
                    ))
                    logger.debug(f"新增模组: {mod_data['mod_id']} (uid: {mod_uid})")
                
                # 保存版本信息到core_mod_versions表
                self._save_mod_version_to_db(cursor, mod_uid, mod_data)
                
                conn.commit()
                return mod_uid
                
        except Exception as e:
            logger.error(f"保存模组数据失败: {mod_data['mod_id']}, 错误: {e}")
            raise

    def _save_mod_version_to_db(self, cursor, mod_uid: str, mod_data: dict) -> None:
        """保存MOD版本信息到core_mod_versions表"""
        try:
            import uuid
            import json
            
            # 生成版本记录的UID
            version_uid = str(uuid.uuid4())
            
            # 从MOD数据中提取版本信息
            version = mod_data.get('version', 'unknown')
            loader = mod_data.get('mod_loader', 'unknown')
            mc_version = mod_data.get('mc_version', 'unknown')
            
            # 准备元数据JSON
            meta_json = json.dumps({
                'description': mod_data.get('description'),
                'authors': mod_data.get('authors', []),
                'dependencies': mod_data.get('dependencies', []),
                'file_path': mod_data.get('file_path')
            })
            
            # 检查是否已存在相同的版本记录（避免重复）
            cursor.execute("""
                SELECT uid FROM core_mod_versions 
                WHERE mod_uid = ? AND loader = ? AND version = ? AND mc_version = ?
            """, (mod_uid, loader, version, mc_version))
            
            existing_version = cursor.fetchone()
            
            if existing_version:
                # 更新现有版本记录
                cursor.execute("""
                    UPDATE core_mod_versions SET 
                        meta_json = ?, source = 'file_scan', discovered_at = CURRENT_TIMESTAMP
                    WHERE uid = ?
                """, (meta_json, existing_version['uid']))
                logger.debug(f"更新版本记录: {mod_data['mod_id']} v{version}")
            else:
                # 插入新版本记录
                cursor.execute("""
                    INSERT INTO core_mod_versions (
                        uid, mod_uid, loader, mc_version, version, 
                        meta_json, source, discovered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'file_scan', CURRENT_TIMESTAMP)
                """, (
                    version_uid, mod_uid, loader, mc_version, version, meta_json
                ))
                logger.debug(f"新增版本记录: {mod_data['mod_id']} v{version} ({loader}, MC {mc_version})")
                
        except Exception as e:
            logger.error(f"保存版本信息失败: {mod_data.get('mod_id', 'unknown')}, 错误: {e}")
            # 不抛出异常，避免影响主扫描流程

    async def _save_language_files_to_database(self, db_manager, jar: zipfile.ZipFile, mod_info: dict, scan_id: str, mod_uid: str) -> None:
        """保存语言文件数据到V6数据库"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                for file_info in jar.filelist:
                    file_path = file_info.filename
                    
                    # 检查是否是语言文件
                    if "/lang/" in file_path and (file_path.endswith(".json") or file_path.endswith(".lang")):
                        try:
                            # 提取语言代码
                            lang_code = self._extract_language_code(file_path)
                            if not lang_code:
                                continue
                                
                            # 读取语言文件内容
                            lang_content = jar.read(file_info).decode("utf-8")
                            
                            # 解析语言文件
                            entries = {}
                            if file_path.endswith(".json"):
                                entries = json.loads(lang_content)
                            elif file_path.endswith(".lang"):
                                # 解析 .lang 文件
                                lines = lang_content.split('\n')
                                for line in lines:
                                    if '=' in line and not line.strip().startswith('#'):
                                        key, value = line.split('=', 1)
                                        entries[key.strip()] = value.strip()
                            
                            if not entries:
                                continue
                            
                            # V6架构：保存语言文件记录到core_language_files
                            import uuid
                            file_uid = str(uuid.uuid4())
                            file_format = "json" if file_path.endswith(".json") else "lang"
                            
                            cursor.execute("""
                                INSERT OR REPLACE INTO core_language_files (
                                    uid, carrier_type, carrier_uid, locale, rel_path, 
                                    format, size, discovered_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                            """, (
                                file_uid, 'mod', mod_uid, lang_code, file_path,
                                file_format, len(lang_content)
                            ))
                            
                            # V6架构：保存翻译条目到core_translation_entries
                            for key, value in entries.items():
                                entry_uid = str(uuid.uuid4())
                                cursor.execute("""
                                    INSERT OR REPLACE INTO core_translation_entries (
                                        uid, language_file_uid, key, src_text, 
                                        status, updated_at
                                    ) VALUES (?, ?, ?, ?, 'new', CURRENT_TIMESTAMP)
                                """, (entry_uid, file_uid, key, value))
                            
                            logger.debug(f"保存语言文件: {file_path} ({len(entries)} 条目)")
                            
                        except (json.JSONDecodeError, UnicodeDecodeError) as e:
                            logger.debug(f"解析语言文件失败: {file_path}, 错误: {e}")
                            continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"保存语言文件失败: {mod_info['mod_id']}, 错误: {e}")
            raise

    def _extract_language_code(self, file_path: str) -> str:
        """从文件路径中提取语言代码"""
        # 从路径如 "assets/mod/lang/zh_cn.json" 中提取 "zh_cn"
        import re
        match = re.search(r'/lang/([^/]+)\.(json|lang)$', file_path)
        return match.group(1) if match else None

    def _parse_filename_intelligently(self, filename: str) -> tuple[str, str]:
        """智能解析文件名，分离模组名称和版本号
        
        Args:
            filename: 文件名（无扩展名），如 "AI-Improvements-1.18.2-0.5.2"
            
        Returns:
            tuple: (clean_name, extracted_version)
                例如: ("AI-Improvements", "1.18.2-0.5.2")
        """
        import re
        
        # 模式1: 匹配 name-mcversion-modversion 格式
        # 如: "AI-Improvements-1.18.2-0.5.2" -> "AI-Improvements", "1.18.2-0.5.2"
        match1 = re.match(r'^(.+?)-(\d+\.\d+(?:\.\d+)?(?:-\d+\.\d+(?:\.\d+)?)*)$', filename)
        if match1:
            name_part, version_part = match1.groups()
            return name_part, version_part
            
        # 模式2: 匹配 name-version 格式
        # 如: "jei-1.19.2-11.5.0.297" -> "jei", "1.19.2-11.5.0.297"
        # 或: "mod-name-v2.0" -> "mod-name", "v2.0"
        match2 = re.match(r'^(.+?)-((?:\d+\.\d+(?:\.\d+)?.*?|v\d+\.\d+.*?))$', filename)
        if match2:
            name_part, version_part = match2.groups()
            # 检查name_part是否太短（可能过度切分）
            if len(name_part) >= 3:
                return name_part, version_part
                
        # 模式3: 匹配末尾有版本号的格式
        # 如: "betterend_1.18.2" -> "betterend", "1.18.2"
        match3 = re.match(r'^(.+?)_(\d+\.\d+(?:\.\d+)?)$', filename)
        if match3:
            name_part, version_part = match3.groups()
            return name_part, version_part
            
        # 如果都不匹配，返回原始名称和空版本
        return filename, ""

    def _parse_mods_toml(self, content: str, jar_path) -> dict:
        """解析 META-INF/mods.toml 文件（现代Forge模组）
        
        Args:
            content: mods.toml 文件内容
            jar_path: JAR文件路径对象
            
        Returns:
            dict: 解析出的模组信息
        """
        try:
            import tomllib
        except ImportError:
            # Python < 3.11 的向后兼容
            try:
                import tomli as tomllib
            except ImportError:
                logger.warning("缺少 TOML 解析库，无法解析 mods.toml")
                return {}
        
        try:
            data = tomllib.loads(content)
            
            # 获取第一个模组定义
            mods = data.get('mods', [])
            if not mods:
                return {}
                
            mod_data = mods[0]  # 取第一个模组
            
            result = {}
            if 'modId' in mod_data:
                result['mod_id'] = mod_data['modId']
            if 'displayName' in mod_data:
                result['name'] = mod_data['displayName']
            if 'version' in mod_data:
                raw_version = mod_data['version']
                result['version'] = self._resolve_template_variables(raw_version, str(jar_path))
            if 'description' in mod_data:
                result['description'] = mod_data['description']
                
            return result
            
        except Exception as e:
            logger.debug(f"解析 mods.toml 失败: {e}")
            return {}

    def _resolve_template_variables(self, template_str: str, file_path: str) -> str:
        """解析模版变量（如 ${version}）
        
        Args:
            template_str: 包含模版变量的字符串
            file_path: 文件路径，用于提取版本信息
            
        Returns:
            str: 解析后的字符串
        """
        if not template_str or '${' not in template_str:
            return template_str
            
        import re
        from pathlib import Path
        
        # 从文件名尝试提取版本号
        file_stem = Path(file_path).stem
        _, extracted_version = self._parse_filename_intelligently(file_stem)
        
        # 替换常见的模版变量
        result = template_str
        
        # ${version} 或 ${file.jarVersion}
        if '${version}' in result or '${file.jarVersion}' in result:
            replacement = extracted_version if extracted_version else "unknown"
            result = result.replace('${version}', replacement)
            result = result.replace('${file.jarVersion}', replacement)
            
        # ${mc_version} - 尝试从版本字符串中提取MC版本
        if '${mc_version}' in result:
            mc_version = "unknown"
            if extracted_version:
                # 尝试匹配像 "1.18.2-0.5.2" 中的 "1.18.2"
                match = re.match(r'^(\d+\.\d+(?:\.\d+)?)', extracted_version)
                if match:
                    mc_version = match.group(1)
            result = result.replace('${mc_version}', mc_version)
            
        return result


def get_scanner_instance(database_path: str = None) -> DDDScanner:
    """获取扫描器实例（单例模式）"""
    global _scanner_instance
    if database_path is None:
        database_path = str(Path(__file__).parent.parent / "data" / "mc_l10n_v6.db")
    
    # 如果路径改变，需要重新创建实例
    if _scanner_instance is None or _scanner_instance.database_path != database_path:
        _scanner_instance = DDDScanner(database_path)
    return _scanner_instance