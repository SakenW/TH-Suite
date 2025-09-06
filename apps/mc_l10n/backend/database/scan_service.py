#!/usr/bin/env python
"""
扫描服务与数据库集成
处理MOD扫描、缓存管理和数据持久化
"""

import sqlite3
import hashlib
import json
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
import toml
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScanDatabaseService:
    """扫描数据库服务"""
    
    def __init__(self, db_path: str = "mc_l10n_local.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        
    def get_cache_ttl(self) -> int:
        """获取缓存TTL设置"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT setting_value FROM local_settings 
            WHERE setting_key = 'cache_ttl'
        """)
        result = cursor.fetchone()
        return int(result['setting_value']) if result else 86400
        
    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
        
    def check_scan_cache(self, scan_path: str, file_hash: Optional[str] = None) -> Optional[Dict]:
        """检查扫描缓存"""
        cursor = self.conn.cursor()
        
        query = """
            SELECT * FROM scan_cache 
            WHERE scan_path = ? 
            AND is_valid = 1
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        """
        params = [scan_path]
        
        if file_hash:
            query += " AND file_hash = ?"
            params.append(file_hash)
            
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        if result:
            return {
                'cache_id': result['cache_id'],
                'scan_result': json.loads(result['scan_result']) if result['scan_result'] else None,
                'metadata': json.loads(result['metadata']) if result['metadata'] else None,
                'created_at': result['created_at']
            }
        return None
        
    def save_scan_cache(self, scan_path: str, file_hash: str, scan_result: Dict, metadata: Optional[Dict] = None):
        """保存扫描缓存"""
        ttl = self.get_cache_ttl()
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        self.conn.execute("""
            INSERT OR REPLACE INTO scan_cache (scan_path, file_hash, scan_result, metadata, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            scan_path,
            file_hash,
            json.dumps(scan_result, ensure_ascii=False),
            json.dumps(metadata, ensure_ascii=False) if metadata else None,
            expires_at
        ))
        self.conn.commit()
        
    def discover_mod(self, jar_path: Path) -> Optional[Dict]:
        """发现并分析MOD"""
        try:
            # 计算文件哈希
            file_hash = self.calculate_file_hash(jar_path)
            
            # 检查缓存
            cached = self.check_scan_cache(str(jar_path), file_hash)
            if cached:
                logger.info(f"使用缓存: {jar_path.name}")
                return cached['scan_result']
                
            # 提取MOD信息
            mod_info = self.extract_mod_info(jar_path)
            if not mod_info:
                return None
                
            # 保存到发现表
            self.save_mod_discovery(mod_info, jar_path, file_hash)
            
            # 保存缓存
            self.save_scan_cache(str(jar_path), file_hash, mod_info)
            
            return mod_info
            
        except Exception as e:
            logger.error(f"扫描MOD失败 {jar_path}: {e}")
            return None
            
    def extract_mod_info(self, jar_path: Path) -> Optional[Dict]:
        """从JAR文件提取MOD信息"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # 检查Forge MOD
                if 'META-INF/mods.toml' in jar.namelist():
                    return self.parse_forge_mod(jar, jar_path)
                # 检查Fabric MOD
                elif 'fabric.mod.json' in jar.namelist():
                    return self.parse_fabric_mod(jar, jar_path)
                # 检查Quilt MOD
                elif 'quilt.mod.json' in jar.namelist():
                    return self.parse_quilt_mod(jar, jar_path)
                    
        except Exception as e:
            logger.error(f"提取MOD信息失败: {e}")
            
        return None
        
    def parse_forge_mod(self, jar: zipfile.ZipFile, jar_path: Path) -> Dict:
        """解析Forge MOD"""
        try:
            toml_content = jar.read('META-INF/mods.toml').decode('utf-8')
            # 清理TOML内容
            clean_content = self.clean_toml_content(toml_content)
            data = toml.loads(clean_content)
            
            mod = data.get('mods', [{}])[0]
            
            # 统计语言文件
            lang_stats = self.count_language_files(jar)
            
            return {
                'mod_id': mod.get('modId', jar_path.stem),
                'mod_name': mod.get('modId', jar_path.stem),
                'display_name': mod.get('displayName', ''),
                'version': mod.get('version', 'unknown'),
                'minecraft_version': self.extract_mc_version(data),
                'mod_loader': 'forge',
                'language_count': lang_stats['count'],
                'total_keys': lang_stats['total_keys'],
                'metadata': data
            }
        except Exception as e:
            logger.error(f"解析Forge MOD失败: {e}")
            return None
            
    def parse_fabric_mod(self, jar: zipfile.ZipFile, jar_path: Path) -> Dict:
        """解析Fabric MOD"""
        try:
            json_content = jar.read('fabric.mod.json').decode('utf-8')
            data = json.loads(json_content)
            
            lang_stats = self.count_language_files(jar)
            
            return {
                'mod_id': data.get('id', jar_path.stem),
                'mod_name': data.get('id', jar_path.stem),
                'display_name': data.get('name', ''),
                'version': data.get('version', 'unknown'),
                'minecraft_version': data.get('depends', {}).get('minecraft', '*'),
                'mod_loader': 'fabric',
                'language_count': lang_stats['count'],
                'total_keys': lang_stats['total_keys'],
                'metadata': data
            }
        except Exception as e:
            logger.error(f"解析Fabric MOD失败: {e}")
            return None
            
    def parse_quilt_mod(self, jar: zipfile.ZipFile, jar_path: Path) -> Dict:
        """解析Quilt MOD"""
        try:
            json_content = jar.read('quilt.mod.json').decode('utf-8')
            data = json.loads(json_content)
            
            quilt_loader = data.get('quilt_loader', {})
            lang_stats = self.count_language_files(jar)
            
            return {
                'mod_id': quilt_loader.get('id', jar_path.stem),
                'mod_name': quilt_loader.get('id', jar_path.stem),
                'display_name': quilt_loader.get('metadata', {}).get('name', ''),
                'version': quilt_loader.get('version', 'unknown'),
                'minecraft_version': quilt_loader.get('depends', [{}])[0].get('id', '*') if quilt_loader.get('depends') else '*',
                'mod_loader': 'quilt',
                'language_count': lang_stats['count'],
                'total_keys': lang_stats['total_keys'],
                'metadata': data
            }
        except Exception as e:
            logger.error(f"解析Quilt MOD失败: {e}")
            return None
            
    def clean_toml_content(self, content: str) -> str:
        """清理TOML内容"""
        lines = []
        for line in content.split('\n'):
            # 移除注释
            if '#' in line:
                line = line[:line.index('#')]
            # 替换变量
            line = line.replace('${file.jarVersion}', '"unknown"')
            lines.append(line)
        return '\n'.join(lines)
        
    def extract_mc_version(self, toml_data: Dict) -> str:
        """提取Minecraft版本"""
        dependencies = toml_data.get('dependencies', {})
        if isinstance(dependencies, dict):
            for mod_id, deps in dependencies.items():
                if isinstance(deps, list):
                    for dep in deps:
                        if isinstance(dep, dict) and dep.get('modId') == 'minecraft':
                            return dep.get('versionRange', '*')
        return '*'
        
    def count_language_files(self, jar: zipfile.ZipFile) -> Dict:
        """统计语言文件"""
        lang_files = []
        total_keys = 0
        
        for file_name in jar.namelist():
            if '/lang/' in file_name and (file_name.endswith('.json') or file_name.endswith('.lang')):
                lang_files.append(file_name)
                try:
                    content = jar.read(file_name).decode('utf-8')
                    if file_name.endswith('.json'):
                        data = json.loads(content)
                        total_keys += len(data)
                    else:  # .lang file
                        # 简单统计行数（不包括空行和注释）
                        lines = content.split('\n')
                        total_keys += sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))
                except:
                    pass
                    
        return {
            'count': len(lang_files),
            'total_keys': total_keys,
            'files': lang_files
        }
        
    def save_mod_discovery(self, mod_info: Dict, jar_path: Path, file_hash: str):
        """保存MOD发现记录"""
        self.conn.execute("""
            INSERT OR REPLACE INTO mod_discoveries (
                mod_id, mod_name, display_name, version, minecraft_version,
                mod_loader, file_path, file_hash, file_size,
                language_count, total_keys, metadata, scan_result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mod_info['mod_id'],
            mod_info['mod_name'],
            mod_info.get('display_name', ''),
            mod_info.get('version', 'unknown'),
            mod_info.get('minecraft_version', '*'),
            mod_info.get('mod_loader', 'unknown'),
            str(jar_path),
            file_hash,
            jar_path.stat().st_size,
            mod_info.get('language_count', 0),
            mod_info.get('total_keys', 0),
            json.dumps(mod_info.get('metadata', {}), ensure_ascii=False),
            json.dumps(mod_info, ensure_ascii=False)
        ))
        self.conn.commit()
        
    def extract_language_files(self, mod_id: str) -> List[Dict]:
        """提取MOD的语言文件"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT file_path, file_hash FROM mod_discoveries
            WHERE mod_id = ?
        """, (mod_id,))
        
        result = cursor.fetchone()
        if not result:
            return []
            
        jar_path = Path(result['file_path'])
        if not jar_path.exists():
            return []
            
        language_files = []
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                for file_name in jar.namelist():
                    if '/lang/' in file_name and (file_name.endswith('.json') or file_name.endswith('.lang')):
                        # 提取语言代码
                        lang_code = Path(file_name).stem
                        content = jar.read(file_name).decode('utf-8')
                        
                        # 保存语言文件缓存
                        self.save_language_cache(mod_id, lang_code, file_name, content)
                        
                        language_files.append({
                            'mod_id': mod_id,
                            'language_code': lang_code,
                            'file_path': file_name,
                            'content': content
                        })
                        
        except Exception as e:
            logger.error(f"提取语言文件失败: {e}")
            
        return language_files
        
    def save_language_cache(self, mod_id: str, lang_code: str, file_path: str, content: str):
        """保存语言文件缓存"""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # 统计条目数
        entry_count = 0
        if file_path.endswith('.json'):
            try:
                data = json.loads(content)
                entry_count = len(data)
            except:
                pass
        else:  # .lang file
            lines = content.split('\n')
            entry_count = sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))
            
        ttl = self.get_cache_ttl()
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        cursor = self.conn.execute("""
            INSERT OR REPLACE INTO language_file_cache (
                mod_id, language_code, file_path, file_format, 
                content, content_hash, entry_count, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mod_id,
            lang_code,
            file_path,
            'json' if file_path.endswith('.json') else 'properties',
            content,
            content_hash,
            entry_count,
            expires_at
        ))
        
        cache_id = cursor.lastrowid
        
        # 解析并保存翻译条目
        if file_path.endswith('.json'):
            self.save_translation_entries_json(cache_id, content)
        else:
            self.save_translation_entries_lang(cache_id, content)
            
        self.conn.commit()
        
    def save_translation_entries_json(self, cache_id: int, content: str):
        """保存JSON格式的翻译条目"""
        try:
            data = json.loads(content)
            for key, value in data.items():
                self.conn.execute("""
                    INSERT OR REPLACE INTO translation_entry_cache (
                        cache_id, translation_key, original_text, status
                    ) VALUES (?, ?, ?, ?)
                """, (cache_id, key, value, 'pending'))
        except Exception as e:
            logger.error(f"保存JSON翻译条目失败: {e}")
            
    def save_translation_entries_lang(self, cache_id: int, content: str):
        """保存.lang格式的翻译条目"""
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                self.conn.execute("""
                    INSERT OR REPLACE INTO translation_entry_cache (
                        cache_id, translation_key, original_text, status
                    ) VALUES (?, ?, ?, ?)
                """, (cache_id, key.strip(), value.strip(), 'pending'))
                
    def scan_directory(self, directory: Path, progress_callback=None) -> Dict:
        """扫描目录"""
        jar_files = list(directory.rglob("*.jar"))
        total = len(jar_files)
        
        results = {
            'total_files': total,
            'successful': 0,
            'failed': 0,
            'cached': 0,
            'mods': []
        }
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.discover_mod, jar_path): jar_path 
                      for jar_path in jar_files}
            
            for i, future in enumerate(as_completed(futures), 1):
                jar_path = futures[future]
                try:
                    mod_info = future.result()
                    if mod_info:
                        results['successful'] += 1
                        results['mods'].append(mod_info)
                    else:
                        results['failed'] += 1
                        
                    if progress_callback:
                        progress_callback(i, total, jar_path.name)
                        
                except Exception as e:
                    logger.error(f"处理失败 {jar_path}: {e}")
                    results['failed'] += 1
                    
        return results
        
    def add_to_work_queue(self, task_type: str, task_data: Dict, priority: int = 5):
        """添加任务到工作队列"""
        self.conn.execute("""
            INSERT INTO work_queue (task_type, task_data, priority)
            VALUES (?, ?, ?)
        """, (
            task_type,
            json.dumps(task_data, ensure_ascii=False),
            priority
        ))
        self.conn.commit()
        
    def get_pending_tasks(self, task_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """获取待处理任务"""
        query = """
            SELECT * FROM work_queue 
            WHERE status = 'pending'
        """
        params = []
        
        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)
            
        query += " ORDER BY priority DESC, created_at ASC LIMIT ?"
        params.append(limit)
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'task_id': row['task_id'],
                'task_type': row['task_type'],
                'task_data': json.loads(row['task_data']) if row['task_data'] else {},
                'priority': row['priority'],
                'retry_count': row['retry_count']
            })
            
        return tasks
        
    def update_task_status(self, task_id: str, status: str, error_message: Optional[str] = None):
        """更新任务状态"""
        if status == 'processing':
            self.conn.execute("""
                UPDATE work_queue 
                SET status = ?, started_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (status, task_id))
        elif status == 'completed':
            self.conn.execute("""
                UPDATE work_queue 
                SET status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (status, task_id))
        elif status == 'failed':
            self.conn.execute("""
                UPDATE work_queue 
                SET status = ?, error_message = ?, retry_count = retry_count + 1
                WHERE task_id = ?
            """, (status, error_message, task_id))
            
        self.conn.commit()
        
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        cursor = self.conn.cursor()
        
        # MOD统计
        cursor.execute("SELECT COUNT(*) as total FROM mod_discoveries")
        mod_count = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as uploaded FROM mod_discoveries WHERE is_uploaded = 1")
        uploaded_count = cursor.fetchone()['uploaded']
        
        # 语言文件统计
        cursor.execute("SELECT COUNT(*) as total FROM language_file_cache")
        lang_count = cursor.fetchone()['total']
        
        # 翻译条目统计
        cursor.execute("SELECT COUNT(*) as total FROM translation_entry_cache")
        entry_count = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM translation_entry_cache 
            GROUP BY status
        """)
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # 工作队列统计
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM work_queue 
            GROUP BY status
        """)
        queue_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        return {
            'mods': {
                'total': mod_count,
                'uploaded': uploaded_count,
                'pending': mod_count - uploaded_count
            },
            'language_files': lang_count,
            'translation_entries': {
                'total': entry_count,
                'by_status': status_counts
            },
            'work_queue': queue_counts
        }
        
    def cleanup_expired_cache(self):
        """清理过期缓存"""
        self.conn.execute("""
            UPDATE scan_cache 
            SET is_valid = 0 
            WHERE expires_at <= CURRENT_TIMESTAMP
        """)
        
        self.conn.execute("""
            DELETE FROM language_file_cache 
            WHERE expires_at <= CURRENT_TIMESTAMP
        """)
        
        self.conn.commit()
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT changes() as deleted")
        deleted_count = cursor.fetchone()['deleted']
        
        logger.info(f"清理了 {deleted_count} 条过期缓存")
        
    def close(self):
        """关闭数据库连接"""
        self.conn.close()


