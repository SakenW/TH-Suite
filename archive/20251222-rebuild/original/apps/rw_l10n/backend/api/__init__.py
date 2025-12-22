from fastapi import APIRouter

from .config import router as config_router
from .mods import router as mods_router
from .saves import router as saves_router
from .system import router as system_router
from .workshop import router as workshop_router

# 创建主路由
router = APIRouter()

# 注册子路由
router.include_router(mods_router, prefix="/mods", tags=["mods"])
router.include_router(workshop_router, prefix="/workshop", tags=["workshop"])
router.include_router(saves_router, prefix="/saves", tags=["saves"])
router.include_router(config_router, prefix="/config", tags=["config"])
router.include_router(system_router, prefix="/system", tags=["system"])
