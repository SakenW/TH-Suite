"""
冲突解决领域服务
处理翻译冲突和合并策略
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..models.mod import Mod, TranslationEntry
from ..value_objects import LanguageCode, TranslationKey


class ConflictResolutionStrategy(Enum):
    """冲突解决策略"""

    KEEP_NEWEST = "keep_newest"  # 保留最新的
    KEEP_OLDEST = "keep_oldest"  # 保留最旧的
    KEEP_HIGHEST_QUALITY = "keep_quality"  # 保留质量最高的
    KEEP_APPROVED = "keep_approved"  # 保留已批准的
    MANUAL_REVIEW = "manual_review"  # 手动审核
    MERGE_COMBINE = "merge_combine"  # 合并组合


@dataclass
class TranslationConflict:
    """翻译冲突记录"""

    key: TranslationKey
    language: LanguageCode
    existing_entry: TranslationEntry
    new_entry: TranslationEntry
    conflict_type: str  # duplicate, override, quality_diff
    detected_at: datetime

    def get_quality_diff(self) -> float:
        """获取质量差异"""
        existing_score = (
            self.existing_entry.quality_score.value
            if self.existing_entry.quality_score
            else 0
        )
        new_score = (
            self.new_entry.quality_score.value if self.new_entry.quality_score else 0
        )
        return abs(existing_score - new_score)

    def requires_manual_review(self) -> bool:
        """是否需要人工审核"""
        # 质量差异大于0.3需要人工审核
        if self.get_quality_diff() > 0.3:
            return True

        # 都是已批准的需要人工审核
        if (
            self.existing_entry.status == "approved"
            and self.new_entry.status == "approved"
        ):
            return True

        return False


class ConflictResolutionService:
    """冲突解决服务"""

    @staticmethod
    def detect_conflicts(
        mod: Mod, new_translations: dict[LanguageCode, list[TranslationEntry]]
    ) -> list[TranslationConflict]:
        """检测翻译冲突

        Args:
            mod: 目标模组
            new_translations: 新的翻译条目

        Returns:
            冲突列表
        """
        conflicts = []

        for language, new_entries in new_translations.items():
            existing_entries = mod.get_translations(language)
            existing_map = {e.key: e for e in existing_entries}

            for new_entry in new_entries:
                if new_entry.key in existing_map:
                    existing_entry = existing_map[new_entry.key]

                    # 检测不同类型的冲突
                    if existing_entry.translated.value != new_entry.translated.value:
                        conflict_type = "override"

                        # 如果质量分数差异大，标记为质量差异冲突
                        if existing_entry.quality_score and new_entry.quality_score:
                            diff = abs(
                                existing_entry.quality_score.value
                                - new_entry.quality_score.value
                            )
                            if diff > 0.2:
                                conflict_type = "quality_diff"

                        conflict = TranslationConflict(
                            key=new_entry.key,
                            language=language,
                            existing_entry=existing_entry,
                            new_entry=new_entry,
                            conflict_type=conflict_type,
                            detected_at=datetime.now(),
                        )
                        conflicts.append(conflict)

        return conflicts

    @staticmethod
    def resolve_conflict(
        conflict: TranslationConflict, strategy: ConflictResolutionStrategy
    ) -> TranslationEntry:
        """解决单个冲突

        Args:
            conflict: 冲突记录
            strategy: 解决策略

        Returns:
            解决后的翻译条目
        """
        if strategy == ConflictResolutionStrategy.KEEP_NEWEST:
            # 比较更新时间，保留较新的
            if conflict.new_entry.updated_at > conflict.existing_entry.updated_at:
                return conflict.new_entry
            return conflict.existing_entry

        elif strategy == ConflictResolutionStrategy.KEEP_OLDEST:
            # 比较创建时间，保留较旧的
            if conflict.existing_entry.created_at < conflict.new_entry.created_at:
                return conflict.existing_entry
            return conflict.new_entry

        elif strategy == ConflictResolutionStrategy.KEEP_HIGHEST_QUALITY:
            # 保留质量分数最高的
            existing_score = (
                conflict.existing_entry.quality_score.value
                if conflict.existing_entry.quality_score
                else 0
            )
            new_score = (
                conflict.new_entry.quality_score.value
                if conflict.new_entry.quality_score
                else 0
            )

            if new_score > existing_score:
                return conflict.new_entry
            return conflict.existing_entry

        elif strategy == ConflictResolutionStrategy.KEEP_APPROVED:
            # 优先保留已批准的
            if conflict.existing_entry.status == "approved":
                return conflict.existing_entry
            if conflict.new_entry.status == "approved":
                return conflict.new_entry
            # 如果都未批准，保留新的
            return conflict.new_entry

        elif strategy == ConflictResolutionStrategy.MERGE_COMBINE:
            # 合并策略：结合两者的最佳特性
            merged = conflict.new_entry

            # 保留更高的质量分数
            if (
                conflict.existing_entry.quality_score
                and conflict.new_entry.quality_score
            ):
                if (
                    conflict.existing_entry.quality_score.value
                    > conflict.new_entry.quality_score.value
                ):
                    merged.quality_score = conflict.existing_entry.quality_score

            # 保留批准状态
            if conflict.existing_entry.status == "approved":
                merged.status = "approved"
                merged.reviewed_by = conflict.existing_entry.reviewed_by

            return merged

        else:  # MANUAL_REVIEW
            # 需要人工审核，暂时保留现有的
            return conflict.existing_entry

    @staticmethod
    def resolve_conflicts(
        conflicts: list[TranslationConflict],
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.KEEP_HIGHEST_QUALITY,
    ) -> tuple[list[TranslationEntry], list[TranslationConflict]]:
        """批量解决冲突

        Args:
            conflicts: 冲突列表
            strategy: 解决策略

        Returns:
            (解决后的条目列表, 需要人工审核的冲突列表)
        """
        resolved_entries = []
        manual_review_conflicts = []

        for conflict in conflicts:
            # 如果需要人工审核且策略不是强制的
            if (
                conflict.requires_manual_review()
                and strategy == ConflictResolutionStrategy.MANUAL_REVIEW
            ):
                manual_review_conflicts.append(conflict)
            else:
                resolved_entry = ConflictResolutionService.resolve_conflict(
                    conflict, strategy
                )
                resolved_entries.append(resolved_entry)

        return resolved_entries, manual_review_conflicts

    @staticmethod
    def merge_translations(
        mod: Mod,
        other_mod: Mod,
        languages: list[LanguageCode],
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.KEEP_HIGHEST_QUALITY,
    ) -> dict[str, int]:
        """合并两个模组的翻译

        Args:
            mod: 目标模组
            other_mod: 源模组
            languages: 要合并的语言列表
            strategy: 冲突解决策略

        Returns:
            统计信息 {merged: 合并数, conflicts: 冲突数, skipped: 跳过数}
        """
        stats = {"merged": 0, "conflicts": 0, "skipped": 0}

        for language in languages:
            other_translations = other_mod.get_translations(language)
            if not other_translations:
                continue

            # 检测冲突
            conflicts = ConflictResolutionService.detect_conflicts(
                mod, {language: other_translations}
            )

            if conflicts:
                stats["conflicts"] += len(conflicts)

                # 解决冲突
                resolved, manual = ConflictResolutionService.resolve_conflicts(
                    conflicts, strategy
                )

                # 应用解决后的翻译
                for entry in resolved:
                    mod.add_translation(language, entry)
                    stats["merged"] += 1

                stats["skipped"] += len(manual)
            else:
                # 没有冲突，直接添加
                for entry in other_translations:
                    mod.add_translation(language, entry)
                    stats["merged"] += 1

        return stats

    @staticmethod
    def create_conflict_report(conflicts: list[TranslationConflict]) -> dict[str, any]:
        """创建冲突报告

        Args:
            conflicts: 冲突列表

        Returns:
            冲突报告
        """
        report = {
            "total_conflicts": len(conflicts),
            "by_type": {},
            "by_language": {},
            "requires_review": [],
            "quality_differences": [],
        }

        for conflict in conflicts:
            # 按类型统计
            conflict_type = conflict.conflict_type
            if conflict_type not in report["by_type"]:
                report["by_type"][conflict_type] = 0
            report["by_type"][conflict_type] += 1

            # 按语言统计
            language = conflict.language.value
            if language not in report["by_language"]:
                report["by_language"][language] = 0
            report["by_language"][language] += 1

            # 需要审核的冲突
            if conflict.requires_manual_review():
                report["requires_review"].append(
                    {
                        "key": str(conflict.key),
                        "language": language,
                        "existing": conflict.existing_entry.translated.value,
                        "new": conflict.new_entry.translated.value,
                        "quality_diff": conflict.get_quality_diff(),
                    }
                )

            # 质量差异
            if conflict.get_quality_diff() > 0.1:
                report["quality_differences"].append(
                    {
                        "key": str(conflict.key),
                        "language": language,
                        "diff": conflict.get_quality_diff(),
                    }
                )

        return report
