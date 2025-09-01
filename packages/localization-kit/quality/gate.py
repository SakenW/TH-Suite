"""
质量门禁服务 - 协调和执行质量检查

管理验证器的注册、执行和结果汇总
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from .validators import (
    QualityValidator, ValidationResult, ValidationLevel,
    PlaceholderValidator, ColorCodeValidator, LengthRatioValidator,
    EmptyValueValidator, FormatValidator, LineBreakValidator
)
from ..database.schema import QualityCheckTable
from ..models import PatchItem, Blob

logger = logging.getLogger(__name__)


class QualityGate:
    """
    质量门禁
    
    负责：
    1. 管理验证器
    2. 执行质量检查
    3. 汇总结果
    4. 决定是否通过
    """
    
    def __init__(self, session: Optional[Session] = None):
        """
        初始化质量门禁
        
        Args:
            session: 数据库会话（可选）
        """
        self.session = session
        self.validators: Dict[str, QualityValidator] = {}
        
        # 注册默认验证器
        self._register_default_validators()
        
        # 配置
        self.config = {
            'fail_on_error': True,      # 错误时失败
            'fail_on_warning': False,   # 警告时失败
            'max_warnings': 10,         # 最大警告数
            'save_to_db': True,         # 保存到数据库
        }
    
    def _register_default_validators(self) -> None:
        """注册默认验证器"""
        default_validators = [
            PlaceholderValidator(),
            ColorCodeValidator(),
            LengthRatioValidator(),
            EmptyValueValidator(),
            FormatValidator(),
            LineBreakValidator(),
        ]
        
        for validator in default_validators:
            self.register_validator(validator)
        
        logger.info(f"注册了 {len(default_validators)} 个默认验证器")
    
    def register_validator(self, validator: QualityValidator) -> None:
        """
        注册验证器
        
        Args:
            validator: 验证器实例
        """
        self.validators[validator.name] = validator
        logger.debug(f"注册验证器: {validator.name}")
    
    def unregister_validator(self, name: str) -> None:
        """
        注销验证器
        
        Args:
            name: 验证器名称
        """
        if name in self.validators:
            del self.validators[name]
            logger.debug(f"注销验证器: {name}")
    
    def configure(self, **kwargs) -> None:
        """
        配置质量门禁
        
        Args:
            fail_on_error: 是否在错误时失败
            fail_on_warning: 是否在警告时失败
            max_warnings: 最大警告数
            save_to_db: 是否保存到数据库
        """
        self.config.update(kwargs)
    
    def validate_entry(
        self,
        key: str,
        source_value: str,
        target_value: str,
        validators: Optional[List[str]] = None,
        context: Optional[Dict] = None
    ) -> Tuple[bool, List[ValidationResult]]:
        """
        验证单个条目
        
        Args:
            key: 翻译键
            source_value: 源值
            target_value: 目标值
            validators: 要使用的验证器列表（None 表示全部）
            context: 上下文信息
            
        Returns:
            (是否通过, 验证结果列表)
        """
        results = []
        
        # 选择验证器
        if validators:
            selected_validators = [
                self.validators[name] 
                for name in validators 
                if name in self.validators
            ]
        else:
            selected_validators = list(self.validators.values())
        
        # 执行验证
        for validator in selected_validators:
            try:
                result = validator.validate(key, source_value, target_value, context)
                results.append(result)
            except Exception as e:
                logger.error(f"验证器 {validator.name} 执行失败: {e}")
                results.append(ValidationResult(
                    validator=validator.name,
                    passed=False,
                    level=ValidationLevel.ERROR,
                    message=f"验证器执行失败: {str(e)}",
                    details={'key': key, 'error': str(e)}
                ))
        
        # 判断是否通过
        passed = self._evaluate_results(results)
        
        # 保存到数据库
        if self.session and self.config['save_to_db']:
            self._save_results(key, results)
        
        return passed, results
    
    def validate_batch(
        self,
        entries: Dict[str, str],
        source_entries: Optional[Dict[str, str]] = None,
        validators: Optional[List[str]] = None,
        context: Optional[Dict] = None
    ) -> Tuple[bool, Dict[str, List[ValidationResult]]]:
        """
        批量验证
        
        Args:
            entries: 目标翻译条目
            source_entries: 源翻译条目
            validators: 要使用的验证器列表
            context: 上下文信息
            
        Returns:
            (是否全部通过, {key: 验证结果列表})
        """
        all_results = {}
        all_passed = True
        
        for key, target_value in entries.items():
            source_value = source_entries.get(key, "") if source_entries else ""
            passed, results = self.validate_entry(
                key, source_value, target_value, validators, context
            )
            
            all_results[key] = results
            if not passed:
                all_passed = False
        
        return all_passed, all_results
    
    def validate_patch_item(
        self,
        patch_item: PatchItem,
        source_blob: Optional[Blob] = None
    ) -> Tuple[bool, List[ValidationResult]]:
        """
        验证补丁项
        
        Args:
            patch_item: 补丁项
            source_blob: 源内容 Blob
            
        Returns:
            (是否通过, 验证结果列表)
        """
        # 获取源内容
        source_entries = {}
        if source_blob:
            source_blob.load_entries()
            source_entries = source_blob.entries
        
        # 验证补丁内容
        all_results = []
        all_passed = True
        
        for key, target_value in patch_item.content.items():
            source_value = source_entries.get(key, "")
            passed, results = self.validate_entry(
                key, source_value, target_value,
                context={'patch_item_id': patch_item.patch_item_id}
            )
            
            all_results.extend(results)
            if not passed:
                all_passed = False
        
        return all_passed, all_results
    
    def _evaluate_results(self, results: List[ValidationResult]) -> bool:
        """评估验证结果是否通过"""
        error_count = 0
        warning_count = 0
        
        for result in results:
            if not result.passed:
                if result.level == ValidationLevel.ERROR:
                    error_count += 1
                elif result.level == ValidationLevel.WARNING:
                    warning_count += 1
        
        # 根据配置判断
        if self.config['fail_on_error'] and error_count > 0:
            return False
        
        if self.config['fail_on_warning'] and warning_count > 0:
            return False
        
        if warning_count > self.config['max_warnings']:
            return False
        
        return True
    
    def _save_results(self, entry_key: str, results: List[ValidationResult]) -> None:
        """保存验证结果到数据库"""
        if not self.session:
            return
        
        for result in results:
            if not result.passed:  # 只保存失败的结果
                check = QualityCheckTable(
                    check_id=str(uuid.uuid4()),
                    entry_key=entry_key,
                    check_type=result.validator,
                    status='failed' if result.level == ValidationLevel.ERROR else 'warning',
                    details={
                        'message': result.message,
                        'level': result.level.value,
                        **result.details
                    },
                    checked_at=datetime.now()
                )
                self.session.add(check)
        
        try:
            self.session.commit()
        except Exception as e:
            logger.error(f"保存质量检查结果失败: {e}")
            self.session.rollback()
    
    def get_statistics(self) -> Dict[str, any]:
        """获取质量检查统计"""
        stats = {
            'validators': list(self.validators.keys()),
            'validator_count': len(self.validators),
            'config': self.config.copy()
        }
        
        if self.session:
            # 从数据库获取统计
            from sqlalchemy import func
            
            total_checks = self.session.query(
                func.count(QualityCheckTable.check_id)
            ).scalar() or 0
            
            failed_checks = self.session.query(
                func.count(QualityCheckTable.check_id)
            ).filter_by(status='failed').scalar() or 0
            
            warning_checks = self.session.query(
                func.count(QualityCheckTable.check_id)
            ).filter_by(status='warning').scalar() or 0
            
            stats.update({
                'total_checks': total_checks,
                'failed_checks': failed_checks,
                'warning_checks': warning_checks,
                'failure_rate': failed_checks / total_checks if total_checks > 0 else 0
            })
        
        return stats
    
    def generate_report(
        self,
        results: Dict[str, List[ValidationResult]]
    ) -> Dict[str, any]:
        """
        生成质量报告
        
        Args:
            results: 验证结果字典
            
        Returns:
            质量报告
        """
        total_entries = len(results)
        passed_entries = 0
        failed_entries = 0
        
        error_count = 0
        warning_count = 0
        info_count = 0
        
        validator_stats = {}
        failed_keys = []
        
        for key, entry_results in results.items():
            entry_passed = True
            
            for result in entry_results:
                # 统计验证器
                if result.validator not in validator_stats:
                    validator_stats[result.validator] = {
                        'total': 0,
                        'passed': 0,
                        'failed': 0
                    }
                
                validator_stats[result.validator]['total'] += 1
                
                if result.passed:
                    validator_stats[result.validator]['passed'] += 1
                    if result.level == ValidationLevel.INFO:
                        info_count += 1
                else:
                    validator_stats[result.validator]['failed'] += 1
                    entry_passed = False
                    
                    if result.level == ValidationLevel.ERROR:
                        error_count += 1
                    elif result.level == ValidationLevel.WARNING:
                        warning_count += 1
            
            if entry_passed:
                passed_entries += 1
            else:
                failed_entries += 1
                failed_keys.append(key)
        
        report = {
            'summary': {
                'total_entries': total_entries,
                'passed_entries': passed_entries,
                'failed_entries': failed_entries,
                'pass_rate': passed_entries / total_entries if total_entries > 0 else 0,
                'error_count': error_count,
                'warning_count': warning_count,
                'info_count': info_count
            },
            'validator_stats': validator_stats,
            'failed_keys': failed_keys[:10],  # 只显示前10个失败的键
            'timestamp': datetime.now().isoformat()
        }
        
        return report