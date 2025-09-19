"""
游戏专属数据提取器基础架构
支持多游戏的翻译数据提取，集成现有的扫描系统和数据传输架构
"""

import asyncio
import hashlib
import json
import structlog
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Union

logger = structlog.get_logger(__name__)


class GameType(Enum):
    """支持的游戏类型"""
    MINECRAFT = "minecraft"
    RIMWORLD = "rimworld"
    FACTORIO = "factorio"


class FileFormat(Enum):
    """支持的文件格式"""
    JSON = "json"
    LANG = "lang"  # Minecraft 1.12-
    PROPERTIES = "properties"
    XML = "xml"  # RimWorld DefInjection
    CFG = "cfg"  # Factorio locale


@dataclass
class TranslationEntry:
    """翻译条目数据结构"""
    key: str
    source_text: str
    target_text: str = ""
    namespace: str = ""
    context: str = ""
    format: FileFormat = FileFormat.JSON
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LanguageFile:
    """语言文件数据结构"""
    uid: str
    path: str
    relative_path: str
    locale: str
    format: FileFormat
    size: int
    carrier_type: str  # mod, resource_pack, data_pack
    carrier_uid: str
    entries: List[TranslationEntry]
    keyset_hash: str = ""
    content_hash: str = ""
    
    def __post_init__(self):
        if not self.uid:
            self.uid = str(uuid.uuid4())
        if not self.keyset_hash:
            self.keyset_hash = self._calculate_keyset_hash()
        if not self.content_hash:
            self.content_hash = self._calculate_content_hash()
    
    def _calculate_keyset_hash(self) -> str:
        """计算键集指纹"""
        keys = sorted([entry.key for entry in self.entries])
        key_string = '|'.join(keys)
        return hashlib.blake3(key_string.encode('utf-8')).hexdigest()[:16]
    
    def _calculate_content_hash(self) -> str:
        """计算内容哈希（包含翻译文本）"""
        content_items = []
        for entry in sorted(self.entries, key=lambda x: x.key):
            content_items.append(f"{entry.key}={entry.source_text}")
        content_string = '\n'.join(content_items)
        return hashlib.blake3(content_string.encode('utf-8')).hexdigest()[:16]


@dataclass
class ExtractionResult:
    """提取结果"""
    success: bool
    language_files: List[LanguageFile]
    statistics: Dict[str, Any]
    errors: List[str]
    duration_ms: int
    
    def __post_init__(self):
        if not self.statistics:
            self.statistics = {
                "files_processed": len(self.language_files),
                "total_entries": sum(len(lf.entries) for lf in self.language_files),
                "locales_found": len(set(lf.locale for lf in self.language_files)),
                "carriers_found": len(set(lf.carrier_uid for lf in self.language_files))
            }


