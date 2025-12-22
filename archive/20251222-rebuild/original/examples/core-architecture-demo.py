"""
底层架构使用示例
展示如何使用新的Core Platform组件
"""

import asyncio
from datetime import datetime

from packages.core.framework import (
    CacheManager,
    CacheStrategy,
    ConfigManager,
    ContainerBuilder,
    Entity,
    Event,
    EventBus,
    Logger,
    TaskManager,
    UnitOfWork,
    ValueObject,
    cached,
    event_handler,
    get_logger,
    task,
    unit_of_work,
)


# 定义领域模型
class User(Entity):
    """用户实体"""

    def __init__(self, id: int, name: str, email: str):
        super().__init__(id)
        self.name = name
        self.email = email
        self.created_at = datetime.now()


class Email(ValueObject):
    """邮箱值对象"""

    def __init__(self, address: str):
        if "@" not in address:
            raise ValueError("Invalid email address")
        self.address = address


# 定义事件
class UserCreatedEvent(Event):
    """用户创建事件"""

    def __init__(self, user: User):
        super().__init__()
        self.user = user


class UserUpdatedEvent(Event):
    """用户更新事件"""

    def __init__(self, user: User, old_name: str):
        super().__init__()
        self.user = user
        self.old_name = old_name


# 定义事件处理器
@event_handler(UserCreatedEvent)
async def on_user_created(event: UserCreatedEvent):
    """用户创建事件处理器"""
    logger = get_logger(__name__)
    logger.info(f"New user created: {event.user.name} ({event.user.email})")

    # 发送欢迎邮件
    await send_welcome_email(event.user)


@event_handler(UserUpdatedEvent)
async def on_user_updated(event: UserUpdatedEvent):
    """用户更新事件处理器"""
    logger = get_logger(__name__)
    logger.info(f"User updated: {event.old_name} -> {event.user.name}")


# 定义服务
class UserService:
    """用户服务"""

    def __init__(self, event_bus: EventBus, cache_manager: CacheManager):
        self.event_bus = event_bus
        self.cache_manager = cache_manager
        self.logger = get_logger(__name__)

    @cached(key_prefix="user:", expiration=300)  # 缓存5分钟
    async def get_user(self, user_id: int) -> User | None:
        """获取用户（带缓存）"""
        self.logger.info(f"Getting user {user_id}")

        # 模拟数据库查询
        await asyncio.sleep(0.1)  # 模拟IO延迟

        # 这里应该从数据库查询
        if user_id == 1:
            return User(1, "Alice", "alice@example.com")
        elif user_id == 2:
            return User(2, "Bob", "bob@example.com")

        return None

    @unit_of_work
    async def create_user(
        self, name: str, email: str, unit_of_work: UnitOfWork
    ) -> User:
        """创建用户"""
        self.logger.info(f"Creating user: {name}")

        # 验证邮箱
        Email(email)  # 如果无效会抛出异常

        # 创建用户
        user = User(
            id=int(datetime.now().timestamp()),  # 简化ID生成
            name=name,
            email=email,
        )

        # 保存到数据库（通过工作单元）
        # repository = unit_of_work.repositories.get('user_repository')
        # repository.add(user)

        # 发布事件
        await self.event_bus.publish(UserCreatedEvent(user))

        # 清除相关缓存
        self.cache_manager.delete(f"user:{user.id}")

        return user

    @unit_of_work
    async def update_user_name(
        self, user_id: int, new_name: str, unit_of_work: UnitOfWork
    ) -> bool:
        """更新用户名"""
        user = await self.get_user(user_id)
        if not user:
            return False

        old_name = user.name
        user.name = new_name

        # 更新数据库
        # repository = unit_of_work.repositories.get('user_repository')
        # repository.update(user)

        # 发布事件
        await self.event_bus.publish(UserUpdatedEvent(user, old_name))

        # 清除缓存
        self.cache_manager.delete(f"user:{user_id}")

        return True


# 辅助函数
async def send_welcome_email(user: User):
    """发送欢迎邮件"""
    logger = get_logger(__name__)
    logger.info(f"Sending welcome email to {user.email}")
    await asyncio.sleep(0.5)  # 模拟发送邮件


# 任务示例
@task(name="Generate Report", priority=2)
async def generate_report():
    """生成报告任务"""
    logger = get_logger(__name__)
    logger.info("Starting report generation...")

    # 模拟耗时操作
    await asyncio.sleep(2)

    logger.info("Report generated successfully")
    return {"status": "completed", "records": 100}


async def main():
    """主函数"""
    # 1. 创建并配置依赖注入容器
    builder = ContainerBuilder()

    # 注册服务
    builder.register_singleton(EventBus, EventBus)
    builder.register_singleton(ConfigManager, ConfigManager)
    builder.register_singleton(Logger, Logger)
    builder.register_singleton(CacheManager, CacheManager)
    builder.register_singleton(TaskManager, TaskManager)
    builder.register_scoped(UserService, UserService)

    container = builder.build()

    # 2. 启动任务管理器
    task_manager = container.get_service(TaskManager)
    await task_manager.start()

    try:
        # 3. 获取服务
        user_service = container.get_service(UserService)
        container.get_service(EventBus)
        logger = container.get_service(Logger)

        logger.info("=== Core Architecture Demo ===")

        # 4. 创建用户
        logger.info("\n1. Creating user...")
        user = await user_service.create_user("Charlie", "charlie@example.com")
        logger.info(f"User created: {user.name}")

        # 5. 获取用户（使用缓存）
        logger.info("\n2. Getting user (first call)...")
        user1 = await user_service.get_user(1)
        logger.info(f"User: {user1.name if user1 else 'Not found'}")

        logger.info("\n3. Getting user (second call - from cache)...")
        user2 = await user_service.get_user(1)
        logger.info(f"User: {user2.name if user2 else 'Not found'}")

        # 6. 更新用户
        logger.info("\n4. Updating user...")
        success = await user_service.update_user_name(1, "Alice Smith")
        logger.info(f"Update {'succeeded' if success else 'failed'}")

        # 7. 提交任务
        logger.info("\n5. Submitting task...")
        task_id = task_manager.submit("Generate Report", generate_report)
        logger.info(f"Task submitted with ID: {task_id}")

        # 8. 等待任务完成
        logger.info("\n6. Waiting for task to complete...")
        while True:
            task = task_manager.get_task(task_id)
            if task and task.status.name in ["COMPLETED", "FAILED", "CANCELLED"]:
                logger.info(f"Task completed with status: {task.status.name}")
                if task.result and task.result.success:
                    logger.info(f"Task result: {task.result.value}")
                break
            await asyncio.sleep(0.5)

        # 9. 显示统计信息
        logger.info("\n7. System Statistics:")
        cache_stats = (
            container.get_service(CacheManager)
            .get_provider(CacheStrategy.MEMORY)
            .get_stats()
        )
        logger.info(f"Cache stats: {cache_stats}")

        task_stats = task_manager.get_stats()
        logger.info(f"Task stats: {task_stats}")

    finally:
        # 清理
        await task_manager.stop()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
