"""
基于UPSERT逻辑的新扫描服务
使用重新设计的数据库结构，完全解决重复数据问题
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
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

# 导入重新设计的数据库类
from database_redesign import DatabaseRedesign

# 导入现有的智能识别组件
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src.mc_l10n.infrastructure.parsers.enhanced_parser import ModFileAnalyzer
    from src.mc_l10n.domain.scan_models import ModpackScanRule, MinecraftModScanRule
    HAS_ENHANCED_PARSER = True
except ImportError:
    logger.warning("Enhanced parser not available, using simplified parsing")
    HAS_ENHANCED_PARSER = False

logger = logging.getLogger(__name__)

class UpsertScanner:
    """基于UPSERT逻辑的扫描服务"""
    
    def __init__(self, db_path: str = "mc_l10n_v2.db"):
        self.db_redesign = DatabaseRedesign(db_path)
        self.db_path = db_path
        self.active_scans = {}
        
        # 初始化智能解析器
        if HAS_ENHANCED_PARSER:
            self.mod_analyzer = ModFileAnalyzer()
            self.modpack_rule = ModpackScanRule()
            self.mod_rule = MinecraftModScanRule()
            logger.info("使用增强型MOD信息解析器")
        else:
            self.mod_analyzer = None
            self.modpack_rule = None
            self.mod_rule = None
            logger.info("使用简化MOD信息解析器")
        
        # 确保数据库结构存在
        self.db_redesign.create_new_schema()
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件内容哈希"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {e}")
            return hashlib.sha256(str(file_path).encode()).hexdigest()  # 使用路径作为后备
    
    def extract_mod_info_from_jar(self, jar_path: Path) -> Tuple[Optional[Dict], List[Dict]]:
        """从JAR文件提取模组信息和语言文件 - 使用增强解析器"""
        try:
            if HAS_ENHANCED_PARSER and self.mod_analyzer:
                # 使用增强解析器获取完整信息
                analysis_result = self.mod_analyzer.analyze_mod_archive(jar_path)
                
                if analysis_result.get('errors'):
                    logger.warning(f"MOD解析存在错误 {jar_path}: {analysis_result['errors']}")
                
                # 提取MOD信息
                mod_info = analysis_result.get('mod_info', {})
                if not mod_info:
                    # 如果没有解析到信息，使用文件名作为后备
                    mod_info = {
                        "mod_id": jar_path.stem,
                        "name": jar_path.stem,
                        "version": "unknown"
                    }
                
                # 添加文件信息和加载器类型
                mod_info.update({
                    "file_path": str(jar_path),
                    "file_size": analysis_result.get('file_size', 0),
                    "mod_loader": analysis_result.get('loader_type', 'unknown')
                })
                
                # 转换语言文件格式
                language_files = []
                for lang_file in analysis_result.get('language_files', []):
                    # 从JAR中读取实际内容
                    try:
                        with zipfile.ZipFile(jar_path, 'r') as jar:
                            with jar.open(lang_file['path']) as f:
                                if lang_file['file_type'].name.lower() == 'json':
                                    content = json.load(f)
                                    if isinstance(content, dict):
                                        language_files.append({
                                            "file_path": lang_file['path'],
                                            "locale": lang_file['locale'],
                                            "namespace": lang_file['namespace'],
                                            "key_count": len(content),
                                            "entries": content
                                        })
                    except Exception as lang_error:
                        logger.warning(f"读取语言文件内容失败 {lang_file['path']}: {lang_error}")
                
                return mod_info, language_files
            
            else:
                # 回退到简化解析
                return self._extract_mod_info_simple(jar_path)
        
        except Exception as e:
            logger.error(f"解析JAR失败 {jar_path}: {e}")
            return None, []
    
    def _extract_mod_info_simple(self, jar_path: Path) -> Tuple[Optional[Dict], List[Dict]]:
        """简化的MOD信息提取（后备方案）"""
        try:
            mod_info = {"mod_id": jar_path.stem, "name": jar_path.stem, "version": "unknown"}
            language_files = []
            
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # 检测加载器类型和提取基本信息
                file_list = jar.namelist()
                
                if 'fabric.mod.json' in file_list:
                    mod_info['mod_loader'] = 'Fabric'
                    try:
                        with jar.open('fabric.mod.json') as f:
                            fabric_data = json.load(f)
                            mod_info.update({
                                'mod_id': fabric_data.get('id', jar_path.stem),
                                'name': fabric_data.get('name', jar_path.stem),
                                'version': fabric_data.get('version', 'unknown'),
                                'description': fabric_data.get('description', ''),
                                'authors': fabric_data.get('authors', [])
                            })
                    except Exception as e:
                        logger.warning(f"解析fabric.mod.json失败: {e}")
                
                elif 'META-INF/mods.toml' in file_list:
                    mod_info['mod_loader'] = 'Forge'
                    try:
                        with jar.open('META-INF/mods.toml') as f:
                            content = f.read().decode('utf-8')
                            # 简单TOML解析
                            for line in content.split('\n'):
                                line = line.strip()
                                if '=' in line and not line.startswith('#'):
                                    key, value = line.split('=', 1)
                                    key = key.strip()
                                    value = value.strip().strip('"\'')
                                    
                                    if key == 'modId':
                                        mod_info['mod_id'] = value
                                    elif key == 'displayName':
                                        mod_info['name'] = value
                                    elif key == 'version':
                                        mod_info['version'] = value
                                    elif key == 'description':
                                        mod_info['description'] = value
                    except Exception as e:
                        logger.warning(f"解析mods.toml失败: {e}")
                
                elif 'mcmod.info' in file_list:
                    mod_info['mod_loader'] = 'Forge'
                    try:
                        with jar.open('mcmod.info') as f:
                            mcmod_data = json.load(f)
                            if isinstance(mcmod_data, list) and mcmod_data:
                                mod_data = mcmod_data[0]
                                mod_info.update({
                                    'mod_id': mod_data.get('modid', jar_path.stem),
                                    'name': mod_data.get('name', jar_path.stem),
                                    'version': mod_data.get('version', 'unknown'),
                                    'description': mod_data.get('description', ''),
                                    'authors': mod_data.get('authorList', [])
                                })
                    except Exception as e:
                        logger.warning(f"解析mcmod.info失败: {e}")
                
                # 提取语言文件
                for file_path in file_list:
                    if self._is_language_file(file_path):
                        try:
                            with jar.open(file_path) as f:
                                if file_path.endswith('.json'):
                                    content = json.load(f)
                                    if isinstance(content, dict):
                                        locale = self._extract_locale(file_path)
                                        namespace = self._extract_namespace(file_path)
                                        
                                        language_files.append({
                                            "file_path": file_path,
                                            "locale": locale,
                                            "namespace": namespace,
                                            "key_count": len(content),
                                            "entries": content
                                        })
                        except Exception as lang_error:
                            logger.warning(f"解析语言文件失败 {file_path}: {lang_error}")
                
                # 添加文件信息
                mod_info.update({
                    "file_path": str(jar_path),
                    "file_size": jar_path.stat().st_size if jar_path.exists() else 0,
                })
            
            return mod_info, language_files
        
        except Exception as e:
            logger.error(f"简化解析JAR失败 {jar_path}: {e}")
            return None, []
    
    def _is_language_file(self, file_path: str) -> bool:
        """判断是否为语言文件"""
        patterns = [
            r"assets/[^/]+/lang/[^/]+\.(json|lang)$",
            r"data/[^/]+/lang/[^/]+\.(json|lang)$", 
            r"lang/[^/]+\.(json|lang)$",
        ]
        return any(re.search(pattern, file_path, re.IGNORECASE) for pattern in patterns)
    
    def _extract_locale(self, file_path: str) -> str:
        """从文件路径提取语言代码"""
        match = re.search(r"/([a-z]{2}_[a-z]{2})\.[^/]+$", file_path.lower())
        return match.group(1) if match else "unknown"
    
    def _extract_namespace(self, file_path: str) -> str:
        """从文件路径提取命名空间"""
        # assets/{namespace}/lang/{locale}.json
        match = re.search(r"assets/([^/]+)/lang/", file_path)
        if match:
            return match.group(1)
        
        # data/{namespace}/lang/{locale}.json  
        match = re.search(r"data/([^/]+)/lang/", file_path)
        if match:
            return match.group(1)
            
        return "minecraft"
    
    def detect_modpack_info(self, directory: str) -> Optional[Dict]:
        """检测组合包信息"""
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
            "mod_count": 0
        }
        
        try:
            # CurseForge 格式
            manifest_path = scan_path / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                        if manifest.get('manifestType') == 'minecraftModpack':
                            modpack_info.update({
                                "name": manifest.get('name', scan_path.name),
                                "version": manifest.get('version', 'unknown'),
                                "platform": "CurseForge",
                                "minecraft_version": manifest.get('minecraft', {}).get('version', 'unknown'),
                                "loader": manifest.get('minecraft', {}).get('modLoaders', [{}])[0].get('id', 'unknown').split('-')[0] if manifest.get('minecraft', {}).get('modLoaders') else 'unknown',
                                "author": manifest.get('author', 'unknown'),
                                "mod_count": len(manifest.get('files', []))
                            })
                            logger.info(f"检测到CurseForge组合包: {modpack_info['name']}")
                            return modpack_info
                except Exception as e:
                    logger.warning(f"解析CurseForge manifest失败: {e}")
            
            # Modrinth 格式
            modrinth_path = scan_path / "modrinth.index.json"
            if modrinth_path.exists():
                try:
                    with open(modrinth_path, 'r', encoding='utf-8') as f:
                        modrinth = json.load(f)
                        modpack_info.update({
                            "name": modrinth.get('name', scan_path.name),
                            "version": modrinth.get('versionId', 'unknown'),
                            "platform": "Modrinth",
                            "minecraft_version": modrinth.get('dependencies', {}).get('minecraft', 'unknown'),
                            "loader": list(modrinth.get('dependencies', {}).keys())[1] if len(modrinth.get('dependencies', {})) > 1 else 'unknown',
                            "mod_count": len(modrinth.get('files', []))
                        })
                        logger.info(f"检测到Modrinth组合包: {modpack_info['name']}")
                        return modpack_info
                except Exception as e:
                    logger.warning(f"解析Modrinth index失败: {e}")
            
            # MultiMC 格式
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
                                "platform": "MultiMC"
                            })
                    
                    if instance_cfg_path.exists():
                        with open(instance_cfg_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith('name='):
                                    modpack_info['name'] = line.split('=', 1)[1]
                                elif line.startswith('IntendedVersion='):
                                    modpack_info['minecraft_version'] = line.split('=', 1)[1]
                    
                    logger.info(f"检测到MultiMC实例: {modpack_info['name']}")
                    return modpack_info
                except Exception as e:
                    logger.warning(f"解析MultiMC配置失败: {e}")
            
            # 通用目录结构检测
            mods_dir = scan_path / "mods"
            if mods_dir.exists() and mods_dir.is_dir():
                jar_files = list(mods_dir.glob("*.jar"))
                if jar_files:
                    modpack_info.update({
                        "platform": "Generic",
                        "mod_count": len(jar_files)
                    })
                    logger.info(f"检测到通用组合包目录: {modpack_info['name']} ({len(jar_files)} mods)")
                    return modpack_info
            
        except Exception as e:
            logger.error(f"组合包信息检测失败 {directory}: {e}")
        
        return None
    
    async def scan_directory_with_upsert(self, scan_id: str, directory: str, incremental: bool = True):
        """使用UPSERT逻辑扫描目录"""
        logger.info(f"开始使用UPSERT逻辑进行{'增量' if incremental else '全量'}扫描: {directory}")
        
        try:
            scan_path = Path(directory)
            if not scan_path.exists():
                raise ValueError(f"目录不存在: {directory}")
            
            # 首先检测组合包信息
            modpack_info = self.detect_modpack_info(directory)
            if modpack_info:
                logger.info(f"识别组合包: {modpack_info['name']} ({modpack_info['platform']})")
            
            # 查找所有jar文件
            jar_files = []
            for root, dirs, files in os.walk(scan_path):
                for file in files:
                    if file.endswith('.jar'):
                        jar_files.append(Path(root) / file)
            
            # 初始化扫描状态，包含组合包信息
            scan_status = {
                "status": "scanning",
                "progress": 0,
                "total_files": len(jar_files),
                "processed_files": 0,
                "current_file": "",
                "total_mods": 0,
                "total_language_files": 0,
                "total_keys": 0,
                "scan_mode": "增量" if incremental else "全量",
                "started_at": datetime.now().isoformat()
            }
            
            # 添加组合包信息到扫描状态
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
            
            for i, jar_path in enumerate(jar_files):
                # 检查是否取消
                if scan_id in self.active_scans and self.active_scans[scan_id].get("status") == "cancelled":
                    logger.info(f"扫描被取消: {scan_id}")
                    break
                
                # 更新进度
                self.active_scans[scan_id].update({
                    "current_file": jar_path.name,
                    "processed_files": i + 1,
                    "progress": ((i + 1) / len(jar_files)) * 100
                })
                
                try:
                    # 计算文件哈希
                    file_hash = self.calculate_file_hash(jar_path)
                    
                    # UPSERT文件内容记录
                    with open(jar_path, 'rb') as f:
                        file_content = f.read()
                    
                    content_hash = self.db_redesign.upsert_file_content(
                        cursor, str(jar_path), file_content, 'jar'
                    )
                    
                    # 记录扫描发现
                    self.db_redesign.record_scan_discovery(cursor, scan_id, content_hash, 'file')
                    
                    # 提取模组信息
                    mod_info, language_files = self.extract_mod_info_from_jar(jar_path)
                    
                    if mod_info:
                        # UPSERT模组记录
                        mod_key = self.db_redesign.upsert_mod(cursor, mod_info, content_hash)
                        discovered_mods.add(mod_key)
                        self.db_redesign.record_scan_discovery(cursor, scan_id, mod_key, 'mod')
                        
                        # 处理语言文件
                        for lang_file in language_files:
                            if 'entries' in lang_file:
                                # UPSERT语言文件记录
                                lang_file_hash = self.db_redesign.upsert_language_file(
                                    cursor, mod_key, lang_file, lang_file['entries']
                                )
                                discovered_language_files.add(lang_file_hash)
                                self.db_redesign.record_scan_discovery(cursor, scan_id, lang_file_hash, 'language_file')
                                
                                # UPSERT翻译条目
                                self.db_redesign.upsert_translation_entries(
                                    cursor, lang_file_hash, lang_file['entries']
                                )
                                discovered_translations += len(lang_file['entries'])
                                
                                # 记录翻译条目发现
                                for key in lang_file['entries'].keys():
                                    entry_key = self.db_redesign.generate_entry_key(lang_file_hash, key)
                                    self.db_redesign.record_scan_discovery(cursor, scan_id, entry_key, 'translation_entry')
                    
                    # 每处理5个文件提交一次
                    if (i + 1) % 5 == 0:
                        conn.commit()
                        logger.debug(f"已处理 {i + 1}/{len(jar_files)} 个文件")
                    
                except Exception as file_error:
                    logger.error(f"处理文件 {jar_path} 时出错: {file_error}")
                    continue
                
                # 让出CPU时间
                if i % 10 == 0:
                    await asyncio.sleep(0.1)
            
            # 更新扫描会话统计
            cursor.execute("""
                UPDATE scan_sessions 
                SET status = 'completed', completed_at = ?, 
                    total_mods = ?, total_language_files = ?, total_keys = ?
                WHERE id = ?
            """, (
                datetime.now().isoformat(),
                len(discovered_mods),
                len(discovered_language_files),
                discovered_translations,
                scan_id
            ))
            
            conn.commit()
            conn.close()
            
            # 更新内存状态
            final_status = {
                "status": "completed",
                "progress": 100,
                "total_files": len(jar_files),
                "processed_files": len(jar_files),
                "total_mods": len(discovered_mods),
                "total_language_files": len(discovered_language_files),
                "total_keys": discovered_translations,
                "completed_at": datetime.now().isoformat()
            }
            self.active_scans[scan_id].update(final_status)
            
            logger.info(f"UPSERT扫描完成: {scan_id}, 发现{len(discovered_mods)}个模组，{len(discovered_language_files)}个语言文件，{discovered_translations}个翻译条目")
            
        except Exception as e:
            logger.error(f"UPSERT扫描失败: {e}")
            self.active_scans[scan_id] = {"status": "failed", "error": str(e)}
            
            # 更新数据库状态
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE scan_sessions SET status = 'failed' WHERE id = ?", (scan_id,))
                conn.commit()
                conn.close()
            except:
                pass
    
    def start_scan(self, directory: str, incremental: bool = True) -> str:
        """启动扫描，包含组合包信息检测"""
        scan_id = str(uuid.uuid4())
        
        # 检测组合包信息
        modpack_info = self.detect_modpack_info(directory)
        
        # 创建扫描会话记录，包含组合包信息
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if modpack_info:
            cursor.execute("""
                INSERT INTO scan_sessions (
                    id, directory, started_at, status, scan_mode,
                    modpack_name, modpack_platform, modpack_version, 
                    minecraft_version, mod_loader, expected_mod_count
                ) VALUES (?, ?, ?, 'scanning', ?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_id, directory, datetime.now().isoformat(), 
                "增量" if incremental else "全量",
                modpack_info['name'], modpack_info['platform'], 
                modpack_info['version'], modpack_info['minecraft_version'],
                modpack_info['loader'], modpack_info.get('mod_count', 0)
            ))
        else:
            cursor.execute("""
                INSERT INTO scan_sessions (id, directory, started_at, status, scan_mode)
                VALUES (?, ?, ?, 'scanning', ?)
            """, (scan_id, directory, datetime.now().isoformat(), "增量" if incremental else "全量"))
        
        conn.commit()
        conn.close()
        
        return scan_id
    
    def get_scan_status(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """获取扫描状态"""
        # 优先返回内存中的状态
        if scan_id in self.active_scans:
            return self.active_scans[scan_id]
        
        # 从数据库查询
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scan_sessions WHERE id = ?", (scan_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                status_data = dict(zip(columns, row))
                
                # 转换为前端期望的格式
                return {
                    "status": status_data.get("status", "unknown"),
                    "progress": 100 if status_data.get("status") == "completed" else 0,
                    "total_files": 0,
                    "processed_files": 0,
                    "total_mods": status_data.get("total_mods", 0),
                    "total_language_files": status_data.get("total_language_files", 0),
                    "total_keys": status_data.get("total_keys", 0),
                    "scan_mode": status_data.get("scan_mode", "未知"),
                    "started_at": status_data.get("started_at")
                }
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"查询扫描状态失败: {e}")
            return None
    
    def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        if scan_id in self.active_scans:
            self.active_scans[scan_id]["status"] = "cancelled"
            
            # 更新数据库状态
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE scan_sessions SET status = 'cancelled' WHERE id = ?", (scan_id,))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"更新取消状态失败: {e}")
            
            return True
        return False
    
    def get_scan_results(self, scan_id: str) -> Optional[Dict]:
        """获取扫描结果"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取基本统计
            stats = self.db_redesign.get_scan_statistics(scan_id)
            
            # 获取模组列表
            cursor.execute("""
                SELECT DISTINCT m.mod_key, m.mod_id, m.display_name, m.version, m.mod_loader
                FROM mods m
                JOIN scan_discoveries sd ON sd.content_hash = m.mod_key
                WHERE sd.scan_id = ? AND sd.content_type = 'mod'
            """, (scan_id,))
            
            mods = []
            for row in cursor.fetchall():
                mods.append({
                    "mod_key": row[0],
                    "mod_id": row[1],
                    "display_name": row[2],
                    "version": row[3],
                    "mod_loader": row[4]
                })
            
            # 获取语言文件列表
            cursor.execute("""
                SELECT DISTINCT lf.content_hash, lf.namespace, lf.locale, lf.key_count
                FROM language_files lf
                JOIN scan_discoveries sd ON sd.content_hash = lf.content_hash
                WHERE sd.scan_id = ? AND sd.content_type = 'language_file'
            """, (scan_id,))
            
            language_files = []
            for row in cursor.fetchall():
                language_files.append({
                    "hash": row[0],
                    "namespace": row[1],
                    "locale": row[2],
                    "key_count": row[3]
                })
            
            conn.close()
            
            return {
                "scan_id": scan_id,
                "mods": mods,
                "language_files": language_files,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"获取扫描结果失败: {e}")
            return None

# 全局实例
upsert_scanner = UpsertScanner()

if __name__ == "__main__":
    # 测试UPSERT扫描器
    import asyncio
    
    async def test_scanner():
        scanner = UpsertScanner("test_upsert.db")
        
        # 启动测试扫描
        scan_id = scanner.start_scan(".", incremental=True)
        print(f"启动扫描: {scan_id}")
        
        # 模拟扫描
        await scanner.scan_directory_with_upsert(scan_id, ".", incremental=True)
        
        # 获取结果
        results = scanner.get_scan_results(scan_id)
        print(f"扫描结果: {results}")
    
    asyncio.run(test_scanner())