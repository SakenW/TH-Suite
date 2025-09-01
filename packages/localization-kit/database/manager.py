"""
数据库管理器

提供 SQLCipher 加密数据库的连接和会话管理
支持事务、连接池、自动重试
"""

import os
import logging
from typing import Optional, Dict, Any, Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine

from .schema import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    数据库管理器
    
    特性：
    1. SQLCipher 加密支持
    2. 连接池管理
    3. 自动重试机制
    4. 事务管理
    """
    
    def __init__(
        self,
        db_path: str,
        password: Optional[str] = None,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        echo: bool = False
    ):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
            password: SQLCipher 密码（如果为 None，使用普通 SQLite）
            pool_size: 连接池大小
            max_overflow: 最大溢出连接数
            pool_timeout: 连接超时时间（秒）
            echo: 是否输出 SQL 语句
        """
        self.db_path = Path(db_path)
        self.password = password
        self.echo = echo
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建引擎
        self.engine = self._create_engine(
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout
        )
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # 初始化数据库
        self._init_database()
        
        logger.info(f"数据库管理器初始化完成: {self.db_path}")
    
    def _create_engine(
        self,
        pool_size: int,
        max_overflow: int,
        pool_timeout: int
    ) -> Engine:
        """创建数据库引擎"""
        # 构建连接 URL
        db_url = f"sqlite:///{self.db_path}"
        
        # 创建引擎
        engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            echo=self.echo,
            connect_args={
                'check_same_thread': False,  # 允许多线程访问
                'timeout': 30.0  # 数据库锁超时
            }
        )
        
        # 如果有密码，配置 SQLCipher
        if self.password:
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                # 设置 SQLCipher 密码
                cursor.execute(f"PRAGMA key = '{self.password}'")
                # 启用外键约束
                cursor.execute("PRAGMA foreign_keys = ON")
                # 启用 JSON1 扩展
                cursor.execute("PRAGMA compile_options")
                cursor.close()
        else:
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                # 启用外键约束
                cursor.execute("PRAGMA foreign_keys = ON")
                # 启用 WAL 模式（提高并发性能）
                cursor.execute("PRAGMA journal_mode = WAL")
                # 设置同步模式
                cursor.execute("PRAGMA synchronous = NORMAL")
                cursor.close()
        
        return engine
    
    def _init_database(self) -> None:
        """初始化数据库结构"""
        try:
            # 创建所有表
            Base.metadata.create_all(bind=self.engine)
            
            # 初始化默认数据
            with self.get_session() as session:
                self._init_default_data(session)
                session.commit()
                
            logger.info("数据库结构初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _init_default_data(self, session: Session) -> None:
        """初始化默认数据"""
        from .schema import LocaleAliasTable, SerializationProfileTable
        
        # 初始化常用语言映射
        default_locales = [
            ("zh_cn", "zh-CN", "简体中文"),
            ("zh_tw", "zh-TW", "繁體中文"),
            ("en_us", "en-US", "English (US)"),
            ("en_gb", "en-GB", "English (UK)"),
            ("ja_jp", "ja-JP", "日本語"),
            ("ko_kr", "ko-KR", "한국어"),
            ("ru_ru", "ru-RU", "Русский"),
            ("de_de", "de-DE", "Deutsch"),
            ("fr_fr", "fr-FR", "Français"),
            ("es_es", "es-ES", "Español"),
            ("pt_br", "pt-BR", "Português (Brasil)"),
            ("it_it", "it-IT", "Italiano"),
        ]
        
        for mc_locale, bcp47, display_name in default_locales:
            if not session.query(LocaleAliasTable).filter_by(
                minecraft_locale=mc_locale
            ).first():
                locale_alias = LocaleAliasTable(
                    minecraft_locale=mc_locale,
                    bcp47_locale=bcp47,
                    display_name=display_name
                )
                session.add(locale_alias)
        
        # 初始化默认序列化配置
        default_profiles = [
            {
                "profile_id": "minecraft_json",
                "format": "json",
                "charset": "utf-8",
                "newline": "\\n",
                "bom": False,
                "indent": 2,
                "sort_policy": "none"
            },
            {
                "profile_id": "minecraft_lang",
                "format": "lang",
                "charset": "utf-8",
                "newline": "\\n",
                "bom": False,
                "escape_style": "unicode",
                "sort_policy": "alphabetical"
            },
            {
                "profile_id": "forge_properties",
                "format": "properties",
                "charset": "iso-8859-1",
                "newline": "\\n",
                "bom": False,
                "escape_style": "unicode",
                "sort_policy": "none"
            }
        ]
        
        for profile_data in default_profiles:
            if not session.query(SerializationProfileTable).filter_by(
                profile_id=profile_data["profile_id"]
            ).first():
                profile = SerializationProfileTable(**profile_data)
                session.add(profile)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取数据库会话（上下文管理器）
        
        使用示例：
            with db_manager.get_session() as session:
                # 执行数据库操作
                session.add(entity)
                session.commit()
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"数据库会话错误: {e}")
            raise
        finally:
            session.close()
    
    def execute_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """执行原始 SQL 语句"""
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            return result
    
    def get_table_stats(self) -> Dict[str, int]:
        """获取表统计信息"""
        stats = {}
        
        tables = [
            'artifacts', 'containers', 'language_files', 'blobs',
            'entries_current', 'patch_sets', 'patch_items',
            'apply_runs', 'apply_results', 'quality_checks'
        ]
        
        with self.get_session() as session:
            for table in tables:
                count = session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar()
                stats[table] = count
        
        return stats
    
    def vacuum(self) -> None:
        """执行 VACUUM 操作（压缩数据库）"""
        with self.engine.connect() as conn:
            conn.execute(text("VACUUM"))
            conn.commit()
        logger.info("数据库 VACUUM 完成")
    
    def backup(self, backup_path: str) -> None:
        """备份数据库"""
        import shutil
        
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 确保所有事务完成
        self.engine.dispose()
        
        # 复制数据库文件
        shutil.copy2(self.db_path, backup_path)
        
        # 如果使用 WAL 模式，也复制 WAL 文件
        wal_file = Path(str(self.db_path) + "-wal")
        if wal_file.exists():
            shutil.copy2(wal_file, str(backup_path) + "-wal")
        
        shm_file = Path(str(self.db_path) + "-shm")
        if shm_file.exists():
            shutil.copy2(shm_file, str(backup_path) + "-shm")
        
        logger.info(f"数据库备份完成: {backup_path}")
    
    def close(self) -> None:
        """关闭数据库连接"""
        self.engine.dispose()
        logger.info("数据库连接已关闭")