class BaseGameDataExtractor(ABC):
    """游戏数据提取器基础类"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.game_type = self._get_game_type()
        self.supported_formats = self._get_supported_formats()
        self._cache: Dict[str, Any] = {}
        
    @abstractmethod
    def _get_game_type(self) -> GameType:
        """返回支持的游戏类型"""
        pass
    
    @abstractmethod
    def _get_supported_formats(self) -> List[FileFormat]:
        """返回支持的文件格式"""
        pass
    
    @abstractmethod
    async def extract_from_discovered_items(
        self, 
        discovered_items: List[Dict[str, Any]]
    ) -> ExtractionResult:
        """从扫描发现的项目中提取翻译数据"""
        pass
    
    @abstractmethod
    async def extract_from_file(
        self, 
        file_path: Path, 
        carrier_info: Dict[str, Any]
    ) -> List[LanguageFile]:
        """从单个文件提取翻译数据"""
        pass
    
    async def extract_incremental(
        self, 
        discovered_items: List[Dict[str, Any]], 
        last_keyset_hashes: Dict[str, str]
    ) -> ExtractionResult:
        """增量提取：只处理键集发生变化的文件"""
        start_time = time.time()
        
        language_files = []
        errors = []
        
        for item in discovered_items:
            try:
                # 预先提取键集哈希进行比较
                candidate_files = await self._extract_keyset_preview(item)
                
                for candidate in candidate_files:
                    cache_key = f"{candidate['carrier_uid']}:{candidate['relative_path']}"
                    
                    # 检查键集是否变化
                    if cache_key in last_keyset_hashes:
                        if last_keyset_hashes[cache_key] == candidate['keyset_hash']:
                            logger.debug(f"键集未变化，跳过: {candidate['relative_path']}")
                            continue
                    
                    # 键集有变化，执行完整提取
                    extracted_files = await self.extract_from_file(
                        Path(candidate['path']), 
                        candidate['carrier_info']
                    )
                    language_files.extend(extracted_files)
                    
            except Exception as e:
                error_msg = f"增量提取失败 {item.get('path', 'unknown')}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return ExtractionResult(
            success=len(errors) == 0,
            language_files=language_files,
            statistics={},
            errors=errors,
            duration_ms=duration_ms
        )
    
    async def _extract_keyset_preview(
        self, 
        item: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """快速预览提取键集信息，用于增量比较"""
        # 子类可以重写此方法提供更高效的键集提取
        return []
    
    def _is_supported_file(self, file_path: Path) -> bool:
        """检查文件是否为支持的格式"""
        suffix = file_path.suffix.lower()
        format_mapping = {
            '.json': FileFormat.JSON,
            '.lang': FileFormat.LANG,
            '.properties': FileFormat.PROPERTIES,
            '.xml': FileFormat.XML,
            '.cfg': FileFormat.CFG
        }
        
        file_format = format_mapping.get(suffix)
        return file_format in self.supported_formats
    
    def _detect_locale_from_path(self, file_path: Path) -> str:
        """从文件路径检测语言代码"""
        # 通用的语言代码检测逻辑
        stem = file_path.stem
        
        # 常见的语言代码模式
        common_locales = {
            'en_us', 'zh_cn', 'zh_tw', 'ja_jp', 'ko_kr',
            'fr_fr', 'de_de', 'es_es', 'pt_br', 'ru_ru',
            'it_it', 'nl_nl', 'sv_se', 'pl_pl', 'cs_cz'
        }
        
        if stem.lower() in common_locales:
            return stem.lower()
        
        # 如果文件名就是语言代码
        if len(stem) == 5 and '_' in stem:
            return stem.lower()
        
        # 默认返回文件名
        return stem.lower()
    
    def _get_cache_key(self, *args) -> str:
        """生成缓存键"""
        key_string = '|'.join(str(arg) for arg in args)
        return hashlib.blake3(key_string.encode('utf-8')).hexdigest()[:16]
    
    async def _save_to_database(
        self, 
        language_files: List[LanguageFile]
    ) -> Dict[str, Any]:
        """保存语言文件和翻译条目到数据库"""
        try:
            from infrastructure.repositories.repository_factory import get_repository_factory
            from infrastructure.repositories.core_language_file_repository import CoreLanguageFile
            from infrastructure.repositories.core_translation_entry_repository import CoreTranslationEntry
            
            factory = get_repository_factory()
            lang_file_repo = factory.get_core_language_file_repo()
            translation_repo = factory.get_core_translation_entry_repo()
            
            saved_files = 0
            saved_entries = 0
            
            for lang_file in language_files:
                # 保存语言文件记录
                core_lang_file = CoreLanguageFile(
                    uid=lang_file.uid,
                    carrier_type=lang_file.carrier_type,
                    carrier_uid=lang_file.carrier_uid,
                    locale=lang_file.locale,
                    rel_path=lang_file.relative_path,
                    format=lang_file.format.value,
                    size=lang_file.size
                )
                
                file_uid = lang_file_repo.create(core_lang_file)
                saved_files += 1
                
                # 批量保存翻译条目
                translation_entries = []
                for entry in lang_file.entries:
                    core_entry = CoreTranslationEntry(
                        uid=str(uuid.uuid4()),
                        language_file_uid=file_uid,
                        key=entry.key,
                        src_text=entry.source_text,
                        dst_text=entry.target_text,
                        status='new'
                    )
                    translation_entries.append(core_entry)
                
                # 批量插入翻译条目
                for entry in translation_entries:
                    translation_repo.create(entry)
                    saved_entries += 1
            
            logger.info(f"数据库保存完成: {saved_files} 个语言文件, {saved_entries} 个翻译条目")
            
            return {
                "success": True,
                "saved_files": saved_files,
                "saved_entries": saved_entries
            }
            
        except Exception as e:
            logger.error(f"数据库保存失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _emit_lang_upsert_event(
        self, 
        language_file: LanguageFile,
        session_id: str = None
    ):
        """发送LANG_UPSERT事件"""
        try:
            from infrastructure.services.event_applier import ScanEvent, EventType
            
            if not session_id:
                session_id = f"extract_{uuid.uuid4().hex[:8]}"
            
            event = ScanEvent(
                event_id=f"lang_{uuid.uuid4().hex[:8]}",
                session_id=session_id,
                event_type=EventType.LANG_UPSERT,
                entity_ref=language_file.carrier_uid,
                stage="extraction",
                artifact_hash=language_file.content_hash,
                payload={
                    "language_file_uid": language_file.uid,
                    "locale": language_file.locale,
                    "carrier_type": language_file.carrier_type,
                    "entry_count": len(language_file.entries),
                    "keyset_hash": language_file.keyset_hash,
                    "format": language_file.format.value
                },
                timestamp=datetime.now().isoformat()
            )
            
            # 这里可以集成到事件系统
            logger.info(f"LANG_UPSERT事件: {language_file.relative_path} ({len(language_file.entries)} 条目)")
            
        except Exception as e:
            logger.warning(f"发送LANG_UPSERT事件失败: {e}")


class ExtractorRegistry:
    """数据提取器注册表"""
    
    _extractors: Dict[GameType, BaseGameDataExtractor] = {}
    
    @classmethod
    def register(cls, game_type: GameType, extractor: BaseGameDataExtractor):
        """注册提取器"""
        cls._extractors[game_type] = extractor
        logger.info(f"已注册 {game_type.value} 数据提取器")
    
    @classmethod
    def get_extractor(cls, game_type: GameType) -> Optional[BaseGameDataExtractor]:
        """获取指定游戏的提取器"""
        return cls._extractors.get(game_type)
    
    @classmethod
    def get_all_extractors(cls) -> Dict[GameType, BaseGameDataExtractor]:
        """获取所有注册的提取器"""
        return cls._extractors.copy()
    
    @classmethod
    def detect_game_type(cls, discovered_items: List[Dict[str, Any]]) -> Optional[GameType]:
        """从扫描结果中检测游戏类型"""
        # 检测Minecraft特征
        for item in discovered_items:
            if item.get("type") == "mod":
                loader_type = item.get("loader_type", "").lower()
                if loader_type in ["forge", "fabric", "quilt", "neoforge"]:
                    return GameType.MINECRAFT
            
            # 检测文件路径特征
            path = item.get("path", "")
            if "assets/" in path and "/lang/" in path:
                return GameType.MINECRAFT
            if "DefInjected/" in path or "Defs/" in path:
                return GameType.RIMWORLD
            if "/locale/" in path and path.endswith(".cfg"):
                return GameType.FACTORIO
        
        return None