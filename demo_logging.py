#!/usr/bin/env python3
"""
Trans-Hub 日志系统演示

展示 Core Platform 集成的 structlog + rich 日志系统的美观输出效果
"""

import asyncio

from packages.core.platform import CorePlatform


async def main():
    """日志系统演示"""
    print("🚀 Trans-Hub 日志系统演示")
    print("=" * 50)

    # 1. 创建并初始化平台
    platform = CorePlatform("demo-app")

    try:
        # 初始化平台
        await platform.initialize()

        # 2. 基本日志记录
        logger = platform.logger
        logger.info("平台初始化完成", version="1.0.0", mode="演示")

        # 3. 不同级别的日志
        logger.debug("调试信息", component="demo", debug_mode=True)
        logger.info("用户操作", action="登录", user_id=123, username="demo_user")
        logger.warning("性能警告", response_time=1500, threshold=1000, unit="ms")
        logger.error("业务错误", error_code="E001", error_msg="用户未找到", user_id=999)

        # 4. 带异常的日志
        try:
            raise ValueError("这是一个演示异常")
        except ValueError as e:
            logger.error("捕获到异常", exception=e, operation="demo_error")

        # 5. 结构化上下文日志
        contextual_logger = logger.bind(
            session_id="abc-123", request_id="req-456", component="auth_service"
        )
        contextual_logger.info(
            "用户认证成功",
            user_id=123,
            role="admin",
            login_method="password",
            ip_address="192.168.1.100",
        )

        # 6. 复杂数据结构
        user_profile = {
            "id": 123,
            "username": "demo_user",
            "email": "demo@example.com",
            "roles": ["admin", "user"],
            "preferences": {
                "theme": "dark",
                "language": "zh-CN",
                "notifications": True,
            },
            "last_login": "2025-08-30T10:30:00Z",
        }

        logger.info(
            "用户资料更新",
            user_profile=user_profile,
            operation="profile_update",
            changes_count=3,
        )

        # 7. 长文本处理演示
        long_description = """
        这是一个很长的描述文本，用来演示 Trans-Hub 日志系统如何优雅地处理长文本内容。
        系统会自动折行显示，并且去掉引号以提供更好的阅读体验。
        这个功能对于记录用户输入、API响应或者错误详情非常有用。

        支持多行文本、中文字符和特殊符号！✨
        """

        logger.info(
            "长文本日志演示",
            description=long_description.strip(),
            text_length=len(long_description),
            encoding="UTF-8",
        )

        # 8. 任务执行日志
        task_logger = logger.bind(task_id="task-789", task_type="file_processing")
        task_logger.info("任务开始执行", file_count=1500, estimated_duration="5分钟")

        # 模拟一些处理时间
        await asyncio.sleep(0.1)

        task_logger.info(
            "任务进度更新",
            progress=45,
            processed=675,
            remaining=825,
            rate="135 files/sec",
        )

        await asyncio.sleep(0.1)

        task_logger.info(
            "任务完成",
            total_processed=1500,
            success_count=1485,
            error_count=15,
            duration="4分32秒",
            status="success",
        )

        # 9. 系统监控日志
        system_logger = logger.bind(component="system_monitor")
        system_logger.warning(
            "系统资源警告",
            cpu_usage=85.5,
            memory_usage=78.2,
            disk_usage=92.1,
            threshold=80.0,
            recommendation="清理临时文件",
        )

        # 10. API调用日志
        api_logger = logger.bind(component="api_client", service="trans_hub")
        api_logger.info(
            "API调用成功",
            endpoint="/api/v1/translate",
            method="POST",
            status_code=200,
            response_time=245,
            request_size=1024,
            response_size=2048,
            cache_hit=False,
        )

        logger.info(
            "日志演示完成",
            demo_items=10,
            status="success",
            result="Trans-Hub 日志系统运行完美！🎉",
        )

    finally:
        # 关闭平台
        await platform.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
