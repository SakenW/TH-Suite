#!/usr/bin/env python3
"""
MC L10n后端服务器，实现真实的扫描和数据库功能
"""
import asyncio
import json
import os
import sqlite3
import zipfile
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import uuid
import logging

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import websockets

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MC L10n API",
    description="Minecraft本地化工具后端API服务",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class ScanRequest(BaseModel):
    directory: str
    recursive: bool = True
    include_patterns: list = []
    exclude_patterns: list = []
    incremental: bool = True  # 默认启用增量扫描

class ModInfo(BaseModel):
    mod_id: str
    display_name: str
    version: str
    file_path: str
    size: int
    mod_loader: Optional[str] = None
    description: Optional[str] = None
    authors: List[str] = []

class LanguageFile(BaseModel):
    namespace: str
    locale: str
    file_path: str
    key_count: int
    entries: Dict[str, Any] = {}  # 允许任何类型的值，包括嵌套对象
    mod_id: str = ""

# 数据库初始化
def init_database():
    """初始化SQLite数据库"""
    db_path = Path("mc_l10n.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建扫描记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_sessions (
            id TEXT PRIMARY KEY,
            directory TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            status TEXT DEFAULT 'running',
            total_mods INTEGER DEFAULT 0,
            total_language_files INTEGER DEFAULT 0,
            total_keys INTEGER DEFAULT 0
        )
    """)
    
    # 创建模组信息表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mods (
            id TEXT PRIMARY KEY,
            scan_id TEXT,
            mod_id TEXT,
            display_name TEXT,
            version TEXT,
            file_path TEXT,
            size INTEGER,
            mod_loader TEXT,
            description TEXT,
            authors TEXT,
            FOREIGN KEY (scan_id) REFERENCES scan_sessions(id)
        )
    """)
    
    # 创建语言文件表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS language_files (
            id TEXT PRIMARY KEY,
            scan_id TEXT,
            mod_id TEXT,
            namespace TEXT,
            locale TEXT,
            file_path TEXT,
            key_count INTEGER,
            FOREIGN KEY (scan_id) REFERENCES scan_sessions(id)
        )
    """)
    
    # 创建翻译条目表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translation_entries (
            id TEXT PRIMARY KEY,
            language_file_id TEXT,
            key TEXT,
            value TEXT,
            FOREIGN KEY (language_file_id) REFERENCES language_files(id),
            UNIQUE(language_file_id, key)
        )
    """)
    
    # 创建文件哈希表，用于增量扫描
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_hashes (
            file_path TEXT PRIMARY KEY,
            file_hash TEXT NOT NULL,
            last_modified TIMESTAMP NOT NULL,
            file_size INTEGER NOT NULL,
            last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建关键索引提升查询性能
    logger.info("创建数据库索引...")
    
    # translation_entries 表的复合索引（13.5M记录的关键优化）
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_translation_entries_file_key 
        ON translation_entries(language_file_id, key)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_translation_entries_key_search 
        ON translation_entries(key)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_translation_entries_value_search 
        ON translation_entries(value)
    """)
    
    # language_files 表索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_language_files_mod 
        ON language_files(mod_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_language_files_locale 
        ON language_files(locale)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_language_files_namespace_locale 
        ON language_files(namespace, locale)
    """)
    
    # mods 表索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_mods_scan 
        ON mods(scan_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_mods_id_version 
        ON mods(mod_id, version)
    """)
    
    # scan_sessions 表索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_scan_sessions_status_time 
        ON scan_sessions(status, started_at)
    """)
    
    # file_hashes 表索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_hashes_modified 
        ON file_hashes(last_modified)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_hashes_scanned 
        ON file_hashes(last_scanned)
    """)
    
    logger.info("索引创建完成")
    
    conn.commit()
    conn.close()
    logger.info("数据库初始化完成")

def optimize_database():
    """优化数据库性能"""
    db_path = Path("mc_l10n.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    logger.info("开始数据库优化...")
    
    try:
        # 启用WAL模式提升并发性能
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # 更新统计信息优化查询计划
        cursor.execute("ANALYZE")
        
        # 碎片整理（警告：会锁表较长时间）
        cursor.execute("VACUUM")
        
        # 优化内存设置
        cursor.execute("PRAGMA cache_size=10000")  # 10MB缓存
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB内存映射
        
        conn.commit()
        logger.info("数据库优化完成")
        
    except Exception as e:
        logger.error(f"数据库优化失败: {e}")
    finally:
        conn.close()

def cleanup_old_scans(days_old: int = 7):
    """清理旧的扫描记录"""
    db_path = Path("mc_l10n.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 删除N天前的扫描记录及相关数据
        cursor.execute("""
            DELETE FROM translation_entries 
            WHERE language_file_id IN (
                SELECT lf.id FROM language_files lf
                JOIN scan_sessions ss ON lf.scan_id = ss.id
                WHERE datetime(ss.started_at) < datetime('now', '-{} days')
            )
        """.format(days_old))
        
        cursor.execute("""
            DELETE FROM language_files 
            WHERE scan_id IN (
                SELECT id FROM scan_sessions 
                WHERE datetime(started_at) < datetime('now', '-{} days')
            )
        """.format(days_old))
        
        cursor.execute("""
            DELETE FROM mods 
            WHERE scan_id IN (
                SELECT id FROM scan_sessions 
                WHERE datetime(started_at) < datetime('now', '-{} days')
            )
        """.format(days_old))
        
        cursor.execute("""
            DELETE FROM scan_sessions 
            WHERE datetime(started_at) < datetime('now', '-{} days')
        """.format(days_old))
        
        conn.commit()
        logger.info(f"清理了{days_old}天前的扫描记录")
        
    except Exception as e:
        logger.error(f"清理旧记录失败: {e}")
    finally:
        conn.close()

def cleanup_active_scans():
    """清理内存中的扫描状态"""
    global active_scans
    current_time = datetime.now()
    
    # 清理超过1小时的扫描状态
    expired_scans = []
    for scan_id, scan_data in active_scans.items():
        try:
            # 检查扫描开始时间或完成时间
            start_time_str = scan_data.get('start_time') or scan_data.get('started_at', '')
            completed_time_str = scan_data.get('completed_at', '')
            
            # 使用最新的时间戳
            time_str = completed_time_str if completed_time_str else start_time_str
            
            if time_str:
                scan_time = datetime.fromisoformat(time_str)
                # 如果已完成超过30分钟，或运行中超过2小时，则清理
                if scan_data.get('status') == 'completed' and (current_time - scan_time).total_seconds() > 1800:  # 30分钟
                    expired_scans.append(scan_id)
                elif scan_data.get('status') in ['scanning', 'running'] and (current_time - scan_time).total_seconds() > 7200:  # 2小时
                    expired_scans.append(scan_id)
        except (ValueError, TypeError) as e:
            logger.warning(f"清理扫描状态时解析时间失败 {scan_id}: {e}")
            # 如果时间解析失败，也清理掉
            expired_scans.append(scan_id)
    
    for scan_id in expired_scans:
        del active_scans[scan_id]
        logger.info(f"清理过期扫描状态: {scan_id}")

# 初始化数据库
init_database()

# 在应用启动时优化数据库
optimize_database()

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.scan_connections: Dict[str, List[WebSocket]] = {}  # 按扫描ID分组连接
    
    async def connect(self, websocket: WebSocket, scan_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if scan_id:
            if scan_id not in self.scan_connections:
                self.scan_connections[scan_id] = []
            self.scan_connections[scan_id].append(websocket)
        
        logger.info(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, scan_id: str = None):
        self.active_connections.remove(websocket)
        
        if scan_id and scan_id in self.scan_connections:
            if websocket in self.scan_connections[scan_id]:
                self.scan_connections[scan_id].remove(websocket)
            if not self.scan_connections[scan_id]:
                del self.scan_connections[scan_id]
        
        logger.info(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")
    
    async def broadcast_to_scan(self, scan_id: str, message: dict):
        """向特定扫描的所有连接广播消息"""
        if scan_id in self.scan_connections:
            disconnected = []
            for connection in self.scan_connections[scan_id]:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    disconnected.append(connection)
                except Exception as e:
                    logger.error(f"WebSocket发送失败: {e}")
                    disconnected.append(connection)
            
            # 清理断开的连接
            for connection in disconnected:
                self.disconnect(connection, scan_id)
    
    async def broadcast_all(self, message: dict):
        """向所有连接广播消息"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"WebSocket广播失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

