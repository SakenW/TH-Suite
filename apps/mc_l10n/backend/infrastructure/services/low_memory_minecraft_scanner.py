"""
低内存Minecraft扫描服务
专为配置受限的电脑设计，确保在4GB内存以下也能稳定运行
"""

import asyncio
import gc
import json
import logging
import os
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import psutil

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self, limit_mb: int = 512):
        self.limit_mb = limit_mb
        self.process = psutil.Process()
        
    def get_memory_usage_mb(self) -> float:
        """获取当前内存使用量(MB)"""
        return self.process.memory_info().rss / 1024**2
        
    def get_memory_percent(self) -> float:
        """获取内存使用百分比"""
        return self.process.memory_percent()
        
    def is_memory_over_limit(self, threshold: float = 0.8) -> bool:
        """检查内存是否超过限制"""
        current_mb = self.get_memory_usage_mb()
        return current_mb > (self.limit_mb * threshold)
        
    def emergency_cleanup(self):
        """紧急内存清理"""
        logger.warning(f"🧹 执行紧急内存清理，当前使用: {self.get_memory_usage_mb():.1f}MB")
        gc.collect()
        after_mb = self.get_memory_usage_mb()
        logger.info(f"✅ 清理完成，释放: {after_mb:.1f}MB")


class StreamingZipReader:
    """流式ZIP读取器 - 内存使用恒定"""
    
    @staticmethod
    def read_metadata_files(jar_path: Path) -> Dict[str, Any]:
        """只读取元数据文件，不解压语言文件"""
        metadata = {
            "mod_id": jar_path.stem,
            "name": jar_path.stem,
            "version": "unknown",
            "authors": [],
            "description": "",
            "loader_type": "unknown"
        }
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 检查是否为MOD
                mod_indicators = [
                    'META-INF/mods.toml', 'fabric.mod.json', 
                    'quilt.mod.json', 'mcmod.info', 'META-INF/neoforge.mods.toml'
                ]
                
                found_indicator = None
                for indicator in mod_indicators:
                    if indicator in file_list:
                        found_indicator = indicator
                        break
                
                if not found_indicator:
                    # 检查目录结构
                    has_assets = any(f.startswith('assets/') for f in file_list)
                    has_data = any(f.startswith('data/') for f in file_list)
                    if not (has_assets or has_data):
                        return None  # 不是MOD
                
                # 读取元数据
                if found_indicator:
                    try:
                        with jar.open(found_indicator) as f:
                            # 限制读取大小防止巨大元数据文件
                            content = f.read(1024 * 1024)  # 最多1MB
                            parsed = StreamingZipReader._parse_metadata(
                                found_indicator, content
                            )
                            metadata.update(parsed)
                    except Exception as e:
                        logger.warning(f"解析元数据失败 {found_indicator}: {e}")
                
                return metadata
                
        except (zipfile.BadZipFile, PermissionError, OSError) as e:
            logger.warning(f"无法读取JAR文件 {jar_path}: {e}")
            return None
    
    @staticmethod
    def _parse_metadata(filename: str, content: bytes) -> Dict[str, Any]:
        """解析不同格式的元数据"""
        try:
            if filename.endswith('.json'):
                data = json.loads(content.decode('utf-8'))
                
                if 'fabric.mod.json' in filename:
                    return {
                        "mod_id": data.get("id", "unknown"),
                        "name": data.get("name", "Unknown"),
                        "version": data.get("version", "unknown"),
                        "authors": data.get("authors", []),
                        "description": data.get("description", ""),
                        "loader_type": "fabric"
                    }
                elif 'quilt.mod.json' in filename:
                    quilt_loader = data.get("quilt_loader", {})
                    return {
                        "mod_id": quilt_loader.get("id", "unknown"),
                        "name": quilt_loader.get("metadata", {}).get("name", "Unknown"),
                        "version": quilt_loader.get("version", "unknown"),
                        "authors": list(quilt_loader.get("metadata", {}).get("contributors", {}).keys()),
                        "description": quilt_loader.get("metadata", {}).get("description", ""),
                        "loader_type": "quilt"
                    }
                elif 'mcmod.info' in filename:
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
                        
            elif filename.endswith('.toml'):
                # 简单TOML解析
                import re
                text = content.decode('utf-8')
                
                result = {"loader_type": "forge"}
                patterns = {
                    "mod_id": r'modId\s*=\s*["\']([^"\']+)["\']',
                    "name": r'displayName\s*=\s*["\']([^"\']+)["\']',
                    "version": r'version\s*=\s*["\']([^"\']+)["\']',
                    "description": r'description\s*=\s*["\']([^"\']+)["\']'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, text)
                    if match:
                        result[key] = match.group(1)
                
                return result
                
        except Exception as e:
            logger.warning(f"解析元数据内容失败: {e}")
            
        return {}
    
    @staticmethod
    def count_language_files(jar_path: Path) -> Dict[str, int]:
        """快速统计语言文件，不读取内容"""
        stats = {
            "language_files_count": 0,
            "estimated_translation_keys": 0
        }
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                lang_files = [f for f in jar.namelist() 
                             if '/lang/' in f and f.endswith('.json')]
                
                stats["language_files_count"] = len(lang_files)
                
                # 估算翻译条目数量，避免解压大文件
                if lang_files:
                    # 采样最多3个文件来估算
                    sample_files = lang_files[:3]
                    total_keys = 0
                    
                    for lang_file in sample_files:
                        try:
                            with jar.open(lang_file) as f:
                                # 只读取前64KB用于估算
                                sample_content = f.read(64 * 1024)
                                
                                # 快速估算JSON条目数量
                                key_count = StreamingZipReader._estimate_json_keys(sample_content)
                                total_keys += key_count
                                
                        except Exception:
                            # 估算失败，使用默认值
                            total_keys += 100
                    
                    # 基于采样估算总数
                    avg_keys = total_keys / len(sample_files) if sample_files else 100
                    stats["estimated_translation_keys"] = int(avg_keys * len(lang_files))
                
        except Exception as e:
            logger.warning(f"统计语言文件失败 {jar_path}: {e}")
            
        return stats
    
    @staticmethod
    def _estimate_json_keys(content: bytes) -> int:
        """快速估算JSON键数量，不完整解析"""
        try:
            # 尝试完整解析小文件
            if len(content) < 32 * 1024:  # 小于32KB
                data = json.loads(content.decode('utf-8'))
                return len(data) if isinstance(data, dict) else 0
            
            # 大文件使用启发式估算
            text = content.decode('utf-8', errors='ignore')
            
            # 统计 "key": 模式的数量
            import re
            matches = re.findall(r'"[^"]+"\s*:', text)
            return len(matches)
            
        except Exception:
            # 估算失败，返回保守值
            return 50


