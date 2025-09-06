"""
翻译领域服务
处理跨聚合的翻译逻辑
"""

from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
import logging

from ..models.mod import Mod, ModId, TranslationEntry
from ..models.translation_project import TranslationProject, ProjectStatus
from ..events import TranslationApprovedEvent, TranslationRejectedEvent
from ..value_objects import (
    LanguageCode, TranslationKey, TranslationText, 
    QualityScore, Percentage
)

logger = logging.getLogger(__name__)


class TranslationService:
    """翻译领域服务"""
    
    @staticmethod
    def apply_translations(
        mod: Mod,
        translations: Dict[str, Tuple[str, str]],  # {key: (original, translated)}
        language: LanguageCode,
        source_language: LanguageCode = LanguageCode.EN_US,
        translator: Optional[str] = None
    ) -> Tuple[int, int]:
        """应用翻译到模组
        
        Args:
            mod: 目标模组
            translations: 翻译映射 {key: (original_text, translated_text)}
            language: 目标语言
            source_language: 源语言
            translator: 翻译者ID
            
        Returns:
            (成功数量, 失败数量)
        """
        success_count = 0
        failed_count = 0
        
        for key, (original_text, translated_text) in translations.items():
            try:
                # 创建值对象
                translation_key = TranslationKey(key)
                original = TranslationText(original_text, source_language)
                translated = TranslationText(translated_text, language)
                
                entry = TranslationEntry(
                    key=translation_key,
                    original=original,
                    translated=translated,
                    translator=translator
                )
                
                mod.add_translation(language, entry)
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to apply translation for key {key}: {e}")
                failed_count += 1
        
        return success_count, failed_count
    
    @staticmethod
    def approve_translations(
        mod: Mod,
        language: LanguageCode,
        keys: List[str],
        reviewer: str,
        quality_scores: Optional[Dict[str, float]] = None
    ) -> int:
        """批准翻译
        
        Args:
            mod: 目标模组
            language: 语言
            keys: 要批准的键列表
            reviewer: 审核者ID
            quality_scores: 每个键的质量分数
            
        Returns:
            批准的数量
        """
        approved_count = 0
        translations = mod.get_translations(language)
        quality_scores = quality_scores or {}
        
        for translation in translations:
            key_str = str(translation.key)
            if key_str in keys and translation.status == "pending":
                # 获取质量分数
                score = quality_scores.get(key_str, 1.0)
                quality = QualityScore(score) if score else None
                
                translation.approve(reviewer, quality)
                approved_count += 1
                
                # 发布事件
                mod._add_event(TranslationApprovedEvent(
                    translation_id=f"{mod.mod_id}_{language.value}_{key_str}",
                    mod_id=str(mod.mod_id),
                    language=language.value,
                    key=key_str,
                    approved_by=reviewer,
                    timestamp=datetime.now()
                ))
        
        return approved_count
    
    @staticmethod
    def reject_translations(
        mod: Mod,
        language: LanguageCode,
        keys: List[str],
        reviewer: str,
        reason: Optional[str] = None
    ) -> int:
        """拒绝翻译
        
        Args:
            mod: 目标模组
            language: 语言
            keys: 要拒绝的键列表
            reviewer: 审核者ID
            reason: 拒绝原因
            
        Returns:
            拒绝的数量
        """
        rejected_count = 0
        translations = mod.get_translations(language)
        
        for translation in translations:
            key_str = str(translation.key)
            if key_str in keys and translation.status == "pending":
                translation.reject(reviewer, reason)
                rejected_count += 1
                
                # 发布事件
                mod._add_event(TranslationRejectedEvent(
                    translation_id=f"{mod.mod_id}_{language.value}_{key_str}",
                    mod_id=str(mod.mod_id),
                    language=language.value,
                    key=key_str,
                    rejected_by=reviewer,
                    timestamp=datetime.now(),
                    reason=reason
                ))
        
        return rejected_count
    
    @staticmethod
    def calculate_coverage(
        mod: Mod,
        language: LanguageCode,
        source_language: LanguageCode = LanguageCode.EN_US
    ) -> Percentage:
        """计算翻译覆盖率
        
        Args:
            mod: 目标模组
            language: 目标语言
            source_language: 源语言
            
        Returns:
            覆盖率百分比
        """
        source_translations = mod.get_translations(source_language)
        target_translations = mod.get_translations(language)
        
        if not source_translations:
            return Percentage(0.0)
        
        source_keys = {str(t.key) for t in source_translations}
        target_keys = {str(t.key) for t in target_translations if t.status == "approved"}
        
        covered = len(source_keys & target_keys)
        total = len(source_keys)
        
        return Percentage.from_ratio(covered, total)
    
    @staticmethod
    def find_missing_translations(
        mod: Mod,
        language: LanguageCode,
        source_language: LanguageCode = LanguageCode.EN_US
    ) -> List[TranslationKey]:
        """查找缺失的翻译键
        
        Args:
            mod: 目标模组
            language: 目标语言
            source_language: 源语言
            
        Returns:
            缺失的键列表
        """
        source_translations = mod.get_translations(source_language)
        target_translations = mod.get_translations(language)
        
        source_keys = {t.key for t in source_translations}
        target_keys = {t.key for t in target_translations}
        
        missing_keys = source_keys - target_keys
        return list(missing_keys)
    
    @staticmethod
    def transfer_translations_between_projects(
        source_project: TranslationProject,
        target_project: TranslationProject,
        mod_id: ModId,
        languages: Set[LanguageCode]
    ) -> bool:
        """在项目间转移翻译
        
        Args:
            source_project: 源项目
            target_project: 目标项目
            mod_id: 模组ID
            languages: 要转移的语言集合
            
        Returns:
            是否成功
        """
        # 验证模组在源项目中
        if mod_id not in source_project.mod_ids:
            raise ValueError(f"Mod {mod_id} not found in source project")
        
        # 验证目标项目状态
        if target_project.status == ProjectStatus.ARCHIVED:
            raise ValueError("Cannot transfer to archived project")
        
        # 添加模组到目标项目
        target_project.add_mod(mod_id)
        
        # 从源项目移除
        source_project.remove_mod(mod_id)
        
        # 转移相关任务
        for task in source_project.tasks[:]:
            if task.mod_id == mod_id and task.language in languages:
                # 取消源项目中的任务
                task.cancel()
                
                # 在目标项目中重新创建任务
                # 这由add_mod自动处理
        
        return True