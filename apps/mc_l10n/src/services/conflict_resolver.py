"""
冲突解决器
基于升级方案的Minecraft翻译冲突检测和解决系统
"""

import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

from ..adapters.projection import MinecraftLanguageFile

logger = structlog.get_logger(__name__)


class ConflictType(Enum):
    """冲突类型"""
    CONTENT_MISMATCH = "content_mismatch"      # 内容不匹配
    VERSION_CONFLICT = "version_conflict"       # 版本冲突
    ENCODING_MISMATCH = "encoding_mismatch"     # 编码不匹配
    FORMAT_DIFFERENCE = "format_difference"     # 格式差异
    MISSING_KEYS = "missing_keys"              # 缺失键值
    EXTRA_KEYS = "extra_keys"                  # 多余键值
    PLACEHOLDER_MISMATCH = "placeholder_mismatch"  # 占位符不匹配


class ConflictResolution(Enum):
    """冲突解决策略"""
    KEEP_LOCAL = "keep_local"          # 保留本地版本
    KEEP_REMOTE = "keep_remote"        # 保留远程版本
    MERGE_AUTO = "merge_auto"          # 自动合并
    MERGE_MANUAL = "merge_manual"      # 手动合并
    SKIP = "skip"                      # 跳过处理


@dataclass
class ConflictDetail:
    """冲突详情"""
    key: str
    local_value: Optional[str]
    remote_value: Optional[str]
    conflict_type: ConflictType
    severity: str  # "low", "medium", "high", "critical"
    description: str
    suggestions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileConflict:
    """文件冲突"""
    mod_id: str
    language: str
    file_path: str
    conflict_details: List[ConflictDetail]
    local_hash: str
    remote_hash: str
    resolution_strategy: Optional[ConflictResolution] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mod_id": self.mod_id,
            "language": self.language,
            "file_path": self.file_path,
            "conflict_details": [detail.to_dict() for detail in self.conflict_details],
            "local_hash": self.local_hash,
            "remote_hash": self.remote_hash,
            "resolution_strategy": self.resolution_strategy.value if self.resolution_strategy else None
        }
    
    @property
    def severity_level(self) -> str:
        """获取冲突严重性级别"""
        if not self.conflict_details:
            return "none"
        
        severities = [detail.severity for detail in self.conflict_details]
        if "critical" in severities:
            return "critical"
        elif "high" in severities:
            return "high"
        elif "medium" in severities:
            return "medium"
        else:
            return "low"