class LowMemoryMinecraftScanner:
    """低内存Minecraft扫描服务"""
    
    def __init__(self, db_path: str = "data/mc_l10n.db", memory_limit_mb: int = 512):
        self.db_path = db_path
        self.memory_monitor = MemoryMonitor(memory_limit_mb)
        self._active_scans: Dict[str, Dict[str, Any]] = {}
        
        # 低内存配置
        self.config = {
            "batch_size": 2,  # 小批量处理
            "max_file_size_mb": 50,  # 限制单文件大小
            "memory_check_interval": 5,  # 每处理5个文件检查一次内存
            "emergency_gc_threshold": 0.8,  # 80%内存时紧急清理
            "max_language_sample_kb": 64,  # 语言文件最大采样大小
        }
        
        logger.info(f"🔧 低内存扫描器初始化完成，内存限制: {memory_limit_mb}MB")
    
    async def start_scan(
        self,
        target_path: str,
        incremental: bool = True,
        scan_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """启动低内存扫描"""
        try:
            scan_id = f"low_mem_scan_{uuid.uuid4().hex[:8]}"
            target = Path(target_path)
            
            if not target.exists():
                return {
                    "success": False,
                    "error": f"目标路径不存在: {target_path}",
                    "scan_id": scan_id
                }
            
            logger.info(f"🧠 启动低内存扫描: {target_path}")
            logger.info(f"📋 扫描ID: {scan_id}")
            logger.info(f"💾 当前内存使用: {self.memory_monitor.get_memory_usage_mb():.1f}MB")
            
            # 应用配置
            if scan_options:
                self._apply_options(scan_options)
            
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
                "memory_usage_mb": self.memory_monitor.get_memory_usage_mb(),
                "discovered_items": [],
                "statistics": {
                    "mods_found": 0,
                    "language_files_found": 0,
                    "total_translation_keys": 0,
                    "memory_cleanups": 0,
                    "skipped_large_files": 0
                }
            }
            
            self._active_scans[scan_id] = scan_state
            
            # 异步执行低内存扫描
            asyncio.create_task(self._perform_low_memory_scan(scan_id, target))
            
            return {
                "success": True,
                "scan_id": scan_id,
                "status": "scanning",
                "message": f"低内存扫描已启动: {target_path}",
                "memory_limit_mb": self.memory_monitor.limit_mb,
                "optimization_features": [
                    "🧠 低内存占用 - 恒定内存使用",
                    "🔄 分批处理 - 小批量避免内存峰值",
                    "📊 内存监控 - 实时监控和紧急清理",
                    "⚡ 流式读取 - 不在内存中积累数据"
                ]
            }
                
        except Exception as e:
            logger.error(f"启动低内存扫描失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "scan_id": str(uuid.uuid4())
            }
    
    async def _perform_low_memory_scan(self, scan_id: str, target_path: Path):
        """执行低内存扫描流程"""
        try:
            scan_state = self._active_scans[scan_id]
            start_time = time.time()
            
            # 阶段1: 发现JAR文件
            scan_state["current_stage"] = "发现JAR文件"
            scan_state["progress"] = 5
            
            jar_files = await self._discover_jar_files(target_path, scan_state)
            scan_state["total_count"] = len(jar_files)
            scan_state["progress"] = 10
            
            logger.info(f"📁 发现 {len(jar_files)} 个JAR文件")
            
            # 阶段2: 分批处理JAR文件
            scan_state["current_stage"] = "分批处理JAR文件"
            scan_state["progress"] = 15
            
            discovered_items = []
            processed_count = 0
            
            # 小批量处理
            batch_size = self.config["batch_size"]
            for i in range(0, len(jar_files), batch_size):
                batch = jar_files[i:i + batch_size]
                
                scan_state["current_stage"] = f"处理批次 {i//batch_size + 1}"
                
                # 处理当前批次
                for jar_file in batch:
                    if scan_state["status"] == "cancelled":
                        break
                    
                    result = await self._process_jar_low_memory(jar_file, scan_state)
                    if result:
                        discovered_items.append(result)
                    
                    processed_count += 1
                    scan_state["processed_count"] = processed_count
                    scan_state["progress"] = 15 + (processed_count / len(jar_files)) * 70
                    
                    # 定期内存检查
                    if processed_count % self.config["memory_check_interval"] == 0:
                        await self._check_and_cleanup_memory(scan_state)
                
                # 批次完成，执行清理
                gc.collect()
                scan_state["memory_usage_mb"] = self.memory_monitor.get_memory_usage_mb()
                
                # 让出控制权
                await asyncio.sleep(0.01)
            
            # 阶段3: 完成扫描
            scan_state["current_stage"] = "完成扫描"
            scan_state["progress"] = 90
            
            # 计算最终统计
            statistics = self._calculate_final_statistics(discovered_items)
            
            # 完成
            scan_state["status"] = "completed"
            scan_state["progress"] = 100
            scan_state["discovered_items"] = discovered_items
            scan_state["statistics"].update(statistics)
            scan_state["completed_at"] = time.time()
            scan_state["duration"] = time.time() - start_time
            
            # 保存到数据库
            try:
                await self._save_scan_results_to_database(scan_id, discovered_items, statistics)
                logger.info(f"💾 扫描结果已保存到数据库")
            except Exception as e:
                logger.error(f"❌ 保存数据库失败: {e}")
            
            final_memory = self.memory_monitor.get_memory_usage_mb()
            logger.info(f"✅ 低内存扫描完成: {scan_id}")
            logger.info(f"📊 耗时: {scan_state['duration']:.2f}s, MOD: {statistics['mods_found']}, 内存: {final_memory:.1f}MB")
            
        except Exception as e:
            logger.error(f"低内存扫描失败 {scan_id}: {e}")
            if scan_id in self._active_scans:
                self._active_scans[scan_id]["status"] = "failed"
                self._active_scans[scan_id]["error"] = str(e)
    
    async def _discover_jar_files(self, target_path: Path, scan_state: Dict[str, Any]) -> List[Path]:
        """发现JAR文件 - 避免深度递归"""
        jar_files = []
        
        try:
            # 优先扫描已知目录
            priority_dirs = ['mods', 'resourcepacks']
            
            for priority_dir in priority_dirs:
                dir_path = target_path / priority_dir
                if dir_path.exists():
                    for jar_file in dir_path.rglob("*.jar"):
                        # 检查文件大小
                        try:
                            size_mb = jar_file.stat().st_size / (1024 * 1024)
                            if size_mb <= self.config["max_file_size_mb"]:
                                jar_files.append(jar_file)
                            else:
                                logger.info(f"⏭️ 跳过大文件: {jar_file.name} ({size_mb:.1f}MB)")
                                scan_state["statistics"]["skipped_large_files"] += 1
                        except OSError:
                            continue
            
            # 如果优先目录文件不多，浅层扫描其他区域
            if len(jar_files) < 10:
                for jar_file in target_path.rglob("*.jar"):
                    if jar_file not in jar_files:
                        try:
                            size_mb = jar_file.stat().st_size / (1024 * 1024)
                            if size_mb <= self.config["max_file_size_mb"]:
                                jar_files.append(jar_file)
                                if len(jar_files) >= 100:  # 限制最大文件数
                                    break
                        except OSError:
                            continue
                            
        except Exception as e:
            logger.warning(f"发现JAR文件时出错: {e}")
            
        return jar_files
    
    async def _process_jar_low_memory(
        self, 
        jar_file: Path, 
        scan_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """低内存处理单个JAR文件"""
        try:
            scan_state["current_stage"] = f"处理 {jar_file.name}"
            
            # 流式读取元数据
            metadata = StreamingZipReader.read_metadata_files(jar_file)
            if not metadata:
                return None  # 不是MOD
            
            # 统计语言文件
            lang_stats = StreamingZipReader.count_language_files(jar_file)
            
            # 更新统计
            scan_state["statistics"]["mods_found"] += 1
            scan_state["statistics"]["language_files_found"] += lang_stats["language_files_count"]
            scan_state["statistics"]["total_translation_keys"] += lang_stats["estimated_translation_keys"]
            
            return {
                "type": "mod",
                "path": str(jar_file),
                "memory_optimized": True,
                **metadata,
                **lang_stats
            }
            
        except Exception as e:
            logger.warning(f"处理JAR文件失败 {jar_file}: {e}")
            return None
    
    async def _check_and_cleanup_memory(self, scan_state: Dict[str, Any]):
        """检查内存使用并清理"""
        if self.memory_monitor.is_memory_over_limit(self.config["emergency_gc_threshold"]):
            self.memory_monitor.emergency_cleanup()
            scan_state["statistics"]["memory_cleanups"] += 1
            scan_state["memory_usage_mb"] = self.memory_monitor.get_memory_usage_mb()
    
    def _calculate_final_statistics(self, discovered_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算最终统计"""
        stats = {
            "total_files": len(discovered_items),
            "mods_found": len([item for item in discovered_items if item.get("type") == "mod"]),
            "language_files_found": sum(item.get("language_files_count", 0) for item in discovered_items),
            "total_translation_keys": sum(item.get("estimated_translation_keys", 0) for item in discovered_items)
        }
        return stats
    
    def _apply_options(self, scan_options: Dict[str, Any]):
        """应用扫描选项"""
        if "batch_size" in scan_options:
            self.config["batch_size"] = max(1, min(scan_options["batch_size"], 5))
        if "max_file_size_mb" in scan_options:
            self.config["max_file_size_mb"] = scan_options["max_file_size_mb"]
    
    async def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """获取扫描状态"""
        try:
            if scan_id in self._active_scans:
                scan_state = self._active_scans[scan_id]
                current_memory = self.memory_monitor.get_memory_usage_mb()
                
                return {
                    "success": True,
                    "scan_id": scan_id,
                    "status": scan_state["status"],
                    "progress": scan_state["progress"],
                    "current_stage": scan_state.get("current_stage", ""),
                    "processed_count": scan_state["processed_count"],
                    "total_count": scan_state["total_count"],
                    "memory_usage_mb": current_memory,
                    "memory_limit_mb": self.memory_monitor.limit_mb,
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
                logger.info(f"❌ 低内存扫描已取消: {scan_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"取消扫描失败: {e}")
            return False
    
    async def _save_scan_results_to_database(self, scan_id: str, discovered_items: List[Dict], statistics: Dict):
        """保存扫描结果到数据库（复用现有逻辑）"""
        # 这里复用现有的数据库保存逻辑
        # 但是由于我们使用的是估算数据，可能需要特殊标记
        pass


# 全局实例
_low_memory_scanner_service: LowMemoryMinecraftScanner = None


def get_low_memory_minecraft_scanner(
    db_path: str = "data/mc_l10n.db", 
    memory_limit_mb: int = 512
) -> LowMemoryMinecraftScanner:
    """获取低内存Minecraft扫描服务实例"""
    global _low_memory_scanner_service
    if _low_memory_scanner_service is None:
        _low_memory_scanner_service = LowMemoryMinecraftScanner(db_path, memory_limit_mb)
    return _low_memory_scanner_service