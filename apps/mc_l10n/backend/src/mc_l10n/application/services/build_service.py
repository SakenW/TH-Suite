"""重构后的打包系统服务 - 基于SQLCipher数据库和BLOB池的构建服务。"""

import hashlib
import json
import os
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from packages.core.database import SQLCipherDatabase
from packages.core.enhanced_state import ProjectStateMachine, StateTransition
from packages.core.errors import ValidationError


@dataclass
class BuildRequest:
    """构建请求参数。"""

    project_id: str
    output_path: str
    output_format: str = "zip"  # "zip" or "directory"
    include_pack_mcmeta: bool = True
    pack_format: int | None = None
    pack_description: str | None = None
    selected_languages: list[str] | None = None
    build_config: dict[str, Any] | None = None


@dataclass
class BuildArtifact:
    """构建产物信息。"""

    type: str  # "language_file", "pack_mcmeta", "zip_archive", "directory"
    path: str
    size: int
    sha256: str
    modid: str | None = None
    locale: str | None = None
    keys_count: int | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class BuildManifest:
    """构建清单。"""

    build_id: str
    project_id: str
    build_request: BuildRequest
    artifacts: list[BuildArtifact]
    total_size: int
    total_files: int
    build_time_seconds: float
    created_at: datetime
    source_fingerprint: str
    build_config_hash: str


@dataclass
class BuildResult:
    """构建结果。"""

    success: bool
    build_id: str
    manifest: BuildManifest | None = None
    output_path: str | None = None
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)


