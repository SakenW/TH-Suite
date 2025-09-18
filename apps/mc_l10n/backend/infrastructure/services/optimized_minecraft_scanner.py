"""
高性能Minecraft扫描服务
针对大型整合包优化，支持并发处理、智能缓存、分层扫描
"""

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
import zipfile
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScanConfig:
    """扫描配置"""
    max_concurrent_jars: int = 8  # 并发处理的JAR数量
    max_file_size_mb: int = 100   # 最大文件大小限制
    enable_cache: bool = True     # 启用缓存
    cache_ttl_hours: int = 24     # 缓存有效期
    skip_known_non_mods: bool = True  # 跳过已知非MOD文件
    deep_scan_threshold: int = 50     # 深度扫描阈值（文件数量）
    
    
@dataclass
class FileCache:
    """文件缓存信息"""
    file_hash: str
    mod_id: Optional[str]
    mod_metadata: Optional[Dict[str, Any]]
    language_files: List[Dict[str, Any]]
    last_scanned: float
    file_size: int
    

class OptimizedMinecraftScanner:
    """优化的Minecraft扫描服务"""
    
    def __init__(self, db_path: str = "data/mc_l10n.db"):
        self.db_path = db_path
        self._active_scans: Dict[str, Dict[str, Any]] = {}
        self._file_cache: Dict[str, FileCache] = {}
        self._thread_pool = ThreadPoolExecutor(max_workers=8)
        self.config = ScanConfig()
        
        # 已知非MOD文件模式（跳过以提高效率）
        self.known_non_mod_patterns = {
            'server.jar', 'minecraft_server', 'forge-', 'fabric-loader',
            'launcher', 'installer', 'modpack', '.old', '.backup', '.disabled',
            'OptiFine', 'log4j', 'asm-', 'guava-', 'gson-'
        }
        
        # 整合包常见目录结构（优先扫描）
        self.priority_directories = ['mods', 'resourcepacks', 'config']
        
        logger.info("🚀 优化Minecraft扫描服务已初始化")

    async def start_scan(
        self,
        target_path: str,
        incremental: bool = True,
        scan_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """启动优化的扫描流程"""
        try:
            scan_id = f"opt_scan_{uuid.uuid4().hex[:8]}"
            target = Path(target_path)
            
            if not target.exists():
                return {
                    "success": False,
                    "error": f"目标路径不存在: {target_path}",
                    "scan_id": scan_id
                }
            
            logger.info(f"🎯 启动优化扫描: {target_path}")
            logger.info(f"📋 扫描ID: {scan_id}")
            
            # 应用扫描选项
            if scan_options:
                self._apply_scan_options(scan_options)
            
            # 初始化扫描状态
            scan_state = {
                "scan_id": scan_id,
                "status": "scanning",
                "progress": 0,
                "target_path": target_path,
                "started_at": time.time(),
                "current_stage": "初始化",
                "processed_count": 0,
                "total_count": 0,
                "discovered_items": [],
                "statistics": {
                    "mods_found": 0,
                    "language_files_found": 0,
                    "total_translation_keys": 0,
                    "cache_hits": 0,
                    "new_files": 0
                }
            }
            
            self._active_scans[scan_id] = scan_state
            
            # 异步执行优化扫描
            asyncio.create_task(self._perform_optimized_scan(scan_id, target))
            
            return {
                "success": True,
                "scan_id": scan_id,
                "status": "scanning", 
                "message": f"优化扫描已启动: {target_path}",
                "optimization_features": [
                    "🔄 并发JAR处理",
                    "💾 智能缓存",
                    "📁 分层目录扫描", 
                    "⚡ 增量更新"
                ]
            }
                
        except Exception as e:
            logger.error(f"启动扫描失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "scan_id": str(uuid.uuid4())
            }

    async def _perform_optimized_scan(self, scan_id: str, target_path: Path):
        """执行优化的扫描流程"""
        try:
            scan_state = self._active_scans[scan_id]
            start_time = time.time()
            
            # 阶段1: 智能路径发现
            scan_state["current_stage"] = "智能路径发现"
            scan_state["progress"] = 5
            
            priority_files, secondary_files = await self._smart_file_discovery(
                target_path, scan_state
            )
            
            all_files = priority_files + secondary_files
            scan_state["total_count"] = len(all_files)
            scan_state["progress"] = 15
            
            logger.info(f"📁 发现文件: 优先={len(priority_files)}, 次要={len(secondary_files)}")
            
            # 阶段2: 缓存检查和过滤
            scan_state["current_stage"] = "缓存检查"
            scan_state["progress"] = 20
            
            cached_results, new_files = await self._check_cache(all_files, scan_state)
            
            logger.info(f"💾 缓存命中: {len(cached_results)}, 新文件: {len(new_files)}")
            scan_state["statistics"]["cache_hits"] = len(cached_results)
            scan_state["statistics"]["new_files"] = len(new_files)
            
            # 阶段3: 并发处理新文件
            if new_files:
                scan_state["current_stage"] = "并发处理JAR文件"
                scan_state["progress"] = 25
                
                new_results = await self._concurrent_jar_processing(
                    new_files, scan_state
                )
            else:
                new_results = []
            
            # 阶段4: 合并结果
            scan_state["current_stage"] = "合并结果"
            scan_state["progress"] = 90
            
            all_results = cached_results + new_results
            
            # 计算统计信息
            statistics = self._calculate_statistics(all_results)
            
            # 完成扫描
            scan_state["status"] = "completed"
            scan_state["progress"] = 100
            scan_state["discovered_items"] = all_results
            scan_state["statistics"].update(statistics)
            scan_state["completed_at"] = time.time()
            scan_state["duration"] = time.time() - start_time
            
            # 保存结果到数据库
            try:
                await self._save_scan_results_to_database(scan_id, all_results, statistics)
                logger.info(f"💾 扫描结果已保存到数据库")
            except Exception as e:
                logger.error(f"❌ 保存数据库失败: {e}")
            
            logger.info(f"✅ 优化扫描完成: {scan_id}")
            logger.info(f"📊 耗时: {scan_state['duration']:.2f}s, MOD: {statistics['mods_found']}, 翻译: {statistics['total_translation_keys']}")
            
        except Exception as e:
            logger.error(f"优化扫描失败 {scan_id}: {e}")
            if scan_id in self._active_scans:
                self._active_scans[scan_id]["status"] = "failed"
                self._active_scans[scan_id]["error"] = str(e)

    async def _smart_file_discovery(
        self, 
        target_path: Path, 
        scan_state: Dict[str, Any]
    ) -> Tuple[List[Path], List[Path]]:
        """智能文件发现 - 分层扫描策略"""
        priority_files = []
        secondary_files = []
        
        # 检测目录类型
        if self._is_modpack_directory(target_path):
            # 整合包模式：优先扫描已知目录
            priority_files = await self._scan_modpack_structure(target_path, scan_state)
            # 可选：扫描其他目录
            if len(priority_files) < self.config.deep_scan_threshold:
                secondary_files = await self._scan_remaining_directories(
                    target_path, set(f.parent for f in priority_files), scan_state
                )
        else:
            # 通用模式：递归扫描但有优化
            all_files = await self._optimized_recursive_scan(target_path, scan_state)
            # 按文件位置分类优先级
            priority_files, secondary_files = self._classify_file_priority(all_files)
        
        return priority_files, secondary_files

    def _is_modpack_directory(self, path: Path) -> bool:
        """检测是否为整合包目录"""
        # 检查是否包含典型的整合包目录结构
        expected_dirs = {'mods', 'config'}
        found_dirs = {d.name for d in path.iterdir() if d.is_dir()}
        
        # 如果包含mods目录，很可能是整合包
        return bool(expected_dirs.intersection(found_dirs))

    async def _scan_modpack_structure(
        self, 
        target_path: Path, 
        scan_state: Dict[str, Any]
    ) -> List[Path]:
        """扫描整合包结构 - 只扫描关键目录"""
        files = []
        
        for priority_dir in self.priority_directories:
            dir_path = target_path / priority_dir
            if dir_path.exists() and dir_path.is_dir():
                scan_state["current_stage"] = f"扫描 {priority_dir} 目录"
                await asyncio.sleep(0.001)  # 让出控制权
                
                # 对于mods目录，只扫描第一层
                if priority_dir == 'mods':
                    files.extend(await self._scan_mods_directory(dir_path))
                else:
                    files.extend(await self._scan_directory_shallow(dir_path))
        
        return files

    async def _scan_mods_directory(self, mods_path: Path) -> List[Path]:
        """专门扫描mods目录 - 只取JAR/ZIP文件"""
        files = []
        try:
            for item in mods_path.iterdir():
                if item.is_file() and item.suffix.lower() in ['.jar', '.zip']:
                    # 快速过滤明显非MOD的文件
                    if not self._is_likely_non_mod(item):
                        files.append(item)
                        
        except (PermissionError, OSError) as e:
            logger.warning(f"无法访问mods目录: {e}")
            
        return files

    def _is_likely_non_mod(self, file_path: Path) -> bool:
        """快速判断文件是否可能不是MOD"""
        if not self.config.skip_known_non_mods:
            return False
            
        name_lower = file_path.name.lower()
        return any(pattern in name_lower for pattern in self.known_non_mod_patterns)

    async def _check_cache(
        self, 
        files: List[Path], 
        scan_state: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Path]]:
        """检查缓存并过滤需要处理的文件"""
        cached_results = []
        new_files = []
        current_time = time.time()
        
        for file_path in files:
            file_key = str(file_path.absolute())
            
            # 检查文件是否在缓存中且有效
            if self.config.enable_cache and file_key in self._file_cache:
                cache_entry = self._file_cache[file_key]
                
                # 检查缓存是否过期
                cache_age_hours = (current_time - cache_entry.last_scanned) / 3600
                if cache_age_hours < self.config.cache_ttl_hours:
                    # 检查文件是否被修改
                    try:
                        current_size = file_path.stat().st_size
                        current_hash = await self._calculate_file_hash(file_path)
                        
                        if (current_size == cache_entry.file_size and 
                            current_hash == cache_entry.file_hash):
                            # 缓存有效，使用缓存结果
                            if cache_entry.mod_metadata:
                                cached_result = {
                                    "type": "mod",
                                    "path": str(file_path),
                                    "cache_hit": True,
                                    **cache_entry.mod_metadata,
                                    "language_files": cache_entry.language_files
                                }
                                cached_results.append(cached_result)
                            continue
                    except (OSError, PermissionError):
                        pass
            
            # 文件需要重新处理
            new_files.append(file_path)
        
        return cached_results, new_files

    async def _concurrent_jar_processing(
        self, 
        files: List[Path], 
        scan_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """并发处理JAR文件"""
        results = []
        semaphore = asyncio.Semaphore(self.config.max_concurrent_jars)
        
        async def process_single_jar(file_path: Path) -> Optional[Dict[str, Any]]:
            async with semaphore:
                return await self._process_jar_with_cache(file_path, scan_state)
        
        # 创建并发任务
        tasks = [process_single_jar(file_path) for file_path in files]
        
        # 执行并发处理，同时更新进度
        completed = 0
        total = len(tasks)
        
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                results.append(result)
            
            completed += 1
            progress = 25 + (completed / total) * 60  # 25% 到 85%
            scan_state["progress"] = progress
            scan_state["processed_count"] = completed
            scan_state["current_stage"] = f"处理JAR文件 ({completed}/{total})"
        
        return results

    async def _process_jar_with_cache(
        self, 
        file_path: Path, 
        scan_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """处理单个JAR文件并更新缓存"""
        try:
            # 在线程池中执行IO密集的操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._thread_pool, 
                self._process_jar_sync, 
                file_path
            )
            
            if result:
                # 更新缓存
                await self._update_file_cache(file_path, result)
                
            return result
            
        except Exception as e:
            logger.warning(f"处理JAR文件失败 {file_path}: {e}")
            return None

    def _process_jar_sync(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """同步处理JAR文件（在线程池中执行）"""
        try:
            # 检查文件大小限制
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.config.max_file_size_mb:
                logger.warning(f"文件过大，跳过: {file_path} ({file_size_mb:.1f}MB)")
                return None
            
            # 检查是否为MOD
            if not self._is_minecraft_mod_sync(file_path):
                return None
            
            # 提取MOD元数据
            mod_metadata = self._extract_mod_metadata_sync(file_path)
            if not mod_metadata:
                return None
            
            # 提取语言文件
            language_files = self._extract_language_files_sync(file_path)
            
            return {
                "type": "mod",
                "path": str(file_path),
                "cache_hit": False,
                **mod_metadata,
                "language_files": language_files
            }
            
        except Exception as e:
            logger.warning(f"同步处理JAR失败 {file_path}: {e}")
            return None

    def _is_minecraft_mod_sync(self, file_path: Path) -> bool:
        """同步版本的MOD检测"""
        try:
            with zipfile.ZipFile(file_path, 'r') as jar:
                file_list = set(jar.namelist())
                
                # 检查MOD元数据文件
                mod_indicators = {
                    'META-INF/mods.toml',  # Forge
                    'fabric.mod.json',     # Fabric
                    'quilt.mod.json',      # Quilt
                    'mcmod.info',          # 旧版Forge
                    'META-INF/neoforge.mods.toml'  # NeoForge
                }
                
                if file_list.intersection(mod_indicators):
                    return True
                
                # 检查典型MOD文件结构
                has_assets = any(f.startswith('assets/') for f in file_list)
                has_data = any(f.startswith('data/') for f in file_list)
                
                return has_assets or has_data
                
        except (zipfile.BadZipFile, PermissionError, OSError):
            return False

    def _extract_mod_metadata_sync(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """同步提取MOD元数据"""
        metadata = {
            "mod_id": file_path.stem,
            "name": file_path.stem,
            "version": "unknown",
            "authors": [],
            "description": "",
            "minecraft_version": "unknown",
            "loader_type": "unknown"
        }
        
        try:
            with zipfile.ZipFile(file_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 尝试读取各种元数据格式
                if 'fabric.mod.json' in file_list:
                    metadata.update(self._parse_fabric_metadata(jar))
                elif 'quilt.mod.json' in file_list:
                    metadata.update(self._parse_quilt_metadata(jar))
                elif 'META-INF/mods.toml' in file_list:
                    metadata.update(self._parse_forge_toml(jar))
                elif 'mcmod.info' in file_list:
                    metadata.update(self._parse_mcmod_info(jar))
                    
        except Exception as e:
            logger.warning(f"提取元数据失败 {file_path}: {e}")
            
        return metadata

    def _extract_language_files_sync(self, file_path: Path) -> List[Dict[str, Any]]:
        """同步提取语言文件信息"""
        language_files = []
        
        try:
            with zipfile.ZipFile(file_path, 'r') as jar:
                # 查找语言文件
                lang_files = [f for f in jar.namelist() 
                             if '/lang/' in f and f.endswith('.json')]
                
                for lang_file_path in lang_files:
                    try:
                        lang_code = Path(lang_file_path).stem
                        
                        # 快速读取文件计算条目数量（不存储内容）
                        with jar.open(lang_file_path) as lang_file:
                            content = json.loads(lang_file.read().decode('utf-8'))
                            entries_count = len(content) if isinstance(content, dict) else 0
                        
                        language_files.append({
                            "type": "language_file",
                            "language": lang_code,
                            "path": lang_file_path,
                            "key_count": entries_count,
                            "sample_keys": list(content.keys())[:5] if content else []
                        })
                        
                    except Exception as e:
                        logger.warning(f"处理语言文件失败 {lang_file_path}: {e}")
                        continue
                        
        except Exception as e:
            logger.warning(f"提取语言文件失败 {file_path}: {e}")
            
        return language_files

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        try:
            hash_obj = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception:
            return str(file_path.stat().st_mtime)

    async def _update_file_cache(self, file_path: Path, result: Dict[str, Any]):
        """更新文件缓存"""
        if not self.config.enable_cache:
            return
            
        try:
            file_key = str(file_path.absolute())
            file_hash = await self._calculate_file_hash(file_path)
            
            self._file_cache[file_key] = FileCache(
                file_hash=file_hash,
                mod_id=result.get("mod_id"),
                mod_metadata={k: v for k, v in result.items() 
                             if k not in ['language_files', 'cache_hit', 'type', 'path']},
                language_files=result.get("language_files", []),
                last_scanned=time.time(),
                file_size=file_path.stat().st_size
            )
        except Exception as e:
            logger.warning(f"更新缓存失败 {file_path}: {e}")

    def _calculate_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算扫描统计信息"""
        stats = {
            "total_files": len(results),
            "mods_found": 0,
            "language_files_found": 0,
            "total_translation_keys": 0
        }
        
        for result in results:
            if result.get("type") == "mod":
                stats["mods_found"] += 1
                lang_files = result.get("language_files", [])
                stats["language_files_found"] += len(lang_files)
                stats["total_translation_keys"] += sum(
                    lf.get("key_count", 0) for lf in lang_files
                )
        
        return stats

    # 元数据解析器方法
    def _parse_fabric_metadata(self, jar: zipfile.ZipFile) -> Dict[str, Any]:
        """解析Fabric元数据"""
        try:
            with jar.open('fabric.mod.json') as f:
                data = json.load(f)
                return {
                    "mod_id": data.get("id", "unknown"),
                    "name": data.get("name", "Unknown"),
                    "version": data.get("version", "unknown"),
                    "authors": data.get("authors", []),
                    "description": data.get("description", ""),
                    "loader_type": "fabric"
                }
        except Exception:
            return {}

    def _parse_quilt_metadata(self, jar: zipfile.ZipFile) -> Dict[str, Any]:
        """解析Quilt元数据"""
        try:
            with jar.open('quilt.mod.json') as f:
                data = json.load(f)
                quilt_loader = data.get("quilt_loader", {})
                return {
                    "mod_id": quilt_loader.get("id", "unknown"),
                    "name": quilt_loader.get("metadata", {}).get("name", "Unknown"),
                    "version": quilt_loader.get("version", "unknown"),
                    "authors": list(quilt_loader.get("metadata", {}).get("contributors", {}).keys()),
                    "description": quilt_loader.get("metadata", {}).get("description", ""),
                    "loader_type": "quilt"
                }
        except Exception:
            return {}

    def _parse_forge_toml(self, jar: zipfile.ZipFile) -> Dict[str, Any]:
        """解析Forge TOML元数据"""
        try:
            import re
            with jar.open('META-INF/mods.toml') as f:
                content = f.read().decode('utf-8')
                
                # 简单TOML解析
                metadata = {"loader_type": "forge"}
                patterns = {
                    "mod_id": r'modId\s*=\s*["\']([^"\']+)["\']',
                    "name": r'displayName\s*=\s*["\']([^"\']+)["\']',
                    "version": r'version\s*=\s*["\']([^"\']+)["\']',
                    "description": r'description\s*=\s*["\']([^"\']+)["\']'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, content)
                    if match:
                        metadata[key] = match.group(1)
                
                return metadata
        except Exception:
            return {}

    def _parse_mcmod_info(self, jar: zipfile.ZipFile) -> Dict[str, Any]:
        """解析旧版Forge元数据"""
        try:
            with jar.open('mcmod.info') as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    mod_info = data[0]
                    return {
                        "mod_id": mod_info.get("modid", "unknown"),
                        "name": mod_info.get("name", "Unknown"),
                        "version": mod_info.get("version", "unknown"),
                        "authors": mod_info.get("authorList", []),
                        "description": mod_info.get("description", ""),
                        "loader_type": "forge"
                    }
        except Exception:
            return {}

    async def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """获取扫描状态"""
        try:
            if scan_id in self._active_scans:
                scan_state = self._active_scans[scan_id]
                return {
                    "success": True,
                    "scan_id": scan_id,
                    "status": scan_state["status"],
                    "progress": scan_state["progress"],
                    "current_stage": scan_state.get("current_stage", ""),
                    "processed_count": scan_state["processed_count"],
                    "total_count": scan_state["total_count"],
                    "statistics": scan_state.get("statistics", {}),
                    "duration": time.time() - scan_state["started_at"] if scan_state["status"] == "scanning" else scan_state.get("duration", 0)
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

    def _apply_scan_options(self, scan_options: Dict[str, Any]):
        """应用扫描选项"""
        if "max_concurrent_jars" in scan_options:
            self.config.max_concurrent_jars = scan_options["max_concurrent_jars"]
        if "max_file_size_mb" in scan_options:
            self.config.max_file_size_mb = scan_options["max_file_size_mb"]
        if "enable_cache" in scan_options:
            self.config.enable_cache = scan_options["enable_cache"]

    async def _save_scan_results_to_database(self, scan_id: str, discovered_items: List[Dict], statistics: Dict):
        """保存扫描结果到数据库"""
        logger.info(f"🔧 保存优化扫描结果: scan_id={scan_id}, items={len(discovered_items)}")
        try:
            # 复用原有的保存逻辑
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
            
            project_name = f"优化扫描_{scan_id}"
            project_path = scan_state["target_path"]
            
            logger.info(f"📝 创建V5项目记录: {project_name}")
            
            # 1. 创建项目记录
            now = datetime.now().isoformat()
            project = CoreProject(
                uid=str(uuid.uuid4()),
                name=project_name,
                description=f"优化扫描发现的项目，包含 {statistics.get('mods_found', 0)} 个MOD。扫描路径: {project_path}。缓存命中: {scan_state.get('statistics', {}).get('cache_hits', 0)}",
                created_at=now,
                updated_at=now
            )
            
            project_uid = project_repo.create(project)
            logger.info(f"✅ 项目已创建: {project_uid}")
            
            # 2. 创建整合包记录
            pack = CorePack(
                uid=str(uuid.uuid4()),
                platform=PackPlatform.CUSTOM,
                slug=f"opt-scan-pack-{scan_id[:8]}",
                title=f"优化扫描整合包 {scan_id[:8]}",
                author="MC L10n Optimized Scanner",
                created_at=now,
                updated_at=now
            )
            
            pack_uid = pack_repo.create(pack)
            logger.info(f"✅ 整合包已创建: {pack_uid}")
            
            # 3. 批量保存发现的MOD
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
                        
                        if item.get("cache_hit"):
                            logger.info(f"💾 MOD已保存(缓存): {mod.modid} -> {mod_uid}")
                        else:
                            logger.info(f"📦 MOD已保存(新扫描): {mod.modid} -> {mod_uid}")
                        
                    except Exception as e:
                        logger.warning(f"保存MOD失败 {item.get('mod_id', 'unknown')}: {e}")
                        continue
            
            duration = scan_state.get("duration", 0)
            cache_hits = scan_state.get("statistics", {}).get("cache_hits", 0)
            logger.info(f"💾 优化扫描保存完成: 项目={project_uid}, 整合包={pack_uid}, MOD数量={mod_count}, 耗时={duration:.2f}s, 缓存命中={cache_hits}")
            
            return {
                "success": True,
                "project_uid": project_uid,
                "pack_uid": pack_uid,
                "saved_mods": mod_count,
                "duration": duration,
                "cache_hits": cache_hits
            }
            
        except Exception as e:
            logger.error(f"❌ 优化扫描数据库保存失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _optimized_recursive_scan(self, target_path: Path, scan_state: Dict[str, Any]) -> List[Path]:
        """优化的递归扫描 - 限制深度和文件数量"""
        files = []
        max_depth = 5
        max_files = 1000
        
        async def scan_recursive(path: Path, depth: int = 0):
            nonlocal files
            if depth > max_depth or len(files) > max_files:
                return
                
            try:
                items = list(path.iterdir())
                subdirs = []
                
                # 处理当前目录的文件
                for item in items:
                    if len(files) > max_files:
                        break
                        
                    if item.is_file() and item.suffix.lower() in ['.jar', '.zip']:
                        if not self._is_likely_non_mod(item):
                            files.append(item)
                    elif item.is_dir() and depth < max_depth:
                        subdirs.append(item)
                
                # 异步处理子目录
                for subdir in subdirs:
                    if len(files) <= max_files:
                        await scan_recursive(subdir, depth + 1)
                        await asyncio.sleep(0.001)  # 让出控制权
                        
            except (PermissionError, OSError) as e:
                logger.warning(f"无法访问目录 {path}: {e}")
        
        await scan_recursive(target_path)
        return files

    def _classify_file_priority(self, files: List[Path]) -> Tuple[List[Path], List[Path]]:
        """根据文件位置分类优先级"""
        priority_files = []
        secondary_files = []
        
        for file_path in files:
            # 检查文件路径是否在优先目录中
            path_parts = [p.name.lower() for p in file_path.parents]
            
            if any(priority_dir in path_parts for priority_dir in self.priority_directories):
                priority_files.append(file_path)
            else:
                secondary_files.append(file_path)
        
        return priority_files, secondary_files

    async def _scan_remaining_directories(self, target_path: Path, scanned_dirs: Set[Path], scan_state: Dict[str, Any]) -> List[Path]:
        """扫描剩余目录"""
        files = []
        
        try:
            for item in target_path.rglob("*.jar"):
                if item.parent not in scanned_dirs and not self._is_likely_non_mod(item):
                    files.append(item)
                    
            for item in target_path.rglob("*.zip"):
                if item.parent not in scanned_dirs and not self._is_likely_non_mod(item):
                    files.append(item)
                    
        except Exception as e:
            logger.warning(f"扫描剩余目录失败: {e}")
            
        return files[:100]  # 限制数量

    async def _scan_directory_shallow(self, dir_path: Path) -> List[Path]:
        """浅层目录扫描 - 只扫描2层"""
        files = []
        
        try:
            # 扫描当前层
            for item in dir_path.iterdir():
                if item.is_file() and item.suffix.lower() in ['.jar', '.zip']:
                    if not self._is_likely_non_mod(item):
                        files.append(item)
                        
            # 扫描第二层
            for subdir in dir_path.iterdir():
                if subdir.is_dir():
                    for item in subdir.iterdir():
                        if item.is_file() and item.suffix.lower() in ['.jar', '.zip']:
                            if not self._is_likely_non_mod(item):
                                files.append(item)
                                
        except (PermissionError, OSError) as e:
            logger.warning(f"浅层扫描失败 {dir_path}: {e}")
            
        return files


# 全局实例
_optimized_scanner_service: OptimizedMinecraftScanner = None


def get_optimized_minecraft_scanner(db_path: str = "data/mc_l10n.db") -> OptimizedMinecraftScanner:
    """获取优化的Minecraft扫描服务实例"""
    global _optimized_scanner_service
    if _optimized_scanner_service is None:
        _optimized_scanner_service = OptimizedMinecraftScanner(db_path)
    return _optimized_scanner_service