class MinecraftConflictResolver:
    """Minecraft冲突解决器"""
    
    def __init__(self):
        self.placeholder_patterns = [
            r'%[sd%]',        # %s, %d, %%
            r'\{[0-9]+\}',    # {0}, {1}, etc.
            r'\$\{[^}]+\}',   # ${variable}
            r'§[0-9a-fklmnor]',  # Minecraft颜色码
        ]
        
        self.critical_keys = [
            "death.fell.accident.water",
            "commands.give.success",
            "gui.done",
            "menu.quit",
            "options.title"
        ]
        
        logger.info("Minecraft冲突解决器已初始化")
    
    async def detect_local_conflicts(
        self,
        pack_id: str,
        new_files: List[MinecraftLanguageFile],
        existing_files: Optional[List[MinecraftLanguageFile]] = None
    ) -> List[FileConflict]:
        """检测本地冲突"""
        conflicts = []
        
        if not existing_files:
            # 如果没有现有文件，没有冲突
            return conflicts
        
        # 创建现有文件的索引
        existing_index = {}
        for existing_file in existing_files:
            key = (existing_file.mod_id, existing_file.language)
            existing_index[key] = existing_file
        
        # 检查每个新文件
        for new_file in new_files:
            key = (new_file.mod_id, new_file.language)
            if key in existing_index:
                existing_file = existing_index[key]
                
                file_conflict = await self._compare_language_files(
                    existing_file, new_file
                )
                
                if file_conflict.conflict_details:
                    conflicts.append(file_conflict)
        
        logger.info("冲突检测完成",
                   pack_id=pack_id,
                   files_checked=len(new_files),
                   conflicts_found=len(conflicts))
        
        return conflicts
    
    async def resolve_conflicts(
        self,
        new_files: List[MinecraftLanguageFile],
        conflicts: List[FileConflict]
    ) -> List[MinecraftLanguageFile]:
        """解决冲突"""
        resolved_files = []
        
        # 创建冲突索引
        conflict_index = {}
        for conflict in conflicts:
            key = (conflict.mod_id, conflict.language)
            conflict_index[key] = conflict
        
        # 处理每个文件
        for new_file in new_files:
            key = (new_file.mod_id, new_file.language)
            
            if key in conflict_index:
                conflict = conflict_index[key]
                resolved_file = await self._resolve_file_conflict(new_file, conflict)
                resolved_files.append(resolved_file)
            else:
                # 没有冲突，直接使用新文件
                resolved_files.append(new_file)
        
        logger.info("冲突解决完成",
                   files_processed=len(new_files),
                   conflicts_resolved=len([c for c in conflicts if c.resolution_strategy]))
        
        return resolved_files
    
    async def _compare_language_files(
        self,
        existing_file: MinecraftLanguageFile,
        new_file: MinecraftLanguageFile
    ) -> FileConflict:
        """比较两个语言文件"""
        conflict_details = []
        
        # 计算文件哈希
        local_hash = self._calculate_translation_hash(existing_file.translations)
        remote_hash = self._calculate_translation_hash(new_file.translations)
        
        # 如果哈希相同，没有冲突
        if local_hash == remote_hash:
            return FileConflict(
                mod_id=new_file.mod_id,
                language=new_file.language,
                file_path=new_file.file_path,
                conflict_details=[],
                local_hash=local_hash,
                remote_hash=remote_hash
            )
        
        # 详细比较键值对
        existing_keys = set(existing_file.translations.keys())
        new_keys = set(new_file.translations.keys())
        
        # 检查缺失的键
        missing_keys = existing_keys - new_keys
        for key in missing_keys:
            conflict_details.append(ConflictDetail(
                key=key,
                local_value=existing_file.translations[key],
                remote_value=None,
                conflict_type=ConflictType.MISSING_KEYS,
                severity="high" if key in self.critical_keys else "medium",
                description=f"新版本中缺少键 '{key}'",
                suggestions=[
                    "保留本地版本的键值",
                    "从本地版本恢复此键"
                ]
            ))
        
        # 检查多余的键
        extra_keys = new_keys - existing_keys
        for key in extra_keys:
            conflict_details.append(ConflictDetail(
                key=key,
                local_value=None,
                remote_value=new_file.translations[key],
                conflict_type=ConflictType.EXTRA_KEYS,
                severity="low",
                description=f"新版本中添加了新键 '{key}'",
                suggestions=[
                    "接受新键值",
                    "保持现有文件不变"
                ]
            ))
        
        # 检查值不同的键
        common_keys = existing_keys & new_keys
        for key in common_keys:
            existing_value = existing_file.translations[key]
            new_value = new_file.translations[key]
            
            if existing_value != new_value:
                # 进一步分析冲突类型
                conflict_type, severity, description, suggestions = self._analyze_value_conflict(
                    key, existing_value, new_value
                )
                
                conflict_details.append(ConflictDetail(
                    key=key,
                    local_value=existing_value,
                    remote_value=new_value,
                    conflict_type=conflict_type,
                    severity=severity,
                    description=description,
                    suggestions=suggestions
                ))
        
        return FileConflict(
            mod_id=new_file.mod_id,
            language=new_file.language,
            file_path=new_file.file_path,
            conflict_details=conflict_details,
            local_hash=local_hash,
            remote_hash=remote_hash
        )
    
    def _analyze_value_conflict(
        self,
        key: str,
        local_value: str,
        remote_value: str
    ) -> Tuple[ConflictType, str, str, List[str]]:
        """分析值冲突"""
        import re
        
        # 检查占位符匹配
        local_placeholders = []
        remote_placeholders = []
        
        for pattern in self.placeholder_patterns:
            local_placeholders.extend(re.findall(pattern, local_value))
            remote_placeholders.extend(re.findall(pattern, remote_value))
        
        if set(local_placeholders) != set(remote_placeholders):
            return (
                ConflictType.PLACEHOLDER_MISMATCH,
                "critical" if key in self.critical_keys else "high",
                f"占位符不匹配: 本地 {local_placeholders} vs 远程 {remote_placeholders}",
                [
                    "检查占位符是否正确",
                    "保留包含正确占位符的版本",
                    "手动修正占位符"
                ]
            )
        
        # 检查长度差异
        length_diff = abs(len(local_value) - len(remote_value))
        if length_diff > len(local_value) * 0.5:  # 50%以上差异
            return (
                ConflictType.CONTENT_MISMATCH,
                "medium",
                f"内容长度差异较大: {len(local_value)} vs {len(remote_value)}",
                [
                    "检查翻译是否完整",
                    "选择更完整的版本",
                    "手动合并两个版本"
                ]
            )
        
        # 默认内容不匹配
        severity = "critical" if key in self.critical_keys else "low"
        return (
            ConflictType.CONTENT_MISMATCH,
            severity,
            "翻译内容不同",
            [
                "比较两个版本的翻译质量",
                "保留更准确的翻译",
                "考虑合并两个版本的优点"
            ]
        )
    
    async def _resolve_file_conflict(
        self,
        new_file: MinecraftLanguageFile,
        conflict: FileConflict
    ) -> MinecraftLanguageFile:
        """解决单个文件冲突"""
        if not conflict.conflict_details:
            return new_file
        
        # 确定解决策略
        if not conflict.resolution_strategy:
            conflict.resolution_strategy = self._determine_auto_resolution_strategy(conflict)
        
        # 应用解决策略
        resolved_translations = {}
        
        if conflict.resolution_strategy == ConflictResolution.KEEP_REMOTE:
            resolved_translations = new_file.translations.copy()
        
        elif conflict.resolution_strategy == ConflictResolution.KEEP_LOCAL:
            # 需要获取本地版本，这里简化处理
            resolved_translations = new_file.translations.copy()
        
        elif conflict.resolution_strategy == ConflictResolution.MERGE_AUTO:
            resolved_translations = await self._auto_merge_translations(new_file, conflict)
        
        elif conflict.resolution_strategy == ConflictResolution.SKIP:
            resolved_translations = new_file.translations.copy()
        
        else:
            # 默认使用远程版本
            resolved_translations = new_file.translations.copy()
        
        # 创建解决后的文件
        resolved_file = MinecraftLanguageFile(
            mod_id=new_file.mod_id,
            language=new_file.language,
            file_path=new_file.file_path
        )
        resolved_file.translations = resolved_translations
        resolved_file.mod_version = new_file.mod_version
        
        return resolved_file
    
    def _determine_auto_resolution_strategy(self, conflict: FileConflict) -> ConflictResolution:
        """确定自动解决策略"""
        # 如果有关键冲突，需要手动处理
        critical_conflicts = [
            detail for detail in conflict.conflict_details
            if detail.severity == "critical"
        ]
        
        if critical_conflicts:
            return ConflictResolution.MERGE_MANUAL
        
        # 如果主要是新增键，自动合并
        extra_key_conflicts = [
            detail for detail in conflict.conflict_details
            if detail.conflict_type == ConflictType.EXTRA_KEYS
        ]
        
        if len(extra_key_conflicts) > len(conflict.conflict_details) * 0.8:
            return ConflictResolution.MERGE_AUTO
        
        # 默认策略
        return ConflictResolution.KEEP_REMOTE
    
    async def _auto_merge_translations(
        self,
        new_file: MinecraftLanguageFile,
        conflict: FileConflict
    ) -> Dict[str, str]:
        """自动合并翻译"""
        merged_translations = new_file.translations.copy()
        
        for detail in conflict.conflict_details:
            if detail.conflict_type == ConflictType.MISSING_KEYS and detail.local_value:
                # 保留本地缺失的键
                merged_translations[detail.key] = detail.local_value
            
            elif detail.conflict_type == ConflictType.EXTRA_KEYS and detail.remote_value:
                # 接受新增的键
                merged_translations[detail.key] = detail.remote_value
            
            elif detail.conflict_type == ConflictType.CONTENT_MISMATCH:
                # 内容冲突默认使用远程版本，除非是占位符问题
                if detail.severity != "critical":
                    merged_translations[detail.key] = detail.remote_value or ""
        
        return merged_translations
    
    def _calculate_translation_hash(self, translations: Dict[str, str]) -> str:
        """计算翻译内容哈希"""
        # 创建确定性的字符串表示
        sorted_items = sorted(translations.items())
        content = json.dumps(sorted_items, ensure_ascii=False, separators=(',', ':'))
        
        # 计算哈希
        return hashlib.blake2b(content.encode('utf-8'), digest_size=16).hexdigest()
    
    def get_conflict_summary(self, conflicts: List[FileConflict]) -> Dict[str, Any]:
        """获取冲突摘要"""
        if not conflicts:
            return {
                "total_conflicts": 0,
                "severity_distribution": {},
                "conflict_type_distribution": {},
                "affected_files": 0
            }
        
        severity_count = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        type_count = {}
        
        for conflict in conflicts:
            # 统计严重性
            severity = conflict.severity_level
            if severity in severity_count:
                severity_count[severity] += 1
            
            # 统计冲突类型
            for detail in conflict.conflict_details:
                conflict_type = detail.conflict_type.value
                type_count[conflict_type] = type_count.get(conflict_type, 0) + 1
        
        return {
            "total_conflicts": len(conflicts),
            "severity_distribution": severity_count,
            "conflict_type_distribution": type_count,
            "affected_files": len(conflicts),
            "total_conflict_details": sum(len(c.conflict_details) for c in conflicts)
        }


# ==================== 工厂函数和便捷接口 ====================

def create_conflict_resolver() -> MinecraftConflictResolver:
    """创建冲突解决器"""
    return MinecraftConflictResolver()


async def detect_and_resolve_conflicts(
    pack_id: str,
    new_files: List[MinecraftLanguageFile],
    existing_files: Optional[List[MinecraftLanguageFile]] = None
) -> Tuple[List[MinecraftLanguageFile], List[FileConflict]]:
    """检测并解决冲突（便捷函数）"""
    resolver = create_conflict_resolver()
    
    # 检测冲突
    conflicts = await resolver.detect_local_conflicts(pack_id, new_files, existing_files)
    
    # 解决冲突
    resolved_files = await resolver.resolve_conflicts(new_files, conflicts)
    
    return resolved_files, conflicts