# 全局WebSocket管理器
manager = ConnectionManager()

# 全局变量存储扫描状态
active_scans = {}

def calculate_file_hash(file_path: Path) -> str:
    """计算文件的SHA256哈希值"""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        logger.error(f"计算文件哈希失败 {file_path}: {e}")
        return ""

def get_file_info(file_path: Path) -> Tuple[str, datetime, int]:
    """获取文件基本信息：哈希、修改时间、大小"""
    try:
        stat = file_path.stat()
        file_hash = calculate_file_hash(file_path)
        modified_time = datetime.fromtimestamp(stat.st_mtime)
        file_size = stat.st_size
        return file_hash, modified_time, file_size
    except Exception as e:
        logger.error(f"获取文件信息失败 {file_path}: {e}")
        return "", datetime.now(), 0

def should_scan_file(file_path: Path, force_scan: bool = False) -> bool:
    """检查文件是否需要重新扫描"""
    if force_scan:
        return True
    
    try:
        conn = sqlite3.connect("mc_l10n.db", timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        cursor = conn.cursor()
        
        # 获取当前文件信息
        current_hash, current_modified, current_size = get_file_info(file_path)
        if not current_hash:
            return True  # 无法获取文件信息，需要扫描
        
        # 查询数据库中的记录
        cursor.execute("""
            SELECT file_hash, last_modified, file_size 
            FROM file_hashes 
            WHERE file_path = ?
        """, (str(file_path),))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            # 文件未记录过，需要扫描
            return True
        
        stored_hash, stored_modified_str, stored_size = result
        stored_modified = datetime.fromisoformat(stored_modified_str)
        
        # 比较哈希值、修改时间和文件大小
        if (current_hash != stored_hash or 
            current_modified > stored_modified or 
            current_size != stored_size):
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"检查文件扫描状态失败 {file_path}: {e}")
        return True  # 出错时默认需要扫描

