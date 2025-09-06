"""
领域服务
处理跨聚合的业务逻辑
"""

from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import hashlib
import json

from .models.mod import Mod, ModId, TranslationEntry
from .models.translation_project import TranslationProject, TranslationTask
from .repositories import ModRepository, TranslationRepository, TranslationProjectRepository
from .events import TranslationConflictEvent


class TranslationService:
    """翻译领域服务"""
    
    def __init__(
        self,
        mod_repository: ModRepository,
        translation_repository: TranslationRepository
    ):
        self.mod_repository = mod_repository
        self.translation_repository = translation_repository
    
    def translate_mod(
        self,
        mod_id: ModId,
        source_language: str,
        target_language: str,
        translations: Dict[str, str]
    ) -> Tuple[int, int]:
        """翻译模组
        
        Returns:
            (成功数, 失败数)
        """
        mod = self.mod_repository.find_by_id(mod_id)
        if not mod:
            raise ValueError(f"Mod {mod_id} not found")
        
        success_count = 0
        failure_count = 0
        
        for key, value in translations.items():
            entry = TranslationEntry(
                key=key,
                original=key,  # 假设key就是原文
                translated=value,
                language=target_language,
                status="pending"
            )
            
            try:
                mod.add_translation(target_language, entry)
                success_count += 1
            except Exception as e:
                failure_count += 1
        
        # 保存更新
        self.mod_repository.update(mod)
        self.translation_repository.save_translations(mod_id, target_language, translations)
        
        return success_count, failure_count
    
    def merge_translations(
        self,
        mod_id: ModId,
        language: str,
        new_translations: Dict[str, str],
        strategy: str = "override"
    ) -> Dict[str, str]:
        """合并翻译
        
        Args:
            strategy: 合并策略 (override, keep_existing, merge)
        """
        existing = self.translation_repository.find_by_mod_and_language(mod_id, language)
        
        if strategy == "override":
            # 新翻译覆盖旧翻译
            merged = {**existing, **new_translations}
        elif strategy == "keep_existing":
            # 保留已存在的翻译
            merged = {**new_translations, **existing}
        elif strategy == "merge":
            # 智能合并（需要更复杂的逻辑）
            merged = self._smart_merge(existing, new_translations)
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")
        
        self.translation_repository.save_translations(mod_id, language, merged)
        return merged
    
    def _smart_merge(
        self,
        existing: Dict[str, str],
        new: Dict[str, str]
    ) -> Dict[str, str]:
        """智能合并翻译"""
        merged = existing.copy()
        
        for key, new_value in new.items():
            if key not in existing:
                # 新键，直接添加
                merged[key] = new_value
            elif existing[key] != new_value:
                # 冲突，使用更长的翻译（假设更详细）
                if len(new_value) > len(existing[key]):
                    merged[key] = new_value
        
        return merged
    
    def calculate_translation_quality(
        self,
        mod_id: ModId,
        language: str
    ) -> float:
        """计算翻译质量分数
        
        Returns:
            质量分数 (0.0-1.0)
        """
        translations = self.translation_repository.find_by_mod_and_language(mod_id, language)
        
        if not translations:
            return 0.0
        
        quality_factors = []
        
        for key, value in translations.items():
            # 检查是否为空
            if not value or value.strip() == "":
                quality_factors.append(0.0)
                continue
            
            # 检查是否与原文相同（可能未翻译）
            if key == value:
                quality_factors.append(0.3)
                continue
            
            # 检查长度比例（过短或过长可能有问题）
            length_ratio = len(value) / len(key) if len(key) > 0 else 1.0
            if 0.5 <= length_ratio <= 3.0:
                quality_factors.append(1.0)
            else:
                quality_factors.append(0.7)
        
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.0


