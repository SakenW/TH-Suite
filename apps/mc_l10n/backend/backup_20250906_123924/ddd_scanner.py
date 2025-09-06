#!/usr/bin/env python3
"""
基于DDD架构的扫描器服务
实现UPSERT逻辑，避免数据重复
"""
import sqlite3
import json
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import uuid
import asyncio
import structlog

logger = structlog.get_logger()


class DDDScannerService:
    """符合DDD设计的扫描服务"""
    
    def __init__(self, db_path: str = "mc_l10n_unified.db"):
        self.db_path = db_path
        self.current_scan_id: Optional[str] = None
        self.progress_callback = None
        
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
        return conn
    
    async def start_scan(
        self, 
        target_path: str, 
        project_id: Optional[str] = None,
        scan_type: str = 'full',
        incremental: bool = True,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """启动扫描任务"""
        self.current_scan_id = str(uuid.uuid4())
        project_id = project_id or 'default-project'
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 创建扫描会话
            cursor.execute("""
                INSERT INTO scan_sessions (
                    scan_id, project_id, scan_type, target_path, 
                    status, progress_percent, started_at
                ) VALUES (?, ?, ?, ?, 'scanning', 0, CURRENT_TIMESTAMP)
            """, (self.current_scan_id, project_id, scan_type, target_path))
            
            conn.commit()
            logger.info(f"开始扫描", scan_id=self.current_scan_id, path=target_path)
            
            # 异步执行扫描
            asyncio.create_task(self._execute_scan(
                self.current_scan_id, 
                target_path,
                project_id,
                scan_type
            ))
            
            return {
                "scan_id": self.current_scan_id,
                "status": "started",
                "message": "扫描任务已启动"
            }
            
        except Exception as e:
            logger.error(f"创建扫描会话失败: {e}")
            raise
        finally:
            conn.close()
    
    async def _execute_scan(
        self, 
        scan_id: str, 
        target_path: str,
        project_id: str,
        scan_type: str
    ):
        """执行扫描任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            path = Path(target_path)
            if not path.exists():
                raise ValueError(f"路径不存在: {target_path}")
            
            # 查找JAR文件
            jar_files = list(path.glob("**/*.jar"))
            total_files = len(jar_files)
            
            if total_files == 0:
                logger.warning("没有找到JAR文件")
                self._update_scan_status(scan_id, 'completed', 100, {
                    'total_mods': 0,
                    'total_language_files': 0,
                    'total_keys': 0
                })
                return
            
            logger.info(f"找到 {total_files} 个JAR文件")
            
            processed = 0
            total_mods = 0
            total_lang_files = 0
            total_keys = 0
            
            for jar_path in jar_files:
                try:
                    # 处理单个JAR文件
                    mod_info = await self._process_jar_file(
                        scan_id, 
                        jar_path,
                        project_id
                    )
                    
                    if mod_info:
                        total_mods += 1
                        total_lang_files += mod_info['language_files_count']
                        total_keys += mod_info['total_keys']
                    
                    processed += 1
                    progress = (processed / total_files) * 100
                    
                    # 更新进度
                    self._update_scan_progress(scan_id, progress, str(jar_path.name))
                    
                    # 触发进度回调
                    if self.progress_callback:
                        await self.progress_callback(scan_id, progress, {
                            'current_file': str(jar_path.name),
                            'processed': processed,
                            'total': total_files
                        })
                    
                    await asyncio.sleep(0.01)  # 避免阻塞
                    
                except Exception as e:
                    logger.error(f"处理JAR文件失败: {jar_path}", error=str(e))
                    continue
            
            # 扫描完成，更新统计信息
            statistics = {
                'total_mods': total_mods,
                'total_language_files': total_lang_files,
                'total_keys': total_keys,
                'scan_type': scan_type
            }
            
            self._update_scan_status(scan_id, 'completed', 100, statistics)
            
            # 发布领域事件
            self._publish_domain_event('ScanCompletedEvent', {
                'scan_id': scan_id,
                'project_id': project_id,
                'statistics': statistics
            })
            
            logger.info(f"扫描完成", scan_id=scan_id, statistics=statistics)
            
        except Exception as e:
            logger.error(f"扫描失败: {e}", scan_id=scan_id)
            self._update_scan_status(scan_id, 'failed', -1, error=str(e))
        finally:
            conn.close()
    
    async def _process_jar_file(
        self, 
        scan_id: str, 
        jar_path: Path,
        project_id: str
    ) -> Optional[Dict]:
        """处理单个JAR文件（实现UPSERT逻辑）"""
        
        try:
            # 计算文件哈希
            file_hash = self._calculate_file_hash(jar_path)
            file_size = jar_path.stat().st_size
            
            # 提取模组信息
            mod_info = self._extract_mod_info(jar_path)
            if not mod_info:
                return None
            
            mod_id = mod_info['mod_id']
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 检查模组是否已存在
            cursor.execute("""
                SELECT mod_id, file_hash FROM mods WHERE mod_id = ?
            """, (mod_id,))
            existing_mod = cursor.fetchone()
            
            # UPSERT模组信息
            if existing_mod:
                # 模组已存在，检查是否有更新
                if existing_mod['file_hash'] != file_hash:
                    # 文件已更新，更新模组信息
                    cursor.execute("""
                        UPDATE mods SET
                            name = ?,
                            display_name = ?,
                            version = ?,
                            minecraft_version = ?,
                            mod_loader = ?,
                            file_path = ?,
                            file_hash = ?,
                            metadata = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE mod_id = ?
                    """, (
                        mod_info['name'],
                        mod_info.get('display_name'),
                        mod_info.get('version'),
                        mod_info.get('minecraft_version'),
                        mod_info.get('mod_loader'),
                        str(jar_path),
                        file_hash,
                        json.dumps(mod_info.get('metadata', {})),
                        mod_id
                    ))
                    logger.info(f"更新模组: {mod_id}")
                else:
                    logger.debug(f"模组未变化，跳过: {mod_id}")
            else:
                # 新模组，插入数据
                cursor.execute("""
                    INSERT INTO mods (
                        mod_id, name, display_name, version,
                        minecraft_version, mod_loader, file_path, 
                        file_hash, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mod_id,
                    mod_info['name'],
                    mod_info.get('display_name'),
                    mod_info.get('version'),
                    mod_info.get('minecraft_version'),
                    mod_info.get('mod_loader'),
                    str(jar_path),
                    file_hash,
                    json.dumps(mod_info.get('metadata', {}))
                ))
                logger.info(f"新增模组: {mod_id}")
            
            # 关联模组到项目（如果还未关联）
            cursor.execute("""
                INSERT OR IGNORE INTO project_mods (
                    project_id, mod_id
                ) VALUES (?, ?)
            """, (project_id, mod_id))
            
            # 处理语言文件
            language_files = self._extract_language_files(jar_path)
            total_keys = 0
            
            for lang_code, lang_content in language_files.items():
                # 计算内容哈希
                content_hash = hashlib.md5(
                    json.dumps(lang_content, sort_keys=True).encode()
                ).hexdigest()
                
                file_id = f"{mod_id}_{lang_code}"
                
                # 检查语言文件是否已存在
                cursor.execute("""
                    SELECT file_id, content_hash FROM language_files 
                    WHERE mod_id = ? AND language_code = ?
                """, (mod_id, lang_code))
                existing_file = cursor.fetchone()
                
                entry_count = len(lang_content)
                total_keys += entry_count
                
                # UPSERT语言文件
                if existing_file:
                    if existing_file['content_hash'] != content_hash:
                        # 内容已更新
                        cursor.execute("""
                            UPDATE language_files SET
                                file_path = ?,
                                content_hash = ?,
                                entry_count = ?,
                                last_modified = CURRENT_TIMESTAMP
                            WHERE file_id = ?
                        """, (
                            f"assets/{mod_id}/lang/{lang_code}.json",
                            content_hash,
                            entry_count,
                            file_id
                        ))
                        
                        # 更新翻译条目
                        self._update_translation_entries(
                            cursor, file_id, lang_content
                        )
                        logger.debug(f"更新语言文件: {file_id}")
                else:
                    # 新语言文件
                    cursor.execute("""
                        INSERT INTO language_files (
                            file_id, mod_id, language_code, file_path,
                            file_format, content_hash, entry_count
                        ) VALUES (?, ?, ?, ?, 'json', ?, ?)
                    """, (
                        file_id,
                        mod_id,
                        lang_code,
                        f"assets/{mod_id}/lang/{lang_code}.json",
                        content_hash,
                        entry_count
                    ))
                    
                    # 插入翻译条目
                    self._insert_translation_entries(
                        cursor, file_id, lang_content
                    )
                    logger.debug(f"新增语言文件: {file_id}")
            
            # 记录扫描发现
            cursor.execute("""
                INSERT INTO scan_discoveries (
                    discovery_id, scan_id, mod_id, mod_name, 
                    mod_version, file_path, file_size,
                    language_files_count, total_keys, is_processed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE)
            """, (
                str(uuid.uuid4()),
                scan_id,
                mod_id,
                mod_info['name'],
                mod_info.get('version'),
                str(jar_path),
                file_size,
                len(language_files),
                total_keys
            ))
            
            conn.commit()
            
            return {
                'mod_id': mod_id,
                'language_files_count': len(language_files),
                'total_keys': total_keys
            }
            
        except Exception as e:
            logger.error(f"处理JAR文件失败: {jar_path}", error=str(e))
            return None
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _extract_mod_info(self, jar_path: Path) -> Optional[Dict]:
        """提取模组信息"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # 尝试不同的元数据文件
                metadata_files = [
                    'META-INF/mods.toml',  # Forge 1.13+
                    'mcmod.info',          # Forge 1.12-
                    'fabric.mod.json',     # Fabric
                    'quilt.mod.json'       # Quilt
                ]
                
                for meta_file in metadata_files:
                    if meta_file in jar.namelist():
                        content = jar.read(meta_file).decode('utf-8', errors='ignore')
                        
                        # 解析不同格式的元数据
                        if meta_file.endswith('.json'):
                            data = json.loads(content)
                            return self._parse_json_metadata(data, meta_file)
                        elif meta_file.endswith('.toml'):
                            # 简单的TOML解析
                            return self._parse_toml_metadata(content)
                
                # 如果没有元数据文件，使用文件名作为模组ID
                mod_id = jar_path.stem.lower().replace(' ', '_')
                return {
                    'mod_id': mod_id,
                    'name': jar_path.stem,
                    'version': 'unknown',
                    'mod_loader': 'unknown'
                }
                
        except Exception as e:
            logger.error(f"提取模组信息失败: {jar_path}", error=str(e))
            return None
    
    def _parse_json_metadata(self, data: Any, filename: str) -> Dict:
        """解析JSON格式的模组元数据"""
        if 'fabric.mod.json' in filename or 'quilt.mod.json' in filename:
            # Fabric/Quilt格式
            return {
                'mod_id': data.get('id', 'unknown'),
                'name': data.get('name', data.get('id', 'Unknown')),
                'display_name': data.get('name'),
                'version': data.get('version', 'unknown'),
                'minecraft_version': self._extract_mc_version(data),
                'mod_loader': 'fabric' if 'fabric' in filename else 'quilt',
                'metadata': data
            }
        else:
            # 老版Forge格式 (mcmod.info)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            return {
                'mod_id': data.get('modid', 'unknown'),
                'name': data.get('name', 'Unknown'),
                'display_name': data.get('name'),
                'version': data.get('version', 'unknown'),
                'minecraft_version': data.get('mcversion'),
                'mod_loader': 'forge',
                'metadata': data
            }
    
    def _parse_toml_metadata(self, content: str) -> Dict:
        """简单解析TOML格式的模组元数据"""
        # 这是一个简化的TOML解析器
        mod_info = {
            'mod_loader': 'forge',
            'metadata': {}
        }
        
        for line in content.split('\n'):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                
                if 'modId' in key:
                    mod_info['mod_id'] = value
                elif 'displayName' in key:
                    mod_info['name'] = value
                    mod_info['display_name'] = value
                elif key == 'version':
                    mod_info['version'] = value
        
        return mod_info or {
            'mod_id': 'unknown',
            'name': 'Unknown',
            'version': 'unknown',
            'mod_loader': 'forge'
        }
    
    def _extract_mc_version(self, data: Dict) -> Optional[str]:
        """提取Minecraft版本"""
        if 'depends' in data:
            for dep in data['depends']:
                if dep == 'minecraft' or (isinstance(dep, dict) and dep.get('id') == 'minecraft'):
                    if isinstance(dep, dict):
                        return dep.get('version')
        return None
    
    def _extract_language_files(self, jar_path: Path) -> Dict[str, Dict]:
        """提取语言文件内容"""
        language_files = {}
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # 查找语言文件
                for file_name in jar.namelist():
                    # 匹配语言文件路径模式
                    if '/lang/' in file_name and file_name.endswith('.json'):
                        # 提取语言代码
                        lang_code = Path(file_name).stem
                        
                        try:
                            content = jar.read(file_name).decode('utf-8')
                            lang_data = json.loads(content)
                            
                            if isinstance(lang_data, dict) and lang_data:
                                language_files[lang_code] = lang_data
                                
                        except Exception as e:
                            logger.debug(f"解析语言文件失败: {file_name}", error=str(e))
                            continue
                            
        except Exception as e:
            logger.error(f"提取语言文件失败: {jar_path}", error=str(e))
        
        return language_files
    
    def _insert_translation_entries(
        self, 
        cursor: sqlite3.Cursor, 
        file_id: str, 
        entries: Dict[str, str]
    ):
        """插入翻译条目"""
        for key, value in entries.items():
            entry_id = str(uuid.uuid4())
            key_type = self._detect_key_type(key)
            
            cursor.execute("""
                INSERT OR IGNORE INTO translation_entries (
                    entry_id, file_id, translation_key, key_type,
                    original_value, translated_value, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                file_id,
                key,
                key_type,
                value,
                value,  # 初始时原文和译文相同
                'untranslated' if file_id.endswith('_en_us') else 'translated'
            ))
    
    def _update_translation_entries(
        self, 
        cursor: sqlite3.Cursor, 
        file_id: str, 
        entries: Dict[str, str]
    ):
        """更新翻译条目（保留用户修改）"""
        # 获取现有条目
        cursor.execute("""
            SELECT translation_key, translated_value, status 
            FROM translation_entries 
            WHERE file_id = ?
        """, (file_id,))
        
        existing = {row['translation_key']: row for row in cursor.fetchall()}
        
        for key, value in entries.items():
            if key in existing:
                # 只更新原文，保留用户的翻译
                cursor.execute("""
                    UPDATE translation_entries 
                    SET original_value = ?, last_modified = CURRENT_TIMESTAMP
                    WHERE file_id = ? AND translation_key = ?
                """, (value, file_id, key))
            else:
                # 新键，插入
                self._insert_translation_entries(cursor, file_id, {key: value})
        
        # 标记已删除的键
        deleted_keys = set(existing.keys()) - set(entries.keys())
        for key in deleted_keys:
            cursor.execute("""
                UPDATE translation_entries 
                SET status = 'deleted', last_modified = CURRENT_TIMESTAMP
                WHERE file_id = ? AND translation_key = ?
            """, (file_id, key))
    
    def _detect_key_type(self, key: str) -> str:
        """检测翻译键类型"""
        if key.startswith('item.'):
            return 'item'
        elif key.startswith('block.'):
            return 'block'
        elif key.startswith('entity.'):
            return 'entity'
        elif key.startswith('gui.'):
            return 'gui'
        elif key.startswith('tooltip.'):
            return 'tooltip'
        else:
            return 'other'
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _update_scan_progress(self, scan_id: str, progress: float, current_item: str):
        """更新扫描进度"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE scan_sessions 
                SET progress_percent = ?, current_item = ?
                WHERE scan_id = ?
            """, (progress, current_item, scan_id))
            conn.commit()
        finally:
            conn.close()
    
    def _update_scan_status(
        self, 
        scan_id: str, 
        status: str, 
        progress: float,
        statistics: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """更新扫描状态"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if status == 'completed':
                cursor.execute("""
                    UPDATE scan_sessions 
                    SET status = ?, progress_percent = ?, 
                        statistics = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE scan_id = ?
                """, (status, progress, json.dumps(statistics), scan_id))
            elif status == 'failed':
                cursor.execute("""
                    UPDATE scan_sessions 
                    SET status = ?, error_message = ?, 
                        completed_at = CURRENT_TIMESTAMP
                    WHERE scan_id = ?
                """, (status, error, scan_id))
            else:
                cursor.execute("""
                    UPDATE scan_sessions 
                    SET status = ?, progress_percent = ?
                    WHERE scan_id = ?
                """, (status, progress, scan_id))
            
            conn.commit()
        finally:
            conn.close()
    
    def _publish_domain_event(self, event_type: str, event_data: Dict):
        """发布领域事件"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO domain_events (
                    event_id, event_type, event_data, occurred_at
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                str(uuid.uuid4()),
                event_type,
                json.dumps(event_data)
            ))
            conn.commit()
        finally:
            conn.close()
    
    async def get_scan_status(self, scan_id: str) -> Dict:
        """获取扫描状态"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM scan_sessions WHERE scan_id = ?
            """, (scan_id,))
            
            session = cursor.fetchone()
            if not session:
                return {'status': 'not_found'}
            
            result = dict(session)
            
            # 解析JSON字段
            if result.get('statistics'):
                result['statistics'] = json.loads(result['statistics'])
            
            # 获取发现的模组数量
            cursor.execute("""
                SELECT COUNT(*) as count FROM scan_discoveries 
                WHERE scan_id = ?
            """, (scan_id,))
            discoveries = cursor.fetchone()
            result['discovered_mods'] = discoveries['count']
            
            return result
            
        finally:
            conn.close()


