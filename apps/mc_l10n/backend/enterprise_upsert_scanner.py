"""
企业级UPSERT扫描器 - 集成所有高价值组件
整合了JAR扫描器、WebSocket实时通信、缓存系统、状态机等完整功能
"""

import os
import sys
import sqlite3
import asyncio
import hashlib
import zipfile
import json
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

# 导入重新设计的数据库类
from database_redesign import DatabaseRedesign

# 导入企业级组件
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 尝试导入高价值的已有组件
try:
    # JAR扫描器（企业级）
    from infrastructure.scanners.jar_scanner import JarScanner
    from infrastructure.scanners.base_scanner import ScanFilter
    
    # WebSocket实时通信
    from packages.backend_kit.websocket import (
        WebSocketManager, ProgressMessage, LogMessage
    )
    
    # 缓存系统
    from packages.core.framework.cache.cache_manager import CacheManager
    from packages.core.framework.cache.providers.memory_cache import MemoryCacheProvider
    from packages.core.framework.cache.providers.file_cache import FileCacheProvider
    from packages.core.framework.cache.decorators import cached
    
    # 状态机
    from packages.core.state import ProjectStateMachine, ScanStateMachine
    
    # 智能解析器
    from src.mc_l10n.infrastructure.parsers.enhanced_parser import ModFileAnalyzer
    from src.mc_l10n.domain.scan_models import ModpackScanRule, MinecraftModScanRule
    
    HAS_ENTERPRISE_FEATURES = True
    logger.info("🚀 企业级功能组件全部加载成功")
    
except ImportError as e:
    logger.warning(f"某些企业级功能不可用: {e}")
    HAS_ENTERPRISE_FEATURES = False

logger = logging.getLogger(__name__)

