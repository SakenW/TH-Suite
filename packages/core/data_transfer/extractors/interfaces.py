"""
翻译数据提取器接口定义

定义了翻译数据提取的标准接口和协议
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Protocol

from ..models import (
    GameType,
    TranslationDelta,
    TranslationEntry,
    TranslationProject,
)


class ITranslationExtractor(Protocol):
    """翻译数据提取器接口"""
    
    @property
    def game_type(self) -> GameType:
        """获取支持的游戏类型"""
        ...
    
    async def extract_project(self, project_path: str) -> TranslationProject:
        """提取项目信息"""
        ...
    
    async def extract_entries(
        self, 
        project: TranslationProject,
        incremental: bool = True,
        target_languages: Optional[List[str]] = None
    ) -> List[TranslationEntry]:
        """提取翻译条目"""
        ...
    
    async def detect_changes(
        self, 
        project: TranslationProject,
        last_scan: Optional[datetime] = None
    ) -> TranslationDelta:
        """检测翻译变更"""
        ...
    
    async def validate_project(self, project_path: str) -> bool:
        """验证项目路径是否有效"""
        ...


class IGameSpecificParser(Protocol):
    """游戏特定解析器接口"""
    
    async def parse_language_file(self, file_path: Path) -> dict[str, str]:
        """解析语言文件"""
        ...
    
    async def extract_mod_info(self, mod_path: Path) -> dict:
        """提取MOD信息"""
        ...
    
    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        ...
    
    def detect_language_code(self, file_path: Path) -> str:
        """检测语言代码"""
        ...


class IFileScanner(Protocol):
    """文件扫描器接口"""
    
    async def scan_directory(
        self, 
        root_path: Path,
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None
    ) -> List[Path]:
        """扫描目录获取相关文件"""
        ...
    
    async def find_language_files(self, mod_path: Path) -> List[Path]:
        """查找语言文件"""
        ...
    
    async def find_mod_metadata(self, mod_path: Path) -> Optional[Path]:
        """查找MOD元数据文件"""
        ...


class BaseTranslationExtractor(ABC):
    """翻译数据提取器基类"""
    
    def __init__(self, game_type: GameType):
        self._game_type = game_type
        self.checksum_cache: dict[str, str] = {}
    
    @property
    def game_type(self) -> GameType:
        """获取支持的游戏类型"""
        return self._game_type
    
    @abstractmethod
    async def extract_project(self, project_path: str) -> TranslationProject:
        """提取项目信息"""
        pass
    
    @abstractmethod
    async def extract_entries(
        self, 
        project: TranslationProject,
        incremental: bool = True,
        target_languages: Optional[List[str]] = None
    ) -> List[TranslationEntry]:
        """提取翻译条目"""
        pass
    
    async def detect_changes(
        self, 
        project: TranslationProject,
        last_scan: Optional[datetime] = None
    ) -> TranslationDelta:
        """检测翻译变更"""
        from ..models import TranslationDelta, generate_delta_id
        
        # 获取当前条目
        current_entries = await self.extract_entries(project, incremental=False)
        
        # 如果没有上次扫描时间，认为全部是新增
        if last_scan is None:
            return TranslationDelta(
                delta_id=generate_delta_id(project.project_id, 0, 1),
                project_id=project.project_id,
                base_version=0,
                target_version=1,
                added=current_entries,
                author="system",
                commit_message="Initial scan"
            )
        
        # TODO: 实现增量变更检测逻辑
        # 这里需要与存储层集成，比较当前条目与上次扫描的差异
        
        return TranslationDelta(
            delta_id=generate_delta_id(project.project_id, project.current_version, project.current_version + 1),
            project_id=project.project_id,
            base_version=project.current_version,
            target_version=project.current_version + 1,
            author="system",
            commit_message="Incremental scan"
        )
    
    async def validate_project(self, project_path: str) -> bool:
        """验证项目路径是否有效"""
        path = Path(project_path)
        return path.exists() and path.is_dir()
    
    def _calculate_checksum(self, content: str) -> str:
        """计算内容校验和"""
        import blake3
        return blake3.blake3(content.encode()).hexdigest()[:16]
    
    def _normalize_key(self, key: str, namespace: str = None) -> str:
        """标准化翻译键"""
        if namespace and not key.startswith(namespace):
            return f"{namespace}.{key}"
        return key
    
    def _detect_encoding(self, file_path: Path) -> str:
        """检测文件编码"""
        import chardet
        
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                return result.get('encoding', 'utf-8') or 'utf-8'
        except Exception:
            return 'utf-8'
    
    def _categorize_key(self, key: str) -> Optional[str]:
        """根据键名推断分类"""
        key_lower = key.lower()
        
        # 通用分类规则
        if any(word in key_lower for word in ['item', 'items']):
            return 'item'
        elif any(word in key_lower for word in ['block', 'blocks']):
            return 'block'
        elif any(word in key_lower for word in ['entity', 'entities', 'mob', 'mobs']):
            return 'entity'
        elif any(word in key_lower for word in ['gui', 'screen', 'menu']):
            return 'gui'
        elif any(word in key_lower for word in ['tooltip', 'tip']):
            return 'tooltip'
        elif any(word in key_lower for word in ['enchantment', 'enchant']):
            return 'enchantment'
        elif any(word in key_lower for word in ['effect', 'potion']):
            return 'effect'
        elif any(word in key_lower for word in ['advancement', 'achieve']):
            return 'advancement'
        elif any(word in key_lower for word in ['biome']):
            return 'biome'
        elif any(word in key_lower for word in ['sound']):
            return 'sound'
        elif any(word in key_lower for word in ['config', 'configuration']):
            return 'config'
        else:
            return None
    
    async def _read_file_safely(self, file_path: Path) -> str:
        """安全读取文件内容"""
        try:
            encoding = self._detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            # 记录错误但不抛出异常
            import structlog
            logger = structlog.get_logger(__name__)
            logger.warning(
                "Failed to read file",
                file_path=str(file_path),
                error=str(e)
            )
            return ""