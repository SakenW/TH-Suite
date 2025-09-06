"""
验证领域服务
提供翻译验证相关的业务逻辑
"""

import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import logging

from ..models.mod import Mod, TranslationEntry

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)


class ValidationService:
    """验证领域服务"""
    
    # Minecraft格式化代码模式
    FORMAT_CODE_PATTERN = re.compile(r'§[0-9a-fklmnor]')
    
    # 占位符模式
    PLACEHOLDER_PATTERN = re.compile(r'%[sdif]|\{[0-9]+\}')
    
    @classmethod
    def validate_translation_entry(
        cls,
        entry: TranslationEntry,
        original: Optional[str] = None
    ) -> ValidationResult:
        """验证单个翻译条目
        
        Args:
            entry: 翻译条目
            original: 原文（如果提供，将进行更严格的验证）
            
        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # 基础验证
        if not entry.translated:
            result.add_error(f"Translation for key '{entry.key}' is empty")
            return result
        
        # 如果有原文，进行对比验证
        if original:
            # 检查格式化代码
            original_format_codes = set(cls.FORMAT_CODE_PATTERN.findall(original))
            translated_format_codes = set(cls.FORMAT_CODE_PATTERN.findall(entry.translated))
            
            if original_format_codes != translated_format_codes:
                result.add_warning(
                    f"Format codes mismatch in '{entry.key}': "
                    f"original has {original_format_codes}, "
                    f"translated has {translated_format_codes}"
                )
            
            # 检查占位符
            original_placeholders = cls.PLACEHOLDER_PATTERN.findall(original)
            translated_placeholders = cls.PLACEHOLDER_PATTERN.findall(entry.translated)
            
            if len(original_placeholders) != len(translated_placeholders):
                result.add_error(
                    f"Placeholder count mismatch in '{entry.key}': "
                    f"original has {len(original_placeholders)}, "
                    f"translated has {len(translated_placeholders)}"
                )
            
            # 检查换行符
            if original.count('\n') != entry.translated.count('\n'):
                result.add_warning(
                    f"Line break count mismatch in '{entry.key}'"
                )
        
        # 检查特殊字符
        if cls._contains_suspicious_characters(entry.translated):
            result.add_warning(
                f"Translation for '{entry.key}' contains suspicious characters"
            )
        
        return result
    
    @classmethod
    def validate_mod_translations(
        cls,
        mod: Mod,
        language: str,
        source_language: str = "en_us"
    ) -> ValidationResult:
        """验证模组的所有翻译
        
        Args:
            mod: 模组
            language: 目标语言
            source_language: 源语言
            
        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        source_translations = {t.key: t for t in mod.get_translations(source_language)}
        target_translations = mod.get_translations(language)
        
        for translation in target_translations:
            source = source_translations.get(translation.key)
            entry_result = cls.validate_translation_entry(
                translation,
                source.original if source else None
            )
            
            result.errors.extend(entry_result.errors)
            result.warnings.extend(entry_result.warnings)
            
            if entry_result.errors:
                result.is_valid = False
        
        return result
    
    @classmethod
    def check_consistency(
        cls,
        translations: List[TranslationEntry]
    ) -> Dict[str, List[str]]:
        """检查翻译一致性
        
        查找相同原文但翻译不同的情况
        
        Args:
            translations: 翻译条目列表
            
        Returns:
            不一致的翻译映射 {原文: [翻译1, 翻译2, ...]}
        """
        original_to_translations: Dict[str, Set[str]] = {}
        
        for entry in translations:
            if entry.original:
                if entry.original not in original_to_translations:
                    original_to_translations[entry.original] = set()
                original_to_translations[entry.original].add(entry.translated)
        
        # 找出有多个不同翻译的原文
        inconsistencies = {}
        for original, translations_set in original_to_translations.items():
            if len(translations_set) > 1:
                inconsistencies[original] = list(translations_set)
        
        return inconsistencies
    
    @classmethod
    def check_terminology(
        cls,
        translation: str,
        terminology: Dict[str, str]
    ) -> List[str]:
        """检查术语使用
        
        Args:
            translation: 翻译文本
            terminology: 术语表 {原文: 标准翻译}
            
        Returns:
            违反术语规范的列表
        """
        violations = []
        
        for term, standard_translation in terminology.items():
            # 简单的包含检查，实际应该更智能
            if term.lower() in translation.lower():
                if standard_translation not in translation:
                    violations.append(
                        f"Term '{term}' should be translated as '{standard_translation}'"
                    )
        
        return violations
    
    @staticmethod
    def _contains_suspicious_characters(text: str) -> bool:
        """检查是否包含可疑字符
        
        Args:
            text: 要检查的文本
            
        Returns:
            是否包含可疑字符
        """
        # 检查控制字符（除了换行和制表符）
        for char in text:
            if ord(char) < 32 and char not in '\n\t\r':
                return True
        
        # 检查零宽字符
        zero_width_chars = ['\u200b', '\u200c', '\u200d', '\ufeff']
        for char in zero_width_chars:
            if char in text:
                return True
        
        return False
    
    @classmethod
    def validate_project_quality(
        cls,
        mod: Mod,
        language: str,
        quality_threshold: float = 0.8
    ) -> bool:
        """验证项目质量是否达标
        
        Args:
            mod: 模组
            language: 语言
            quality_threshold: 质量阈值 (0-1)
            
        Returns:
            是否达标
        """
        translations = mod.get_translations(language)
        
        if not translations:
            return False
        
        approved_count = sum(1 for t in translations if t.status == "approved")
        total_count = len(translations)
        
        quality = approved_count / total_count if total_count > 0 else 0
        
        return quality >= quality_threshold