#!/usr/bin/env python3
"""强制数据库初始化脚本"""

from infrastructure.db_initializer import DatabaseInitializer
import structlog

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

def main():
    db_path = "data/mc_l10n.db"
    logger.info("🚀 开始强制数据库初始化", db_path=db_path)
    
    # 删除现有数据库
    import os
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info("🗑️ 已删除现有数据库")
    
    # 初始化数据库
    initializer = DatabaseInitializer(db_path)
    success = initializer.ensure_database_exists()
    
    if success:
        logger.info("✅ 数据库初始化成功")
        
        # 验证表结构
        import sqlite3
        conn = sqlite3.connect(db_path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        table_names = [t[0] for t in tables]
        logger.info("📋 创建的表", tables=table_names, count=len(table_names))
        conn.close()
        
    else:
        logger.error("❌ 数据库初始化失败")

if __name__ == "__main__":
    main()