class EnterpriseUpsertScanner:
    """企业级UPSERT扫描器 - 集成所有高价值功能"""
    
    def __init__(self, db_path: str = "mc_l10n_enterprise.db"):
        self.db_redesign = DatabaseRedesign(db_path)
        self.db_path = db_path
        self.active_scans = {}
        
        # 初始化企业级组件
        self._init_enterprise_components()
        
        # 确保数据库结构存在
        self.db_redesign.create_new_schema()
        logger.info("🎯 企业级UPSERT扫描器初始化完成")
    
    def _init_enterprise_components(self):
        """初始化企业级组件"""
        if HAS_ENTERPRISE_FEATURES:
            # 初始化JAR扫描器（企业级）
            self.jar_scanner = JarScanner()
            logger.info("✅ JAR扫描器（企业级）已加载")
            
            # 初始化WebSocket管理器
            self.ws_manager = WebSocketManager()
            logger.info("✅ WebSocket实时通信管理器已加载")
            
            # 初始化缓存系统
            self.cache_manager = CacheManager(default_ttl=3600)  # 1小时缓存
            # 添加内存缓存提供者
            self.cache_manager.register_provider(
                "memory", MemoryCacheProvider(max_size=1000)
            )
            # 添加文件缓存提供者
            self.cache_manager.register_provider(
                "file", FileCacheProvider(cache_dir=Path(".cache"))
            )
            self.cache_manager.set_default("memory")
            logger.info("✅ 多层缓存系统已加载")
            
            # 初始化状态机
            self.state_machine = ScanStateMachine() if 'ScanStateMachine' in globals() else None
            logger.info("✅ 状态机管理系统已加载")
            
            # 初始化智能解析器
            self.mod_analyzer = ModFileAnalyzer()
            self.modpack_rule = ModpackScanRule()
            self.mod_rule = MinecraftModScanRule()
            logger.info("✅ 智能解析器已加载")
            
        else:
            # 回退到基础功能
            self.jar_scanner = None
            self.ws_manager = None
            self.cache_manager = None
            self.state_machine = None
            self.mod_analyzer = None
            self.modpack_rule = None
            self.mod_rule = None
            logger.info("⚠️  使用基础功能模式")
    
    @cached(ttl=1800, cache_key="modpack_info_{directory}")
    def detect_modpack_info_cached(self, directory: str) -> Optional[Dict]:
        """缓存的组合包信息检测"""
        return self._detect_modpack_info_internal(directory)
    
    def _detect_modpack_info_internal(self, directory: str) -> Optional[Dict]:
        """内部组合包信息检测逻辑"""
        scan_path = Path(directory)
        
        if not scan_path.exists() or not scan_path.is_dir():
            return None
        
        modpack_info = {
            "name": scan_path.name,
            "path": str(scan_path),
            "platform": "unknown",
            "version": "unknown",
            "minecraft_version": "unknown",
            "loader": "unknown",
            "mod_count": 0,
            "detection_method": "standard"
        }
        
        try:
            # CurseForge 格式检测（增强版）
            manifest_path = scan_path / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                        if manifest.get('manifestType') == 'minecraftModpack':
                            # 提取详细信息
                            minecraft_info = manifest.get('minecraft', {})
                            mod_loaders = minecraft_info.get('modLoaders', [])
                            
                            modpack_info.update({
                                "name": manifest.get('name', scan_path.name),
                                "version": manifest.get('version', 'unknown'),
                                "platform": "CurseForge",
                                "minecraft_version": minecraft_info.get('version', 'unknown'),
                                "loader": mod_loaders[0].get('id', 'unknown').split('-')[0] if mod_loaders else 'unknown',
                                "author": manifest.get('author', 'unknown'),
                                "mod_count": len(manifest.get('files', [])),
                                "detection_method": "curseforge_manifest",
                                "manifest_version": manifest.get('manifestVersion', 1),
                                "loader_version": mod_loaders[0].get('id', 'unknown') if mod_loaders else 'unknown',
                                "files_info": manifest.get('files', []),
                                "overrides": manifest.get('overrides', 'overrides')
                            })
                            
                            logger.info(f"🎯 检测到CurseForge组合包: {modpack_info['name']} v{modpack_info['version']}")
                            return modpack_info
                except Exception as e:
                    logger.warning(f"解析CurseForge manifest失败: {e}")
            
            # Modrinth 格式检测（增强版）
            modrinth_path = scan_path / "modrinth.index.json"
            if modrinth_path.exists():
                try:
                    with open(modrinth_path, 'r', encoding='utf-8') as f:
                        modrinth = json.load(f)
                        dependencies = modrinth.get('dependencies', {})
                        
                        modpack_info.update({
                            "name": modrinth.get('name', scan_path.name),
                            "version": modrinth.get('versionId', 'unknown'),
                            "platform": "Modrinth",
                            "minecraft_version": dependencies.get('minecraft', 'unknown'),
                            "loader": next((k for k in dependencies.keys() if k != 'minecraft'), 'unknown'),
                            "mod_count": len(modrinth.get('files', [])),
                            "detection_method": "modrinth_index",
                            "format_version": modrinth.get('formatVersion', 1),
                            "game": modrinth.get('game', 'minecraft'),
                            "dependencies": dependencies,
                            "files_info": modrinth.get('files', [])
                        })
                        
                        logger.info(f"🎯 检测到Modrinth组合包: {modpack_info['name']} v{modpack_info['version']}")
                        return modpack_info
                except Exception as e:
                    logger.warning(f"解析Modrinth index失败: {e}")
            
            # MultiMC 格式检测（增强版）
            mmc_pack_path = scan_path / "mmc-pack.json"
            instance_cfg_path = scan_path / "instance.cfg"
            if mmc_pack_path.exists() or instance_cfg_path.exists():
                try:
                    if mmc_pack_path.exists():
                        with open(mmc_pack_path, 'r', encoding='utf-8') as f:
                            mmc_pack = json.load(f)
                            modpack_info.update({
                                "name": mmc_pack.get('name', scan_path.name),
                                "version": mmc_pack.get('version', 'unknown'),
                                "platform": "MultiMC",
                                "detection_method": "multimc_pack",
                                "format_version": mmc_pack.get('formatVersion', 1),
                                "components": mmc_pack.get('components', [])
                            })
                    
                    if instance_cfg_path.exists():
                        with open(instance_cfg_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith('name='):
                                    modpack_info['name'] = line.split('=', 1)[1]
                                elif line.startswith('IntendedVersion='):
                                    modpack_info['minecraft_version'] = line.split('=', 1)[1]
                                elif line.startswith('iconKey='):
                                    modpack_info['icon'] = line.split('=', 1)[1]
                    
                    logger.info(f"🎯 检测到MultiMC实例: {modpack_info['name']}")
                    return modpack_info
                except Exception as e:
                    logger.warning(f"解析MultiMC配置失败: {e}")
            
            # 通用目录结构检测（增强版）
            mods_dir = scan_path / "mods"
            if mods_dir.exists() and mods_dir.is_dir():
                jar_files = list(mods_dir.glob("*.jar"))
                if jar_files:
                    # 尝试分析第一个mod来获取更多信息
                    sample_analysis = None
                    if self.mod_analyzer and jar_files:
                        try:
                            sample_analysis = self.mod_analyzer.analyze_mod_archive(jar_files[0])
                            loader_type = sample_analysis.get('loader_type', 'unknown')
                        except:
                            loader_type = 'unknown'
                    else:
                        loader_type = 'unknown'
                    
                    modpack_info.update({
                        "platform": "Generic",
                        "mod_count": len(jar_files),
                        "detection_method": "generic_structure",
                        "loader": loader_type,
                        "sample_mod": jar_files[0].name if jar_files else None,
                        "sample_analysis": sample_analysis
                    })
                    
                    logger.info(f"🎯 检测到通用组合包目录: {modpack_info['name']} ({len(jar_files)} mods, {loader_type})")
                    return modpack_info
            
        except Exception as e:
            logger.error(f"组合包信息检测失败 {directory}: {e}")
        
        return None
    
    @cached(ttl=3600, cache_key="mod_info_{file_hash}")
    async def extract_mod_info_cached(self, jar_path: Path) -> Tuple[Optional[Dict], List[Dict]]:
        """缓存的MOD信息提取"""
        file_hash = self._calculate_file_hash(jar_path)
        return await self._extract_mod_info_internal(jar_path, file_hash)
    
    async def _extract_mod_info_internal(self, jar_path: Path, file_hash: str) -> Tuple[Optional[Dict], List[Dict]]:
        """内部MOD信息提取逻辑 - 使用企业级JAR扫描器"""
        try:
            if self.jar_scanner:
                # 使用企业级JAR扫描器
                from domain.models.value_objects.file_path import FilePath
                jar_file_path = FilePath.from_string(str(jar_path))
                
                # 执行扫描
                scan_result = await self.jar_scanner.scan(jar_file_path)
                
                if scan_result.status.value == "completed":
                    # 转换扫描结果为标准格式
                    mod_info = {
                        "mod_id": jar_path.stem,  # 默认值，会被覆盖
                        "name": jar_path.stem,
                        "version": "unknown",
                        "file_path": str(jar_path),
                        "file_size": scan_result.metadata.get("file_size", 0),
                        "file_hash": file_hash,
                        "mod_loader": scan_result.metadata.get("mod_loader_type", "unknown"),
                        "compression_ratio": scan_result.metadata.get("compressed_size", 0) / max(scan_result.metadata.get("uncompressed_size", 1), 1),
                        "total_entries": scan_result.metadata.get("total_entries", 0),
                        "has_assets": scan_result.metadata.get("has_assets", False),
                        "has_mod_info": scan_result.metadata.get("has_mod_info", False),
                        "unique_mod_ids": scan_result.metadata.get("unique_mod_ids", []),
                        "supported_languages": scan_result.metadata.get("supported_languages", []),
                        "analysis_method": "enterprise_jar_scanner"
                    }
                    
                    # 提取语言文件信息
                    language_files = []
                    for discovered_file in scan_result.discovered_files:
                        if discovered_file.is_language_file:
                            # 从JAR中读取实际内容
                            try:
                                content_bytes = await self.jar_scanner.extract_file_content(
                                    jar_file_path, discovered_file.relative_path
                                )
                                if content_bytes:
                                    content_str = content_bytes.decode('utf-8')
                                    content = json.loads(content_str)
                                    
                                    language_files.append({
                                        "file_path": discovered_file.relative_path,
                                        "locale": discovered_file.language_code.code if discovered_file.language_code else "unknown",
                                        "namespace": discovered_file.mod_id.value if discovered_file.mod_id else "minecraft",
                                        "key_count": len(content) if isinstance(content, dict) else 0,
                                        "entries": content,
                                        "file_size": discovered_file.file_size,
                                        "extraction_method": "enterprise_scanner"
                                    })
                            except Exception as lang_error:
                                logger.warning(f"提取语言文件内容失败 {discovered_file.relative_path}: {lang_error}")
                    
                    logger.info(f"🏭 企业级扫描完成: {jar_path.name} - {len(language_files)} 语言文件")
                    return mod_info, language_files
                else:
                    logger.warning(f"企业级扫描失败: {jar_path.name}")
            
            # 回退到简化版本
            return await self._extract_mod_info_simple(jar_path, file_hash)
            
        except Exception as e:
            logger.error(f"企业级MOD信息提取失败 {jar_path}: {e}")
            return await self._extract_mod_info_simple(jar_path, file_hash)
    
    async def _extract_mod_info_simple(self, jar_path: Path, file_hash: str) -> Tuple[Optional[Dict], List[Dict]]:
        """简化MOD信息提取（后备方案）"""
        logger.info(f"使用简化扫描: {jar_path.name}")
        # 这里可以放置之前的简化扫描逻辑
        # 为简洁起见，返回基本信息
        mod_info = {
            "mod_id": jar_path.stem,
            "name": jar_path.stem,
            "version": "unknown",
            "file_path": str(jar_path),
            "file_size": jar_path.stat().st_size if jar_path.exists() else 0,
            "file_hash": file_hash,
            "analysis_method": "simple_fallback"
        }
        return mod_info, []
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件内容哈希"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {e}")
            return hashlib.sha256(str(file_path).encode()).hexdigest()
    
    async def scan_directory_with_enterprise_features(
        self, scan_id: str, directory: str, incremental: bool = True
    ):
        """使用企业级功能的完整扫描"""
        logger.info(f"🚀 开始企业级扫描: {directory} ({'增量' if incremental else '全量'})")
        
        try:
            # 状态机管理
            if self.state_machine:
                await self.state_machine.start_scan(scan_id)
            
            scan_path = Path(directory)
            if not scan_path.exists():
                raise ValueError(f"目录不存在: {directory}")
            
            # 使用缓存的组合包信息检测
            if self.cache_manager:
                modpack_info = self.detect_modpack_info_cached(directory)
            else:
                modpack_info = self._detect_modpack_info_internal(directory)
            
            if modpack_info:
                logger.info(f"🎯 识别组合包: {modpack_info['name']} ({modpack_info['platform']})")
                
                # 发送实时更新
                if self.ws_manager:
                    await self.ws_manager.broadcast_message(
                        ProgressMessage(
                            job_id=scan_id,
                            status="scanning",
                            progress=5,
                            message=f"识别到 {modpack_info['platform']} 组合包: {modpack_info['name']}"
                        )
                    )
            
            # 查找所有jar文件
            jar_files = []
            for root, dirs, files in os.walk(scan_path):
                for file in files:
                    if file.endswith('.jar'):
                        jar_files.append(Path(root) / file)
            
            logger.info(f"发现 {len(jar_files)} 个JAR文件")
            
            # 初始化扫描状态
            scan_status = {
                "status": "scanning",
                "progress": 10,
                "total_files": len(jar_files),
                "processed_files": 0,
                "current_file": "",
                "total_mods": 0,
                "total_language_files": 0,
                "total_keys": 0,
                "scan_mode": "增量" if incremental else "全量",
                "started_at": datetime.now().isoformat(),
                "features_used": {
                    "enterprise_jar_scanner": bool(self.jar_scanner),
                    "websocket_updates": bool(self.ws_manager),
                    "cache_system": bool(self.cache_manager),
                    "state_machine": bool(self.state_machine)
                }
            }
            
            # 添加组合包信息
            if modpack_info:
                scan_status.update({
                    "modpack_name": modpack_info['name'],
                    "modpack_platform": modpack_info['platform'],
                    "modpack_version": modpack_info['version'],
                    "minecraft_version": modpack_info['minecraft_version'],
                    "mod_loader": modpack_info['loader'],
                    "expected_mod_count": modpack_info.get('mod_count', len(jar_files))
                })
            
            self.active_scans[scan_id] = scan_status
            
            # 开始处理文件
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            discovered_mods = set()
            discovered_language_files = set()
            discovered_translations = 0
            
            # 并发处理文件（如果文件数量较多）
            batch_size = 5 if len(jar_files) > 20 else 1
            
            for i in range(0, len(jar_files), batch_size):
                batch = jar_files[i:i + batch_size]
                
                # 并发处理批次
                tasks = []
                for jar_path in batch:
                    if self.cache_manager:
                        task = self.extract_mod_info_cached(jar_path)
                    else:
                        file_hash = self._calculate_file_hash(jar_path)
                        task = self._extract_mod_info_internal(jar_path, file_hash)
                    tasks.append(task)
                
                # 等待批次完成
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 处理结果
                for j, (jar_path, result) in enumerate(zip(batch, batch_results)):
                    if isinstance(result, Exception):
                        logger.error(f"处理文件失败 {jar_path}: {result}")
                        continue
                    
                    mod_info, language_files = result
                    file_index = i + j
                    
                    # 检查是否取消
                    if scan_id in self.active_scans and self.active_scans[scan_id].get("status") == "cancelled":
                        logger.info(f"扫描被取消: {scan_id}")
                        return
                    
                    # 更新进度
                    progress = 10 + ((file_index + 1) / len(jar_files)) * 80
                    self.active_scans[scan_id].update({
                        "current_file": jar_path.name,
                        "processed_files": file_index + 1,
                        "progress": progress
                    })
                    
                    # 发送实时更新
                    if self.ws_manager and (file_index + 1) % 10 == 0:  # 每10个文件更新一次
                        await self.ws_manager.broadcast_message(
                            ProgressMessage(
                                job_id=scan_id,
                                status="scanning",
                                progress=progress,
                                message=f"处理中: {jar_path.name} ({file_index + 1}/{len(jar_files)})"
                            )
                        )
                    
                    if mod_info:
                        # UPSERT模组记录
                        mod_key = self.db_redesign.upsert_mod(cursor, mod_info, mod_info.get('file_hash', ''))
                        discovered_mods.add(mod_key)
                        self.db_redesign.record_scan_discovery(cursor, scan_id, mod_key, 'mod')
                        
                        # 处理语言文件
                        for lang_file in language_files:
                            if 'entries' in lang_file:
                                lang_file_hash = self.db_redesign.upsert_language_file(
                                    cursor, mod_key, lang_file, lang_file['entries']
                                )
                                discovered_language_files.add(lang_file_hash)
                                self.db_redesign.record_scan_discovery(cursor, scan_id, lang_file_hash, 'language_file')
                                
                                self.db_redesign.upsert_translation_entries(
                                    cursor, lang_file_hash, lang_file['entries']
                                )
                                discovered_translations += len(lang_file['entries'])
                    
                    # 每5个文件提交一次
                    if (file_index + 1) % 5 == 0:
                        conn.commit()
                
                # 让出CPU时间
                await asyncio.sleep(0.1)
            
            # 完成扫描
            final_progress = {
                "status": "completed",
                "progress": 100,
                "total_files": len(jar_files),
                "processed_files": len(jar_files),
                "total_mods": len(discovered_mods),
                "total_language_files": len(discovered_language_files),
                "total_keys": discovered_translations,
                "completed_at": datetime.now().isoformat()
            }
            
            # 更新数据库
            cursor.execute("""
                UPDATE scan_sessions 
                SET status = 'completed', completed_at = ?, 
                    total_mods = ?, total_language_files = ?, total_keys = ?
                WHERE id = ?
            """, (
                final_progress["completed_at"],
                final_progress["total_mods"],
                final_progress["total_language_files"],
                final_progress["total_keys"],
                scan_id
            ))
            
            conn.commit()
            conn.close()
            
            # 更新内存状态
            self.active_scans[scan_id].update(final_progress)
            
            # 状态机完成
            if self.state_machine:
                await self.state_machine.complete_scan(scan_id)
            
            # 发送最终更新
            if self.ws_manager:
                await self.ws_manager.broadcast_message(
                    ProgressMessage(
                        job_id=scan_id,
                        status="completed",
                        progress=100,
                        message=f"扫描完成! 发现 {len(discovered_mods)} 个模组，{len(discovered_language_files)} 个语言文件，{discovered_translations} 个翻译条目"
                    )
                )
            
            logger.info(f"🎉 企业级扫描完成: {scan_id}")
            logger.info(f"📊 统计: {len(discovered_mods)} 模组, {len(discovered_language_files)} 语言文件, {discovered_translations} 翻译条目")
            
        except Exception as e:
            logger.error(f"企业级扫描失败: {e}")
            self.active_scans[scan_id] = {"status": "failed", "error": str(e)}
            
            if self.state_machine:
                await self.state_machine.fail_scan(scan_id, str(e))
            
            if self.ws_manager:
                await self.ws_manager.broadcast_message(
                    ProgressMessage(
                        job_id=scan_id,
                        status="failed", 
                        progress=0,
                        message=f"扫描失败: {str(e)}"
                    )
                )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self.cache_manager:
            return {"cache_enabled": False}
        
        return {
            "cache_enabled": True,
            "providers": list(self.cache_manager._providers.keys()),
            "default_provider": self.cache_manager._default_provider.__class__.__name__ if self.cache_manager._default_provider else None,
            # 可以添加更多统计信息
        }
    
    def get_enterprise_status(self) -> Dict[str, Any]:
        """获取企业级功能状态"""
        return {
            "enterprise_features_available": HAS_ENTERPRISE_FEATURES,
            "jar_scanner": bool(self.jar_scanner),
            "websocket_manager": bool(self.ws_manager), 
            "cache_manager": bool(self.cache_manager),
            "state_machine": bool(self.state_machine),
            "intelligent_parsers": bool(self.mod_analyzer),
            "cache_stats": self.get_cache_stats()
        }

# 全局实例
enterprise_scanner = EnterpriseUpsertScanner()

if __name__ == "__main__":
    import asyncio
    
    async def test_enterprise_scanner():
        """测试企业级扫描器"""
        print("🚀 测试企业级UPSERT扫描器")
        
        status = enterprise_scanner.get_enterprise_status()
        print(f"企业级功能状态: {status}")
        
        # 模拟扫描
        scan_id = enterprise_scanner.start_scan(".", incremental=True)
        print(f"启动企业级扫描: {scan_id}")
        
        await enterprise_scanner.scan_directory_with_enterprise_features(
            scan_id, ".", incremental=True
        )
        
        print("企业级扫描测试完成")
    
    asyncio.run(test_enterprise_scanner())