def main():
    """测试函数"""
    import sys
    
    # 初始化服务
    service = ScanDatabaseService()
    
    if len(sys.argv) > 1:
        scan_path = Path(sys.argv[1])
        if scan_path.exists():
            if scan_path.is_file() and scan_path.suffix == '.jar':
                # 扫描单个JAR文件
                result = service.discover_mod(scan_path)
                if result:
                    print(f"✅ 成功扫描: {result['mod_name']}")
                    print(f"  - MOD ID: {result['mod_id']}")
                    print(f"  - 版本: {result['version']}")
                    print(f"  - 语言文件: {result['language_count']}")
                    print(f"  - 翻译键: {result['total_keys']}")
            elif scan_path.is_dir():
                # 扫描目录
                def progress(current, total, name):
                    print(f"[{current}/{total}] 扫描: {name}")
                    
                results = service.scan_directory(scan_path, progress)
                print(f"\n扫描完成:")
                print(f"  - 总文件: {results['total_files']}")
                print(f"  - 成功: {results['successful']}")
                print(f"  - 失败: {results['failed']}")
                
    # 显示统计
    stats = service.get_statistics()
    print(f"\n📊 数据库统计:")
    print(f"  - MOD总数: {stats['mods']['total']}")
    print(f"  - 已上传: {stats['mods']['uploaded']}")
    print(f"  - 语言文件: {stats['language_files']}")
    print(f"  - 翻译条目: {stats['translation_entries']['total']}")
    
    service.close()


if __name__ == "__main__":
    main()