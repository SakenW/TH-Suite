"""
Minecraft核心适配器
实现Minecraft数据与Trans-Hub Core的完整集成
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import structlog

from .core_client import (
    TransHubClient, TransHubConfig, ContentItem, 
    ProjectInfo, IngestionResult, ExportFilter, 
    create_transhub_client
)
from .projection import (
    MinecraftProjectionAdapter, MinecraftLanguageData,
    MinecraftLanguageFile, load_projection_spec_from_config
)
from ..domain.jar_processor import JarProcessor, get_jar_processor
from ..domain.mod_scanner import DDDScanner, get_scanner_instance

logger = structlog.get_logger(__name__)


@dataclass 
class PackIngestionResult:
    """组合包摄入结果"""
    success: bool
    pack_id: str
    processed_mods: int
    processed_translations: int
    failed_items: int
    errors: List[str]
    
    @classmethod
    def from_core_result(cls, ingestion_result: IngestionResult) -> 'PackIngestionResult':
        """从核心摄入结果创建"""
        return cls(
            success=ingestion_result.success,
            pack_id=ingestion_result.project_id,
            processed_mods=0,  # 将在处理过程中计算
            processed_translations=ingestion_result.processed_items,
            failed_items=ingestion_result.failed_items,
            errors=ingestion_result.errors
        )


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    pack_id: str
    languages: List[str]
    synced_files: int
    conflicts: List[Dict[str, Any]]
    errors: List[str]
    
    def add_language_result(self, language: str, file_count: int):
        """添加语言结果"""
        if language not in self.languages:
            self.languages.append(language)
        self.synced_files += file_count
    
    def add_conflicts(self, language: str, conflicts: List[Dict[str, Any]]):
        """添加冲突"""
        for conflict in conflicts:
            conflict['language'] = language
            self.conflicts.append(conflict)
    
    def add_error(self, language: str, error: str):
        """添加错误"""
        self.errors.append(f"{language}: {error}")


class MinecraftCoreAdapter:
    """Minecraft核心适配器"""
    
    def __init__(
        self,
        transhub_config: TransHubConfig,
        projection_spec_path: Optional[str] = None,
        database_path: Optional[str] = None
    ):
        self.transhub_config = transhub_config
        self.core_client = TransHubClient(transhub_config)
        
        # 初始化投影适配器
        if projection_spec_path is None:
            # 使用默认路径
            config_dir = Path(__file__).parent.parent / "configs"
            projection_spec_path = str(config_dir / "mc-projection.yaml")
        
        self.projection_adapter = MinecraftProjectionAdapter(projection_spec_path)
        
        # 初始化JAR处理器
        self.jar_processor = get_jar_processor()
        
        # 初始化扫描器
        self.scanner = get_scanner_instance(database_path)
        
        logger.info("Minecraft核心适配器初始化完成",
                   base_url=transhub_config.base_url,
                   app_name=transhub_config.app_name)
    
    async def initialize(self):
        """初始化适配器"""
        # 连接到Trans-Hub Core
        await self.core_client.connect()
        
        # 注册投影规范到核心
        if self.projection_adapter.spec:
            spec_dict = asdict(self.projection_adapter.spec)
            await self.core_client.register_projection_spec(spec_dict)
            
        logger.info("Minecraft适配器初始化完成")
    
    async def scan_and_ingest_pack(
        self, 
        pack_path: str,
        pack_id: str,
        incremental: bool = True
    ) -> PackIngestionResult:
        """扫描并摄入组合包"""
        try:
            # 1. 扫描Minecraft文件结构
            logger.info("开始扫描组合包", pack_path=pack_path, pack_id=pack_id)
            
            scan_result = await self.scanner.start_scan(
                pack_path,
                incremental=incremental
            )
            
            # 等待扫描完成
            scan_id = scan_result["scan_id"]
            while True:
                status = await self.scanner.get_scan_status(scan_id)
                if status["status"] in ["completed", "failed"]:
                    break
                await asyncio.sleep(1)
            
            if status["status"] == "failed":
                return PackIngestionResult(
                    success=False,
                    pack_id=pack_id,
                    processed_mods=0,
                    processed_translations=0,
                    failed_items=0,
                    errors=[status.get("error", "扫描失败")]
                )
            
            # 2. 转换为Minecraft格式
            minecraft_data = await self._convert_scan_result_to_minecraft_data(
                status, pack_id, pack_path
            )
            
            # 3. 转换为标准格式
            logger.info("转换为核心格式", 
                       mods=len(set(lf.mod_id for lf in minecraft_data.language_files)),
                       files=len(minecraft_data.language_files))
            
            core_items = await self.projection_adapter.minecraft_to_core(minecraft_data)
            
            # 转换为ContentItem格式
            content_items = [
                ContentItem(
                    uida_hash=item["uida_hash"],
                    uida_uri=item["uida_uri"],
                    namespace=item["namespace"],
                    project_id=item["project_id"],
                    keys=item["keys"],
                    context=item["context"],
                    source_text=item["source_text"],
                    target_text=item.get("target_text"),
                    metadata=item.get("metadata"),
                    status="active"
                )
                for item in core_items
            ]
            
            # 4. 通过SDK摄入到核心
            logger.info("摄入内容到Trans-Hub Core", items_count=len(content_items))
            
            ingestion_result = await self.core_client.ingest_content(
                pack_id, content_items
            )
            
            # 5. 构建结果
            result = PackIngestionResult.from_core_result(ingestion_result)
            result.processed_mods = len(set(lf.mod_id for lf in minecraft_data.language_files))
            
            logger.info("组合包摄入完成",
                       pack_id=pack_id,
                       success=result.success,
                       mods=result.processed_mods,
                       translations=result.processed_translations)
            
            return result
            
        except Exception as e:
            logger.error("扫描摄入失败", pack_id=pack_id, error=str(e))
            return PackIngestionResult(
                success=False,
                pack_id=pack_id,
                processed_mods=0,
                processed_translations=0,
                failed_items=0,
                errors=[str(e)]
            )
    
    async def sync_pack_translations(
        self,
        pack_id: str,
        target_languages: List[str],
        output_path: Optional[str] = None
    ) -> SyncResult:
        """同步组合包翻译"""
        result = SyncResult(
            success=True,
            pack_id=pack_id,
            languages=[],
            synced_files=0,
            conflicts=[],
            errors=[]
        )
        
        try:
            for lang in target_languages:
                try:
                    # 从核心导出最新翻译
                    logger.info("导出翻译", pack_id=pack_id, language=lang)
                    
                    export_filter = ExportFilter(
                        target_language=lang,
                        status_filter=["completed", "reviewed", "active"]
                    )
                    
                    translations = []
                    async for item in self.core_client.export_content(pack_id, export_filter):
                        translations.append(item)
                    
                    if not translations:
                        logger.warning("没有找到翻译内容", pack_id=pack_id, language=lang)
                        continue
                    
                    # 转换为Minecraft格式
                    logger.info("转换为Minecraft格式", 
                               pack_id=pack_id,
                               language=lang,
                               items_count=len(translations))
                    
                    minecraft_data = await self.projection_adapter.core_to_minecraft(
                        translations, pack_id
                    )
                    
                    # 写回文件（如果指定了输出路径）
                    if output_path:
                        file_count = await self._write_minecraft_files(
                            output_path, minecraft_data, lang
                        )
                        result.add_language_result(lang, file_count)
                    
                    logger.info("语言同步完成", 
                               pack_id=pack_id,
                               language=lang,
                               files=len(minecraft_data.language_files))
                
                except Exception as e:
                    logger.error("语言同步失败",
                               pack_id=pack_id,
                               language=lang,
                               error=str(e))
                    result.add_error(lang, str(e))
                    result.success = False
            
            return result
            
        except Exception as e:
            logger.error("同步过程失败", pack_id=pack_id, error=str(e))
            result.success = False
            result.add_error("general", str(e))
            return result
    
    async def create_project(
        self,
        pack_name: str,
        pack_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProjectInfo:
        """创建项目"""
        project_data = {
            "name": pack_name,
            "type": "minecraft_modpack",
            "metadata": metadata or {}
        }
        
        # 添加扫描信息
        project_data["metadata"].update({
            "pack_path": pack_path,
            "app_name": self.transhub_config.app_name,
            "created_by": "minecraft_core_adapter"
        })
        
        return await self.core_client.create_project(project_data)
    
    async def get_project(self, project_id: str) -> Optional[ProjectInfo]:
        """获取项目信息"""
        return await self.core_client.get_project(project_id)
    
    async def get_translation_progress(self, project_id: str) -> Dict[str, Any]:
        """获取翻译进度"""
        return await self.core_client.get_translation_progress(project_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return await self.core_client.health_check()
    
    async def _convert_scan_result_to_minecraft_data(
        self,
        scan_status: Dict[str, Any],
        pack_id: str,
        pack_path: str
    ) -> MinecraftLanguageData:
        """转换扫描结果为Minecraft数据格式"""
        # 创建基础数据结构
        minecraft_data = MinecraftLanguageData(
            pack_id=pack_id,
            pack_format=9,  # 默认格式版本
            minecraft_version="1.19.2",  # 默认版本，将从实际数据推断
            mod_loader="forge",  # 默认加载器，将从实际数据推断
            language_files=[]
        )
        
        # 扫描JAR文件提取语言数据
        pack_path_obj = Path(pack_path)
        jar_files = list(pack_path_obj.rglob("*.jar"))
        
        for jar_path in jar_files:
            try:
                # 提取MOD信息
                mod_info = self.jar_processor.extract_mod_info(jar_path)
                if not mod_info:
                    continue
                
                # 提取语言文件
                language_files = self.jar_processor.extract_language_files(jar_path, mod_info)
                
                for lang_file in language_files:
                    mc_lang_file = MinecraftLanguageFile(
                        mod_id=lang_file.mod_id,
                        language=lang_file.language,
                        file_path=lang_file.file_path
                    )
                    mc_lang_file.translations = lang_file.translations
                    mc_lang_file.mod_version = mod_info.version
                    
                    minecraft_data.add_language_file(mc_lang_file)
                
                # 更新元数据
                if mod_info.loader_type.value != "unknown":
                    minecraft_data.mod_loader = mod_info.loader_type.value
                    
            except Exception as e:
                logger.warning("处理JAR文件失败", jar_path=str(jar_path), error=str(e))
                continue
        
        return minecraft_data
    
    async def _write_minecraft_files(
        self,
        output_path: str,
        minecraft_data: MinecraftLanguageData,
        language: str
    ) -> int:
        """写入Minecraft文件"""
        import json
        
        output_dir = Path(output_path)
        written_files = 0
        
        for lang_file in minecraft_data.language_files:
            if lang_file.language != language:
                continue
                
            # 构建输出路径
            file_path = output_dir / lang_file.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                # 写入JSON格式
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(lang_file.translations, f, ensure_ascii=False, indent=2)
                
                written_files += 1
                logger.debug("写入语言文件", file_path=str(file_path))
                
            except Exception as e:
                logger.error("写入文件失败", file_path=str(file_path), error=str(e))
                
        return written_files
    
    async def close(self):
        """关闭适配器"""
        if self.core_client:
            await self.core_client.disconnect()
        
        logger.info("Minecraft核心适配器已关闭")


# ==================== 工厂函数 ====================

def create_minecraft_core_adapter(
    base_url: str,
    api_key: str,
    app_name: str = "mc-l10n",
    projection_spec_path: Optional[str] = None,
    database_path: Optional[str] = None,
    **kwargs
) -> MinecraftCoreAdapter:
    """创建Minecraft核心适配器"""
    config = TransHubConfig(
        base_url=base_url,
        api_key=api_key,
        app_name=app_name,
        **kwargs
    )
    
    return MinecraftCoreAdapter(
        transhub_config=config,
        projection_spec_path=projection_spec_path,
        database_path=database_path
    )


async def test_minecraft_adapter(
    base_url: str,
    api_key: str,
    pack_path: str,
    pack_id: str = "test_pack"
) -> Dict[str, Any]:
    """测试Minecraft适配器"""
    adapter = create_minecraft_core_adapter(base_url, api_key)
    
    try:
        await adapter.initialize()
        
        # 健康检查
        health = await adapter.health_check()
        
        # 测试扫描（不实际摄入）
        if os.path.exists(pack_path):
            scan_result = await adapter.scan_and_ingest_pack(
                pack_path, pack_id, incremental=True
            )
            
            return {
                "success": True,
                "health": health,
                "scan_result": asdict(scan_result),
                "message": "适配器测试成功"
            }
        else:
            return {
                "success": True,
                "health": health,
                "message": "适配器连接成功，跳过扫描（路径不存在）"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "适配器测试失败"
        }
    finally:
        await adapter.close()


# ==================== 异步上下文管理器支持 ====================

class MinecraftCoreAdapterContext:
    """Minecraft核心适配器上下文管理器"""
    
    def __init__(self, adapter: MinecraftCoreAdapter):
        self.adapter = adapter
    
    async def __aenter__(self):
        await self.adapter.initialize()
        return self.adapter
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.adapter.close()


def minecraft_adapter_context(
    base_url: str,
    api_key: str,
    app_name: str = "mc-l10n",
    **kwargs
) -> MinecraftCoreAdapterContext:
    """创建Minecraft适配器上下文管理器"""
    adapter = create_minecraft_core_adapter(base_url, api_key, app_name, **kwargs)
    return MinecraftCoreAdapterContext(adapter)