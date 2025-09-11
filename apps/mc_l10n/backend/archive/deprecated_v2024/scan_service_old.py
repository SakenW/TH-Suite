#!/usr/bin/env python
"""
扫描服务 V6
集成现有DDD扫描器功能到V6架构
输出到V6表结构，支持工作队列异步处理
"""

import asyncio
import json
import logging
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib

from ..database.core.manager import get_global_database_manager
from ..database.repositories import (
    ModRepository, 
    LanguageFileRepository,
    TranslationEntryRepository
)
from packages.core.data.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ScanResultCache(BaseRepository):
    """扫描结果缓存"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager, "cache_scan_results")
    
    async def get_cached_result(self, scan_path: str, file_hash: str) -> Optional[Dict[str, Any]]:
        """获取缓存的扫描结果"""
        sql = """
        SELECT result_json FROM cache_scan_results 
        WHERE scan_path = ? AND scan_hash = ? 
        AND valid_until > datetime('now')
        """
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql, (scan_path, file_hash)).fetchone()
            if result:
                return json.loads(result['result_json'])
        return None
    
    async def save_scan_result(self, scan_path: str, file_hash: str, result: Dict[str, Any], ttl_hours: int = 24):
        """保存扫描结果到缓存"""
        from datetime import datetime, timedelta
        
        valid_until = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
        
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache_scan_results 
                (scan_path, scan_hash, result_json, valid_until, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                scan_path, 
                file_hash, 
                json.dumps(result, ensure_ascii=False),
                valid_until,
                datetime.now().isoformat()
            ))


class ModScanner:
    """MOD扫描器核心类"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.mod_repo = ModRepository(db_manager)
        self.lang_file_repo = LanguageFileRepository(db_manager) 
        self.translation_repo = TranslationEntryRepository(db_manager)
        self.cache = ScanResultCache(db_manager)
    
    def _extract_version_from_filename(self, filename: str) -> str:
        """从文件名中提取版本号"""
        name = Path(filename).stem
        
        version_patterns = [
            r"-mc\d+(?:\.\d+)*-(\d+(?:\.\d+)*)",
            r"-\d+(?:\.\d+)*-(\d+(?:\.\d+)*)",
            r"[_-]v(\d+(?:\.\d+)*(?:[.-](?:alpha|beta|rc|snapshot|SNAPSHOT)\d*)?)",
            r"-(\d+(?:\.\d+)*(?:[.-](?:alpha|beta|rc|snapshot|SNAPSHOT)\d*)?)$",
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "unknown"
    
    def _resolve_template_variables(self, template_str: str, file_path: str) -> str:
        """解析模板变量"""
        if not isinstance(template_str, str):
            return str(template_str)
            
        result = template_str
        
        if "${file.jarVersion}" in result:
            version = self._extract_version_from_filename(file_path)
            result = result.replace("${file.jarVersion}", version)
        
        return result
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    async def scan_jar_file(self, jar_path: Path) -> Dict[str, Any]:
        """扫描单个JAR文件"""
        try:
            # 计算文件哈希用于缓存
            file_hash = self._calculate_file_hash(jar_path)
            
            # 检查缓存
            cached_result = await self.cache.get_cached_result(str(jar_path), file_hash)
            if cached_result:
                logger.debug(f"使用缓存结果: {jar_path}")
                return cached_result
            
            result = {
                'jar_path': str(jar_path),
                'file_size': jar_path.stat().st_size,
                'file_hash': file_hash,
                'mod_info': None,
                'language_files': [],
                'errors': []
            }
            
            # 解析JAR文件
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # 提取MOD信息
                mod_info = await self._extract_mod_info(jar, jar_path)
                result['mod_info'] = mod_info
                
                # 提取语言文件
                if mod_info:
                    language_files = await self._extract_language_files(jar, mod_info)
                    result['language_files'] = language_files
            
            # 保存到缓存
            await self.cache.save_scan_result(str(jar_path), file_hash, result)
            
            return result
            
        except Exception as e:
            error_msg = f"扫描JAR文件失败 {jar_path}: {e}"
            logger.error(error_msg)
            return {
                'jar_path': str(jar_path),
                'errors': [error_msg],
                'mod_info': None,
                'language_files': []
            }
    
    async def _extract_mod_info(self, jar: zipfile.ZipFile, jar_path: Path) -> Optional[Dict[str, Any]]:
        """从JAR中提取MOD信息"""
        try:
            # 查找mods.toml文件（NeoForge/Forge）
            if 'META-INF/mods.toml' in jar.namelist():
                return await self._parse_mods_toml(jar)
            
            # 查找fabric.mod.json（Fabric）
            if 'fabric.mod.json' in jar.namelist():
                return await self._parse_fabric_mod_json(jar)
            
            # 查找mcmod.info（旧版Forge）
            if 'mcmod.info' in jar.namelist():
                return await self._parse_mcmod_info(jar)
            
            # 如果没有找到元数据文件，使用文件名猜测
            return {
                'modid': jar_path.stem.lower(),
                'name': jar_path.stem,
                'version': self._extract_version_from_filename(jar_path.name),
                'loader': 'unknown',
                'mc_version': 'unknown',
                'source': 'filename_guess'
            }
            
        except Exception as e:
            logger.error(f"提取MOD信息失败: {e}")
            return None
    
    async def _parse_mods_toml(self, jar: zipfile.ZipFile) -> Dict[str, Any]:
        """解析mods.toml文件"""
        try:
            import tomllib
            
            toml_content = jar.read('META-INF/mods.toml').decode('utf-8')
            toml_data = tomllib.loads(toml_content)
            
            # 获取第一个模组的信息
            mods = toml_data.get('mods', [])
            if not mods:
                return None
            
            mod = mods[0]
            
            # 获取MC版本和加载器信息
            dependencies = toml_data.get('dependencies', {})
            minecraft_dep = dependencies.get(mod['modId'], {}).get('minecraft', '')
            
            return {
                'modid': mod.get('modId', ''),
                'name': mod.get('displayName', mod.get('modId', '')),
                'version': mod.get('version', ''),
                'description': mod.get('description', ''),
                'authors': mod.get('authors', ''),
                'homepage': mod.get('displayURL', ''),
                'loader': 'forge',  # mods.toml通常是Forge/NeoForge
                'mc_version': minecraft_dep,
                'source': 'mods.toml'
            }
            
        except Exception as e:
            logger.error(f"解析mods.toml失败: {e}")
            return None
    
    async def _parse_fabric_mod_json(self, jar: zipfile.ZipFile) -> Dict[str, Any]:
        """解析fabric.mod.json文件"""
        try:
            json_content = jar.read('fabric.mod.json').decode('utf-8')
            fabric_data = json.loads(json_content)
            
            # 获取MC版本依赖
            depends = fabric_data.get('depends', {})
            minecraft_dep = depends.get('minecraft', '')
            
            return {
                'modid': fabric_data.get('id', ''),
                'name': fabric_data.get('name', fabric_data.get('id', '')),
                'version': fabric_data.get('version', ''),
                'description': fabric_data.get('description', ''),
                'authors': ', '.join(fabric_data.get('authors', [])),
                'homepage': fabric_data.get('contact', {}).get('homepage', ''),
                'loader': 'fabric',
                'mc_version': minecraft_dep,
                'source': 'fabric.mod.json'
            }
            
        except Exception as e:
            logger.error(f"解析fabric.mod.json失败: {e}")
            return None
    
    async def _parse_mcmod_info(self, jar: zipfile.ZipFile) -> Dict[str, Any]:
        """解析mcmod.info文件"""
        try:
            json_content = jar.read('mcmod.info').decode('utf-8')
            mcmod_data = json.loads(json_content)
            
            # mcmod.info通常是数组
            if isinstance(mcmod_data, list) and mcmod_data:
                mod = mcmod_data[0]
            else:
                mod = mcmod_data
            
            authors = mod.get('authorList', [])
            if isinstance(authors, list):
                authors = ', '.join(authors)
            
            return {
                'modid': mod.get('modid', ''),
                'name': mod.get('name', mod.get('modid', '')),
                'version': mod.get('version', ''),
                'description': mod.get('description', ''),
                'authors': authors,
                'homepage': mod.get('url', ''),
                'loader': 'forge',  # mcmod.info通常是旧版Forge
                'mc_version': mod.get('mcversion', ''),
                'source': 'mcmod.info'
            }
            
        except Exception as e:
            logger.error(f"解析mcmod.info失败: {e}")
            return None
    
    async def _extract_language_files(self, jar: zipfile.ZipFile, mod_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从JAR中提取语言文件"""
        language_files = []
        
        try:
            # 搜索语言文件模式
            lang_patterns = [
                r'assets/[^/]+/lang/([a-z]{2}_[a-z]{2})\.json$',  # JSON格式
                r'assets/[^/]+/lang/([a-z]{2}_[a-z]{2})\.lang$',  # .lang格式
                r'data/[^/]+/lang/([a-z]{2}_[a-z]{2})\.json$',   # 数据包语言文件
            ]
            
            for file_path in jar.namelist():
                for pattern in lang_patterns:
                    match = re.match(pattern, file_path, re.IGNORECASE)
                    if match:
                        locale = match.group(1).lower()
                        
                        try:
                            # 读取语言文件内容
                            content = jar.read(file_path).decode('utf-8')
                            
                            # 解析内容
                            if file_path.endswith('.json'):
                                translations = json.loads(content)
                                file_format = 'json'
                            else:
                                # .lang格式解析
                                translations = {}
                                for line in content.split('\n'):
                                    line = line.strip()
                                    if line and not line.startswith('#') and '=' in line:
                                        key, value = line.split('=', 1)
                                        translations[key.strip()] = value.strip()
                                file_format = 'lang'
                            
                            language_files.append({
                                'locale': locale,
                                'rel_path': file_path,
                                'format': file_format,
                                'size': len(content),
                                'translations': translations,
                                'entry_count': len(translations)
                            })
                            
                        except Exception as e:
                            logger.error(f"解析语言文件失败 {file_path}: {e}")
                            continue
            
        except Exception as e:
            logger.error(f"提取语言文件失败: {e}")
        
        return language_files


class ScanService:
    """扫描服务V6 - 集成到工作队列的扫描服务"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_global_database_manager()
        self.scanner = ModScanner(self.db_manager)
        self.active_scans = {}
    
    async def start_scan(self, target_path: str, incremental: bool = True, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """启动扫描任务"""
        try:
            if not os.path.exists(target_path):
                raise ValueError(f"路径不存在: {target_path}")
            
            # 生成扫描ID
            scan_id = hashlib.md5(f"{target_path}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
            
            # 创建扫描会话记录
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
            
            # 将扫描任务添加到工作队列
            await self._enqueue_scan_task(scan_id)
            
            logger.info(f"启动扫描任务: {scan_id}, 路径: {target_path}")
            
            return {"scan_id": scan_id}
            
        except Exception as e:
            logger.error(f"启动扫描失败: {e}")
            raise
    
    async def _enqueue_scan_task(self, scan_id: str):
        """将扫描任务加入工作队列"""
        scan_data = self.active_scans[scan_id]
        
        payload = {
            "scan_id": scan_id,
            "target_path": scan_data["target_path"],
            "incremental": scan_data["incremental"]
        }
        
        task_id = self.db_manager.work_queue.enqueue_task(
            task_type="scan_directory",
            payload=payload,
            priority=10
        )
        
        scan_data["task_id"] = task_id
    
    async def execute_scan_task(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行扫描任务（工作队列调用）"""
        scan_id = task_payload["scan_id"]
        target_path = Path(task_payload["target_path"])
        
        try:
            scan_data = self.active_scans.get(scan_id)
            if not scan_data:
                raise ValueError(f"扫描会话不存在: {scan_id}")
            
            scan_data["status"] = "scanning"
            
            # 收集JAR文件
            jar_files = []
            for root, dirs, files in os.walk(target_path):
                for file in files:
                    if file.endswith(".jar"):
                        jar_files.append(Path(root) / file)
            
            scan_data["total_files"] = len(jar_files)
            logger.info(f"扫描 {len(jar_files)} 个JAR文件")
            
            # 处理结果统计
            total_mods = 0
            total_language_files = 0
            total_keys = 0
            
            # 处理每个JAR文件
            for idx, jar_path in enumerate(jar_files):
                if scan_id not in self.active_scans:
                    break  # 扫描被取消
                
                # 更新进度
                scan_data["processed_files"] = idx + 1
                scan_data["progress"] = ((idx + 1) / len(jar_files)) * 100
                scan_data["current_file"] = jar_path.name
                
                # 扫描JAR文件
                jar_result = await self.scanner.scan_jar_file(jar_path)
                
                # 保存到数据库
                if jar_result.get("mod_info"):
                    await self._save_scan_result(jar_result)
                    
                    total_mods += 1
                    total_language_files += len(jar_result.get("language_files", []))
                    
                    for lang_file in jar_result.get("language_files", []):
                        total_keys += lang_file.get("entry_count", 0)
                
                # 更新统计
                scan_data["statistics"] = {
                    "total_mods": total_mods,
                    "total_language_files": total_language_files,
                    "total_keys": total_keys
                }
            
            # 完成扫描
            scan_data["status"] = "completed"
            scan_data["progress"] = 100.0
            scan_data["completed_at"] = datetime.now().isoformat()
            
            logger.info(f"扫描完成: {scan_id}, 找到 {total_mods} 个MOD")
            
            return scan_data
            
        except Exception as e:
            logger.error(f"执行扫描失败 {scan_id}: {e}")
            if scan_id in self.active_scans:
                self.active_scans[scan_id]["status"] = "error"
                self.active_scans[scan_id]["errors"].append(str(e))
            raise
    
    async def _save_scan_result(self, jar_result: Dict[str, Any]):
        """保存扫描结果到V6数据库"""
        try:
            mod_info = jar_result["mod_info"]
            language_files = jar_result.get("language_files", [])
            
            # 保存MOD信息
            from ..database.repositories.mod_repository import Mod, ModVersion
            
            # 创建或更新MOD记录
            existing_mod = await self.scanner.mod_repo.find_by_modid(mod_info["modid"])
            
            if existing_mod:
                mod_uid = existing_mod.uid
            else:
                mod = Mod(
                    modid=mod_info["modid"],
                    slug=mod_info["modid"],
                    name=mod_info["name"],
                    homepage=mod_info.get("homepage"),
                )
                mod_id = await self.scanner.mod_repo.create(mod)
                mod_record = await self.scanner.mod_repo.get_by_id(mod_id)
                mod_uid = mod_record.uid
            
            # 创建MOD版本记录
            mod_version = ModVersion(
                mod_uid=mod_uid,
                loader=mod_info.get("loader", "unknown"),
                mc_version=mod_info.get("mc_version", "unknown"),
                version=mod_info.get("version", "unknown"),
                meta_json={
                    "description": mod_info.get("description"),
                    "authors": mod_info.get("authors"),
                    "source": mod_info.get("source"),
                    "file_size": jar_result.get("file_size", 0),
                    "file_hash": jar_result.get("file_hash")
                },
                source=jar_result["jar_path"]
            )
            
            # 检查版本是否已存在
            existing_version = await self.scanner.mod_repo.find_exact_version(
                mod_uid, mod_version.loader, mod_version.mc_version, mod_version.version
            )
            
            if not existing_version:
                mod_version_id = await ModVersionRepository(self.db_manager).create(mod_version)
                mod_version_record = await ModVersionRepository(self.db_manager).get_by_id(mod_version_id)
                mod_version_uid = mod_version_record.uid
            else:
                mod_version_uid = existing_version.uid
            
            # 保存语言文件和翻译条目
            await self._save_language_files(mod_uid, language_files)
            
        except Exception as e:
            logger.error(f"保存扫描结果失败: {e}")
            raise
    
    async def _save_language_files(self, mod_uid: str, language_files: List[Dict[str, Any]]):
        """保存语言文件和翻译条目"""
        try:
            from ..database.repositories.language_file_repository import LanguageFile
            from ..database.repositories.translation_entry_repository import TranslationEntry
            
            for lang_file_data in language_files:
                # 创建语言文件记录
                lang_file = LanguageFile(
                    carrier_type="mod",
                    carrier_uid=mod_uid,
                    locale=lang_file_data["locale"],
                    rel_path=lang_file_data["rel_path"],
                    format=lang_file_data["format"],
                    size=lang_file_data["size"]
                )
                
                # 检查是否已存在
                existing_lang_file = await self.scanner.lang_file_repo.get_language_file_by_path(
                    mod_uid, lang_file_data["locale"], lang_file_data["rel_path"]
                )
                
                if existing_lang_file:
                    lang_file_uid = existing_lang_file.uid
                    # 更新大小
                    await self.scanner.lang_file_repo.update(lang_file)
                else:
                    lang_file_id = await self.scanner.lang_file_repo.create(lang_file)
                    lang_file_record = await self.scanner.lang_file_repo.get_by_id(lang_file_id)
                    lang_file_uid = lang_file_record.uid
                
                # 保存翻译条目
                translations = lang_file_data.get("translations", {})
                translation_entries = []
                
                for key, src_text in translations.items():
                    entry = TranslationEntry(
                        language_file_uid=lang_file_uid,
                        key=key,
                        src_text=str(src_text),
                        status="new"
                    )
                    translation_entries.append(entry)
                
                # 批量创建翻译条目
                if translation_entries:
                    await self.scanner.translation_repo.batch_create(translation_entries)
                
        except Exception as e:
            logger.error(f"保存语言文件失败: {e}")
            raise
    
    def get_scan_status(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """获取扫描状态"""
        return self.active_scans.get(scan_id)
    
    async def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        if scan_id in self.active_scans:
            self.active_scans[scan_id]["status"] = "cancelled"
            # 从活动扫描中移除
            del self.active_scans[scan_id]
            return True
        return False
    
    def list_active_scans(self) -> List[Dict[str, Any]]:
        """列出活动扫描"""
        return list(self.active_scans.values())


# 全局扫描服务实例
_scan_service_instance = None


def get_scan_service() -> ScanService:
    """获取全局扫描服务实例"""
    global _scan_service_instance
    if _scan_service_instance is None:
        _scan_service_instance = ScanService()
    return _scan_service_instance