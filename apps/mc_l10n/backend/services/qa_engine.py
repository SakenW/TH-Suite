"""
QA规则引擎
检查翻译质量，包括占位符一致性、格式验证等
"""

import re
import json
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

from database.repositories.translation_entry_repository import TranslationEntry

logger = structlog.get_logger(__name__)


class QASeverity(Enum):
    """QA问题严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class QAIssue:
    """QA问题"""
    rule_id: str
    severity: QASeverity
    message: str
    details: Dict[str, Any] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details or {},
            "suggestion": self.suggestion
        }


class QARule:
    """QA规则基类"""
    
    def __init__(self, rule_id: str, enabled: bool = True):
        self.rule_id = rule_id
        self.enabled = enabled
    
    def check(self, entry: TranslationEntry) -> List[QAIssue]:
        """检查翻译条目，返回发现的问题"""
        if not self.enabled:
            return []
        return self._check_impl(entry)
    
    def _check_impl(self, entry: TranslationEntry) -> List[QAIssue]:
        """具体的检查实现，子类需要重写"""
        raise NotImplementedError


class PlaceholderConsistencyRule(QARule):
    """占位符一致性检查规则"""
    
    def __init__(self):
        super().__init__("placeholder_consistency")
        
        # 定义各种占位符模式
        self.placeholder_patterns = {
            "java_format": re.compile(r'%[sd%]'),          # %s, %d, %%
            "java_indexed": re.compile(r'%\d+\$[sd]'),     # %1$s, %2$d
            "c_style": re.compile(r'%[sd]'),               # %s, %d
            "minecraft_format": re.compile(r'%[sd]'),      # MC格式
            "bracket_format": re.compile(r'\{(\d+)\}'),    # {0}, {1}
            "named_format": re.compile(r'\{(\w+)\}'),      # {name}, {value}
            "dollar_format": re.compile(r'\$\{(\w+)\}'),   # ${var}
            "percent_braces": re.compile(r'%\{(\w+)\}'),   # %{var}
        }
    
    def _check_impl(self, entry: TranslationEntry) -> List[QAIssue]:
        """检查占位符一致性"""
        issues = []
        
        if not entry.src_text or not entry.dst_text:
            return issues
        
        # 提取源文本和目标文本中的占位符
        src_placeholders = self._extract_placeholders(entry.src_text)
        dst_placeholders = self._extract_placeholders(entry.dst_text)
        
        # 检查占位符数量
        issues.extend(self._check_placeholder_count(src_placeholders, dst_placeholders))
        
        # 检查占位符类型
        issues.extend(self._check_placeholder_types(src_placeholders, dst_placeholders))
        
        # 检查索引占位符的连续性
        issues.extend(self._check_indexed_placeholders(src_placeholders, dst_placeholders))
        
        return issues
    
    def _extract_placeholders(self, text: str) -> Dict[str, List[str]]:
        """提取文本中的所有占位符"""
        placeholders = {}
        
        for pattern_name, pattern in self.placeholder_patterns.items():
            matches = pattern.findall(text)
            if matches:
                placeholders[pattern_name] = matches
        
        return placeholders
    
    def _check_placeholder_count(self, src_ph: Dict, dst_ph: Dict) -> List[QAIssue]:
        """检查占位符数量是否一致"""
        issues = []
        
        for pattern_name in set(src_ph.keys()) | set(dst_ph.keys()):
            src_count = len(src_ph.get(pattern_name, []))
            dst_count = len(dst_ph.get(pattern_name, []))
            
            if src_count != dst_count:
                issues.append(QAIssue(
                    rule_id=f"{self.rule_id}.count_mismatch",
                    severity=QASeverity.ERROR,
                    message=f"占位符数量不匹配: {pattern_name}",
                    details={
                        "pattern_type": pattern_name,
                        "source_count": src_count,
                        "target_count": dst_count,
                        "source_placeholders": src_ph.get(pattern_name, []),
                        "target_placeholders": dst_ph.get(pattern_name, [])
                    },
                    suggestion=f"确保目标文本包含相同数量的{pattern_name}占位符"
                ))
        
        return issues
    
    def _check_placeholder_types(self, src_ph: Dict, dst_ph: Dict) -> List[QAIssue]:
        """检查占位符类型是否一致"""
        issues = []
        
        # 检查Java格式占位符类型 (%s vs %d)
        if "java_format" in src_ph and "java_format" in dst_ph:
            src_types = set(src_ph["java_format"])
            dst_types = set(dst_ph["java_format"])
            
            if src_types != dst_types:
                issues.append(QAIssue(
                    rule_id=f"{self.rule_id}.type_mismatch",
                    severity=QASeverity.ERROR,
                    message="占位符类型不匹配",
                    details={
                        "source_types": list(src_types),
                        "target_types": list(dst_types),
                        "missing_in_target": list(src_types - dst_types),
                        "extra_in_target": list(dst_types - src_types)
                    },
                    suggestion="确保目标文本使用相同类型的占位符(%s, %d等)"
                ))
        
        return issues
    
    def _check_indexed_placeholders(self, src_ph: Dict, dst_ph: Dict) -> List[QAIssue]:
        """检查索引占位符的连续性"""
        issues = []
        
        for pattern_name in ["bracket_format", "java_indexed"]:
            if pattern_name in src_ph:
                src_indices = set()
                
                for match in src_ph[pattern_name]:
                    try:
                        if pattern_name == "bracket_format":
                            src_indices.add(int(match))
                        elif pattern_name == "java_indexed":
                            # 从"%1$s"中提取"1"
                            index = int(match.split('$')[0][1:])
                            src_indices.add(index)
                    except (ValueError, IndexError):
                        continue
                
                # 检查索引是否连续
                if src_indices:
                    expected_indices = set(range(min(src_indices), max(src_indices) + 1))
                    if src_indices != expected_indices:
                        missing_indices = expected_indices - src_indices
                        issues.append(QAIssue(
                            rule_id=f"{self.rule_id}.index_gap",
                            severity=QASeverity.WARNING,
                            message=f"索引占位符不连续: {pattern_name}",
                            details={
                                "present_indices": sorted(list(src_indices)),
                                "missing_indices": sorted(list(missing_indices)),
                                "expected_range": f"{min(src_indices)}-{max(src_indices)}"
                            },
                            suggestion="使用连续的索引占位符，避免跳跃"
                        ))
        
        return issues


class TextLengthRule(QARule):
    """文本长度检查规则"""
    
    def __init__(self, max_length_ratio: float = 3.0, max_absolute_diff: int = 1000):
        super().__init__("text_length")
        self.max_length_ratio = max_length_ratio
        self.max_absolute_diff = max_absolute_diff
    
    def _check_impl(self, entry: TranslationEntry) -> List[QAIssue]:
        """检查翻译文本长度是否合理"""
        issues = []
        
        if not entry.src_text or not entry.dst_text:
            return issues
        
        src_len = len(entry.src_text)
        dst_len = len(entry.dst_text)
        
        if src_len == 0:
            return issues
        
        length_ratio = dst_len / src_len
        length_diff = abs(dst_len - src_len)
        
        # 检查长度比例
        if length_ratio > self.max_length_ratio:
            issues.append(QAIssue(
                rule_id=f"{self.rule_id}.ratio_too_high",
                severity=QASeverity.WARNING,
                message=f"翻译文本长度比例过高: {length_ratio:.2f}",
                details={
                    "source_length": src_len,
                    "target_length": dst_len,
                    "ratio": round(length_ratio, 2),
                    "max_ratio": self.max_length_ratio
                },
                suggestion=f"翻译长度不应超过原文的{self.max_length_ratio}倍"
            ))
        
        # 检查绝对长度差异
        if length_diff > self.max_absolute_diff:
            issues.append(QAIssue(
                rule_id=f"{self.rule_id}.absolute_diff",
                severity=QASeverity.WARNING,
                message=f"翻译文本长度差异过大: {length_diff}字符",
                details={
                    "source_length": src_len,
                    "target_length": dst_len,
                    "difference": length_diff,
                    "max_difference": self.max_absolute_diff
                },
                suggestion=f"翻译长度差异不应超过{self.max_absolute_diff}字符"
            ))
        
        return issues


class EmptyTranslationRule(QARule):
    """空翻译检查规则"""
    
    def __init__(self):
        super().__init__("empty_translation")
    
    def _check_impl(self, entry: TranslationEntry) -> List[QAIssue]:
        """检查空翻译"""
        issues = []
        
        # 检查目标文本是否为空
        if not entry.dst_text or entry.dst_text.strip() == "":
            if entry.src_text and entry.src_text.strip():
                issues.append(QAIssue(
                    rule_id=f"{self.rule_id}.missing_translation",
                    severity=QASeverity.ERROR,
                    message="翻译内容为空",
                    details={
                        "source_text": entry.src_text,
                        "target_text": entry.dst_text or ""
                    },
                    suggestion="请提供翻译内容"
                ))
        
        # 检查源文本是否与目标文本完全相同
        if (entry.src_text and entry.dst_text and 
            entry.src_text.strip() == entry.dst_text.strip() and
            len(entry.src_text.strip()) > 0):
            
            # 排除一些可能不需要翻译的内容
            if not self._is_untranslatable(entry.src_text):
                issues.append(QAIssue(
                    rule_id=f"{self.rule_id}.identical_text",
                    severity=QASeverity.WARNING,
                    message="翻译内容与原文相同",
                    details={
                        "text": entry.src_text
                    },
                    suggestion="确认是否需要翻译此内容"
                ))
        
        return issues
    
    def _is_untranslatable(self, text: str) -> bool:
        """判断文本是否不需要翻译"""
        text = text.strip()
        
        # 数字、符号等
        if re.match(r'^[\d\s\-+*/=<>()[\]{},.;:!"\'`~@#$%^&|\\]+$', text):
            return True
        
        # 短的英文单词或缩写 (可能不需要翻译)
        if len(text) <= 3 and re.match(r'^[a-zA-Z]+$', text):
            return True
        
        # 常见的不需要翻译的词
        untranslatable_words = {
            "OK", "ok", "Yes", "No", "ID", "UUID", "URL", "HTTP", "JSON", "XML",
            "API", "GUI", "UI", "OS", "CPU", "GPU", "RAM", "SSD", "HDD"
        }
        
        return text in untranslatable_words


class MinecraftFormatRule(QARule):
    """Minecraft特定格式检查规则"""
    
    def __init__(self):
        super().__init__("minecraft_format")
        
        # MC颜色代码和格式代码
        self.mc_format_pattern = re.compile(r'§[0-9a-fk-or]')
        # MC命名空间格式
        self.namespace_pattern = re.compile(r'[a-z0-9_]+:[a-z0-9_/]+')
    
    def _check_impl(self, entry: TranslationEntry) -> List[QAIssue]:
        """检查Minecraft特定格式"""
        issues = []
        
        if not entry.src_text or not entry.dst_text:
            return issues
        
        # 检查颜色代码
        issues.extend(self._check_color_codes(entry))
        
        # 检查命名空间
        issues.extend(self._check_namespaces(entry))
        
        return issues
    
    def _check_color_codes(self, entry: TranslationEntry) -> List[QAIssue]:
        """检查Minecraft颜色代码"""
        issues = []
        
        src_colors = self.mc_format_pattern.findall(entry.src_text)
        dst_colors = self.mc_format_pattern.findall(entry.dst_text)
        
        if len(src_colors) != len(dst_colors):
            issues.append(QAIssue(
                rule_id=f"{self.rule_id}.color_code_mismatch",
                severity=QASeverity.WARNING,
                message="Minecraft颜色代码数量不匹配",
                details={
                    "source_colors": src_colors,
                    "target_colors": dst_colors,
                    "source_count": len(src_colors),
                    "target_count": len(dst_colors)
                },
                suggestion="确保翻译保留原文的颜色代码"
            ))
        
        return issues
    
    def _check_namespaces(self, entry: TranslationEntry) -> List[QAIssue]:
        """检查命名空间格式"""
        issues = []
        
        src_namespaces = self.namespace_pattern.findall(entry.src_text)
        dst_namespaces = self.namespace_pattern.findall(entry.dst_text)
        
        # 命名空间通常不应该被翻译
        for ns in src_namespaces:
            if ns not in dst_namespaces:
                issues.append(QAIssue(
                    rule_id=f"{self.rule_id}.missing_namespace",
                    severity=QASeverity.ERROR,
                    message=f"缺失命名空间: {ns}",
                    details={
                        "missing_namespace": ns,
                        "source_namespaces": src_namespaces,
                        "target_namespaces": dst_namespaces
                    },
                    suggestion="命名空间通常不应该被翻译，请保留原文"
                ))
        
        return issues


class QAEngine:
    """QA规则引擎"""
    
    def __init__(self):
        self.rules: List[QARule] = []
        self._init_default_rules()
    
    def _init_default_rules(self):
        """初始化默认规则"""
        self.rules = [
            PlaceholderConsistencyRule(),
            TextLengthRule(),
            EmptyTranslationRule(),
            MinecraftFormatRule()
        ]
        
        logger.info("QA规则引擎初始化完成", rules_count=len(self.rules))
    
    def check_entry(self, entry: TranslationEntry) -> List[QAIssue]:
        """检查单个翻译条目"""
        all_issues = []
        
        for rule in self.rules:
            try:
                issues = rule.check(entry)
                all_issues.extend(issues)
            except Exception as e:
                logger.error("QA规则检查失败",
                           rule_id=rule.rule_id,
                           entry_uid=entry.uid,
                           error=str(e))
                
                # 添加规则错误
                all_issues.append(QAIssue(
                    rule_id=f"{rule.rule_id}.rule_error",
                    severity=QASeverity.ERROR,
                    message=f"规则检查失败: {str(e)}",
                    details={"rule_id": rule.rule_id}
                ))
        
        return all_issues
    
    def check_entries(self, entries: List[TranslationEntry]) -> Dict[str, List[QAIssue]]:
        """批量检查翻译条目"""
        results = {}
        
        for entry in entries:
            issues = self.check_entry(entry)
            if issues:
                results[entry.uid] = issues
        
        logger.info("批量QA检查完成",
                   total_entries=len(entries),
                   entries_with_issues=len(results),
                   total_issues=sum(len(issues) for issues in results.values()))
        
        return results
    
    def update_entry_qa_flags(self, entry: TranslationEntry) -> TranslationEntry:
        """更新条目的QA标记"""
        issues = self.check_entry(entry)
        
        if not entry.qa_flags:
            entry.qa_flags = {}
        
        # 清除旧的QA标记
        for key in list(entry.qa_flags.keys()):
            if key.startswith('qa_'):
                del entry.qa_flags[key]
        
        # 添加新的QA标记
        if issues:
            entry.qa_flags['qa_issues'] = [issue.to_dict() for issue in issues]
            entry.qa_flags['qa_issue_count'] = len(issues)
            entry.qa_flags['qa_max_severity'] = max(issue.severity.value for issue in issues)
            entry.qa_flags['qa_checked_at'] = structlog.get_logger().info("QA检查时间")
        else:
            entry.qa_flags['qa_clean'] = True
            entry.qa_flags['qa_checked_at'] = structlog.get_logger().info("QA检查时间")
        
        return entry
    
    def get_rule_by_id(self, rule_id: str) -> Optional[QARule]:
        """根据ID获取规则"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None
    
    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        rule = self.get_rule_by_id(rule_id)
        if rule:
            rule.enabled = True
            logger.info("启用QA规则", rule_id=rule_id)
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        rule = self.get_rule_by_id(rule_id)
        if rule:
            rule.enabled = False
            logger.info("禁用QA规则", rule_id=rule_id)
            return True
        return False
    
    def get_rules_info(self) -> List[Dict[str, Any]]:
        """获取所有规则信息"""
        return [
            {
                "rule_id": rule.rule_id,
                "enabled": rule.enabled,
                "class_name": rule.__class__.__name__
            }
            for rule in self.rules
        ]


# 全局QA引擎实例
_qa_engine: Optional[QAEngine] = None


def get_qa_engine() -> QAEngine:
    """获取QA规则引擎实例"""
    global _qa_engine
    if _qa_engine is None:
        _qa_engine = QAEngine()
        logger.info("全局QA引擎初始化完成")
    return _qa_engine