# 全局实例
_scanner_instance = None


async def init_ddd_scanner(db_path: str = "mc_l10n_unified.db"):
    """初始化DDD扫描器"""
    global _scanner_instance
    _scanner_instance = DDDScannerService(db_path)
    logger.info(f"✅ DDD Scanner initialized with database: {db_path}")
    return _scanner_instance


def get_scanner():
    """获取扫描器实例"""
    return _scanner_instance


# 测试函数
async def test_ddd_scanner():
    """测试DDD扫描器"""
    scanner = DDDScannerService()
    
    # 测试路径
    test_path = "/home/saken/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse/mods"
    
    print(f"🚀 开始测试DDD扫描器...")
    print(f"📁 扫描路径: {test_path}")
    
    # 启动扫描
    scan_id = await scanner.start_scan(test_path, scan_type='full')
    print(f"📋 扫描ID: {scan_id}")
    
    # 等待扫描完成
    while True:
        status = await scanner.get_scan_status(scan_id)
        progress = status.get('progress_percent', 0)
        
        print(f"⏳ 进度: {progress:.1f}% - 状态: {status.get('status')}")
        
        if status.get('status') in ['completed', 'failed']:
            break
        
        await asyncio.sleep(1)
    
    # 显示结果
    if status.get('status') == 'completed':
        stats = status.get('statistics', {})
        print(f"\n✅ 扫描完成!")
        print(f"📊 统计信息:")
        print(f"   - 模组数量: {stats.get('total_mods', 0)}")
        print(f"   - 语言文件: {stats.get('total_language_files', 0)}")
        print(f"   - 翻译键数: {stats.get('total_keys', 0)}")
    else:
        print(f"\n❌ 扫描失败: {status.get('error_message')}")


if __name__ == "__main__":
    asyncio.run(test_ddd_scanner())