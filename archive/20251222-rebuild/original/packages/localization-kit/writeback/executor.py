"""
回写执行器 - 协调和执行回写操作

管理补丁的应用、验证和回滚
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..database.schema import (
    ApplyResultTable,
    ApplyRunTable,
    ArtifactTable,
    ContainerTable,
    WritebackPlanTable,
)
from ..models import PatchItem, PatchPolicy
from ..services.patch_service import PatchService
from .strategy import (
    DirectoryWriteStrategy,
    JarModifyStrategy,
    OverlayStrategy,
    WritebackResult,
    WritebackStrategy,
)

logger = logging.getLogger(__name__)


class WritebackExecutor:
    """
    回写执行器

    负责：
    1. 创建回写计划
    2. 选择合适的策略
    3. 执行补丁应用
    4. 验证结果
    5. 处理回滚
    """

    def __init__(
        self,
        session: Session,
        resource_pack_dir: Path | None = None,
        backup_dir: Path | None = None,
    ):
        """
        初始化回写执行器

        Args:
            session: 数据库会话
            resource_pack_dir: 资源包输出目录
            backup_dir: 备份目录
        """
        self.session = session
        self.patch_service = PatchService(session)

        # 默认目录
        if not resource_pack_dir:
            resource_pack_dir = Path("resourcepacks")
        if not backup_dir:
            backup_dir = Path("backups")

        # 初始化策略
        self.strategies: dict[str, WritebackStrategy] = {
            "overlay": OverlayStrategy(resource_pack_dir),
            "jar_modify": JarModifyStrategy(backup_dir),
            "directory": DirectoryWriteStrategy(),
        }

        # 当前执行状态
        self.current_run: ApplyRunTable | None = None
        self.results: list[WritebackResult] = []

    def create_writeback_plan(self, patch_set_id: str) -> str:
        """
        创建回写计划

        Args:
            patch_set_id: 补丁集 ID

        Returns:
            计划 ID
        """
        # 获取补丁集
        patch_set = self.patch_service.get_patch_set(patch_set_id)
        if not patch_set:
            raise ValueError(f"补丁集不存在: {patch_set_id}")

        # 创建计划
        plan_id = str(uuid.uuid4())
        plan = WritebackPlanTable(
            plan_id=plan_id,
            patch_set_id=patch_set_id,
            created_at=datetime.now(),
            status="pending",
            metadata={
                "patch_item_count": len(patch_set.patch_items),
                "affected_containers": patch_set.get_affected_containers(),
                "affected_locales": patch_set.get_affected_locales(),
            },
        )

        self.session.add(plan)
        self.session.commit()

        logger.info(f"创建回写计划: {plan_id} ({len(patch_set.patch_items)} 个补丁项)")
        return plan_id

    def execute_plan(
        self, plan_id: str, dry_run: bool = False, force: bool = False
    ) -> tuple[bool, list[WritebackResult]]:
        """
        执行回写计划

        Args:
            plan_id: 计划 ID
            dry_run: 如果为 True，只模拟执行
            force: 强制执行，忽略前置条件检查

        Returns:
            (是否成功, 结果列表)
        """
        # 获取计划
        plan = self.session.query(WritebackPlanTable).filter_by(plan_id=plan_id).first()

        if not plan:
            raise ValueError(f"回写计划不存在: {plan_id}")

        # 获取补丁集
        patch_set = self.patch_service.get_patch_set(plan.patch_set_id)
        if not patch_set:
            raise ValueError(f"补丁集不存在: {plan.patch_set_id}")

        # 创建执行记录
        run_id = str(uuid.uuid4())
        trace_id = f"trace_{run_id[:8]}"

        if not dry_run:
            self.current_run = ApplyRunTable(
                run_id=run_id,
                plan_id=plan_id,
                started_at=datetime.now(),
                status="running",
                trace_id=trace_id,
                metadata={"dry_run": dry_run, "force": force},
            )
            self.session.add(self.current_run)
            self.session.commit()

        # 执行补丁项
        self.results = []
        success_count = 0
        failed_count = 0

        for patch_item in patch_set.patch_items:
            logger.info(f"[{trace_id}] 处理补丁项: {patch_item.patch_item_id}")

            try:
                # 获取目标容器和路径
                container_info = self._get_container_info(
                    patch_item.target_container_id
                )
                if not container_info:
                    logger.error(f"容器不存在: {patch_item.target_container_id}")
                    failed_count += 1
                    continue

                target_path = Path(container_info["artifact_path"])

                # 选择策略
                strategy = self._select_strategy(patch_item, target_path)

                if dry_run:
                    # 模拟执行
                    logger.info(f"[模拟] 将使用 {strategy.__class__.__name__} 策略")
                    result = WritebackResult(
                        success=True,
                        patch_item_id=patch_item.patch_item_id,
                        strategy=strategy.__class__.__name__,
                        target_path=str(target_path),
                        metadata={"dry_run": True},
                    )
                else:
                    # 实际执行
                    result = strategy.apply(patch_item, target_path)

                self.results.append(result)

                if result.success:
                    success_count += 1
                    logger.info(
                        f"[{trace_id}] 补丁应用成功: {patch_item.patch_item_id}"
                    )
                else:
                    failed_count += 1
                    logger.error(f"[{trace_id}] 补丁应用失败: {result.error_message}")

                # 记录结果
                if not dry_run:
                    self._record_result(result, patch_item.patch_item_id)

            except Exception as e:
                logger.error(f"[{trace_id}] 处理补丁项失败: {e}")
                failed_count += 1

                result = WritebackResult(
                    success=False,
                    patch_item_id=patch_item.patch_item_id,
                    strategy="unknown",
                    target_path="",
                    error_message=str(e),
                )
                self.results.append(result)

        # 更新执行状态
        overall_success = failed_count == 0

        if not dry_run and self.current_run:
            self.current_run.completed_at = datetime.now()
            self.current_run.status = "success" if overall_success else "failed"
            self.current_run.metadata.update(
                {"success_count": success_count, "failed_count": failed_count}
            )
            self.session.commit()

        logger.info(f"[{trace_id}] 执行完成: 成功 {success_count}, 失败 {failed_count}")

        return overall_success, self.results

    def _get_container_info(self, container_id: str) -> dict | None:
        """获取容器信息"""
        container = (
            self.session.query(ContainerTable)
            .filter_by(container_id=container_id)
            .first()
        )

        if not container:
            return None

        artifact = (
            self.session.query(ArtifactTable)
            .filter_by(artifact_id=container.artifact_id)
            .first()
        )

        if not artifact:
            return None

        return {
            "container_id": container.container_id,
            "container_type": container.container_type,
            "artifact_path": artifact.path,
            "artifact_type": artifact.artifact_type,
        }

    def _select_strategy(
        self, patch_item: PatchItem, target_path: Path
    ) -> WritebackStrategy:
        """选择合适的回写策略"""

        # 根据补丁策略选择
        if patch_item.policy == PatchPolicy.OVERLAY:
            return self.strategies["overlay"]

        # 根据目标类型选择
        if target_path.is_file() and target_path.suffix.lower() in [".jar", ".zip"]:
            if patch_item.policy in [PatchPolicy.REPLACE, PatchPolicy.MERGE]:
                return self.strategies["jar_modify"]
            else:
                return self.strategies["overlay"]

        if target_path.is_dir():
            return self.strategies["directory"]

        # 默认使用 Overlay
        return self.strategies["overlay"]

    def _record_result(self, result: WritebackResult, patch_item_id: str) -> None:
        """记录执行结果"""
        if not self.current_run:
            return

        result_record = ApplyResultTable(
            result_id=str(uuid.uuid4()),
            run_id=self.current_run.run_id,
            patch_item_id=patch_item_id,
            status="success" if result.success else "failed",
            before_hash=result.before_hash,
            after_hash=result.after_hash,
            rollback_status="not_needed",
            metadata=result.metadata,
        )

        self.session.add(result_record)
        self.session.commit()

    def rollback_run(self, run_id: str) -> tuple[bool, list[str]]:
        """
        回滚执行

        Args:
            run_id: 执行 ID

        Returns:
            (是否成功, 错误消息列表)
        """
        # 获取执行记录
        run = self.session.query(ApplyRunTable).filter_by(run_id=run_id).first()

        if not run:
            return False, [f"执行记录不存在: {run_id}"]

        # 获取所有结果
        results = self.session.query(ApplyResultTable).filter_by(run_id=run_id).all()

        errors = []
        rollback_count = 0

        for result_record in results:
            if result_record.status != "success":
                continue

            # 查找对应的策略和结果
            strategy_name = result_record.metadata.get("strategy", "overlay")
            if strategy_name in self.strategies:
                strategy = self.strategies[strategy_name]

                # 构建回写结果对象
                writeback_result = WritebackResult(
                    success=True,
                    patch_item_id=result_record.patch_item_id,
                    strategy=strategy_name,
                    target_path=result_record.metadata.get("target_path", ""),
                    backup_path=result_record.metadata.get("backup_path"),
                )

                # 执行回滚
                if strategy.rollback(writeback_result):
                    rollback_count += 1
                    result_record.rollback_status = "success"
                    logger.info(f"回滚成功: {result_record.patch_item_id}")
                else:
                    errors.append(f"回滚失败: {result_record.patch_item_id}")
                    result_record.rollback_status = "failed"

        # 更新执行状态
        run.status = "rolled_back"
        run.metadata["rollback_count"] = rollback_count
        run.metadata["rollback_errors"] = errors

        self.session.commit()

        overall_success = len(errors) == 0
        logger.info(f"回滚完成: {rollback_count} 个成功, {len(errors)} 个失败")

        return overall_success, errors

    def get_execution_report(self, run_id: str) -> dict:
        """
        获取执行报告

        Args:
            run_id: 执行 ID

        Returns:
            执行报告字典
        """
        run = self.session.query(ApplyRunTable).filter_by(run_id=run_id).first()

        if not run:
            return {}

        results = self.session.query(ApplyResultTable).filter_by(run_id=run_id).all()

        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")

        report = {
            "run_id": run_id,
            "plan_id": run.plan_id,
            "status": run.status,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "trace_id": run.trace_id,
            "statistics": {
                "total": len(results),
                "success": success_count,
                "failed": failed_count,
                "success_rate": success_count / len(results) if results else 0,
            },
            "results": [
                {
                    "patch_item_id": r.patch_item_id,
                    "status": r.status,
                    "rollback_status": r.rollback_status,
                }
                for r in results
            ],
        }

        return report
