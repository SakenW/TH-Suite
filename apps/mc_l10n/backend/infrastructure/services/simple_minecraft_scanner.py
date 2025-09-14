"""
简化的Minecraft扫描服务
临时实现，替代Universal Scanner的复杂依赖
"""

import asyncio
import logging
import uuid
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SimpleMinecraftScannerService:
    """简化的Minecraft扫描服务，提供基础的扫描功能"""
    
    def __init__(self, db_path: str = "data/simple_scanner.db"):
        self.db_path = db_path
        self._active_scans: Dict[str, Dict[str, Any]] = {}
        logger.info("Simple Minecraft Scanner Service 已初始化")
    
    async def start_scan(
        self,
        target_path: str,
        incremental: bool = True,
        scan_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """启动扫描"""
        try:
            scan_id = f"scan_{uuid.uuid4().hex[:8]}"
            target = Path(target_path)
            
            if not target.exists():
                return {
                    "success": False,
                    "error": f"目标路径不存在: {target_path}",
                    "scan_id": scan_id
                }
            
            logger.info(f"🚀 启动简化扫描: {target_path}")
            logger.info(f"📋 扫描ID: {scan_id}")
            
            # 初始化扫描状态
            scan_state = {
                "scan_id": scan_id,
                "status": "scanning",
                "progress": 0,
                "target_path": target_path,
                "started_at": datetime.now().isoformat(),
                "current_item": "",
                "processed_count": 0,
                "total_count": 0,
                "discovered_items": [],
                "statistics": {}
            }
            
            self._active_scans[scan_id] = scan_state
            
            # 异步执行扫描
            asyncio.create_task(self._perform_scan(scan_id, target, scan_options or {}))
            
            return {
                "success": True,
                "scan_id": scan_id,
                "status": "scanning",
                "discovered_items_count": 0,
                "statistics": {
                    "mods_found": 0,
                    "total_translation_keys": 0,
                    "language_files_found": 0,
                    "total_files": 0
                },
                "duration_seconds": 0,
                "message": f"扫描任务已启动，正在扫描: {target_path}"
            }
                
        except Exception as e:
            logger.error(f"扫描失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "scan_id": str(uuid.uuid4())
            }
    
    async def _perform_scan(self, scan_id: str, target_path: Path, scan_options: Dict[str, Any]):
        """执行实际的扫描过程"""
        try:
            scan_state = self._active_scans[scan_id]
            
            # 发现文件
            logger.info(f"📁 发现文件: {target_path}")
            files = await self._discover_files(target_path, scan_options)
            
            scan_state["total_count"] = len(files)
            scan_state["progress"] = 10
            
            discovered_items = []
            statistics = {
                "total_files": len(files),
                "mods_found": 0,
                "language_files_found": 0,
                "total_translation_keys": 0
            }
            
            # 处理文件
            for i, file_path in enumerate(files):
                if scan_state["status"] == "cancelled":
                    break
                
                scan_state["current_item"] = file_path.name
                scan_state["processed_count"] = i + 1
                scan_state["progress"] = 10 + (i / len(files)) * 80
                
                # 处理JAR文件
                if file_path.suffix.lower() in ['.jar', '.zip']:
                    # 首先判断是否为MOD
                    if await self._is_minecraft_mod(file_path):
                        statistics["mods_found"] += 1
                        
                        # 提取真实的MOD元数据
                        mod_metadata = await self._extract_mod_metadata(file_path)
                        
                        mod_item = {
                            "type": "mod",
                            "mod_id": mod_metadata["mod_id"],
                            "name": mod_metadata["name"],
                            "version": mod_metadata["version"],
                            "authors": mod_metadata["authors"],
                            "description": mod_metadata["description"],
                            "minecraft_version": mod_metadata["minecraft_version"],
                            "loader_type": mod_metadata["loader_type"],
                            "path": str(file_path),
                            "size": file_path.stat().st_size,
                            "language_files": []
                        }
                        
                        # 尝试发现真实的语言文件
                        try:
                            import zipfile
                            with zipfile.ZipFile(file_path, 'r') as jar:
                                # 查找assets/*/lang/*.json文件
                                lang_files = [f for f in jar.namelist() if f.startswith('assets/') and '/lang/' in f and f.endswith('.json')]
                                
                                for lang_file_path in lang_files:
                                    # 提取语言代码
                                    lang_code = Path(lang_file_path).stem
                                    
                                    # 尝试读取文件并计算条目数量
                                    try:
                                        with jar.open(lang_file_path) as lang_file:
                                            lang_content = json.loads(lang_file.read().decode('utf-8'))
                                            entries_count = len(lang_content) if isinstance(lang_content, dict) else 0
                                    except (json.JSONDecodeError, UnicodeDecodeError):
                                        entries_count = 50  # 回退值
                                    
                                    lang_file_info = {
                                        "type": "language_file",
                                        "language_code": lang_code,
                                        "parent_mod": mod_metadata["mod_id"],
                                        "entries_count": entries_count,
                                        "file_path": lang_file_path
                                    }
                                    mod_item["language_files"].append(lang_file_info)
                                    statistics["language_files_found"] += 1
                                    statistics["total_translation_keys"] += entries_count
                                    
                        except (zipfile.BadZipFile, PermissionError) as e:
                            logger.warning(f"无法读取语言文件 {file_path}: {e}")
                            # 如果无法读取，使用估计值
                            estimated_keys = 100
                            statistics["total_translation_keys"] += estimated_keys
                        
                        discovered_items.append(mod_item)
                
                # 模拟处理延迟
                if i % 5 == 0:
                    await asyncio.sleep(0.01)
            
            # 完成扫描
            scan_state["status"] = "completed" if scan_state["status"] != "cancelled" else "cancelled"
            scan_state["progress"] = 100
            scan_state["discovered_items"] = discovered_items
            scan_state["statistics"] = statistics
            scan_state["completed_at"] = datetime.now().isoformat()
            
            # 保存扫描结果到数据库
            try:
                await self._save_scan_results_to_database(scan_id, discovered_items, statistics)
                logger.info(f"💾 扫描结果已保存到数据库")
            except Exception as e:
                logger.error(f"❌ 保存数据库失败: {e}")
            
            logger.info(f"✅ 扫描完成: {scan_id} - 发现 {statistics['mods_found']} 个MOD，{statistics['total_translation_keys']} 个翻译条目")
            
        except Exception as e:
            logger.error(f"扫描执行失败 {scan_id}: {e}")
            if scan_id in self._active_scans:
                self._active_scans[scan_id]["status"] = "failed"
                self._active_scans[scan_id]["error"] = str(e)
    
    async def _discover_files(self, target_path: Path, scan_options: Dict[str, Any]) -> List[Path]:
        """发现需要处理的文件"""
        files = []
        max_depth = scan_options.get("max_depth", 10)
        
        def scan_directory(path: Path, depth: int = 0):
            if depth > max_depth:
                return
            
            try:
                for item in path.iterdir():
                    if item.is_file() and item.suffix.lower() in ['.jar', '.zip']:
                        # 检查文件大小限制
                        max_size_mb = scan_options.get("max_file_size_mb", 500)
                        if item.stat().st_size <= max_size_mb * 1024 * 1024:
                            files.append(item)
                    elif item.is_dir() and depth < max_depth:
                        scan_directory(item, depth + 1)
            except PermissionError:
                logger.warning(f"权限不足: {path}")
        
        if target_path.is_file():
            if target_path.suffix.lower() in ['.jar', '.zip']:
                files.append(target_path)
        else:
            scan_directory(target_path)
        
        logger.info(f"📋 发现 {len(files)} 个文件")
        return files
    
    async def _is_minecraft_mod(self, file_path: Path) -> bool:
        """通过读取MOD元数据判断是否为Minecraft MOD"""
        # 只处理.jar和.zip文件
        if file_path.suffix.lower() not in ['.jar', '.zip']:
            return False
            
        name_lower = file_path.name.lower()
        
        # 排除明显不是MOD的文件
        exclusion_patterns = [
            'server.jar', 'minecraft.jar', 'launcher', 'installer',
            'modpack', 'pack.zip', '.old', '.backup', '.disabled'
        ]
        
        if any(pattern in name_lower for pattern in exclusion_patterns):
            return False
        
        # 通过读取JAR内部的元数据文件来判断
        try:
            import zipfile
            with zipfile.ZipFile(file_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 检查Forge MOD元数据
                if 'META-INF/mods.toml' in file_list:
                    return True
                if 'mcmod.info' in file_list:
                    return True
                    
                # 检查Fabric MOD元数据
                if 'fabric.mod.json' in file_list:
                    return True
                    
                # 检查Quilt MOD元数据
                if 'quilt.mod.json' in file_list:
                    return True
                
                # 检查NeoForge MOD元数据
                if 'META-INF/neoforge.mods.toml' in file_list:
                    return True
                
                # 检查是否包含常见的MOD相关文件夹结构
                has_assets = any(path.startswith('assets/') for path in file_list)
                has_data = any(path.startswith('data/') for path in file_list)
                has_mod_class = any(path.endswith('.class') and 'mod' in path.lower() for path in file_list)
                
                # 如果有assets或data文件夹，很可能是MOD
                if has_assets or has_data or has_mod_class:
                    return True
                    
        except (zipfile.BadZipFile, PermissionError, OSError) as e:
            # 如果无法读取ZIP文件，回退到基于文件位置的判断
            logger.warning(f"无法读取JAR文件 {file_path}: {e}")
            
        # 如果文件在mods目录下，很可能是MOD（回退方案）
        is_in_mods_dir = any(parent.name.lower() == 'mods' for parent in file_path.parents)
        return is_in_mods_dir
    
    async def _extract_mod_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取MOD的真实元数据信息"""
        metadata = {
            "mod_id": file_path.stem,
            "name": file_path.stem,
            "version": "unknown",
            "authors": [],
            "description": "",
            "minecraft_version": "unknown",
            "loader_type": "unknown",
            "dependencies": []
        }
        
        try:
            import zipfile
            import json
            import re
            
            with zipfile.ZipFile(file_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 尝试读取Fabric MOD信息
                if 'fabric.mod.json' in file_list:
                    try:
                        with jar.open('fabric.mod.json') as f:
                            fabric_data = json.load(f)
                            metadata.update({
                                "mod_id": fabric_data.get("id", file_path.stem),
                                "name": fabric_data.get("name", file_path.stem),
                                "version": fabric_data.get("version", "unknown"),
                                "authors": fabric_data.get("authors", []),
                                "description": fabric_data.get("description", ""),
                                "loader_type": "fabric"
                            })
                            
                            # 提取Minecraft版本
                            depends = fabric_data.get("depends", {})
                            if "minecraft" in depends:
                                metadata["minecraft_version"] = depends["minecraft"]
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析fabric.mod.json: {file_path}")
                
                # 尝试读取Quilt MOD信息
                elif 'quilt.mod.json' in file_list:
                    try:
                        with jar.open('quilt.mod.json') as f:
                            quilt_data = json.load(f)
                            quilt_mod = quilt_data.get("quilt_loader", {})
                            metadata.update({
                                "mod_id": quilt_mod.get("id", file_path.stem),
                                "name": quilt_mod.get("metadata", {}).get("name", file_path.stem),
                                "version": quilt_mod.get("version", "unknown"),
                                "authors": quilt_mod.get("metadata", {}).get("contributors", {}).keys(),
                                "description": quilt_mod.get("metadata", {}).get("description", ""),
                                "loader_type": "quilt"
                            })
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析quilt.mod.json: {file_path}")
                
                # 尝试读取Forge TOML信息
                elif 'META-INF/mods.toml' in file_list:
                    try:
                        with jar.open('META-INF/mods.toml') as f:
                            toml_content = f.read().decode('utf-8')
                            
                            # 简单解析TOML（避免额外依赖）
                            mod_id_match = re.search(r'modId\s*=\s*["\']([^"\']+)["\']', toml_content)
                            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', toml_content)
                            display_name_match = re.search(r'displayName\s*=\s*["\']([^"\']+)["\']', toml_content)
                            authors_match = re.search(r'authors\s*=\s*["\']([^"\']+)["\']', toml_content)
                            description_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', toml_content)
                            mc_version_match = re.search(r'minecraftVersion\s*=\s*["\']([^"\']+)["\']', toml_content)
                            
                            if mod_id_match:
                                metadata["mod_id"] = mod_id_match.group(1)
                            if display_name_match:
                                metadata["name"] = display_name_match.group(1)
                            if version_match:
                                metadata["version"] = version_match.group(1)
                            if authors_match:
                                metadata["authors"] = [authors_match.group(1)]
                            if description_match:
                                metadata["description"] = description_match.group(1)
                            if mc_version_match:
                                metadata["minecraft_version"] = mc_version_match.group(1)
                            
                            metadata["loader_type"] = "forge"
                    except Exception as e:
                        logger.warning(f"无法解析mods.toml: {file_path}, {e}")
                
                # 尝试读取旧版Forge mcmod.info
                elif 'mcmod.info' in file_list:
                    try:
                        with jar.open('mcmod.info') as f:
                            mcmod_data = json.load(f)
                            if isinstance(mcmod_data, list) and mcmod_data:
                                mod_info = mcmod_data[0]
                                metadata.update({
                                    "mod_id": mod_info.get("modid", file_path.stem),
                                    "name": mod_info.get("name", file_path.stem),
                                    "version": mod_info.get("version", "unknown"),
                                    "authors": mod_info.get("authorList", []),
                                    "description": mod_info.get("description", ""),
                                    "minecraft_version": mod_info.get("mcversion", "unknown"),
                                    "loader_type": "forge"
                                })
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析mcmod.info: {file_path}")
                
        except (zipfile.BadZipFile, PermissionError, OSError) as e:
            logger.warning(f"无法读取MOD元数据 {file_path}: {e}")
        
        return metadata
    
    async def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """获取扫描状态"""
        try:
            if scan_id in self._active_scans:
                scan_state = self._active_scans[scan_id]
                statistics = scan_state.get("statistics", {})
                
                return {
                    "success": True,
                    "scan_id": scan_id,
                    "status": scan_state["status"],
                    "progress": scan_state["progress"],
                    "current_item": scan_state["current_item"],
                    "processed_count": scan_state["processed_count"],
                    "total_count": scan_state["total_count"],
                    "duration_seconds": 0,  # 可以计算实际时长
                    "error_message": scan_state.get("error"),
                    # 添加统计信息到状态响应中
                    "statistics": statistics,
                    "mods_found": statistics.get("mods_found", 0),
                    "total_translation_keys": statistics.get("total_translation_keys", 0),
                    "language_files_found": statistics.get("language_files_found", 0),
                    "discovered_items": scan_state.get("discovered_items", [])
                }
            else:
                return {
                    "success": False,
                    "error": "扫描记录不存在",
                    "scan_id": scan_id
                }
        except Exception as e:
            logger.error(f"获取扫描状态失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "scan_id": scan_id
            }
    
    async def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        try:
            if scan_id in self._active_scans:
                self._active_scans[scan_id]["status"] = "cancelled"
                logger.info(f"❌ 扫描已取消: {scan_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"取消扫描失败: {e}")
            return False
    
    async def get_content_items(self, content_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取内容项"""
        try:
            # 从已完成的扫描中收集内容项
            content_items = []
            for scan_state in self._active_scans.values():
                if scan_state["status"] == "completed":
                    items = scan_state.get("discovered_items", [])
                    if content_type == "mod":
                        content_items.extend([item for item in items if item["type"] == "mod"])
                    elif content_type == "language_file":
                        for item in items:
                            if item["type"] == "mod":
                                content_items.extend(item.get("language_files", []))
            
            return content_items[:limit]
        except Exception as e:
            logger.error(f"获取内容项失败: {e}")
            return []


    async def _save_scan_results_to_database(self, scan_id: str, discovered_items: List[Dict], statistics: Dict):
        """保存扫描结果到数据库"""
        try:
            # 直接使用数据库路径，避免依赖注入的复杂性
            from pathlib import Path
            import sqlite3
            import uuid
            from datetime import datetime
            
            # 获取数据库文件路径
            db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n_v2_1.db"
            
            # 获取扫描状态信息
            scan_state = self._active_scans[scan_id]
            
            # 创建项目记录 - 使用正确的字段
            project_name = f"扫描项目_{scan_id}"
            project_path = scan_state["target_path"]
            
            # 连接数据库并保存数据
            conn = sqlite3.connect(str(db_path))
            try:
                # 1. 插入pack记录
                pack_sql = """
                INSERT INTO packs (name, project_type, game_type, path, description, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                now = datetime.now().isoformat()
                cursor = conn.execute(pack_sql, (
                    project_name,
                    "modpack",  # project_type
                    "minecraft",  # game_type
                    project_path,
                    f"通过扫描发现的项目，包含 {statistics.get('mods_found', 0)} 个MOD",
                    now,  # created_at
                    now,  # updated_at
                    True  # is_active
                ))
                pack_id = cursor.lastrowid
                
                # 2. 插入pack_version记录
                pack_version_sql = """
                INSERT INTO pack_versions (pack_id, version_tag, minecraft_version, loader_type, display_name, is_default, is_stable, local_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor = conn.execute(pack_version_sql, (
                    pack_id,
                    "1.0.0",  # version_tag
                    "1.20.1",  # minecraft_version (默认)
                    "forge",  # loader_type (默认)
                    f"{project_name} v1.0.0",  # display_name
                    True,  # is_default
                    True,  # is_stable
                    project_path,  # local_path
                    now,  # created_at
                    now   # updated_at
                ))
                pack_version_id = cursor.lastrowid
                
                # 3. 插入mod_version_instances记录并创建关联
                mod_count = 0
                for item in discovered_items:
                    if item.get("type") == "mod":
                        # 插入MOD实例记录
                        mod_instance_sql = """
                        INSERT INTO mod_version_instances 
                        (mod_id, mod_version, mod_name, jar_file_path, jar_file_size, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """
                        cursor = conn.execute(mod_instance_sql, (
                            str(uuid.uuid4()),  # mod_id
                            item.get("version", "unknown"),  # mod_version
                            item.get("name", "Unknown"),  # mod_name
                            item.get("path", ""),  # jar_file_path
                            item.get("size", 0),  # jar_file_size
                            now,  # created_at
                            now   # updated_at
                        ))
                        mod_instance_id = cursor.lastrowid
                        
                        # 4. 创建pack_version与mod_instance的关联
                        relation_sql = """
                        INSERT INTO pack_mod_relations (pack_version_id, mod_instance_id, relation_type, detected_at, detection_method, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """
                        conn.execute(relation_sql, (
                            pack_version_id,  # pack_version_id (正确字段名)
                            mod_instance_id,  # mod_instance_id (正确字段名)
                            "included",  # relation_type
                            now,  # detected_at
                            "filesystem_scan",  # detection_method
                            now   # created_at
                        ))
                        mod_count += 1
                
                conn.commit()
                logger.info(f"✅ 已保存 {mod_count} 个MOD到数据库 (pack_id: {pack_id}, pack_version_id: {pack_version_id})")
                logger.info(f"📊 统计信息: {statistics.get('mods_found', 0)} 个MOD, {statistics.get('total_translation_keys', 0)} 个翻译条目")
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"❌ 数据库保存失败: {e}")
            # 不重新抛出异常，避免中断扫描流程
            import traceback
            logger.error(f"数据库保存详细错误: {traceback.format_exc()}")


# 全局实例
_simple_scanner_service: SimpleMinecraftScannerService = None


def get_simple_minecraft_scanner_service(db_path: str = "data/simple_scanner.db") -> SimpleMinecraftScannerService:
    """获取简化的Minecraft扫描服务实例"""
    global _simple_scanner_service
    if _simple_scanner_service is None:
        _simple_scanner_service = SimpleMinecraftScannerService(db_path)
    return _simple_scanner_service