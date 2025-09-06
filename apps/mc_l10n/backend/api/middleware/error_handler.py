"""
错误处理中间件
统一处理应用程序异常和错误响应格式
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import traceback

logger = logging.getLogger(__name__)


def setup_error_handlers(app: FastAPI) -> None:
    """
    设置全局错误处理器
    
    Args:
        app: FastAPI应用实例
    """
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理HTTP异常"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "status_code": exc.status_code
                }
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求验证错误"""
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "请求参数验证失败",
                    "details": exc.errors()
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理通用异常"""
        error_detail = str(exc)
        error_traceback = traceback.format_exc()
        
        logger.error(f"未处理的异常: {error_detail}")
        logger.error(f"异常堆栈: {error_traceback}")
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误",
                    "details": error_detail if app.debug else "请联系系统管理员"
                }
            }
        )
    
    logger.info("全局错误处理器配置完成")