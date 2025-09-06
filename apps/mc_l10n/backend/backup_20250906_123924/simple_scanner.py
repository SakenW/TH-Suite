"""
简单的扫描服务实现
直接使用数据库，不依赖外部包
"""

import asyncio
import sqlite3
import json
import logging
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import uuid

logger = logging.getLogger(__name__)

class SimpleScannerService:
    """简单的扫描服务实现"""
    
    def __init__(self, db_path: str = "mc_l10n_unified.db"):
        self.db_path = db_path
        self._scan_cache: Dict[str, Dict[str, Any]] = {}
        logger.info(f"🚀 Simple Scanner Service initialized with db: {db_path}")
    
    async def start_scan(
        self, 
        target_path: str,
        incremental: bool = True,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """启动扫描并返回扫描ID"""
        
        scan_id = str(uuid.uuid4())
        
        # 保存扫描会话到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO scan_sessions (
                    scan_id, status, path, target_path, game_type, scan_mode, 
                    started_at, progress_percent, total_files, processed_files,
                    processed_count, total_count, current_item
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_id, 'scanning', target_path, target_path, 'minecraft', 
                'full' if not incremental else 'incremental',
                datetime.now().isoformat(), 0.0, 0, 0, 0, 0, '初始化扫描...'
            ))
            conn.commit()
            
            logger.info(f"🔍 Starting scan: {scan_id} for path: {target_path}")
            
            # 初始化缓存
            self._scan_cache[scan_id] = {
                "scan_id": scan_id,
                "status": "scanning",
                "progress_percent": 0.0,
                "current_item": "初始化扫描...",
                "processed_count": 0,
                "total_count": 0,
                "statistics": {},
                "started_at": datetime.now()
            }
            
            # 在后台执行扫描
            asyncio.create_task(self._execute_scan(scan_id, target_path))
            
        except Exception as e:
            logger.error(f"Failed to start scan: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
        
        return {
            "scan_id": scan_id,
            "target_path": target_path,
            "game_type": "minecraft",
            "status": "scanning",
            "started_at": datetime.now().isoformat()
        }
    
    async def _execute_scan(self, scan_id: str, target_path: str) -> None:
        """执行实际的扫描工作"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            logger.info(f"🔍 Executing scan {scan_id} for {target_path}")
            
            # 扫描目标路径
            target = Path(target_path)
            if not target.exists():
                raise ValueError(f"路径不存在: {target_path}")
            
            # 查找所有 JAR 文件和 mods 目录
            jar_files = []
            if target.is_dir():
                # 查找 mods 目录
                mods_dir = target / "mods"
                if mods_dir.exists():
                    jar_files = list(mods_dir.glob("*.jar"))
                # 也查找根目录的 JAR 文件
                jar_files.extend(list(target.glob("*.jar")))
            elif target.suffix == ".jar":
                jar_files = [target]
            
            total_files = len(jar_files)
            logger.info(f"📦 Found {total_files} JAR files to scan")
            
            # 更新总数
            self._update_progress(cursor, scan_id, 0, total_files, "开始扫描...")
            
            # 扫描每个 JAR 文件
            total_mods = 0
            total_lang_files = 0
            total_keys = 0
            
            for idx, jar_file in enumerate(jar_files):
                try:
                    # 更新进度
                    progress_percent = (idx / total_files * 100) if total_files > 0 else 0
                    self._update_progress(cursor, scan_id, idx, total_files, f"扫描: {jar_file.name}")
                    
                    # 扫描 JAR 文件
                    mod_info = await self._scan_jar_file(jar_file)
                    if mod_info:
                        total_mods += 1
                        total_lang_files += mod_info.get('lang_files', 0)
                        total_keys += mod_info.get('total_keys', 0)
                        
                        # 保存扫描结果
                        cursor.execute("""
                            INSERT INTO scan_results (
                                scan_id, mod_id, mod_name, mod_version, 
                                file_path, language_code, keys_count
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            scan_id, mod_info.get('mod_id', ''), 
                            mod_info.get('name', jar_file.stem),
                            mod_info.get('version', 'unknown'),
                            str(jar_file), 'en_us', mod_info.get('total_keys', 0)
                        ))
                    
                    await asyncio.sleep(0.01)  # 避免阻塞事件循环
                    
                except Exception as e:
                    logger.warning(f"Failed to scan {jar_file}: {e}")
            
            # 更新最终状态
            cursor.execute("""
                UPDATE scan_sessions SET 
                    status = 'completed',
                    completed_at = ?,
                    progress_percent = 100,
                    processed_files = ?,
                    processed_count = ?,
                    total_count = ?,
                    total_mods = ?,
                    total_language_files = ?,
                    total_keys = ?,
                    current_item = '扫描完成'
                WHERE scan_id = ?
            """, (
                datetime.now().isoformat(), total_files, total_files, 
                total_files, total_mods, total_lang_files, total_keys, scan_id
            ))
            conn.commit()
            
            # 更新缓存
            self._scan_cache[scan_id] = {
                "scan_id": scan_id,
                "status": "completed",
                "progress_percent": 100.0,
                "current_item": "扫描完成",
                "processed_count": total_files,
                "total_count": total_files,
                "statistics": {
                    "total_mods": total_mods,
                    "total_language_files": total_lang_files,
                    "total_keys": total_keys
                },
                "duration_seconds": (datetime.now() - self._scan_cache[scan_id]['started_at']).total_seconds()
            }
            
            logger.info(f"✅ Scan {scan_id} completed: {total_mods} mods, {total_lang_files} lang files, {total_keys} keys")
            
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            
            # 更新为失败状态
            cursor.execute("""
                UPDATE scan_sessions SET 
                    status = 'failed',
                    error_message = ?,
                    completed_at = ?,
                    current_item = '扫描失败'
                WHERE scan_id = ?
            """, (str(e), datetime.now().isoformat(), scan_id))
            conn.commit()
            
            # 更新缓存
            self._scan_cache[scan_id]['status'] = 'failed'
            self._scan_cache[scan_id]['error_message'] = str(e)
            
        finally:
            conn.close()
    
    def _update_progress(self, cursor, scan_id: str, processed: int, total: int, current_item: str):
        """更新扫描进度"""
        progress_percent = (processed / total * 100) if total > 0 else 0
        
        cursor.execute("""
            UPDATE scan_sessions SET 
                progress_percent = ?,
                processed_files = ?,
                processed_count = ?,
                total_files = ?,
                total_count = ?,
                current_item = ?
            WHERE scan_id = ?
        """, (progress_percent, processed, processed, total, total, current_item, scan_id))
        
        # 更新缓存
        if scan_id in self._scan_cache:
            self._scan_cache[scan_id].update({
                "progress_percent": progress_percent,
                "current_item": current_item,
                "processed_count": processed,
                "total_count": total
            })
    
    async def _scan_jar_file(self, jar_path: Path) -> Optional[Dict[str, Any]]:
        """扫描单个 JAR 文件"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # 查找语言文件
                lang_files = [f for f in jar.namelist() if '/lang/' in f and f.endswith('.json')]
                
                # 查找 mod 信息
                mod_info = {
                    'mod_id': jar_path.stem.lower().replace(' ', '_'),
                    'name': jar_path.stem,
                    'version': 'unknown',
                    'lang_files': len(lang_files),
                    'total_keys': 0
                }
                
                # 统计翻译键数量
                for lang_file in lang_files:
                    if lang_file.endswith('en_us.json'):
                        try:
                            content = jar.read(lang_file).decode('utf-8')
                            data = json.loads(content)
                            mod_info['total_keys'] = len(data)
                            break
                        except:
                            pass
                
                return mod_info
                
        except Exception as e:
            logger.warning(f"Failed to scan JAR {jar_path}: {e}")
            return None
    
    async def get_scan_status(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """获取扫描状态（别名）"""
        return await self.get_scan_progress(scan_id)
    
    async def get_scan_progress(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """获取扫描进度"""
        
        # 优先从缓存获取
        if scan_id in self._scan_cache:
            return self._scan_cache[scan_id].copy()
        
        # 从数据库获取
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT status, progress_percent, processed_files, total_files,
                       current_item, total_mods, total_language_files, total_keys,
                       error_message
                FROM scan_sessions
                WHERE scan_id = ?
            """, (scan_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "scan_id": scan_id,
                    "status": row[0],
                    "progress_percent": row[1],
                    "processed_count": row[2],
                    "total_count": row[3],
                    "current_item": row[4] or "",
                    "statistics": {
                        "total_mods": row[5] or 0,
                        "total_language_files": row[6] or 0,
                        "total_keys": row[7] or 0
                    },
                    "error_message": row[8]
                }
        finally:
            conn.close()
        
        return None

# 单例实例
_simple_scanner = None

async def init_simple_scanner(db_path: str) -> SimpleScannerService:
    """初始化简单扫描服务"""
    global _simple_scanner
    _simple_scanner = SimpleScannerService(db_path)
    return _simple_scanner

def get_scanner() -> Optional[SimpleScannerService]:
    """获取扫描服务实例"""
    return _simple_scanner