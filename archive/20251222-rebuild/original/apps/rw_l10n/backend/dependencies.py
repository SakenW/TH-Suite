from typing import Annotated

from fastapi import Depends, Request

from packages.protocol.websocket import WebSocketManager

from .services import ConfigService, ModService, SaveGameService, WorkshopService


def get_mod_service(request: Request) -> ModService:
    """获取模组服务实例"""
    return request.app.state.mod_service


def get_workshop_service(request: Request) -> WorkshopService:
    """获取 Workshop 服务实例"""
    return request.app.state.workshop_service


def get_save_game_service(request: Request) -> SaveGameService:
    """获取存档服务实例"""
    return request.app.state.save_game_service


def get_config_service(request: Request) -> ConfigService:
    """获取配置服务实例"""
    return request.app.state.config_service


def get_websocket_manager(request: Request) -> WebSocketManager:
    """获取 WebSocket 管理器实例"""
    return request.app.state.websocket_manager


# 类型注解别名
ModServiceDep = Annotated[ModService, Depends(get_mod_service)]
WorkshopServiceDep = Annotated[WorkshopService, Depends(get_workshop_service)]
SaveGameServiceDep = Annotated[SaveGameService, Depends(get_save_game_service)]
ConfigServiceDep = Annotated[ConfigService, Depends(get_config_service)]
WebSocketManagerDep = Annotated[WebSocketManager, Depends(get_websocket_manager)]
