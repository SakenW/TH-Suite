"""
测试数据路由 - 用于在Web模式下测试功能
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import random
import asyncio
from datetime import datetime

router = APIRouter(prefix="/api/v1/test", tags=["测试数据"])

# 模拟的模组数据
MOCK_MODS = [
    {
        "id": "twilightforest",
        "name": "Twilight Forest",
        "version": "1.21.1-4.7.3196",
        "file_path": "/mods/twilightforest-1.21.1-4.7.3196.jar",
        "total_keys": 1250,
        "translated_keys": 1063,
        "progress": 85,
        "status": "translated",
        "languages": ["en_us", "zh_cn"],
        "type": "mod",
        "size": "45.2 MB"
    },
    {
        "id": "ae2",
        "name": "Applied Energistics 2",
        "version": "15.3.1-beta",
        "file_path": "/mods/ae2-15.3.1-beta.jar",
        "total_keys": 890,
        "translated_keys": 285,
        "progress": 32,
        "status": "partial",
        "languages": ["en_us", "zh_cn"],
        "type": "mod",
        "size": "12.8 MB"
    },
    {
        "id": "jei",
        "name": "Just Enough Items",
        "version": "1.21.1-20.1.16",
        "file_path": "/mods/jei-1.21.1-20.1.16.jar",
        "total_keys": 450,
        "translated_keys": 450,
        "progress": 100,
        "status": "completed",
        "languages": ["en_us", "zh_cn"],
        "type": "mod",
        "size": "8.5 MB"
    },
    {
        "id": "create",
        "name": "Create",
        "version": "0.5.1-f",
        "file_path": "/mods/create-0.5.1-f.jar",
        "total_keys": 2100,
        "translated_keys": 1470,
        "progress": 70,
        "status": "translated",
        "languages": ["en_us", "zh_cn", "ja_jp"],
        "type": "mod",
        "size": "28.3 MB"
    },
    {
        "id": "botania",
        "name": "Botania",
        "version": "1.21.1-445",
        "file_path": "/mods/botania-1.21.1-445.jar",
        "total_keys": 1800,
        "translated_keys": 900,
        "progress": 50,
        "status": "partial",
        "languages": ["en_us"],
        "type": "mod",
        "size": "15.7 MB"
    }
]

@router.get("/mods", summary="获取模拟的模组列表")
async def get_mock_mods() -> List[Dict[str, Any]]:
    """获取模拟的模组列表数据"""
    return MOCK_MODS

@router.post("/scan", summary="模拟扫描过程")
async def mock_scan_directory(directory: str = "/minecraft/mods") -> Dict[str, Any]:
    """
    模拟扫描目录过程
    返回扫描任务ID，可用于查询进度
    """
    task_id = f"scan_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "task_id": task_id,
        "status": "started",
        "directory": directory,
        "message": "扫描任务已启动"
    }

@router.get("/scan/{task_id}/progress", summary="获取扫描进度")
async def get_scan_progress(task_id: str) -> Dict[str, Any]:
    """
    模拟扫描进度
    返回随机生成的进度数据
    """
    # 模拟进度（实际应该从数据库或缓存获取）
    progress = random.randint(0, 100)
    
    return {
        "task_id": task_id,
        "status": "completed" if progress >= 100 else "scanning",
        "progress": min(progress, 100),
        "current_file": f"mod_{random.randint(1, 50)}.jar",
        "total_files": 125,
        "scanned_files": min(int(125 * progress / 100), 125),
        "found_mods": len(MOCK_MODS),
        "message": f"正在扫描: {min(int(125 * progress / 100), 125)}/125 个文件"
    }

@router.get("/mod/{mod_id}/details", summary="获取模组详细信息")
async def get_mod_details(mod_id: str) -> Dict[str, Any]:
    """获取模组的详细信息"""
    mod = next((m for m in MOCK_MODS if m["id"] == mod_id), None)
    if not mod:
        raise HTTPException(status_code=404, detail=f"模组 {mod_id} 未找到")
    
    # 添加更多详细信息
    details = mod.copy()
    details.update({
        "description": f"{mod['name']} 是一个流行的 Minecraft 模组",
        "authors": ["ModAuthor"],
        "license": "MIT",
        "homepage": f"https://example.com/mods/{mod_id}",
        "last_updated": "2024-12-20",
        "download_count": random.randint(10000, 1000000),
        "categories": ["Adventure", "Technology"],
        "dependencies": ["minecraft", "forge"],
        "language_stats": {
            "en_us": {"keys": mod["total_keys"], "progress": 100},
            "zh_cn": {"keys": mod["translated_keys"], "progress": mod["progress"]},
            "ja_jp": {"keys": random.randint(0, mod["total_keys"]), "progress": random.randint(0, 100)}
        }
    })
    
    return details

@router.post("/translate", summary="模拟翻译过程")
async def mock_translate(mod_id: str, target_language: str = "zh_cn") -> Dict[str, Any]:
    """模拟翻译过程"""
    mod = next((m for m in MOCK_MODS if m["id"] == mod_id), None)
    if not mod:
        raise HTTPException(status_code=404, detail=f"模组 {mod_id} 未找到")
    
    return {
        "task_id": f"translate_{mod_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "mod_id": mod_id,
        "mod_name": mod["name"],
        "source_language": "en_us",
        "target_language": target_language,
        "total_keys": mod["total_keys"],
        "status": "processing",
        "message": f"开始翻译 {mod['name']} 到 {target_language}"
    }

@router.get("/statistics", summary="获取统计信息")
async def get_statistics() -> Dict[str, Any]:
    """获取整体统计信息"""
    total_mods = len(MOCK_MODS)
    total_keys = sum(mod["total_keys"] for mod in MOCK_MODS)
    translated_keys = sum(mod["translated_keys"] for mod in MOCK_MODS)
    
    return {
        "total_mods": total_mods,
        "completed_mods": sum(1 for mod in MOCK_MODS if mod["progress"] == 100),
        "partial_mods": sum(1 for mod in MOCK_MODS if 0 < mod["progress"] < 100),
        "untranslated_mods": sum(1 for mod in MOCK_MODS if mod["progress"] == 0),
        "total_keys": total_keys,
        "translated_keys": translated_keys,
        "overall_progress": round(translated_keys / total_keys * 100, 2),
        "supported_languages": ["en_us", "zh_cn", "ja_jp", "ko_kr", "es_es", "fr_fr"],
        "last_scan": "2024-12-30 10:30:00",
        "storage_used": "256 MB",
        "cache_size": "32 MB"
    }

@router.post("/export", summary="模拟导出语言包")
async def mock_export(mod_ids: List[str], language: str = "zh_cn") -> Dict[str, Any]:
    """模拟导出语言包"""
    selected_mods = [mod for mod in MOCK_MODS if mod["id"] in mod_ids]
    
    if not selected_mods:
        raise HTTPException(status_code=400, detail="未选择任何模组")
    
    return {
        "export_id": f"export_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "mods_count": len(selected_mods),
        "language": language,
        "format": "resource_pack",
        "file_size": f"{random.randint(1, 10)} MB",
        "download_url": f"/api/v1/test/download/export_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip",
        "status": "ready",
        "message": f"成功导出 {len(selected_mods)} 个模组的 {language} 语言包"
    }