def update_file_hash(file_path: Path):
    """更新文件哈希记录"""
    try:
        current_hash, current_modified, current_size = get_file_info(file_path)
        if not current_hash:
            return
        
        # 增加超时时间和重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect("mc_l10n.db", timeout=30.0)  # 30秒超时
                conn.execute("PRAGMA busy_timeout = 30000")  # 30秒忙等待
                cursor = conn.cursor()
                
                # 使用 REPLACE INTO 更新或插入记录
                cursor.execute("""
                    REPLACE INTO file_hashes 
                    (file_path, file_hash, last_modified, file_size, last_scanned)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    str(file_path),
                    current_hash,
                    current_modified.isoformat(),
                    current_size,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                conn.close()
                logger.debug(f"更新文件哈希记录: {file_path}")
                return  # 成功，退出重试循环
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.debug(f"数据库锁定，重试 {attempt + 1}/{max_retries}: {file_path}")
                    import time
                    time.sleep(0.1 * (attempt + 1))  # 递增延迟
                    continue
                else:
                    raise e
        
    except Exception as e:
        logger.error(f"更新文件哈希记录失败 {file_path}: {e}")

def get_incremental_scan_stats(scan_directory: str) -> Dict[str, int]:
    """获取增量扫描统计信息"""
    try:
        scan_path = Path(scan_directory)
        if not scan_path.exists():
            return {"total_files": 0, "unchanged_files": 0, "changed_files": 0, "new_files": 0}
        
        # 查找所有jar文件
        jar_files = []
        if scan_path.is_file() and scan_path.suffix == '.jar':
            jar_files = [scan_path]
        else:
            jar_files = list(scan_path.rglob("*.jar"))
            mods_dir = scan_path / "mods"
            if mods_dir.exists():
                jar_files.extend(list(mods_dir.rglob("*.jar")))
        
        total_files = len(jar_files)
        unchanged_files = 0
        changed_files = 0
        new_files = 0
        
        # 检查每个文件的状态
        for jar_path in jar_files:
            if should_scan_file(jar_path):
                # 检查是新文件还是变更文件
                conn = sqlite3.connect("mc_l10n.db", timeout=30.0)
                conn.execute("PRAGMA busy_timeout = 30000")
                cursor = conn.cursor()
                cursor.execute("SELECT file_path FROM file_hashes WHERE file_path = ?", (str(jar_path),))
                if cursor.fetchone():
                    changed_files += 1
                else:
                    new_files += 1
                conn.close()
            else:
                unchanged_files += 1
        
        return {
            "total_files": total_files,
            "unchanged_files": unchanged_files,
            "changed_files": changed_files,
            "new_files": new_files
        }
        
    except Exception as e:
        logger.error(f"获取增量扫描统计失败: {e}")
        return {"total_files": 0, "unchanged_files": 0, "changed_files": 0, "new_files": 0}

def _parse_fabric_config(zip_file, config_file: str, fallback_id: str) -> dict:
    """解析Fabric模组配置文件"""
    try:
        fabric_data = json.loads(zip_file.read(config_file).decode('utf-8'))
        authors = fabric_data.get("authors", [])
        if isinstance(authors, str):
            authors = [authors]
        
        return {
            'mod_id': fabric_data.get("id", fallback_id),
            'display_name': fabric_data.get("name", fallback_id),
            'version': fabric_data.get("version", "unknown"),
            'description': fabric_data.get("description", ""),
            'authors': authors
        }
    except Exception as e:
        return {}

def _parse_forge_config(zip_file, config_file: str, fallback_id: str) -> dict:
    """解析Forge/NeoForge模组配置文件"""
    try:
        toml_content = zip_file.read(config_file).decode('utf-8')
        
        # 解析TOML内容
        mod_id = fallback_id
        display_name = fallback_id
        version = "unknown"
        description = ""
        authors = []
        
        in_mod_section = False
        for line in toml_content.split('\n'):
            line = line.strip()
            if line.startswith('[[mods]]'):
                in_mod_section = True
            elif line.startswith('[[') and line != '[[mods]]':
                in_mod_section = False
            elif in_mod_section and '=' in line and not line.startswith('#'):
                parts = line.split('=', 1)
                if len(parts) != 2:
                    continue
                
                key = parts[0].strip()
                value = parts[1].strip()
                
                # 移除行尾注释
                if '#' in value and not (value.startswith('"') or value.startswith("'")):
                    value = value.split('#')[0].strip()
                
                # 清理引号、空白和注释
                value = value.strip().strip('"').strip("'").strip()
                
                # 特殊处理：移除末尾的注释标识符
                if value.endswith('" #mandatory') or value.endswith('" #optional'):
                    value = value.split('" #')[0].strip('"').strip()
                elif '#' in value and not value.startswith('#'):
                    # 如果有#但不是开头，且不在引号内，则可能是注释
                    if not ('"' in value and value.index('#') > value.rindex('"')):
                        value = value.split('#')[0].strip()
                
                if key == 'modId':
                    mod_id = value
                elif key == 'displayName':
                    display_name = value
                elif key == 'version':
                    version = value
                elif key == 'description':
                    description = value.strip("'''").strip('"""')
                elif key == 'authors':
                    authors = [value] if value else []
        
        return {
            'mod_id': mod_id,
            'display_name': display_name,
            'version': version,
            'description': description,
            'authors': authors
        }
    except Exception as e:
        return {}

def _calculate_info_score(info: dict) -> int:
    """计算模组信息的完整度得分"""
    score = 0
    
    # 基础信息得分
    if info.get('mod_id') and info['mod_id'] != 'unknown':
        score += 10
    if info.get('display_name') and info['display_name'] != info.get('mod_id', ''):
        score += 10
    if info.get('version') and info['version'] not in ('unknown', 'unspecified', ''):
        score += 20  # 版本信息最重要
    if info.get('description') and info['description'].strip():
        score += 5
    if info.get('authors') and len(info['authors']) > 0:
        score += 5
    
    # 额外的质量评估
    version = info.get('version', '')
    if version and version not in ('unknown', 'unspecified', ''):
        # 如果版本看起来像真实的版本号（包含数字和点）
        import re
        if re.match(r'.*\d+\.\d+', version):
            score += 10
        # 如果版本没有明显的错误格式（如包含注释符号）
        if '#' not in version and '"' not in version:
            score += 5
    
    return score

def parse_mod_jar(jar_path: Path) -> tuple[Optional[ModInfo], List[LanguageFile]]:
    """解析mod的jar文件，提取模组信息和语言文件"""
    try:
        with zipfile.ZipFile(jar_path, 'r') as zip_file:
            # 默认值
            mod_id = jar_path.stem
            display_name = jar_path.stem
            version = "unknown"
            description = ""
            authors = []
            mod_loader = "unknown"
            
            # 找到所有可能的配置文件
            config_files = []
            file_list = zip_file.namelist()
            
            if "fabric.mod.json" in file_list:
                config_files.append(("fabric", "fabric.mod.json"))
            if "META-INF/neoforge.mods.toml" in file_list:
                config_files.append(("neoforge", "META-INF/neoforge.mods.toml"))
            if "META-INF/mods.toml" in file_list:
                config_files.append(("forge", "META-INF/mods.toml"))
            
            # 尝试解析每个配置文件，选择信息最完整的
            best_info = None
            best_score = -1
            
            for loader_type, config_file in config_files:
                try:
                    parsed_info = None
                    
                    if loader_type == "fabric":
                        parsed_info = _parse_fabric_config(zip_file, config_file, jar_path.stem)
                    elif loader_type in ("neoforge", "forge"):
                        parsed_info = _parse_forge_config(zip_file, config_file, jar_path.stem)
                    
                    if parsed_info:
                        # 计算信息完整度得分
                        score = _calculate_info_score(parsed_info)
                        logger.debug(f"{jar_path.name}: {config_file} score: {score}, info: {parsed_info}")
                        
                        if score > best_score:
                            best_score = score
                            best_info = parsed_info
                            mod_loader = loader_type
                            
                except Exception as e:
                    logger.warning(f"Failed to parse {config_file} in {jar_path}: {e}")
            
            # 使用最佳解析结果
            if best_info:
                mod_id = best_info.get('mod_id', jar_path.stem)
                display_name = best_info.get('display_name', mod_id)
                version = best_info.get('version', 'unknown')
                description = best_info.get('description', '')
                authors = best_info.get('authors', [])
            
            logger.debug(f"Selected {mod_loader} config for {jar_path.name}: version={version}, score={best_score}")
            
            # 创建模组信息
            mod_info = ModInfo(
                mod_id=mod_id,
                display_name=display_name,
                version=version,
                file_path=str(jar_path),
                size=jar_path.stat().st_size,
                mod_loader=mod_loader,
                description=description,
                authors=authors
            )
            
            # 提取语言文件
            language_files = []
            for file_path in zip_file.namelist():
                if "/lang/" in file_path and file_path.endswith('.json'):
                    try:
                        # 解析语言文件路径：assets/namespace/lang/locale.json
                        path_parts = file_path.split('/')
                        if len(path_parts) >= 4 and path_parts[-2] == 'lang':
                            namespace = path_parts[-3] if len(path_parts) > 3 else mod_id
                            locale = path_parts[-1].replace('.json', '')
                            
                            # 读取语言文件内容
                            lang_content = zip_file.read(file_path).decode('utf-8')
                            entries = json.loads(lang_content)
                            
                            lang_file = LanguageFile(
                                namespace=namespace,
                                locale=locale,
                                file_path=file_path,
                                key_count=len(entries),
                                entries=entries,
                                mod_id=mod_id
                            )
                            language_files.append(lang_file)
                            
                    except Exception as e:
                        logger.warning(f"Failed to parse language file {file_path} in {jar_path}: {e}")
            
            return mod_info, language_files
            
    except Exception as e:
        logger.error(f"Failed to parse jar file {jar_path}: {e}")
        return None, []

async def scan_directory_real(scan_id: str, directory: str, incremental: bool = True):
    """实际扫描目录函数"""
    logger.info(f"开始{'增量' if incremental else '全量'}扫描目录: {directory}")
    
    try:
        scan_path = Path(directory)
        if not scan_path.exists():
            raise ValueError(f"目录不存在: {directory}")
        
        # 数据库连接
        conn = sqlite3.connect("mc_l10n.db", timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        cursor = conn.cursor()
        
        # 更新扫描状态
        active_scans[scan_id] = {
            "status": "scanning", 
            "progress": 0,
            "total_files": 0,
            "processed_files": 0,
            "current_file": "",
            "total_mods": 0,
            "total_language_files": 0,
            "total_keys": 0,
            "start_time": datetime.now().isoformat()
        }
        
        # 查找所有jar文件
        jar_files = []
        if scan_path.is_file() and scan_path.suffix == '.jar':
            jar_files = [scan_path]
        else:
            # 在目录中递归查找jar文件
            jar_files = list(scan_path.rglob("*.jar"))
            # 也检查mods子目录
            mods_dir = scan_path / "mods"
            if mods_dir.exists():
                jar_files.extend(list(mods_dir.rglob("*.jar")))
        
        logger.info(f"找到 {len(jar_files)} 个jar文件")
        
        # 增量扫描过滤
        if incremental:
            files_to_scan = []
            skipped_files = 0
            for jar_path in jar_files:
                if should_scan_file(jar_path, force_scan=not incremental):
                    files_to_scan.append(jar_path)
                else:
                    skipped_files += 1
            jar_files = files_to_scan
            logger.info(f"增量扫描：需要处理 {len(jar_files)} 个文件，跳过 {skipped_files} 个未变更文件")
        
        # 更新扫描状态 - 设置总文件数
        active_scans[scan_id]["total_files"] = len(jar_files)
        active_scans[scan_id]["scan_mode"] = "增量" if incremental else "全量"
        
        # 同时更新数据库状态为正在扫描
        cursor.execute("UPDATE scan_sessions SET status = 'scanning' WHERE id = ?", (scan_id,))
        conn.commit()
        
        total_mods = 0
        total_language_files = 0
        total_keys = 0
        
        for i, jar_path in enumerate(jar_files):
            try:
                # 每个文件都更新基本进度信息
                current_progress = int((i + 1) / len(jar_files) * 100)
                
                # 更新基本进度信息（轻量级操作）
                active_scans[scan_id].update({
                    "processed_files": i + 1,
                    "current_file": jar_path.name,
                    "progress": current_progress,
                    "total_mods": total_mods,
                    "total_language_files": total_language_files,
                    "total_keys": total_keys,
                    "status": "scanning"
                })
                
                # 每隔5个文件或重要节点进行详细更新和广播
                should_broadcast = (i + 1) % 5 == 0 or (i + 1) == len(jar_files) or (i + 1) <= 10
                
                if should_broadcast:
                    progress_data = {
                        "processed_files": i + 1,
                        "current_file": jar_path.name,
                        "progress": current_progress,
                        "total_mods": total_mods,
                        "total_language_files": total_language_files,
                        "total_keys": total_keys,
                        "status": "scanning"
                    }
                    
                    # WebSocket实时广播进度
                    await manager.broadcast_to_scan(scan_id, {
                        "type": "progress_update",
                        "scan_id": scan_id,
                        "data": progress_data
                    })
                    
                    logger.info(f"进度广播: {current_progress}% ({i+1}/{len(jar_files)})")
                
                logger.info(f"正在处理 ({i+1}/{len(jar_files)}): {jar_path.name}")
                mod_info, language_files = parse_mod_jar(jar_path)
                
                # 更新文件哈希记录（无论是否解析成功）
                update_file_hash(jar_path)
                
                if mod_info:
                    # 检查模组是否已存在（基于mod_id和scan_id）
                    cursor.execute("""
                        SELECT id FROM mods WHERE scan_id = ? AND mod_id = ?
                    """, (scan_id, mod_info.mod_id))
                    existing_mod = cursor.fetchone()
                    
                    if not existing_mod:
                        # 保存模组信息到数据库
                        cursor.execute("""
                            INSERT INTO mods (id, scan_id, mod_id, display_name, version, 
                                             file_path, size, mod_loader, description, authors)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(uuid.uuid4()), scan_id, mod_info.mod_id, mod_info.display_name,
                            mod_info.version, mod_info.file_path, mod_info.size,
                            mod_info.mod_loader, mod_info.description, ','.join(mod_info.authors)
                        ))
                    else:
                        logger.debug(f"模组 {mod_info.mod_id} 已存在，跳过重复插入")
                    
                    total_mods += 1
                    
                    # 保存语言文件
                    for lang_file in language_files:
                        # 检查语言文件是否已存在
                        cursor.execute("""
                            SELECT id FROM language_files 
                            WHERE scan_id = ? AND mod_id = ? AND namespace = ? AND locale = ?
                        """, (scan_id, mod_info.mod_id, lang_file.namespace, lang_file.locale))
                        existing_lang_file = cursor.fetchone()
                        
                        if existing_lang_file:
                            lang_file_id = existing_lang_file[0]
                            logger.debug(f"语言文件已存在 {lang_file.namespace}:{lang_file.locale}，跳过重复插入")
                        else:
                            lang_file_id = str(uuid.uuid4())
                            cursor.execute("""
                                INSERT INTO language_files (id, scan_id, mod_id, namespace, 
                                                           locale, file_path, key_count)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                lang_file_id, scan_id, mod_info.mod_id, lang_file.namespace,
                                lang_file.locale, lang_file.file_path, lang_file.key_count
                            ))
                        
                        # 保存翻译条目 - 使用 INSERT OR IGNORE 避免重复
                        for key, value in lang_file.entries.items():
                            # 如果值不是字符串，则序列化为JSON
                            if isinstance(value, str):
                                stored_value = value
                            else:
                                stored_value = json.dumps(value, ensure_ascii=False)
                            
                            cursor.execute("""
                                INSERT OR IGNORE INTO translation_entries (id, language_file_id, key, value)
                                VALUES (?, ?, ?, ?)
                            """, (str(uuid.uuid4()), lang_file_id, key, stored_value))
                        
                        # 只有新插入的语言文件才计数
                        if not existing_lang_file:
                            total_language_files += 1
                            total_keys += lang_file.key_count
                
                # 每处理5个文件提交一次（更频繁的提交）
                if (i + 1) % 5 == 0:
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"处理文件 {jar_path} 时出错: {e}")
                continue
        
        # 最终提交并更新扫描记录
        cursor.execute("""
            UPDATE scan_sessions 
            SET completed_at = ?, status = 'completed', 
                total_mods = ?, total_language_files = ?, total_keys = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), total_mods, total_language_files, total_keys, scan_id))
        
        conn.commit()
        conn.close()
        
        # 更新扫描状态
        completion_data = {
            "status": "completed", 
            "progress": 100,
            "total_mods": total_mods,
            "total_language_files": total_language_files,
            "total_keys": total_keys,
            "completed_at": datetime.now().isoformat()
        }
        active_scans[scan_id] = completion_data
        
        # WebSocket广播完成状态
        await manager.broadcast_to_scan(scan_id, {
            "type": "scan_completed",
            "scan_id": scan_id,
            "data": completion_data
        })
        
        logger.info(f"扫描完成: {total_mods} 个模组, {total_language_files} 个语言文件, {total_keys} 个翻译条目")
        
    except Exception as e:
        logger.error(f"扫描失败: {e}")
        error_data = {"status": "failed", "error": str(e)}
        active_scans[scan_id] = error_data
        
        # WebSocket广播失败状态
        await manager.broadcast_to_scan(scan_id, {
            "type": "scan_failed",
            "scan_id": scan_id,
            "data": error_data
        })
        
        # 更新数据库状态
        conn = sqlite3.connect("mc_l10n.db", timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        cursor = conn.cursor()
        cursor.execute("UPDATE scan_sessions SET status = 'failed' WHERE id = ?", (scan_id,))
        conn.commit()
        conn.close()

@app.websocket("/ws/scan/{scan_id}")
async def websocket_endpoint(websocket: WebSocket, scan_id: str):
    """WebSocket端点，用于实时扫描进度推送"""
    await manager.connect(websocket, scan_id)
    try:
        # 发送初始连接确认
        await websocket.send_json({
            "type": "connection_established",
            "scan_id": scan_id,
            "message": f"已连接到扫描 {scan_id} 的实时进度推送"
        })
        
        # 如果扫描正在进行中，发送当前状态
        if scan_id in active_scans:
            current_status = active_scans[scan_id]
            await websocket.send_json({
                "type": "current_status",
                "scan_id": scan_id,
                "data": current_status
            })
        
        # 保持连接活跃，接收客户端消息
        while True:
            try:
                data = await websocket.receive_text()
                # 可以处理客户端发送的命令，比如暂停扫描等
                logger.debug(f"收到WebSocket消息: {data}")
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, scan_id)

@app.websocket("/ws/global")
async def websocket_global(websocket: WebSocket):
    """全局WebSocket端点，用于系统级通知"""
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "connection_established",
            "message": "已连接到系统全局通知"
        })
        
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"收到全局WebSocket消息: {data}")
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "MC L10n API", "database": "ready"}

@app.get("/api/v1/scan-status-quick")
async def get_scan_status_quick():
    """快速获取所有活跃扫描状态（无数据库查询）"""
    return {"success": True, "active_scans": list(active_scans.keys()), "data": active_scans}

@app.post("/api/v1/scan-project")
async def scan_project(request: ScanRequest, background_tasks: BackgroundTasks):
    """扫描项目端点 - 启动真实扫描"""
    try:
        # 生成扫描ID
        scan_id = str(uuid.uuid4())
        
        # 创建扫描记录
        conn = sqlite3.connect("mc_l10n.db", timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scan_sessions (id, directory, started_at, status)
            VALUES (?, ?, ?, 'scanning')
        """, (scan_id, request.directory, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        # 启动后台扫描任务
        background_tasks.add_task(scan_directory_real, scan_id, request.directory, request.incremental)
        
        return {
            "success": True,
            "message": f"扫描已开始: {request.directory}",
            "job_id": scan_id,
            "scan_id": scan_id
        }
        
    except Exception as e:
        logger.error(f"启动扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/scans/active")
async def get_active_scans():
    """获取所有活跃的扫描任务"""
    try:
        cleanup_active_scans()  # 清理过期的扫描
        
        active_scan_list = []
        for scan_id, status in active_scans.items():
            if status.get("status") in ["scanning", "starting"]:
                active_scan_list.append({
                    "scan_id": scan_id,
                    "status": status.get("status", "unknown"),
                    "progress": status.get("progress", 0),
                    "started_at": status.get("started_at"),
                    "current_file": status.get("current_file", ""),
                    "processed_files": status.get("processed_files", 0),
                    "total_files": status.get("total_files", 0)
                })
        
        return {
            "success": True,
            "data": {
                "active_scans": active_scan_list,
                "count": len(active_scan_list)
            }
        }
    except Exception as e:
        logger.error(f"获取活跃扫描失败: {e}")
        return {
            "success": False,
            "error": {"message": str(e)}
        }

@app.get("/api/v1/scan-status/{scan_id}")
async def get_scan_status(scan_id: str):
    """获取扫描状态"""
    try:
        # 先进行内存清理
        cleanup_active_scans()
        
        # 检查内存中的扫描状态
        if scan_id in active_scans:
            status = active_scans[scan_id]
            logger.info(f"返回实时扫描状态 {scan_id}: {status}")
            return {"success": True, "data": status}
        
        # 从数据库查询扫描状态
        conn = sqlite3.connect("mc_l10n.db", timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        cursor = conn.cursor()
        cursor.execute("SELECT status, total_mods, total_language_files, total_keys FROM scan_sessions WHERE id = ?", (scan_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "success": True,
                "data": {
                    "status": result[0],
                    "total_mods": result[1],
                    "total_language_files": result[2],
                    "total_keys": result[3]
                }
            }
        else:
            raise HTTPException(status_code=404, detail="扫描记录未找到")
            
    except Exception as e:
        logger.error(f"获取扫描状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/scan-results/{scan_id}")
async def get_scan_results(scan_id: str):
    """获取完整扫描结果"""
    try:
        conn = sqlite3.connect("mc_l10n.db", timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        cursor = conn.cursor()
        
        # 获取扫描基本信息
        cursor.execute("SELECT * FROM scan_sessions WHERE id = ?", (scan_id,))
        scan_info = cursor.fetchone()
        
        if not scan_info:
            raise HTTPException(status_code=404, detail="扫描记录未找到")
        
        # 获取模组列表
        cursor.execute("SELECT * FROM mods WHERE scan_id = ?", (scan_id,))
        mods = cursor.fetchall()
        
        # 获取语言文件列表
        cursor.execute("""
            SELECT lf.*, COUNT(te.id) as actual_entries 
            FROM language_files lf 
            LEFT JOIN translation_entries te ON lf.id = te.language_file_id 
            WHERE lf.scan_id = ? 
            GROUP BY lf.id
        """, (scan_id,))
        language_files = cursor.fetchall()
        
        conn.close()
        
        # 构建响应数据
        return {
            "success": True,
            "data": {
                "scan_id": scan_id,
                "directory": scan_info[1],
                "started_at": scan_info[2],
                "completed_at": scan_info[3],
                "status": scan_info[4],
                "total_mods": scan_info[5] or 0,
                "total_language_files": scan_info[6] or 0,
                "total_keys": scan_info[7] or 0,
                "mods": [
                    {
                        "mod_id": mod[2],
                        "display_name": mod[3],
                        "version": mod[4],
                        "file_path": mod[5],
                        "size": mod[6],
                        "mod_loader": mod[7],
                        "description": mod[8],
                        "authors": mod[9].split(',') if mod[9] else []
                    }
                    for mod in mods
                ],
                "language_files": [
                    {
                        "namespace": lf[3],
                        "locale": lf[4],
                        "file_path": lf[5],
                        "key_count": lf[6],
                        "actual_entries": lf[7],
                        "mod_id": lf[2]
                    }
                    for lf in language_files
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"获取扫描结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/translation-entries/{language_file_id}")
async def get_translation_entries(language_file_id: str, limit: int = 100, offset: int = 0):
    """获取翻译条目"""
    try:
        conn = sqlite3.connect("mc_l10n.db", timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT key, value FROM translation_entries 
            WHERE language_file_id = ? 
            ORDER BY key 
            LIMIT ? OFFSET ?
        """, (language_file_id, limit, offset))
        
        entries = cursor.fetchall()
        
        # 获取总数
        cursor.execute("SELECT COUNT(*) FROM translation_entries WHERE language_file_id = ?", (language_file_id,))
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "entries": [{"key": entry[0], "value": entry[1]} for entry in entries],
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
        
    except Exception as e:
        logger.error(f"获取翻译条目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/projects")  
async def get_projects():
    """获取项目列表"""
    return {
        "success": True,
        "data": [],
        "message": "暂无项目"
    }

@app.post("/api/v1/cleanup/memory")
async def cleanup_memory():
    """手动清理内存中的扫描状态"""
    try:
        before_count = len(active_scans)
        cleanup_active_scans()
        after_count = len(active_scans)
        cleaned_count = before_count - after_count
        
        return {
            "success": True,
            "data": {
                "cleaned_scans": cleaned_count,
                "remaining_scans": after_count
            },
            "message": f"清理了 {cleaned_count} 个过期扫描状态"
        }
    except Exception as e:
        logger.error(f"内存清理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/cleanup/database")
async def cleanup_database_old_scans(days_old: int = 7):
    """清理数据库中的旧扫描记录"""
    try:
        cleanup_old_scans(days_old)
        return {
            "success": True,
            "message": f"清理了 {days_old} 天前的扫描记录"
        }
    except Exception as e:
        logger.error(f"数据库清理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/maintenance/optimize")
async def optimize_database_performance():
    """优化数据库性能"""
    try:
        optimize_database()
        return {
            "success": True,
            "message": "数据库优化完成"
        }
    except Exception as e:
        logger.error(f"数据库优化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/system/stats")
async def get_system_stats():
    """获取系统统计信息"""
    try:
        conn = sqlite3.connect("mc_l10n.db", timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        cursor = conn.cursor()
        
        # 获取各表记录数
        cursor.execute("SELECT COUNT(*) FROM scan_sessions")
        scan_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mods")
        mod_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM language_files")
        lang_file_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM translation_entries")
        entry_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM file_hashes")
        hash_count = cursor.fetchone()[0]
        
        # 获取数据库大小
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        db_size = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "database": {
                    "size_bytes": db_size,
                    "size_mb": round(db_size / (1024 * 1024), 2)
                },
                "records": {
                    "scan_sessions": scan_count,
                    "mods": mod_count,
                    "language_files": lang_file_count,
                    "translation_entries": entry_count,
                    "file_hashes": hash_count
                },
                "memory": {
                    "active_scans": len(active_scans)
                }
            }
        }
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/scan/incremental-stats")
def get_incremental_scan_stats_api(directory: str):
    """获取增量扫描统计信息"""
    try:
        stats = get_incremental_scan_stats(directory)
        
        return {
            "success": True,
            "data": {
                "directory": directory,
                "scan_stats": stats,
                "efficiency": {
                    "skip_rate": round((stats["unchanged_files"] / max(stats["total_files"], 1)) * 100, 2),
                    "change_rate": round(((stats["changed_files"] + stats["new_files"]) / max(stats["total_files"], 1)) * 100, 2)
                }
            },
            "message": f"共 {stats['total_files']} 个文件，{stats['unchanged_files']} 个未变更可跳过"
        }
    except Exception as e:
        logger.error(f"获取增量扫描统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scan/clear-hashes")
async def clear_file_hashes():
    """清理所有文件哈希记录，强制全量扫描"""
    try:
        conn = sqlite3.connect("mc_l10n.db", timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        cursor = conn.cursor()
        
        # 获取清理前的记录数
        cursor.execute("SELECT COUNT(*) FROM file_hashes")
        before_count = cursor.fetchone()[0]
        
        # 清空文件哈希表
        cursor.execute("DELETE FROM file_hashes")
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"已清理 {before_count} 条文件哈希记录，下次扫描将进行全量扫描"
        }
    except Exception as e:
        logger.error(f"清理文件哈希失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 启动简化的MC L10n后端服务器...")
    print("📊 初始化数据库...")
    init_database()
    print("✅ 数据库初始化完成")
    print("📍 API文档: http://localhost:18000/docs")
    uvicorn.run(
        "simple_backend:app",
        host="0.0.0.0", 
        port = 18000,
        reload=True,
        log_level="info"
    )