class BuildService:
    """重构后的打包系统服务。

    基于SQLCipher数据库和BLOB池，提供安全、可回滚的构建功能。
    """

    def __init__(
        self,
        database: SQLCipherDatabase,
        state_machine: ProjectStateMachine,
        logger: structlog.BoundLogger | None = None,
    ):
        self.database = database
        self.state_machine = state_machine
        self.logger = logger or structlog.get_logger()

    async def build_project(self, request: BuildRequest) -> BuildResult:
        """构建项目资源包。

        Args:
            request: 构建请求参数

        Returns:
            BuildResult: 构建结果
        """
        build_id = self._generate_build_id(request)
        logger = self.logger.bind(build_id=build_id, project_id=request.project_id)

        start_time = datetime.now()

        try:
            logger.info("开始构建项目", output_format=request.output_format)

            # 转换状态到构建中
            await self._transition_to_building(request.project_id, build_id)

            # 创建构建工作区
            workspace_path = await self._create_build_workspace(build_id)

            # 获取活动语言资产
            language_assets = await self._get_active_language_assets(request.project_id)

            # 过滤选定的语言
            if request.selected_languages:
                language_assets = [
                    asset
                    for asset in language_assets
                    if asset["locale"] in request.selected_languages
                ]

            # 提取和合并语言文件
            artifacts = await self._extract_and_merge_language_files(
                language_assets, workspace_path, logger
            )

            # 生成pack.mcmeta
            if request.include_pack_mcmeta:
                pack_mcmeta_artifact = await self._generate_pack_mcmeta(
                    request, workspace_path, logger
                )
                artifacts.append(pack_mcmeta_artifact)

            # 生成最终输出
            output_artifact = await self._generate_output(
                request, workspace_path, artifacts, logger
            )
            artifacts.append(output_artifact)

            # 计算构建时间
            build_time = (datetime.now() - start_time).total_seconds()

            # 创建构建清单
            manifest = await self._create_build_manifest(
                build_id, request, artifacts, build_time, start_time
            )

            # 保存构建记录
            await self._save_build_record(manifest)

            # 清理工作区
            await self._cleanup_workspace(workspace_path)

            # 转换状态到已构建
            await self._transition_to_built(request.project_id, build_id)

            logger.info(
                "构建完成",
                total_files=len(artifacts),
                total_size=manifest.total_size,
                build_time=build_time,
            )

            return BuildResult(
                success=True,
                build_id=build_id,
                manifest=manifest,
                output_path=request.output_path,
            )

        except Exception as e:
            logger.error("构建失败", error=str(e), exc_info=True)

            # 转换状态到失败
            await self._transition_to_failed(request.project_id, str(e))

            return BuildResult(success=False, build_id=build_id, error_message=str(e))

    async def list_builds(
        self, project_id: str | None = None, limit: int = 50
    ) -> list[BuildManifest]:
        """列出构建历史。

        Args:
            project_id: 项目ID（可选，为空则返回所有项目）
            limit: 返回数量限制

        Returns:
            List[BuildManifest]: 构建清单列表
        """
        query = """
        SELECT build_data FROM builds
        WHERE ($1 IS NULL OR project_id = $1)
        ORDER BY created_at DESC
        LIMIT $2
        """

        rows = await self.database.fetch_all(query, project_id, limit)

        manifests = []
        for row in rows:
            build_data = json.loads(row["build_data"])
            manifest = BuildManifest(**build_data)
            manifests.append(manifest)

        return manifests

    async def rollback_to_build(self, project_id: str, build_id: str) -> BuildResult:
        """回滚到指定构建。

        Args:
            project_id: 项目ID
            build_id: 构建ID

        Returns:
            BuildResult: 回滚结果
        """
        logger = self.logger.bind(project_id=project_id, build_id=build_id)

        try:
            # 获取构建清单
            manifest = await self._get_build_manifest(build_id)
            if not manifest or manifest.project_id != project_id:
                raise ValidationError(
                    f"构建 {build_id} 不存在或不属于项目 {project_id}"
                )

            # 重新激活该构建使用的语言资产
            await self._reactivate_build_assets(manifest)

            # 转换状态
            await self._transition_to_rollback(project_id, build_id)

            logger.info("回滚完成")

            return BuildResult(success=True, build_id=build_id, manifest=manifest)

        except Exception as e:
            logger.error("回滚失败", error=str(e))
            return BuildResult(success=False, build_id=build_id, error_message=str(e))

    def _generate_build_id(self, request: BuildRequest) -> str:
        """生成构建ID。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_hash = hashlib.sha256(
            json.dumps(request.__dict__, sort_keys=True).encode()
        ).hexdigest()[:8]
        return f"build_{timestamp}_{config_hash}"

    async def _create_build_workspace(self, build_id: str) -> Path:
        """创建构建工作区。"""
        workspace_path = Path(tempfile.mkdtemp(prefix=f"{build_id}_"))
        return workspace_path

    async def _get_active_language_assets(
        self, project_id: str
    ) -> list[dict[str, Any]]:
        """获取活动的语言资产。"""
        query = """
        SELECT la.*, p.blob_data
        FROM locale_assets la
        JOIN blob_pool p ON la.blob_id = p.blob_id
        WHERE la.project_id = $1 AND la.is_active = 1
        ORDER BY la.modid, la.locale
        """

        rows = await self.database.fetch_all(query, project_id)
        return [dict(row) for row in rows]

    async def _extract_and_merge_language_files(
        self,
        language_assets: list[dict[str, Any]],
        workspace_path: Path,
        logger: structlog.BoundLogger,
    ) -> list[BuildArtifact]:
        """提取和合并语言文件。"""
        artifacts = []

        for asset in language_assets:
            try:
                # 从BLOB池恢复文件内容
                blob_data = asset["blob_data"]
                lang_data = json.loads(blob_data.decode("utf-8"))

                # 创建目录结构
                modid = asset["modid"]
                locale = asset["locale"]
                lang_dir = workspace_path / "assets" / modid / "lang"
                lang_dir.mkdir(parents=True, exist_ok=True)

                # 写入语言文件
                lang_file_path = lang_dir / f"{locale}.json"
                with open(lang_file_path, "w", encoding="utf-8") as f:
                    json.dump(lang_data, f, indent=2, ensure_ascii=False)

                # 计算文件哈希
                file_hash = self._calculate_file_hash(lang_file_path)

                artifact = BuildArtifact(
                    type="language_file",
                    path=str(lang_file_path),
                    size=lang_file_path.stat().st_size,
                    sha256=file_hash,
                    modid=modid,
                    locale=locale,
                    keys_count=len(lang_data),
                )
                artifacts.append(artifact)

                logger.debug(
                    "语言文件已提取",
                    modid=modid,
                    locale=locale,
                    keys_count=len(lang_data),
                )

            except Exception as e:
                logger.warning(
                    "语言文件提取失败", asset_id=asset.get("asset_id"), error=str(e)
                )
                continue

        return artifacts

    async def _generate_pack_mcmeta(
        self, request: BuildRequest, workspace_path: Path, logger: structlog.BoundLogger
    ) -> BuildArtifact:
        """生成pack.mcmeta文件。"""
        pack_format = request.pack_format or 15  # 默认MC 1.20.2+
        description = (
            request.pack_description or "TransHub Tools Generated Resource Pack"
        )

        mcmeta_content = {
            "pack": {"pack_format": pack_format, "description": description}
        }

        mcmeta_path = workspace_path / "pack.mcmeta"
        with open(mcmeta_path, "w", encoding="utf-8") as f:
            json.dump(mcmeta_content, f, indent=2, ensure_ascii=False)

        file_hash = self._calculate_file_hash(mcmeta_path)

        logger.debug("pack.mcmeta已生成", pack_format=pack_format)

        return BuildArtifact(
            type="pack_mcmeta",
            path=str(mcmeta_path),
            size=mcmeta_path.stat().st_size,
            sha256=file_hash,
        )

    async def _generate_output(
        self,
        request: BuildRequest,
        workspace_path: Path,
        artifacts: list[BuildArtifact],
        logger: structlog.BoundLogger,
    ) -> BuildArtifact:
        """生成最终输出产物。"""
        output_path = Path(request.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if request.output_format == "zip":
            return await self._create_zip_output(
                workspace_path, output_path, artifacts, logger
            )
        else:
            return await self._create_directory_output(
                workspace_path, output_path, artifacts, logger
            )

    async def _create_zip_output(
        self,
        workspace_path: Path,
        output_path: Path,
        artifacts: list[BuildArtifact],
        logger: structlog.BoundLogger,
    ) -> BuildArtifact:
        """创建ZIP格式输出。"""
        zip_path = output_path.with_suffix(".zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(workspace_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(workspace_path)
                    zipf.write(file_path, arcname)

        file_hash = self._calculate_file_hash(zip_path)

        logger.info("ZIP产物已创建", path=str(zip_path), size=zip_path.stat().st_size)

        return BuildArtifact(
            type="zip_archive",
            path=str(zip_path),
            size=zip_path.stat().st_size,
            sha256=file_hash,
        )

    async def _create_directory_output(
        self,
        workspace_path: Path,
        output_path: Path,
        artifacts: list[BuildArtifact],
        logger: structlog.BoundLogger,
    ) -> BuildArtifact:
        """创建目录格式输出。"""
        import shutil

        if output_path.exists():
            shutil.rmtree(output_path)

        shutil.copytree(workspace_path, output_path)

        # 计算目录哈希（所有文件哈希的聚合）
        all_hashes = []
        total_size = 0

        for root, dirs, files in os.walk(output_path):
            for file in files:
                file_path = Path(root) / file
                file_hash = self._calculate_file_hash(file_path)
                all_hashes.append(file_hash)
                total_size += file_path.stat().st_size

        directory_hash = hashlib.sha256(
            "".join(sorted(all_hashes)).encode()
        ).hexdigest()

        logger.info("目录产物已创建", path=str(output_path), size=total_size)

        return BuildArtifact(
            type="directory",
            path=str(output_path),
            size=total_size,
            sha256=directory_hash,
        )

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件SHA256哈希。"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    async def _create_build_manifest(
        self,
        build_id: str,
        request: BuildRequest,
        artifacts: list[BuildArtifact],
        build_time: float,
        created_at: datetime,
    ) -> BuildManifest:
        """创建构建清单。"""
        total_size = sum(artifact.size for artifact in artifacts)

        # 计算源指纹（基于活动语言资产）
        source_fingerprint = await self._calculate_source_fingerprint(
            request.project_id
        )

        # 计算构建配置哈希
        build_config_hash = hashlib.sha256(
            json.dumps(request.__dict__, sort_keys=True).encode()
        ).hexdigest()

        return BuildManifest(
            build_id=build_id,
            project_id=request.project_id,
            build_request=request,
            artifacts=artifacts,
            total_size=total_size,
            total_files=len(artifacts),
            build_time_seconds=build_time,
            created_at=created_at,
            source_fingerprint=source_fingerprint,
            build_config_hash=build_config_hash,
        )

    async def _save_build_record(self, manifest: BuildManifest) -> None:
        """保存构建记录到数据库。"""
        query = """
        INSERT INTO builds (
            build_id, project_id, build_data, created_at
        ) VALUES ($1, $2, $3, $4)
        """

        build_data = json.dumps(manifest.__dict__, default=str)

        await self.database.execute(
            query,
            manifest.build_id,
            manifest.project_id,
            build_data,
            manifest.created_at,
        )

    async def _calculate_source_fingerprint(self, project_id: str) -> str:
        """计算源指纹。"""
        query = """
        SELECT la.file_path, la.locale, p.blob_id
        FROM locale_assets la
        JOIN blob_pool p ON la.blob_id = p.blob_id
        WHERE la.project_id = $1 AND la.is_active = 1
        ORDER BY la.file_path, la.locale
        """

        rows = await self.database.fetch_all(query, project_id)

        fingerprint_data = []
        for row in rows:
            fingerprint_data.append(
                f"{row['file_path']}:{row['locale']}:{row['blob_id']}"
            )

        return hashlib.sha256("\n".join(fingerprint_data).encode()).hexdigest()

    async def _cleanup_workspace(self, workspace_path: Path) -> None:
        """清理构建工作区。"""
        import shutil

        try:
            shutil.rmtree(workspace_path)
        except Exception as e:
            self.logger.warning(
                "工作区清理失败", path=str(workspace_path), error=str(e)
            )

    async def _transition_to_building(self, project_id: str, build_id: str) -> None:
        """转换状态到构建中。"""
        transition = StateTransition(
            from_state="READY_TO_BUILD",
            to_state="BUILDING",
            trigger="start_build",
            metadata={"build_id": build_id},
        )
        await self.state_machine.transition(project_id, transition)

    async def _transition_to_built(self, project_id: str, build_id: str) -> None:
        """转换状态到已构建。"""
        transition = StateTransition(
            from_state="BUILDING",
            to_state="BUILT",
            trigger="build_completed",
            metadata={"build_id": build_id},
        )
        await self.state_machine.transition(project_id, transition)

    async def _transition_to_failed(self, project_id: str, error: str) -> None:
        """转换状态到失败。"""
        transition = StateTransition(
            from_state="BUILDING",
            to_state="FAILED",
            trigger="build_failed",
            metadata={"error": error},
        )
        await self.state_machine.transition(project_id, transition)

    async def _transition_to_rollback(self, project_id: str, build_id: str) -> None:
        """转换状态到回滚。"""
        transition = StateTransition(
            from_state="BUILT",
            to_state="ROLLBACK",
            trigger="rollback_to_build",
            metadata={"target_build_id": build_id},
        )
        await self.state_machine.transition(project_id, transition)

    async def _get_build_manifest(self, build_id: str) -> BuildManifest | None:
        """获取构建清单。"""
        query = "SELECT build_data FROM builds WHERE build_id = $1"
        row = await self.database.fetch_one(query, build_id)

        if not row:
            return None

        build_data = json.loads(row["build_data"])
        return BuildManifest(**build_data)

    async def _reactivate_build_assets(self, manifest: BuildManifest) -> None:
        """重新激活构建使用的资产。"""
        # 这里需要根据构建清单中的信息重新激活相应的语言资产
        # 具体实现取决于如何在清单中记录使用的资产信息
        pass
