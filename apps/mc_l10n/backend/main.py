"""
MC L10n FastAPI应用主入口点

启动Minecraft本地化工具的后端API服务
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Any
import uuid
import sqlite3
import asyncio
from datetime import datetime
from pathlib import Path
import hashlib
import zipfile
import json
from collections import defaultdict
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

# 加载环境变量
load_dotenv()
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

# 添加项目根目录到Python路径
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# 设置日志
logger = logging.getLogger(__name__)

# 全局变量存储扫描状态
active_scans = {}

# 数据模型
class ScanRequest(BaseModel):
    directory: str
    incremental: bool = True

from api.middleware.cors_config import setup_cors
from api.middleware.error_handler import setup_error_handlers

# 中间件导入
from api.middleware.logging_middleware import LoggingMiddleware
from api.routes.mod_routes import router as mod_router

# API路由导入
from api.routes.project_routes import router as project_router
# from api.routes.scan_routes import router as scan_router  # 暂时移除，避免模型冲突
from api.routes.translation_routes import router as translation_router

# 基础设施初始化
from infrastructure import initialize_infrastructure

from packages.core.framework.logging import StructLogFactory

logger = StructLogFactory.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("MC L10n API服务启动中...")

    try:
        # 初始化基础设施
        logger.info("初始化基础设施组件...")
        initialize_infrastructure()

        # 初始化数据库连接（如果需要）
        # await initialize_database()

        # 初始化缓存系统
        # await initialize_cache()

        logger.info("MC L10n API服务启动完成")

        yield  # 应用运行期间

    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise
    finally:
        # 关闭时执行
        logger.info("MC L10n API服务关闭中...")

        # 清理资源
        # await cleanup_database()
        # await cleanup_cache()

        logger.info("MC L10n API服务关闭完成")


# 创建FastAPI应用实例
def create_app() -> FastAPI:
    """创建并配置FastAPI应用"""

    # 从环境变量获取配置
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    environment = os.getenv("ENVIRONMENT", "production").lower()

    # 创建应用实例
    app = FastAPI(
        title="MC L10n API",
        description="Minecraft本地化工具后端API服务",
        version="1.0.0",
        debug=debug_mode,
        lifespan=lifespan,
        docs_url=None,  # 自定义文档路径
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
    )

    # 设置CORS
    setup_cors(app)

    # 设置全局错误处理
    setup_error_handlers(app)

    # 添加日志中间件
    app.add_middleware(
        LoggingMiddleware,
        log_request_body=False,  # 暂时禁用请求体日志，避免请求体读取冲突
        log_response_body=debug_mode,
        exclude_paths=[
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/openapi.json",
        ],
    )

    # 注册路由
    app.include_router(project_router)
    app.include_router(mod_router)
    # app.include_router(scan_router)  # 暂时移除，避免模型冲突
    app.include_router(translation_router)
    
    # 扫描相关函数
    def init_database():
        """初始化数据库"""
        conn = sqlite3.connect("mc_l10n.db")
        cursor = conn.cursor()
        
        # 创建扫描会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_sessions (
                id TEXT PRIMARY KEY,
                directory TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT DEFAULT 'scanning',
                total_mods INTEGER DEFAULT 0,
                total_language_files INTEGER DEFAULT 0,
                total_keys INTEGER DEFAULT 0,
                scan_mode TEXT DEFAULT '全量'
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
        
        conn.commit()
        conn.close()
    
    def parse_mod_jar(jar_path: Path):
        """简化的JAR解析函数"""
        try:
            mod_info = {"mod_id": jar_path.stem, "name": jar_path.stem}
            language_files = []
            
            with zipfile.ZipFile(jar_path, 'r') as jar:
                for file_info in jar.filelist:
                    file_path = file_info.filename
                    if '/lang/' in file_path and file_path.endswith('.json'):
                        # 提取语言代码
                        lang_file = file_path.split('/')[-1]
                        locale = lang_file.replace('.json', '')
                        
                        try:
                            with jar.open(file_info) as f:
                                content = json.load(f)
                                if isinstance(content, dict):
                                    language_files.append({
                                        "file_path": file_path,
                                        "locale": locale,
                                        "key_count": len(content),
                                        "namespace": file_path.split('/')[1] if '/' in file_path else 'minecraft',
                                        "entries": content  # 添加实际的翻译条目数据
                                    })
                        except:
                            pass  # 忽略解析失败的文件
            
            return mod_info, language_files
        except Exception as e:
            logger.error(f"解析JAR失败 {jar_path}: {e}")
            return None, []
    
    async def scan_directory_real(scan_id: str, directory: str, incremental: bool = True):
        """实际扫描目录函数"""
        logger.info(f"开始{'增量' if incremental else '全量'}扫描目录: {directory}")
        
        try:
            scan_path = Path(directory)
            if not scan_path.exists():
                raise ValueError(f"目录不存在: {directory}")
            
            # 查找所有jar文件
            jar_files = []
            for root, dirs, files in os.walk(scan_path):
                for file in files:
                    if file.endswith('.jar'):
                        jar_files.append(Path(root) / file)
            
            # 更新扫描状态
            active_scans[scan_id] = {
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
            
            # 初始化数据库连接和统计
            conn = sqlite3.connect("mc_l10n.db")
            cursor = conn.cursor()
            
            total_mods = 0
            total_language_files = 0
            total_keys = 0
            
            for i, jar_path in enumerate(jar_files):
                # 检查是否被取消
                if scan_id in active_scans and active_scans[scan_id].get("status") == "cancelled":
                    logger.info(f"扫描被取消: {scan_id}")
                    conn.close()
                    return
                
                # 更新当前处理的文件
                active_scans[scan_id]["current_file"] = jar_path.name
                active_scans[scan_id]["processed_files"] = i + 1
                active_scans[scan_id]["progress"] = ((i + 1) / len(jar_files)) * 100
                
                logger.info(f"正在处理 ({i+1}/{len(jar_files)}): {jar_path.name}")
                
                try:
                    mod_info, language_files = parse_mod_jar(jar_path)
                    
                    if mod_info:
                        # 存储模组信息
                        mod_id = str(uuid.uuid4())
                        cursor.execute("""
                            INSERT OR IGNORE INTO mods (id, scan_id, mod_id, display_name, version, file_path, size)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            mod_id, scan_id, mod_info.get('mod_id', jar_path.stem),
                            mod_info.get('name', jar_path.stem), mod_info.get('version', '未知'),
                            str(jar_path), jar_path.stat().st_size if jar_path.exists() else 0
                        ))
                        total_mods += 1
                        
                        # 存储语言文件和翻译条目
                        for lang_file in language_files:
                            lang_file_id = str(uuid.uuid4())
                            cursor.execute("""
                                INSERT OR IGNORE INTO language_files (id, scan_id, mod_id, namespace, locale, file_path, key_count)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                lang_file_id, scan_id, mod_info.get('mod_id', jar_path.stem),
                                lang_file.get('namespace', 'minecraft'), lang_file.get('locale', 'en_us'),
                                lang_file.get('file_path', ''), lang_file.get('key_count', 0)
                            ))
                            
                            # 存储翻译条目
                            if 'entries' in lang_file:
                                for key, value in lang_file['entries'].items():
                                    if isinstance(value, str):
                                        stored_value = value
                                    else:
                                        stored_value = str(value)
                                    
                                    cursor.execute("""
                                        INSERT OR IGNORE INTO translation_entries (id, language_file_id, key, value)
                                        VALUES (?, ?, ?, ?)
                                    """, (str(uuid.uuid4()), lang_file_id, key, stored_value))
                            
                            total_language_files += 1
                            total_keys += lang_file.get('key_count', 0)
                        
                        # 每处理5个文件提交一次
                        if (i + 1) % 5 == 0:
                            conn.commit()
                
                except Exception as e:
                    logger.error(f"处理文件 {jar_path} 时出错: {e}")
                    continue
                
                # 每10个文件休息一下，避免阻塞
                if i % 10 == 0:
                    await asyncio.sleep(0.1)
            
            cursor.execute("""
                UPDATE scan_sessions 
                SET status = 'completed', completed_at = ?, total_mods = ?, 
                    total_language_files = ?, total_keys = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), total_mods, total_language_files, total_keys, scan_id))
            conn.commit()
            conn.close()
            
            # 更新内存状态
            completion_data = {
                "status": "completed",
                "progress": 100,
                "total_files": len(jar_files),
                "processed_files": len(jar_files),
                "total_mods": total_mods,
                "total_language_files": total_language_files,
                "total_keys": total_keys,
                "completed_at": datetime.now().isoformat()
            }
            active_scans[scan_id].update(completion_data)
            
            logger.info(f"扫描完成: {scan_id}, 发现{total_mods}个模组，{total_language_files}个语言文件，{total_keys}个条目")
            
        except Exception as e:
            logger.error(f"扫描失败: {e}")
            active_scans[scan_id] = {"status": "failed", "error": str(e)}
            
            conn = sqlite3.connect("mc_l10n.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE scan_sessions SET status = 'failed' WHERE id = ?", (scan_id,))
            conn.commit()
            conn.close()
    
    # 初始化数据库
    init_database()
    
    # 兼容性端点
    from fastapi import APIRouter
    compat_router = APIRouter()
    
    @compat_router.get("/api/v1/scan-project-test-get")
    async def scan_project_test_get():
        """GET测试端点"""
        return {"success": True, "message": "GET test endpoint working"}
    
    @compat_router.post("/api/v1/scan-project-test")
    async def scan_project_test():
        """最简单的测试端点"""
        return {"success": True, "message": "test endpoint working"}
    
    @compat_router.post("/api/v1/scan-project-test-json")
    async def scan_project_test_json(request: dict):
        """测试JSON解析"""
        return {"success": True, "received": request}
    
    @compat_router.post("/api/v1/scan-project")
    async def scan_project_v1_compat(request: ScanRequest, background_tasks: BackgroundTasks):
        """真实的扫描端点"""
        try:
            # 提取参数
            directory = request.directory
            incremental = request.incremental
            
            if not directory:
                raise ValueError("directory参数是必需的")
            
            # 生成扫描ID
            scan_id = str(uuid.uuid4())
            
            # 创建扫描记录
            conn = sqlite3.connect("mc_l10n.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scan_sessions (id, directory, started_at, status)
                VALUES (?, ?, ?, 'scanning')
            """, (scan_id, directory, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            
            # 启动后台扫描任务
            background_tasks.add_task(scan_directory_real, scan_id, directory, incremental)
            
            return {
                "success": True,
                "message": f"扫描已开始: {directory}",
                "job_id": scan_id,
                "scan_id": scan_id
            }
            
        except Exception as e:
            logger.error(f"启动扫描失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @compat_router.get("/api/v1/scan-status/{scan_id}")
    async def get_scan_status_v1_compat(scan_id: str):
        """获取扫描状态"""
        try:
            # 检查内存中的扫描状态
            if scan_id in active_scans:
                status = active_scans[scan_id]
                return {"success": True, "data": status}
            
            # 从数据库查询扫描状态
            conn = sqlite3.connect("mc_l10n.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scan_sessions WHERE id = ?", (scan_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "success": True,
                    "data": {
                        "status": row[3],
                        "progress": 100 if row[3] == 'completed' else 0,
                        "total_mods": row[4],
                        "total_language_files": row[5],
                        "total_keys": row[6]
                    }
                }
            else:
                return {"success": False, "message": "扫描任务未找到"}
                
        except Exception as e:
            logger.error(f"获取扫描状态失败: {e}")
            return {"success": False, "message": str(e)}
    
    @compat_router.get("/api/v1/scan-results/{scan_id}")
    async def get_scan_results_v1_compat(scan_id: str):
        """获取扫描结果"""
        try:
            conn = sqlite3.connect("mc_l10n.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scan_sessions WHERE id = ?", (scan_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row and row[3] == 'completed':
                return {
                    "success": True,
                    "data": {
                        "scan_id": scan_id,
                        "mods": [],  # 简化实现
                        "language_files": [],  # 简化实现
                        "statistics": {
                            "total_mods": row[4] or 0,
                            "total_language_files": row[5] or 0, 
                            "total_keys": row[6] or 0,
                            "scan_duration_ms": 0  # 简化实现
                        }
                    }
                }
            else:
                return {"success": False, "message": "扫描未完成或不存在"}
                
        except Exception as e:
            logger.error(f"获取扫描结果失败: {e}")
            return {"success": False, "message": str(e)}
    
    @compat_router.post("/api/v1/scan-cancel/{scan_id}")
    async def cancel_scan_v1_compat(scan_id: str):
        """取消扫描"""
        try:
            # 检查扫描是否存在
            if scan_id not in active_scans:
                return {"success": False, "message": "扫描任务不存在或已完成"}
            
            # 标记为取消
            active_scans[scan_id]["status"] = "cancelled"
            
            # 更新数据库状态
            conn = sqlite3.connect("mc_l10n.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE scan_sessions SET status = 'cancelled' WHERE id = ?", (scan_id,))
            conn.commit()
            conn.close()
            
            logger.info(f"扫描已取消: {scan_id}")
            return {"success": True, "message": "扫描已取消"}
                
        except Exception as e:
            logger.error(f"取消扫描失败: {e}")
            return {"success": False, "message": str(e)}
    
    app.include_router(compat_router)
    
    # 直接在app上添加测试路由
    @app.get("/api/v1/direct-test")
    async def direct_test():
        return {"success": True, "message": "Direct route working"}

    # 添加健康检查端点
    @app.get("/health", tags=["系统"], summary="健康检查")
    async def health_check() -> dict[str, Any]:
        """健康检查端点"""
        return {
            "status": "healthy",
            "service": "mc-l10n-api",
            "version": "1.0.0",
            "environment": environment,
            "timestamp": "2024-12-30T12:00:00",  # 简化实现
        }

    # 添加系统信息端点
    @app.get("/info", tags=["系统"], summary="系统信息")
    async def system_info() -> dict[str, Any]:
        """系统信息端点"""
        import platform

        return {
            "service": {
                "name": "MC L10n API",
                "version": "1.0.0",
                "environment": environment,
                "debug_mode": debug_mode,
            },
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
            },
            "api": {
                "total_routes": len(app.routes),
                "cors_enabled": True,
                "error_handling": True,
                "request_logging": True,
            },
        }

    # 自定义OpenAPI文档
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="MC L10n API",
            version="1.0.0",
            description="""
# Minecraft本地化工具API

这是一个用于Minecraft模组和资源包本地化的完整API服务。

## 功能特性

### 🎯 项目管理
- 创建和管理翻译项目
- 项目配置和设置
- 项目进度统计

### 📦 模组管理
- 扫描和分析JAR/文件夹
- 解析模组元数据
- 依赖关系管理

### 🌐 翻译管理
- 翻译条目提取
- 多格式导入/导出
- 批量翻译操作
- 翻译进度跟踪

### 🔍 搜索功能
- 项目搜索
- 模组搜索
- 翻译内容搜索

## API版本

当前版本: **v1.0.0**

所有API端点都以 `/api/v1/` 开头。

## 认证

目前API处于开发阶段，暂不需要认证。生产环境将使用JWT token认证。

## 响应格式

所有API响应都遵循统一格式：

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功",
  "request_id": "req_12345678"
}
```

错误响应格式：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": { ... }
  },
  "request_id": "req_12345678"
}
```
            """,
            routes=app.routes,
        )

        # 添加自定义信息
        openapi_schema["info"]["x-logo"] = {
            "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
        }

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    # 自定义文档页面
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.0/bundles/redoc.standalone.js",
        )

    return app


# 创建应用实例
app = create_app()


# 启动配置
if __name__ == "__main__":
    import uvicorn

    # 从环境变量获取配置
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    reload = os.getenv("RELOAD", "true" if debug else "false").lower() == "true"
    workers = int(os.getenv("WORKERS", "1"))

    logger.info(f"启动MC L10n API服务: http://{host}:{port}")
    logger.info(f"调试模式: {debug}, 自动重载: {reload}, 工作进程: {workers}")
    logger.info(f"API文档: http://{host}:{port}/docs")
    logger.info(f"ReDoc文档: http://{host}:{port}/redoc")

    # 启动服务器
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not debug else 1,  # 调试模式下只使用1个工作进程
        access_log=True,
        use_colors=True,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(asctime)s %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "access": {
                    "()": "uvicorn.logging.AccessFormatter",
                    "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "uvicorn": {"level": "INFO", "handlers": ["default"], "propagate": False},
                "uvicorn.error": {"level": "INFO", "handlers": ["default"], "propagate": False},
                "uvicorn.access": {"level": "INFO", "handlers": ["access"], "propagate": False},
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        },
    )
