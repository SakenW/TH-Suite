from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from packages.protocol.schemas import (
    ConfigImportRequest,
    ConfigUpdateRequest,
)

from ..dependencies import get_config_service
from ..services import ConfigService

router = APIRouter()


@router.get("/")
async def get_all_config(config_service: ConfigService = Depends(get_config_service)):
    """获取所有配置"""
    try:
        config = await config_service.get_all_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{section}")
async def get_config_section(
    section: str, config_service: ConfigService = Depends(get_config_service)
):
    """获取特定配置节"""
    try:
        config = await config_service.get_config_section(section)
        if config is None:
            raise HTTPException(status_code=404, detail="配置节未找到")
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{section}/{key}")
async def get_config_value(
    section: str, key: str, config_service: ConfigService = Depends(get_config_service)
):
    """获取特定配置值"""
    try:
        value = await config_service.get_config_value(section, key)
        if value is None:
            raise HTTPException(status_code=404, detail="配置项未找到")
        return {"value": value}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{section}/{key}")
async def set_config_value(
    section: str,
    key: str,
    value: dict[str, Any],
    config_service: ConfigService = Depends(get_config_service),
):
    """设置特定配置值"""
    try:
        await config_service.set_config_value(section, key, value.get("value"))
        return {"message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{section}")
async def update_config_section(
    section: str,
    config: dict[str, Any],
    config_service: ConfigService = Depends(get_config_service),
):
    """更新配置节"""
    try:
        await config_service.update_config_section(section, config)
        return {"message": "配置节已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update")
async def update_config(
    request: ConfigUpdateRequest,
    config_service: ConfigService = Depends(get_config_service),
):
    """批量更新配置"""
    try:
        await config_service.update_config(request.config)
        return {"message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_config(
    section: str | None = Query(None, description="要重置的配置节，不指定则重置所有"),
    config_service: ConfigService = Depends(get_config_service),
):
    """重置配置到默认值"""
    try:
        if section:
            await config_service.reset_config_section(section)
            return {"message": f"配置节 {section} 已重置"}
        else:
            await config_service.reset_all_config()
            return {"message": "所有配置已重置"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_config(
    sections: str | None = Query(None, description="要导出的配置节，用逗号分隔"),
    config_service: ConfigService = Depends(get_config_service),
):
    """导出配置"""
    try:
        section_list = sections.split(",") if sections else None
        config_data = await config_service.export_config(section_list)
        return config_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_config(
    request: ConfigImportRequest,
    config_service: ConfigService = Depends(get_config_service),
):
    """导入配置"""
    try:
        result = await config_service.import_config(
            config_data=request.config_data,
            merge=request.merge,
            validate=request.validate,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema")
async def get_config_schema(
    config_service: ConfigService = Depends(get_config_service),
):
    """获取配置模式定义"""
    try:
        schema = await config_service.get_config_schema()
        return schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_config(
    config: dict[str, Any], config_service: ConfigService = Depends(get_config_service)
):
    """验证配置"""
    try:
        result = await config_service.validate_config(config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/game-paths")
async def get_game_paths(config_service: ConfigService = Depends(get_config_service)):
    """获取游戏路径配置"""
    try:
        paths = await config_service.get_game_paths()
        return paths
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/game-paths")
async def set_game_paths(
    paths: dict[str, str], config_service: ConfigService = Depends(get_config_service)
):
    """设置游戏路径配置"""
    try:
        await config_service.set_game_paths(paths)
        return {"message": "游戏路径已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-detect-paths")
async def auto_detect_game_paths(
    config_service: ConfigService = Depends(get_config_service),
):
    """自动检测游戏路径"""
    try:
        paths = await config_service.auto_detect_game_paths()
        return paths
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mod-load-order")
async def get_mod_load_order(
    config_service: ConfigService = Depends(get_config_service),
):
    """获取模组加载顺序"""
    try:
        load_order = await config_service.get_mod_load_order()
        return load_order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mod-load-order")
async def set_mod_load_order(
    load_order: dict[str, Any],
    config_service: ConfigService = Depends(get_config_service),
):
    """设置模组加载顺序"""
    try:
        await config_service.set_mod_load_order(load_order)
        return {"message": "模组加载顺序已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize-load-order")
async def optimize_mod_load_order(
    config_service: ConfigService = Depends(get_config_service),
):
    """优化模组加载顺序"""
    try:
        result = await config_service.optimize_mod_load_order()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backup")
async def list_config_backups(
    config_service: ConfigService = Depends(get_config_service),
):
    """获取配置备份列表"""
    try:
        backups = await config_service.list_config_backups()
        return backups
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup")
async def create_config_backup(
    name: str | None = Query(None, description="备份名称"),
    config_service: ConfigService = Depends(get_config_service),
):
    """创建配置备份"""
    try:
        backup_id = await config_service.create_config_backup(name)
        return {"backup_id": backup_id, "message": "配置备份已创建"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/{backup_id}/restore")
async def restore_config_backup(
    backup_id: str, config_service: ConfigService = Depends(get_config_service)
):
    """恢复配置备份"""
    try:
        await config_service.restore_config_backup(backup_id)
        return {"message": "配置已恢复"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backup/{backup_id}")
async def delete_config_backup(
    backup_id: str, config_service: ConfigService = Depends(get_config_service)
):
    """删除配置备份"""
    try:
        await config_service.delete_config_backup(backup_id)
        return {"message": "配置备份已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
