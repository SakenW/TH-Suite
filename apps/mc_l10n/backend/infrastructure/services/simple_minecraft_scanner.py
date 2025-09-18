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

from .jar_extraction_helper import AsyncJarReader

logger = logging.getLogger(__name__)


class SimpleMinecraftScannerService:
    """简化的Minecraft扫描服务，提供基础的扫描功能"""
    
    def __init__(self, db_path: str = "data/mc_l10n.db"):
        self.db_path = db_path
        self._active_scans: Dict[str, Dict[str, Any]] = {}
        
        # 初始化JAR文件读取器，使用数据库目录内的专用临时目录
        from pathlib import Path
        data_dir = Path(self.db_path).parent
        temp_extract_dir = data_dir / "temp_extracts"
        temp_extract_dir.mkdir(parents=True, exist_ok=True)
        
        self.jar_reader = AsyncJarReader(str(temp_extract_dir))
        
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
            
            # 快速预扫描获取文件数量估计
            estimated_files = await self._quick_count_files(target, scan_options or {})
            scan_state["estimated_files"] = estimated_files
            
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
                    "total_files": 0,
                    "estimated_files": estimated_files
                },
                "duration_seconds": 0,
                "message": f"扫描任务已启动，预计 {estimated_files} 个文件，正在扫描: {target_path}"
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
            scan_state["current_item"] = "正在发现文件..."
            scan_state["progress"] = 5
            
            files = await self._discover_files(target_path, scan_options, scan_state)
            
            scan_state["total_count"] = len(files)
            scan_state["progress"] = 15
            scan_state["current_item"] = f"发现 {len(files)} 个文件，开始处理..."
            
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
                    await self._process_jar_file(file_path, statistics, discovered_items)
                
                # 处理独立的语言文件
                elif file_path.suffix.lower() in ['.json', '.lang', '.properties']:
                    await self._process_language_file(file_path, statistics, discovered_items)
                
                # 原JAR处理逻辑移到单独方法
                continue
                
            if False:  # 保持原代码结构但不执行
                # 处理JAR文件（已移动到_process_jar_file）
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
                                    lang_content = {}
                                    entries_count = 0
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
                                        "file_path": lang_file_path,
                                        "translations": lang_content  # 保存实际翻译内容
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
    
    async def _discover_files(self, target_path: Path, scan_options: Dict[str, Any], scan_state: Dict[str, Any] = None) -> List[Path]:
        """发现需要处理的文件 - 优化版本，支持大型目录"""
        files = []
        max_depth = scan_options.get("max_depth", 10)
        processed_dirs = 0
        total_dirs_estimate = 100  # 初始估计
        
        # 异步递归扫描函数
        async def scan_directory_async(path: Path, depth: int = 0):
            nonlocal processed_dirs, total_dirs_estimate
            
            if depth > max_depth:
                return
            
            try:
                items = list(path.iterdir())
                subdirs = []
                
                # 处理当前目录的文件
                for item in items:
                    # 扩展文件类型支持：JAR、ZIP和语言文件
                    if item.is_file() and item.suffix.lower() in ['.jar', '.zip', '.json', '.lang', '.properties']:
                        # 检查文件大小限制
                        max_size_mb = scan_options.get("max_file_size_mb", 500)
                        try:
                            if item.stat().st_size <= max_size_mb * 1024 * 1024:
                                files.append(item)
                        except (OSError, PermissionError):
                            continue  # 跳过无法访问的文件
                    elif item.is_dir() and depth < max_depth:
                        subdirs.append(item)
                
                processed_dirs += 1
                
                # 每处理10个目录就释放一次控制权，并更新进度
                if processed_dirs % 10 == 0:
                    await asyncio.sleep(0.001)  # 极短暂的异步暂停
                    progress_msg = f"正在发现文件... ({processed_dirs} 个目录，{len(files)} 个文件)"
                    logger.info(f"📁 {progress_msg}")
                    if scan_state:
                        scan_state["current_item"] = progress_msg
                        scan_state["progress"] = min(5 + (processed_dirs / total_dirs_estimate) * 10, 14)
                
                # 递归处理子目录
                for subdir in subdirs:
                    await scan_directory_async(subdir, depth + 1)
                    
            except PermissionError:
                logger.warning(f"权限不足: {path}")
            except Exception as e:
                logger.warning(f"访问目录失败 {path}: {e}")
        
        if target_path.is_file():
            if target_path.suffix.lower() in ['.jar', '.zip']:
                files.append(target_path)
        else:
            # 快速估算目录数量
            try:
                sample_dirs = 0
                for root, dirs, _ in os.walk(target_path):
                    sample_dirs += len(dirs)
                    if sample_dirs > 50:  # 只采样前50个目录
                        total_dirs_estimate = sample_dirs * 10  # 估算总数
                        break
                total_dirs_estimate = max(sample_dirs, 20)
                logger.info(f"📊 估计需要处理约 {total_dirs_estimate} 个目录")
            except:
                pass
            
            # 开始异步扫描
            await scan_directory_async(target_path)
        
        logger.info(f"📋 发现 {len(files)} 个文件（共处理 {processed_dirs} 个目录）")
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
        """保存扫描结果到V5数据库"""
        logger.info(f"🔧 开始保存扫描结果到V5架构: scan_id={scan_id}, items={len(discovered_items)}")
        try:
            # 使用V5架构的Repository模式
            from infrastructure.repositories.repository_factory import get_repository_factory
            from infrastructure.repositories.core_project_repository import CoreProject
            from infrastructure.repositories.core_pack_repository import CorePack, PackPlatform
            from infrastructure.repositories.core_mod_repository import CoreMod
            from datetime import datetime
            import uuid
            
            # 获取扫描状态信息
            scan_state = self._active_scans[scan_id]
            factory = get_repository_factory()
            
            # 使用V5 Repository
            project_repo = factory.get_core_project_repo()
            pack_repo = factory.get_core_pack_repo()
            mod_repo = factory.get_core_mod_repo()
            
            project_name = f"扫描项目_{scan_id}"
            project_path = scan_state["target_path"]
            
            logger.info(f"📝 创建V5项目记录: {project_name}")
            
            # 1. 创建项目记录
            now = datetime.now().isoformat()
            project = CoreProject(
                uid=str(uuid.uuid4()),
                name=project_name,
                description=f"通过扫描发现的项目，包含 {statistics.get('mods_found', 0)} 个MOD。扫描路径: {project_path}",
                created_at=now,
                updated_at=now
            )
            
            project_uid = project_repo.create(project)
            logger.info(f"✅ 项目已创建: {project_uid}")
            
            # 2. 创建整合包记录
            pack = CorePack(
                uid=str(uuid.uuid4()),
                platform=PackPlatform.CUSTOM,
                slug=f"scan-pack-{scan_id[:8]}",
                title=f"扫描发现的整合包 {scan_id[:8]}",
                author="MC L10n Scanner",
                created_at=now,
                updated_at=now
            )
            
            pack_uid = pack_repo.create(pack)
            logger.info(f"✅ 整合包已创建: {pack_uid}")
            
            # 3. 保存发现的MOD
            mod_count = 0
            for item in discovered_items:
                if item.get("type") == "mod":
                    try:
                        mod = CoreMod(
                            uid=str(uuid.uuid4()),
                            modid=item.get("mod_id", f"unknown_mod_{mod_count}"),
                            slug=item.get("mod_id", f"unknown-mod-{mod_count}"),
                            name=item.get("name", "Unknown Mod"),
                            created_at=now,
                            updated_at=now
                        )
                        
                        mod_uid = mod_repo.create(mod)
                        mod_count += 1
                        logger.info(f"📦 MOD已保存: {mod.modid} -> {mod_uid}")
                        
                    except Exception as e:
                        logger.warning(f"保存MOD失败 {item.get('mod_id', 'unknown')}: {e}")
                        continue
            
            logger.info(f"💾 V5数据库保存完成: 项目={project_uid}, 整合包={pack_uid}, MOD数量={mod_count}")
            
            return {
                "success": True,
                "project_uid": project_uid,
                "pack_uid": pack_uid,
                "saved_mods": mod_count
            }
            
        except Exception as e:
            logger.error(f"❌ V5数据库保存失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }


    async def _process_jar_file(self, file_path: Path, statistics: Dict[str, Any], discovered_items: List[Dict[str, Any]]):
        """处理JAR文件（从原代码提取）"""
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
                        lang_content = {}
                        entries_count = 0
                        try:
                            with jar.open(lang_file_path) as lang_file:
                                lang_content = json.loads(lang_file.read().decode('utf-8'))
                                entries_count = len(lang_content)
                                statistics["total_translation_keys"] += entries_count
                                statistics["language_files_found"] += 1
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            logger.warning(f"无法解析语言文件: {lang_file_path}")
                            continue
                        
                        lang_item = {
                            "type": "language_file",
                            "language": lang_code,
                            "path": lang_file_path,
                            "mod_id": mod_metadata["mod_id"],
                            "key_count": entries_count,
                            "sample_keys": list(lang_content.keys())[:10]
                        }
                        mod_item["language_files"].append(lang_item)
                        
            except Exception as e:
                logger.warning(f"处理语言文件时出错 {file_path}: {e}")
            
            discovered_items.append(mod_item)

    async def _process_language_file(self, file_path: Path, statistics: Dict[str, Any], discovered_items: List[Dict[str, Any]]):
        """处理独立的语言文件"""
        try:
            # 识别语言文件类型和语言代码
            lang_code = file_path.stem
            file_type = file_path.suffix.lower()
            
            # 读取并解析文件内容
            content = {}
            entries_count = 0
            
            if file_type == '.json':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        entries_count = len(content)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    logger.warning(f"无法解析JSON语言文件: {file_path}")
                    return
                    
            elif file_type in ['.lang', '.properties']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                content[key.strip()] = value.strip()
                        entries_count = len(content)
                except UnicodeDecodeError:
                    logger.warning(f"无法解析语言文件: {file_path}")
                    return
            
            if entries_count > 0:
                statistics["language_files_found"] += 1
                statistics["total_translation_keys"] += entries_count
                
                # 创建模拟的MOD信息（基于目录结构）
                parent_dir = file_path.parent.name
                mod_id = parent_dir if parent_dir != 'lang' else file_path.parent.parent.name
                
                lang_item = {
                    "type": "standalone_language_file",
                    "language": lang_code,
                    "path": str(file_path),
                    "mod_id": mod_id,
                    "key_count": entries_count,
                    "format": file_type,
                    "sample_keys": list(content.keys())[:10] if content else []
                }
                discovered_items.append(lang_item)
                
                logger.info(f"发现语言文件: {file_path} ({entries_count} 个翻译条目)")
                
        except Exception as e:
            logger.warning(f"处理语言文件时出错 {file_path}: {e}")


    async def _quick_count_files(self, target_path: Path, scan_options: Dict[str, Any]) -> int:
        """快速统计文件数量，用于立即响应"""
        try:
            count = 0
            max_depth = 3  # 限制深度用于快速统计
            max_sample = 500  # 最大采样数量
            
            def quick_count_sync(path: Path, depth: int = 0) -> int:
                nonlocal count
                if depth > max_depth or count > max_sample:
                    return count
                
                try:
                    for item in path.iterdir():
                        if count > max_sample:
                            break
                        if item.is_file() and item.suffix.lower() in ['.jar', '.zip', '.json', '.lang', '.properties']:
                            count += 1
                        elif item.is_dir() and depth < max_depth:
                            quick_count_sync(item, depth + 1)
                except (PermissionError, OSError):
                    pass
                return count
            
            result = quick_count_sync(target_path)
            
            # 如果采样数量达到上限，则估算总数
            if result >= max_sample:
                # 基于采样估算，通常实际文件数量是采样的2-5倍
                estimated_total = result * 3
                logger.info(f"📊 快速采样发现 {result} 个文件，估算总数约 {estimated_total}")
                return estimated_total
            
            logger.info(f"📊 快速统计完成: {result} 个文件")
            return result
            
        except Exception as e:
            logger.warning(f"快速统计失败: {e}")
            return 100  # 默认估算值


# 全局实例
_simple_scanner_service: SimpleMinecraftScannerService = None


def get_simple_minecraft_scanner_service(db_path: str = "data/mc_l10n.db") -> SimpleMinecraftScannerService:
    """获取简化的Minecraft扫描服务实例"""
    global _simple_scanner_service
    if _simple_scanner_service is None:
        _simple_scanner_service = SimpleMinecraftScannerService(db_path)
    return _simple_scanner_service