class ConflictResolutionService:
    """冲突解决领域服务"""
    
    def __init__(self, translation_repository: TranslationRepository):
        self.translation_repository = translation_repository
    
    def detect_conflicts(
        self,
        mod_id: ModId,
        language: str,
        new_translations: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """检测翻译冲突"""
        existing = self.translation_repository.find_by_mod_and_language(mod_id, language)
        conflicts = []
        
        for key, new_value in new_translations.items():
            if key in existing and existing[key] != new_value:
                conflicts.append({
                    'key': key,
                    'existing': existing[key],
                    'new': new_value
                })
        
        return conflicts
    
    def resolve_conflict(
        self,
        conflict: Dict[str, str],
        strategy: str = "newest"
    ) -> str:
        """解决单个冲突
        
        Args:
            strategy: 解决策略 (newest, longest, manual)
        """
        if strategy == "newest":
            return conflict['new']
        elif strategy == "longest":
            return conflict['new'] if len(conflict['new']) > len(conflict['existing']) else conflict['existing']
        elif strategy == "manual":
            # 需要人工介入
            raise ValueError("Manual resolution required")
        else:
            raise ValueError(f"Unknown resolution strategy: {strategy}")
    
    def batch_resolve(
        self,
        conflicts: List[Dict[str, str]],
        strategy: str = "newest"
    ) -> Dict[str, str]:
        """批量解决冲突"""
        resolved = {}
        
        for conflict in conflicts:
            try:
                resolved[conflict['key']] = self.resolve_conflict(conflict, strategy)
            except ValueError:
                # 无法自动解决，保留原值
                resolved[conflict['key']] = conflict['existing']
        
        return resolved


class TerminologyService:
    """术语管理领域服务"""
    
    def __init__(self):
        self.glossary: Dict[str, Dict[str, str]] = {}  # language -> term -> translation
    
    def add_term(self, term: str, language: str, translation: str):
        """添加术语"""
        if language not in self.glossary:
            self.glossary[language] = {}
        self.glossary[language][term] = translation
    
    def get_term(self, term: str, language: str) -> Optional[str]:
        """获取术语翻译"""
        return self.glossary.get(language, {}).get(term)
    
    def apply_terminology(
        self,
        text: str,
        language: str
    ) -> str:
        """应用术语表到文本"""
        if language not in self.glossary:
            return text
        
        result = text
        for term, translation in self.glossary[language].items():
            result = result.replace(term, translation)
        
        return result
    
    def extract_terms(self, text: str) -> Set[str]:
        """从文本提取潜在术语"""
        # 简单实现：提取大写开头的词
        words = text.split()
        terms = set()
        
        for word in words:
            if word and word[0].isupper():
                # 去除标点
                clean_word = ''.join(c for c in word if c.isalnum())
                if clean_word:
                    terms.add(clean_word)
        
        return terms
    
    def validate_consistency(
        self,
        translations: Dict[str, str],
        language: str
    ) -> List[Dict[str, str]]:
        """验证术语一致性"""
        inconsistencies = []
        
        if language not in self.glossary:
            return inconsistencies
        
        for key, text in translations.items():
            for term, expected_translation in self.glossary[language].items():
                if term in text and expected_translation not in text:
                    inconsistencies.append({
                        'key': key,
                        'term': term,
                        'expected': expected_translation,
                        'found_in': text
                    })
        
        return inconsistencies


class ProjectAllocationService:
    """项目分配领域服务"""
    
    def __init__(
        self,
        project_repository: TranslationProjectRepository,
        mod_repository: ModRepository
    ):
        self.project_repository = project_repository
        self.mod_repository = mod_repository
    
    def allocate_mods_to_project(
        self,
        project_id: str,
        mod_ids: List[ModId]
    ) -> Tuple[int, List[str]]:
        """分配模组到项目
        
        Returns:
            (成功数, 失败的mod_id列表)
        """
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        success_count = 0
        failed_mods = []
        
        for mod_id in mod_ids:
            mod = self.mod_repository.find_by_id(mod_id)
            if not mod:
                failed_mods.append(str(mod_id))
                continue
            
            try:
                project.add_mod(mod_id)
                success_count += 1
            except Exception as e:
                failed_mods.append(str(mod_id))
        
        # 保存更新
        self.project_repository.update(project)
        
        return success_count, failed_mods
    
    def auto_assign_tasks(
        self,
        project_id: str,
        strategy: str = "round_robin"
    ) -> Dict[str, str]:
        """自动分配任务给贡献者
        
        Returns:
            任务ID到用户ID的映射
        """
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        assignments = {}
        pending_tasks = [t for t in project.tasks if t.status == "pending"]
        
        if strategy == "round_robin":
            # 轮询分配
            contributors = list(project.contributors.values())
            if not contributors:
                return assignments
            
            contributor_index = 0
            for task in pending_tasks:
                # 找到能处理该语言的贡献者
                while contributor_index < len(contributors):
                    contributor = contributors[contributor_index]
                    if contributor.can_translate(task.language):
                        project.assign_task(task.task_id, contributor.user_id)
                        assignments[task.task_id] = contributor.user_id
                        break
                    contributor_index = (contributor_index + 1) % len(contributors)
                
                contributor_index = (contributor_index + 1) % len(contributors)
        
        elif strategy == "expertise":
            # 基于专长分配（根据贡献数）
            for task in pending_tasks:
                # 找到该语言贡献最多的用户
                best_contributor = None
                max_contributions = -1
                
                for contributor in project.contributors.values():
                    if contributor.can_translate(task.language) and contributor.contribution_count > max_contributions:
                        best_contributor = contributor
                        max_contributions = contributor.contribution_count
                
                if best_contributor:
                    project.assign_task(task.task_id, best_contributor.user_id)
                    assignments[task.task_id] = best_contributor.user_id
        
        # 保存更新
        self.project_repository.update(project)
        
        return assignments