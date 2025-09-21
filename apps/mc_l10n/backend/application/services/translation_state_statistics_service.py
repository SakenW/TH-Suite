"""
翻译状态统计和报表服务
提供详细的翻译进度统计、性能分析和报表生成功能
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog

from infrastructure.repositories.translation_state_repository import (
    StateHistoryRepository, TranslationStateRepository
)
from infrastructure.repositories.core_translation_entry_repository import (
    CoreTranslationEntryRepository
)

logger = structlog.get_logger(__name__)


class TranslationStateStatisticsService:
    """翻译状态统计服务"""
    
    def __init__(
        self,
        history_repo: StateHistoryRepository,
        state_repo: TranslationStateRepository,
        entry_repo: CoreTranslationEntryRepository
    ):
        self.history_repo = history_repo
        self.state_repo = state_repo
        self.entry_repo = entry_repo
    
    def get_comprehensive_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取综合统计信息"""
        try:
            stats = {
                "overview": self._get_overview_stats(),
                "state_distribution": self._get_state_distribution(),
                "progress_trends": self._get_progress_trends(days),
                "productivity_metrics": self._get_productivity_metrics(days),
                "quality_metrics": self._get_quality_metrics(),
                "workload_analysis": self._get_workload_analysis(days),
                "bottleneck_analysis": self._get_bottleneck_analysis(),
                "generated_at": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取综合统计失败: {e}")
            return {"error": str(e)}
    
    def get_progress_report(
        self,
        project_uid: str = None,
        mod_uid: str = None,
        locale: str = None
    ) -> Dict[str, Any]:
        """获取进度报告"""
        try:
            # 构建过滤条件
            filters = {}
            if project_uid:
                filters["project_uid"] = project_uid
            if mod_uid:
                filters["mod_uid"] = mod_uid
            if locale:
                filters["locale"] = locale
            
            report = {
                "filters": filters,
                "summary": self._get_filtered_summary(filters),
                "by_language_file": self._get_progress_by_language_file(filters),
                "by_mod": self._get_progress_by_mod(filters),
                "completion_timeline": self._get_completion_timeline(filters),
                "quality_distribution": self._get_quality_distribution(filters),
                "generated_at": datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"获取进度报告失败: {e}")
            return {"error": str(e)}
    
    def get_performance_analysis(self, days: int = 30) -> Dict[str, Any]:
        """获取性能分析"""
        try:
            analysis = {
                "period_days": days,
                "throughput_analysis": self._get_throughput_analysis(days),
                "translator_performance": self._get_translator_performance(days),
                "reviewer_performance": self._get_reviewer_performance(days),
                "state_transition_efficiency": self._get_transition_efficiency(days),
                "bottleneck_identification": self._get_detailed_bottlenecks(days),
                "recommendations": self._generate_performance_recommendations(days),
                "generated_at": datetime.now().isoformat()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"获取性能分析失败: {e}")
            return {"error": str(e)}
    
    def get_quality_dashboard(self) -> Dict[str, Any]:
        """获取质量仪表板"""
        try:
            dashboard = {
                "quality_overview": self._get_quality_overview(),
                "review_statistics": self._get_review_statistics(),
                "revision_analysis": self._get_revision_analysis(),
                "approval_rates": self._get_approval_rates(),
                "quality_trends": self._get_quality_trends(30),
                "common_issues": self._get_common_quality_issues(),
                "generated_at": datetime.now().isoformat()
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"获取质量仪表板失败: {e}")
            return {"error": str(e)}
    
    def get_workload_report(self, days: int = 30) -> Dict[str, Any]:
        """获取工作负载报告"""
        try:
            report = {
                "period_days": days,
                "team_workload": self._get_team_workload(days),
                "individual_workload": self._get_individual_workload(days),
                "capacity_analysis": self._get_capacity_analysis(days),
                "assignment_distribution": self._get_assignment_distribution(),
                "workload_balance": self._get_workload_balance(days),
                "recommendations": self._generate_workload_recommendations(days),
                "generated_at": datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"获取工作负载报告失败: {e}")
            return {"error": str(e)}
    
    def _get_overview_stats(self) -> Dict[str, Any]:
        """获取总览统计"""
        query = """
            SELECT 
                COUNT(*) as total_entries,
                COUNT(CASE WHEN status = 'translated' THEN 1 END) as translated,
                COUNT(CASE WHEN status = 'reviewed' THEN 1 END) as reviewed,
                COUNT(CASE WHEN status = 'published' THEN 1 END) as published,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected
            FROM core_translation_entries
        """
        
        row = self.entry_repo.execute_single(query)
        if not row:
            return {}
        
        total = row['total_entries']
        if total == 0:
            return {"total_entries": 0}
        
        return {
            "total_entries": total,
            "translated": row['translated'],
            "reviewed": row['reviewed'],
            "published": row['published'],
            "pending": row['pending'],
            "rejected": row['rejected'],
            "translation_rate": round(row['translated'] / total * 100, 2),
            "review_rate": round(row['reviewed'] / total * 100, 2),
            "publication_rate": round(row['published'] / total * 100, 2),
            "completion_rate": round((row['translated'] + row['reviewed'] + row['published']) / total * 100, 2)
        }
    
    def _get_state_distribution(self) -> Dict[str, Any]:
        """获取状态分布"""
        query = """
            SELECT 
                cte.status,
                ts.display_name,
                ts.category,
                ts.color_hex,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM core_translation_entries), 2) as percentage
            FROM core_translation_entries cte
            LEFT JOIN translation_states ts ON cte.status = ts.state_key
            GROUP BY cte.status, ts.display_name, ts.category, ts.color_hex
            ORDER BY count DESC
        """
        
        rows = self.entry_repo.execute_query(query)
        
        distribution = []
        by_category = {}
        
        for row in rows:
            state_info = {
                "state": row['status'],
                "display_name": row['display_name'] or row['status'],
                "category": row['category'] or "unknown",
                "color_hex": row['color_hex'] or "#6B7280",
                "count": row['count'],
                "percentage": row['percentage']
            }
            distribution.append(state_info)
            
            # 按分类聚合
            category = state_info["category"]
            if category not in by_category:
                by_category[category] = {"count": 0, "states": []}
            by_category[category]["count"] += row['count']
            by_category[category]["states"].append(state_info)
        
        return {
            "distribution": distribution,
            "by_category": by_category
        }
    
    def _get_progress_trends(self, days: int) -> Dict[str, Any]:
        """获取进度趋势"""
        query = """
            SELECT 
                DATE(tsh.created_at) as date,
                tsh.to_state,
                COUNT(*) as transition_count
            FROM translation_state_history tsh
            WHERE tsh.created_at >= datetime('now', '-{} days')
            GROUP BY DATE(tsh.created_at), tsh.to_state
            ORDER BY date
        """.format(days)
        
        rows = self.entry_repo.execute_query(query)
        
        # 按日期组织数据
        daily_data = {}
        states = set()
        
        for row in rows:
            date = row['date']
            state = row['to_state']
            count = row['transition_count']
            
            if date not in daily_data:
                daily_data[date] = {}
            daily_data[date][state] = count
            states.add(state)
        
        # 转换为时间序列格式
        timeline = []
        for date in sorted(daily_data.keys()):
            day_data = {"date": date}
            for state in states:
                day_data[state] = daily_data[date].get(state, 0)
            timeline.append(day_data)
        
        return {
            "timeline": timeline,
            "states": list(states),
            "period_days": days
        }
    
    def _get_productivity_metrics(self, days: int) -> Dict[str, Any]:
        """获取生产力指标"""
        # 每日翻译数量
        daily_query = """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as daily_translations
            FROM translation_state_history
            WHERE to_state = 'translated' 
            AND created_at >= datetime('now', '-{} days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """.format(days)
        
        daily_rows = self.entry_repo.execute_query(daily_query)
        
        # 平均处理时间
        avg_time_query = """
            SELECT 
                AVG(julianday(h2.created_at) - julianday(h1.created_at)) as avg_translation_days,
                AVG(julianday(h3.created_at) - julianday(h2.created_at)) as avg_review_days
            FROM translation_state_history h1
            JOIN translation_state_history h2 ON h1.entry_uid = h2.entry_uid 
                AND h1.to_state = 'pending' AND h2.to_state = 'translated'
            LEFT JOIN translation_state_history h3 ON h2.entry_uid = h3.entry_uid 
                AND h3.to_state = 'reviewed'
            WHERE h1.created_at >= datetime('now', '-{} days')
        """.format(days)
        
        avg_row = self.entry_repo.execute_single(avg_time_query)
        
        return {
            "daily_translations": [
                {"date": row['date'], "count": row['daily_translations']} 
                for row in daily_rows
            ],
            "average_translation_days": round(avg_row['avg_translation_days'] or 0, 2),
            "average_review_days": round(avg_row['avg_review_days'] or 0, 2),
            "period_days": days
        }
    
    def _get_quality_metrics(self) -> Dict[str, Any]:
        """获取质量指标"""
        query = """
            SELECT 
                COUNT(CASE WHEN status = 'reviewed' THEN 1 END) as reviewed_count,
                COUNT(CASE WHEN status = 'needs_revision' THEN 1 END) as revision_count,
                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count,
                COUNT(CASE WHEN status IN ('translated', 'reviewed', 'approved', 'published') THEN 1 END) as passed_count,
                COUNT(*) as total_processed
            FROM core_translation_entries
            WHERE status NOT IN ('draft', 'pending')
        """
        
        row = self.entry_repo.execute_single(query)
        if not row or row['total_processed'] == 0:
            return {}
        
        total = row['total_processed']
        
        return {
            "first_pass_rate": round(row['reviewed_count'] / total * 100, 2),
            "revision_rate": round(row['revision_count'] / total * 100, 2),
            "rejection_rate": round(row['rejected_count'] / total * 100, 2),
            "overall_pass_rate": round(row['passed_count'] / total * 100, 2),
            "total_processed": total
        }
    
    def _get_workload_analysis(self, days: int) -> Dict[str, Any]:
        """获取工作负载分析"""
        query = """
            SELECT 
                operator_name,
                COUNT(*) as total_actions,
                COUNT(CASE WHEN to_state = 'translated' THEN 1 END) as translations,
                COUNT(CASE WHEN to_state = 'reviewed' THEN 1 END) as reviews,
                AVG(julianday('now') - julianday(created_at)) as avg_days_ago
            FROM translation_state_history
            WHERE created_at >= datetime('now', '-{} days')
            AND operator_name IS NOT NULL
            AND operator_name != 'system'
            GROUP BY operator_name
            ORDER BY total_actions DESC
        """.format(days)
        
        rows = self.entry_repo.execute_query(query)
        
        workload_data = []
        for row in rows:
            workload_data.append({
                "operator": row['operator_name'],
                "total_actions": row['total_actions'],
                "translations": row['translations'],
                "reviews": row['reviews'],
                "avg_days_ago": round(row['avg_days_ago'], 1)
            })
        
        return {
            "by_operator": workload_data,
            "period_days": days
        }
    
    def _get_bottleneck_analysis(self) -> Dict[str, Any]:
        """获取瓶颈分析"""
        # 查找停留时间最长的状态
        query = """
            SELECT 
                cte.status,
                ts.display_name,
                COUNT(*) as entry_count,
                AVG(julianday('now') - julianday(cte.updated_at)) as avg_days_in_state
            FROM core_translation_entries cte
            LEFT JOIN translation_states ts ON cte.status = ts.state_key
            WHERE cte.updated_at IS NOT NULL
            GROUP BY cte.status, ts.display_name
            HAVING avg_days_in_state > 1
            ORDER BY avg_days_in_state DESC
        """
        
        rows = self.entry_repo.execute_query(query)
        
        bottlenecks = []
        for row in rows:
            bottlenecks.append({
                "state": row['status'],
                "display_name": row['display_name'] or row['status'],
                "entry_count": row['entry_count'],
                "avg_days_in_state": round(row['avg_days_in_state'], 1)
            })
        
        return {
            "bottlenecks": bottlenecks,
            "recommendations": self._generate_bottleneck_recommendations(bottlenecks)
        }
    
    def _get_filtered_summary(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """获取过滤后的摘要"""
        # 这里简化处理，实际应该根据filters构建更复杂的查询
        return self._get_overview_stats()
    
    def _get_progress_by_language_file(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """按语言文件获取进度"""
        query = """
            SELECT 
                clf.uid,
                clf.locale,
                clf.rel_path,
                COUNT(cte.id) as total_entries,
                COUNT(CASE WHEN cte.status IN ('translated', 'reviewed', 'published') THEN 1 END) as completed_entries,
                ROUND(COUNT(CASE WHEN cte.status IN ('translated', 'reviewed', 'published') THEN 1 END) * 100.0 / COUNT(cte.id), 2) as completion_rate
            FROM core_language_files clf
            LEFT JOIN core_translation_entries cte ON clf.uid = cte.language_file_uid
            GROUP BY clf.uid, clf.locale, clf.rel_path
            ORDER BY completion_rate DESC
        """
        
        rows = self.entry_repo.execute_query(query)
        
        progress_data = []
        for row in rows:
            progress_data.append({
                "language_file_uid": row['uid'],
                "locale": row['locale'],
                "file_path": row['rel_path'],
                "total_entries": row['total_entries'],
                "completed_entries": row['completed_entries'],
                "completion_rate": row['completion_rate']
            })
        
        return progress_data
    
    def _get_progress_by_mod(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """按MOD获取进度"""
        query = """
            SELECT 
                clf.carrier_uid as mod_uid,
                clf.carrier_type,
                COUNT(cte.id) as total_entries,
                COUNT(CASE WHEN cte.status IN ('translated', 'reviewed', 'published') THEN 1 END) as completed_entries,
                ROUND(COUNT(CASE WHEN cte.status IN ('translated', 'reviewed', 'published') THEN 1 END) * 100.0 / COUNT(cte.id), 2) as completion_rate
            FROM core_language_files clf
            LEFT JOIN core_translation_entries cte ON clf.uid = cte.language_file_uid
            WHERE clf.carrier_type = 'mod'
            GROUP BY clf.carrier_uid, clf.carrier_type
            ORDER BY completion_rate DESC
        """
        
        rows = self.entry_repo.execute_query(query)
        
        mod_progress = []
        for row in rows:
            mod_progress.append({
                "mod_uid": row['mod_uid'],
                "carrier_type": row['carrier_type'],
                "total_entries": row['total_entries'],
                "completed_entries": row['completed_entries'],
                "completion_rate": row['completion_rate']
            })
        
        return mod_progress
    
    def _get_completion_timeline(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取完成时间线"""
        query = """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as completions
            FROM translation_state_history
            WHERE to_state IN ('translated', 'reviewed', 'published')
            AND created_at >= datetime('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """
        
        rows = self.entry_repo.execute_query(query)
        
        return [
            {"date": row['date'], "completions": row['completions']}
            for row in rows
        ]
    
    def _get_quality_distribution(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """获取质量分布"""
        return self._get_quality_metrics()
    
    def _generate_bottleneck_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """生成瓶颈建议"""
        recommendations = []
        
        for bottleneck in bottlenecks[:3]:  # 只处理前3个最严重的瓶颈
            state = bottleneck["state"]
            days = bottleneck["avg_days_in_state"]
            count = bottleneck["entry_count"]
            
            if state == "pending" and days > 7:
                recommendations.append(f"有{count}个条目在'待翻译'状态停留过久（平均{days:.1f}天），建议增加翻译人员或重新分配任务")
            elif state == "under_review" and days > 3:
                recommendations.append(f"有{count}个条目在'审核中'状态停留过久（平均{days:.1f}天），建议增加审核人员或简化审核流程")
            elif state == "translated" and days > 5:
                recommendations.append(f"有{count}个条目在'已翻译'状态停留过久（平均{days:.1f}天），建议启用自动提交审核")
        
        return recommendations
    
    def _get_throughput_analysis(self, days: int) -> Dict[str, Any]:
        """获取吞吐量分析"""
        # 这里简化实现，实际项目中需要更详细的分析
        return {"period_days": days, "analysis": "throughput_analysis_placeholder"}
    
    def _get_translator_performance(self, days: int) -> Dict[str, Any]:
        """获取翻译者绩效"""
        return {"period_days": days, "performance": "translator_performance_placeholder"}
    
    def _get_reviewer_performance(self, days: int) -> Dict[str, Any]:
        """获取审核者绩效"""
        return {"period_days": days, "performance": "reviewer_performance_placeholder"}
    
    def _get_transition_efficiency(self, days: int) -> Dict[str, Any]:
        """获取转换效率"""
        return {"period_days": days, "efficiency": "transition_efficiency_placeholder"}
    
    def _get_detailed_bottlenecks(self, days: int) -> Dict[str, Any]:
        """获取详细瓶颈分析"""
        return {"period_days": days, "bottlenecks": "detailed_bottlenecks_placeholder"}
    
    def _generate_performance_recommendations(self, days: int) -> List[str]:
        """生成绩效建议"""
        return ["performance_recommendations_placeholder"]
    
    def _get_quality_overview(self) -> Dict[str, Any]:
        """获取质量概览"""
        return self._get_quality_metrics()
    
    def _get_review_statistics(self) -> Dict[str, Any]:
        """获取审核统计"""
        return {"review_stats": "review_statistics_placeholder"}
    
    def _get_revision_analysis(self) -> Dict[str, Any]:
        """获取修订分析"""
        return {"revision_analysis": "revision_analysis_placeholder"}
    
    def _get_approval_rates(self) -> Dict[str, Any]:
        """获取批准率"""
        return {"approval_rates": "approval_rates_placeholder"}
    
    def _get_quality_trends(self, days: int) -> Dict[str, Any]:
        """获取质量趋势"""
        return {"period_days": days, "trends": "quality_trends_placeholder"}
    
    def _get_common_quality_issues(self) -> List[Dict[str, Any]]:
        """获取常见质量问题"""
        return [{"issue": "common_quality_issues_placeholder"}]
    
    def _get_team_workload(self, days: int) -> Dict[str, Any]:
        """获取团队工作负载"""
        return {"period_days": days, "workload": "team_workload_placeholder"}
    
    def _get_individual_workload(self, days: int) -> Dict[str, Any]:
        """获取个人工作负载"""
        return {"period_days": days, "workload": "individual_workload_placeholder"}
    
    def _get_capacity_analysis(self, days: int) -> Dict[str, Any]:
        """获取容量分析"""
        return {"period_days": days, "capacity": "capacity_analysis_placeholder"}
    
    def _get_assignment_distribution(self) -> Dict[str, Any]:
        """获取分配分布"""
        return {"distribution": "assignment_distribution_placeholder"}
    
    def _get_workload_balance(self, days: int) -> Dict[str, Any]:
        """获取工作负载平衡"""
        return {"period_days": days, "balance": "workload_balance_placeholder"}
    
    def _generate_workload_recommendations(self, days: int) -> List[str]:
        """生成工作负载建议"""
        return ["workload_recommendations_placeholder"]