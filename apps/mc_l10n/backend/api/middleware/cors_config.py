"""
CORS配置模块
处理跨域资源共享设置
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

logger = logging.getLogger(__name__)


def setup_cors(app: FastAPI) -> None:
    """
    设置CORS中间件
    
    Args:
        app: FastAPI应用实例
    """
    try:
        # 允许的源地址
        origins = [
            "http://localhost:3000",
            "http://localhost:5173",  # Vite开发服务器
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "https://localhost:1420",  # Tauri应用
            "tauri://localhost",
            "http://tauri.localhost",
            "https://tauri.localhost"
        ]
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        logger.info("CORS中间件配置完成")
        
    except Exception as e:
        logger.error(f"CORS配置失败: {e}")
        raise