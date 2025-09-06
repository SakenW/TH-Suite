"""
术语管理领域服务
管理专业术语和词汇的一致性
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import re

from ..value_objects import (
    LanguageCode, TranslationKey, TranslationText,
    QualityScore
)


@dataclass
class Term:
    """术语定义"""
    key: str                              # 术语标识
    original: str                         # 原文
    language: LanguageCode                # 原语言
    translations: Dict[LanguageCode, str] # 各语言翻译
    category: Optional[str] = None        # 分类（如：item, block, entity）
    context: Optional[str] = None         # 使用上下文
    notes: Optional[str] = None           # 备注
    is_verified: bool = False             # 是否已验证
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_translation(self, language: LanguageCode, translation: str):
        """添加翻译"""
        self.translations[language] = translation
        self.updated_at = datetime.now()
    
    def get_translation(self, language: LanguageCode) -> Optional[str]:
        """获取指定语言的翻译"""
        return self.translations.get(language)
    
    def verify(self):
        """标记为已验证"""
        self.is_verified = True
        self.updated_at = datetime.now()


@dataclass
class Glossary:
    """术语表"""
    name: str
    description: Optional[str] = None
    terms: Dict[str, Term] = field(default_factory=dict)
    categories: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_term(self, term: Term):
        """添加术语"""
        self.terms[term.key] = term
        if term.category:
            self.categories.add(term.category)
        self.updated_at = datetime.now()
    
    def remove_term(self, key: str):
        """移除术语"""
        if key in self.terms:
            del self.terms[key]
            self.updated_at = datetime.now()
    
    def get_term(self, key: str) -> Optional[Term]:
        """获取术语"""
        return self.terms.get(key)
    
    def get_terms_by_category(self, category: str) -> List[Term]:
        """按分类获取术语"""
        return [t for t in self.terms.values() if t.category == category]
    
    def search_terms(self, query: str) -> List[Term]:
        """搜索术语"""
        query_lower = query.lower()
        results = []
        
        for term in self.terms.values():
            # 搜索原文
            if query_lower in term.original.lower():
                results.append(term)
                continue
            
            # 搜索翻译
            for translation in term.translations.values():
                if query_lower in translation.lower():
                    results.append(term)
                    break
        
        return results


class TerminologyService:
    """术语管理服务"""
    
    @staticmethod
    def extract_terms_from_text(
        text: str,
        patterns: Optional[List[str]] = None
    ) -> List[str]:
        """从文本中提取术语
        
        Args:
            text: 源文本
            patterns: 自定义正则模式列表
            
        Returns:
            提取的术语列表
        """
        terms = []
        
        # 默认模式
        default_patterns = [
            r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b',  # CamelCase
            r'\b[A-Z]{2,}\b',                     # 全大写缩写
            r'%\{[^}]+\}',                        # 占位符
            r'\$\{[^}]+\}',                       # 变量
        ]
        
        patterns = patterns or default_patterns
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            terms.extend(matches)
        
        # 去重并返回
        return list(set(terms))
    
    @staticmethod
    def validate_terminology_consistency(
        translations: Dict[TranslationKey, TranslationText],
        glossary: Glossary,
        language: LanguageCode
    ) -> List[Tuple[TranslationKey, str, str]]:
        """验证术语一致性
        
        Args:
            translations: 翻译映射
            glossary: 术语表
            language: 目标语言
            
        Returns:
            不一致的术语列表 [(key, expected, actual)]
        """
        inconsistencies = []
        
        for key, translation in translations.items():
            text = translation.value
            
            # 检查每个术语
            for term_key, term in glossary.terms.items():
                if term.original in text:
                    expected = term.get_translation(language)
                    if expected:
                        # 检查翻译中是否使用了正确的术语
                        if expected not in text:
                            # 尝试找到实际使用的翻译
                            actual = TerminologyService._find_actual_translation(
                                text, 
                                term.original,
                                expected
                            )
                            inconsistencies.append((key, expected, actual))
        
        return inconsistencies
    
    @staticmethod
    def apply_terminology(
        text: str,
        glossary: Glossary,
        source_language: LanguageCode,
        target_language: LanguageCode
    ) -> str:
        """应用术语表到文本
        
        Args:
            text: 源文本
            glossary: 术语表
            source_language: 源语言
            target_language: 目标语言
            
        Returns:
            应用术语后的文本
        """
        result = text
        
        # 按术语长度降序排序，先替换长的术语
        sorted_terms = sorted(
            glossary.terms.values(),
            key=lambda t: len(t.original),
            reverse=True
        )
        
        for term in sorted_terms:
            if term.language == source_language:
                translation = term.get_translation(target_language)
                if translation:
                    # 使用单词边界进行替换
                    pattern = r'\b' + re.escape(term.original) + r'\b'
                    result = re.sub(pattern, translation, result)
        
        return result
    
    @staticmethod
    def suggest_terms(
        text: str,
        glossary: Glossary,
        language: LanguageCode,
        threshold: float = 0.7
    ) -> List[Tuple[str, Term, float]]:
        """建议相关术语
        
        Args:
            text: 文本
            glossary: 术语表
            language: 语言
            threshold: 相似度阈值
            
        Returns:
            建议列表 [(匹配文本, 术语, 相似度)]
        """
        suggestions = []
        words = text.split()
        
        for word in words:
            word_lower = word.lower()
            
            for term in glossary.terms.values():
                # 计算相似度
                similarity = TerminologyService._calculate_similarity(
                    word_lower,
                    term.original.lower()
                )
                
                if similarity >= threshold:
                    suggestions.append((word, term, similarity))
        
        # 按相似度降序排序
        suggestions.sort(key=lambda x: x[2], reverse=True)
        return suggestions
    
    @staticmethod
    def build_glossary_from_translations(
        translations: Dict[LanguageCode, Dict[TranslationKey, TranslationText]],
        base_language: LanguageCode = LanguageCode.EN_US,
        min_frequency: int = 3
    ) -> Glossary:
        """从翻译构建术语表
        
        Args:
            translations: 多语言翻译
            base_language: 基础语言
            min_frequency: 最小出现频率
            
        Returns:
            术语表
        """
        glossary = Glossary(
            name="Auto-generated Glossary",
            description="Automatically generated from translations"
        )
        
        # 统计词频
        word_freq = {}
        base_translations = translations.get(base_language, {})
        
        for key, text in base_translations.items():
            # 提取潜在术语
            terms = TerminologyService.extract_terms_from_text(text.value)
            for term in terms:
                word_freq[term] = word_freq.get(term, 0) + 1
        
        # 创建术语
        for word, freq in word_freq.items():
            if freq >= min_frequency:
                term = Term(
                    key=word.lower().replace(' ', '_'),
                    original=word,
                    language=base_language,
                    translations={},
                    category=TerminologyService._guess_category(word)
                )
                
                # 查找其他语言的翻译
                for lang, trans in translations.items():
                    if lang != base_language:
                        # 简单匹配查找翻译
                        for key, text in trans.items():
                            if word in base_translations.get(key, TranslationText("", base_language)).value:
                                # 假设相同位置的词是翻译
                                # 这是简化的实现，实际可能需要更复杂的算法
                                term.translations[lang] = text.value.split()[0]
                                break
                
                glossary.add_term(term)
        
        return glossary
    
    @staticmethod
    def _find_actual_translation(
        text: str,
        original: str,
        expected: str
    ) -> str:
        """查找实际使用的翻译"""
        # 简单实现：返回文本中与期望翻译最相似的部分
        words = text.split()
        best_match = ""
        best_similarity = 0
        
        for word in words:
            similarity = TerminologyService._calculate_similarity(word, expected)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = word
        
        return best_match or "unknown"
    
    @staticmethod
    def _calculate_similarity(str1: str, str2: str) -> float:
        """计算字符串相似度（简单的Jaccard相似度）"""
        if not str1 or not str2:
            return 0.0
        
        set1 = set(str1)
        set2 = set(str2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def _guess_category(term: str) -> str:
        """猜测术语分类"""
        # 基于命名模式猜测
        if term.endswith("Block") or term.endswith("Ore"):
            return "block"
        elif term.endswith("Item") or term.endswith("Tool"):
            return "item"
        elif term.endswith("Entity") or term.endswith("Mob"):
            return "entity"
        elif term.endswith("Potion") or term.endswith("Effect"):
            return "effect"
        elif term.isupper():
            return "abbreviation"
        else:
            return "general"