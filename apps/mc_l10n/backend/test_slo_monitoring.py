#!/usr/bin/env python
"""
测试SLO性能监控系统
验证SLO监控、评估、告警等功能
"""

import sys
import os
import time
import asyncio
import random
from typing import List, Dict, Any

sys.path.append('.')

import structlog

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger(__name__)

async def test_slo_data_collection():
    """测试SLO数据收集"""
    print("=== 测试SLO数据收集 ===")
    
    try:
        from services.slo_monitoring import SLODataCollector
        
        collector = SLODataCollector(max_data_points=1000)
        print("✓ SLO数据收集器初始化成功")
        
        # 记录一些测试指标
        test_metrics = [
            ("api_latency", 45.5, {"endpoint": "/translations", "method": "GET"}),
            ("api_latency", 67.8, {"endpoint": "/translations", "method": "POST"}),
            ("api_latency", 123.4, {"endpoint": "/packs", "method": "GET"}),
            ("error_rate", 0.5, {"service": "translation_api"}),
            ("error_rate", 1.2, {"service": "sync_service"}),
            ("availability", 99.95, {"service": "translation_api"}),
            ("throughput", 1500.0, {"service": "translation_api"}),
        ]
        
        start_time = time.time()
        
        for slo_name, value, labels in test_metrics:
            await collector.record_metric(
                slo_name=slo_name,
                value=value,
                labels=labels,
                metadata={"test": "true"}
            )
            await asyncio.sleep(0.1)  # 模拟时间间隔
        
        print(f"✓ 记录了 {len(test_metrics)} 个指标数据")
        
        # 查询数据
        api_latency_metrics = await collector.get_metrics("api_latency")
        if len(api_latency_metrics) == 3:
            print("✓ API延迟数据查询成功")
        else:
            print(f"✗ API延迟数据查询失败: 期望3个，实际{len(api_latency_metrics)}个")
            return False
        
        # 时间范围查询
        recent_metrics = await collector.get_metrics(
            "api_latency",
            start_time=start_time,
            limit=2
        )
        
        if len(recent_metrics) == 2:
            print("✓ 时间范围和限制查询成功")
        else:
            print(f"✗ 时间范围查询失败: 期望2个，实际{len(recent_metrics)}个")
            return False
        
        # 测试数据清理
        await collector.cleanup_old_data(retention_seconds=0)  # 清理所有数据
        
        empty_metrics = await collector.get_metrics("api_latency")
        if len(empty_metrics) == 0:
            print("✓ 数据清理功能正常")
        else:
            print(f"✗ 数据清理失败: 期望0个，实际{len(empty_metrics)}个")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ SLO数据收集测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_slo_evaluation():
    """测试SLO评估"""
    print("\n=== 测试SLO评估 ===")
    
    try:
        from services.slo_monitoring import (
            SLODataCollector, SLOEvaluator, SLOTarget, SLOType, SLOStatus
        )
        
        # 创建收集器和评估器
        collector = SLODataCollector()
        evaluator = SLOEvaluator(collector)
        
        print("✓ SLO评估器初始化成功")
        
        # 创建API延迟SLO目标
        latency_target = SLOTarget(
            name="test_api_latency",
            slo_type=SLOType.LATENCY,
            target_value=100.0,  # 目标值100ms
            threshold_warning=80.0,  # 警告阈值80ms
            threshold_critical=50.0,  # 严重阈值50ms
            measurement_window_seconds=60,  # 1分钟窗口
            evaluation_interval_seconds=30,  # 30秒评估
            aggregation_method="p95"
        )
        
        # 创建可用性SLO目标
        availability_target = SLOTarget(
            name="test_availability",
            slo_type=SLOType.AVAILABILITY,
            target_value=99.9,  # 目标99.9%
            threshold_warning=99.5,  # 警告99.5%
            threshold_critical=99.0,  # 严重99.0%
            measurement_window_seconds=300,  # 5分钟窗口
            evaluation_interval_seconds=60,
            aggregation_method="average"
        )
        
        # 模拟收集延迟数据（健康状态）
        healthy_latencies = [25, 32, 28, 41, 33, 35, 29, 47, 31, 38]  # 都小于50ms，应该是HEALTHY
        for latency in healthy_latencies:
            await collector.record_metric("test_api_latency", latency)
            await asyncio.sleep(0.05)
        
        # 评估延迟SLO（应该是健康）
        latency_evaluation = await evaluator.evaluate_slo(latency_target)
        
        if latency_evaluation.status == SLOStatus.HEALTHY:
            print("✓ 延迟SLO健康状态评估正确")
        else:
            print(f"✗ 延迟SLO健康状态评估失败: {latency_evaluation.status}")
            return False
        
        print(f"  P95延迟: {latency_evaluation.current_value:.1f}ms")
        print(f"  样本数: {latency_evaluation.sample_count}")
        
        # 模拟收集延迟数据（警告状态）  
        warning_latencies = [55, 62, 58, 75, 68, 71, 64, 77, 66, 69]  # 在50-80ms之间，应该是WARNING
        for latency in warning_latencies:
            await collector.record_metric("test_api_latency", latency)
            await asyncio.sleep(0.05)
        
        # 重新评估延迟SLO（应该是警告）
        latency_evaluation_warning = await evaluator.evaluate_slo(latency_target)
        
        if latency_evaluation_warning.status == SLOStatus.WARNING:
            print("✓ 延迟SLO警告状态评估正确")
        else:
            print(f"✗ 延迟SLO警告状态评估失败: {latency_evaluation_warning.status}")
            return False
        
        # 模拟可用性数据
        availability_data = [99.95, 99.92, 99.98, 99.94, 99.96]  # 高可用性
        for availability in availability_data:
            await collector.record_metric("test_availability", availability)
            await asyncio.sleep(0.1)
        
        # 评估可用性SLO
        availability_evaluation = await evaluator.evaluate_slo(availability_target)
        
        if availability_evaluation.status == SLOStatus.HEALTHY:
            print("✓ 可用性SLO健康状态评估正确")
        else:
            print(f"✗ 可用性SLO评估失败: {availability_evaluation.status}")
            return False
        
        print(f"  平均可用性: {availability_evaluation.current_value:.2f}%")
        print(f"  错误预算剩余: {availability_evaluation.error_budget_remaining:.1%}")
        
        return True
        
    except Exception as e:
        print(f"✗ SLO评估测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_slo_alerting():
    """测试SLO告警"""
    print("\n=== 测试SLO告警 ===")
    
    try:
        from services.slo_monitoring import (
            SLOAlertManager, SLOEvaluation, SLOTarget, SLOType, SLOStatus, AlertSeverity
        )
        
        alert_manager = SLOAlertManager()
        print("✓ SLO告警管理器初始化成功")
        
        # 创建告警处理器
        received_alerts = []
        
        def alert_handler(alert):
            received_alerts.append(alert)
            print(f"  📢 告警触发: {alert.message}")
        
        alert_manager.add_alert_handler(alert_handler)
        
        # 创建测试SLO目标
        target = SLOTarget(
            name="test_error_rate",
            slo_type=SLOType.ERROR_RATE,
            target_value=1.0,  # 目标错误率1%
            threshold_warning=0.5,  # 警告0.5%
            threshold_critical=0.1,  # 严重0.1%
            measurement_window_seconds=300,
            evaluation_interval_seconds=60,
            aggregation_method="average"
        )
        
        # 模拟健康评估（无告警）
        healthy_evaluation = SLOEvaluation(
            slo_name="test_error_rate",
            timestamp=time.time(),
            status=SLOStatus.HEALTHY,
            current_value=0.05,  # 0.05%错误率
            target_value=1.0,
            error_budget_remaining=0.95,
            sample_count=100,
            evaluation_window_seconds=300
        )
        
        await alert_manager.process_evaluation(healthy_evaluation, target)
        
        if len(received_alerts) == 0:
            print("✓ 健康状态无告警")
        else:
            print(f"✗ 健康状态不应该有告警，实际收到{len(received_alerts)}个")
            return False
        
        # 模拟警告评估
        warning_evaluation = SLOEvaluation(
            slo_name="test_error_rate",
            timestamp=time.time(),
            status=SLOStatus.WARNING,
            current_value=0.7,  # 0.7%错误率
            target_value=1.0,
            error_budget_remaining=0.3,
            sample_count=100,
            evaluation_window_seconds=300
        )
        
        await alert_manager.process_evaluation(warning_evaluation, target)
        
        if len(received_alerts) == 1 and received_alerts[0].severity == AlertSeverity.WARNING:
            print("✓ 警告状态告警触发正确")
        else:
            print(f"✗ 警告状态告警触发失败")
            return False
        
        # 模拟严重评估
        critical_evaluation = SLOEvaluation(
            slo_name="test_error_rate",
            timestamp=time.time(),
            status=SLOStatus.CRITICAL,
            current_value=0.8,  # 0.8%错误率
            target_value=1.0,
            error_budget_remaining=0.2,
            sample_count=100,
            evaluation_window_seconds=300
        )
        
        await alert_manager.process_evaluation(critical_evaluation, target)
        
        if len(received_alerts) == 2 and received_alerts[1].severity == AlertSeverity.ERROR:
            print("✓ 严重状态告警触发正确")
        else:
            print(f"✗ 严重状态告警触发失败")
            return False
        
        # 模拟违反评估
        breach_evaluation = SLOEvaluation(
            slo_name="test_error_rate",
            timestamp=time.time(),
            status=SLOStatus.BREACH,
            current_value=1.5,  # 1.5%错误率，超过目标
            target_value=1.0,
            error_budget_remaining=0.0,
            sample_count=100,
            evaluation_window_seconds=300
        )
        
        await alert_manager.process_evaluation(breach_evaluation, target)
        
        if len(received_alerts) == 3 and received_alerts[2].severity == AlertSeverity.CRITICAL:
            print("✓ 违反状态告警触发正确")
        else:
            print(f"✗ 违反状态告警触发失败")
            return False
        
        # 检查活跃告警
        active_alerts = alert_manager.get_active_alerts()
        if len(active_alerts) > 0:
            print(f"✓ 活跃告警: {len(active_alerts)} 个")
        else:
            print("✗ 应该有活跃告警")
            return False
        
        # 模拟恢复（回到健康状态）
        recovered_evaluation = SLOEvaluation(
            slo_name="test_error_rate",
            timestamp=time.time(),
            status=SLOStatus.HEALTHY,
            current_value=0.05,  # 0.05%错误率
            target_value=1.0,
            error_budget_remaining=0.95,
            sample_count=100,
            evaluation_window_seconds=300
        )
        
        await alert_manager.process_evaluation(recovered_evaluation, target)
        
        # 检查告警是否已解除
        final_active_alerts = alert_manager.get_active_alerts()
        if len(final_active_alerts) == 0:
            print("✓ 告警已自动解除")
        else:
            print(f"✗ 告警未正确解除，仍有{len(final_active_alerts)}个活跃告警")
            return False
        
        # 检查告警历史
        alert_history = alert_manager.get_alert_history()
        if len(alert_history) == 3:
            print("✓ 告警历史记录正确")
        else:
            print(f"✗ 告警历史记录异常: 期望3个，实际{len(alert_history)}个")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ SLO告警测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_slo_monitoring_service():
    """测试SLO监控服务集成"""
    print("\n=== 测试SLO监控服务 ===")
    
    try:
        from services.slo_monitoring import (
            SLOMonitoringService, 
            create_api_latency_slo,
            create_availability_slo,
            create_error_rate_slo
        )
        
        # 创建监控服务
        service = SLOMonitoringService()
        print("✓ SLO监控服务初始化成功")
        
        # 添加SLO目标
        latency_slo = create_api_latency_slo("test_api_latency", 100.0, 80.0, 50.0)
        availability_slo = create_availability_slo("test_availability", 99.9, 99.5, 99.0)
        error_rate_slo = create_error_rate_slo("test_error_rate", 1.0, 0.5, 0.1)
        
        service.add_slo_target(latency_slo)
        service.add_slo_target(availability_slo)
        service.add_slo_target(error_rate_slo)
        
        print("✓ SLO目标已添加")
        
        # 启动监控服务
        await service.start()
        print("✓ SLO监控服务已启动")
        
        # 模拟指标数据记录
        await service.record_metric("test_api_latency", 45.5)
        await service.record_metric("test_api_latency", 67.8)
        await service.record_metric("test_api_latency", 52.3)
        
        await service.record_metric("test_availability", 99.95)
        await service.record_metric("test_availability", 99.92)
        
        await service.record_metric("test_error_rate", 0.3)
        await service.record_metric("test_error_rate", 0.7)  # 触发警告
        
        print("✓ 指标数据已记录")
        
        # 等待评估周期
        await asyncio.sleep(2)
        
        # 获取评估结果
        evaluations = await service.get_all_evaluations()
        
        if len(evaluations) == 3:
            print("✓ 所有SLO评估完成")
            
            for evaluation in evaluations:
                print(f"  {evaluation.slo_name}: {evaluation.status.value} "
                      f"(当前值: {evaluation.current_value:.2f}, "
                      f"目标值: {evaluation.target_value:.2f})")
        else:
            print(f"✗ SLO评估数量不正确: 期望3个，实际{len(evaluations)}个")
            return False
        
        # 获取仪表板数据
        dashboard_data = service.get_dashboard_data()
        
        if dashboard_data["summary"]["total_slos"] == 3:
            print("✓ 仪表板数据正确")
            print(f"  总SLO数: {dashboard_data['summary']['total_slos']}")
            print(f"  启用SLO数: {dashboard_data['summary']['enabled_slos']}")
            print(f"  活跃告警数: {dashboard_data['summary']['active_alerts']}")
        else:
            print("✗ 仪表板数据异常")
            return False
        
        # 停止监控服务
        await service.stop()
        print("✓ SLO监控服务已停止")
        
        return True
        
    except Exception as e:
        print(f"✗ SLO监控服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_slo_performance():
    """测试SLO性能"""
    print("\n=== 测试SLO性能 ===")
    
    try:
        from services.slo_monitoring import SLOMonitoringService, create_api_latency_slo
        
        service = SLOMonitoringService()
        
        # 创建SLO目标
        latency_slo = create_api_latency_slo("perf_test_latency")
        service.add_slo_target(latency_slo)
        
        # 大量数据写入性能测试
        start_time = time.time()
        
        metric_count = 10000
        for i in range(metric_count):
            latency = random.uniform(20, 200)  # 20-200ms随机延迟
            await service.record_metric("perf_test_latency", latency)
            
            if i % 1000 == 0:
                print(f"  已记录 {i} 个指标...")
        
        write_time = time.time() - start_time
        
        print(f"✓ 写入性能测试完成:")
        print(f"  指标数量: {metric_count}")
        print(f"  总耗时: {write_time:.2f} 秒")
        print(f"  写入速率: {metric_count/write_time:.0f} 指标/秒")
        
        # 评估性能测试
        start_time = time.time()
        
        evaluation_count = 100
        for i in range(evaluation_count):
            evaluation = await service.get_slo_evaluation("perf_test_latency")
            if evaluation and evaluation.sample_count > 0:
                continue
        
        eval_time = time.time() - start_time
        
        print(f"✓ 评估性能测试完成:")
        print(f"  评估次数: {evaluation_count}")
        print(f"  总耗时: {eval_time:.2f} 秒")
        print(f"  评估速率: {evaluation_count/eval_time:.0f} 评估/秒")
        
        # 最终评估结果
        final_evaluation = await service.get_slo_evaluation("perf_test_latency")
        if final_evaluation:
            print(f"✓ 最终评估结果:")
            print(f"  样本数量: {final_evaluation.sample_count}")
            print(f"  P95延迟: {final_evaluation.current_value:.1f}ms")
            print(f"  状态: {final_evaluation.status.value}")
            print(f"  错误预算: {final_evaluation.error_budget_remaining:.1%}")
        
        return True
        
    except Exception as e:
        print(f"✗ SLO性能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行所有SLO监控测试"""
    print("🚀 开始SLO性能监控测试")
    print("=" * 60)
    
    tests = [
        test_slo_data_collection,
        test_slo_evaluation,
        test_slo_alerting,
        test_slo_monitoring_service,
        test_slo_performance
    ]
    
    passed = 0
    total = len(tests)
    
    for i, test in enumerate(tests):
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"🏁 SLO性能监控测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有SLO监控测试通过!")
        return 0
    else:
        print("❌ 部分测试失败，需要检查实现")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))