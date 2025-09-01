"""TH Suite MC L10n API routes."""

from pathlib import Path

import structlog
from mc_l10n.application.services.build_service import BuildService
from mc_l10n.application.services.export_service import ExportService
from mc_l10n.application.services.extract_service import ExtractService
from mc_l10n.application.services.project_service import ProjectService
from mc_l10n.application.services.scan_service import ScanService
from fastapi import APIRouter, BackgroundTasks

from packages.backend_kit.dependencies import (
    DatabaseDep,
    JobContext,
    JobContextDep,
    LoggerDep,
    StateMachineDep,
)
from packages.backend_kit.responses import (
    create_error_response,
    create_job_response,
    create_success_response,
)
from packages.core.auto_scan_service import AutoScanService
from packages.core.database import SQLCipherDatabase
from packages.core.enhanced_models import MinecraftLoader, ProjectType
from packages.core.errors import ProcessingError, ValidationError
from packages.core.models import (
    BuildRequest,
    ExportRequest,
    ExtractRequest,
    JobStatus,
    ProjectScanRequest,
    ScanRequest,
)
from packages.core.state import State, StateMachine

router = APIRouter(tags=["TH Suite MC L10n"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return create_success_response(
        data={"status": "healthy", "service": "TH Suite MC L10n"},
        message="TH Suite MC L10n API is running",
    )


@router.post("/scan")
async def scan_directory(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    job_context: JobContext = JobContextDep,
    logger: structlog.BoundLogger = LoggerDep,
    state_machine: StateMachine = StateMachineDep,
    database: SQLCipherDatabase = DatabaseDep,
):
    """Scan a Minecraft directory for language files.

    This endpoint initiates a scan of the specified directory to discover
    Minecraft mods and their language files.
    """
    logger = logger.bind(job_id=job_context.job_id, operation="scan")
    logger.info("Starting directory scan", directory=request.directory)

    try:
        # Validate directory exists
        directory_path = Path(request.directory)
        if not directory_path.exists():
            raise ValidationError(f"Directory does not exist: {request.directory}")

        if not directory_path.is_dir():
            raise ValidationError(f"Path is not a directory: {request.directory}")

        # Initialize state machine
        state_machine.reset()
        context = {
            "job_id": job_context.job_id,
            "directory": request.directory,
            "recursive": request.recursive,
            "include_patterns": request.include_patterns,
            "exclude_patterns": request.exclude_patterns,
        }

        # Transition to scanning state
        if not state_machine.can_transition(State.SCANNING, context):
            raise ProcessingError("Cannot start scan: invalid state")

        state_machine.transition(State.SCANNING, context)

        # Start background scan task
        scan_service = ScanService(logger, state_machine, database)
        background_tasks.add_task(
            scan_service.scan_directory, job_context.job_id, request, context
        )

        return create_job_response(
            job_id=job_context.job_id,
            job_status=JobStatus.RUNNING,
            message="Scan started successfully",
        )

    except (ValidationError, ProcessingError) as e:
        logger.error("Scan request failed", error=str(e))
        return create_error_response(
            error_type=type(e).__name__, message=str(e), code=e.error_code
        )
    except Exception as e:
        logger.error("Unexpected error during scan", error=str(e), exc_info=True)
        return create_error_response(
            error_type="InternalError",
            message="An unexpected error occurred",
            code="INTERNAL_ERROR",
        )


@router.post("/scan-project")
async def scan_project(
    request: ProjectScanRequest,
    background_tasks: BackgroundTasks,
    job_context: JobContext = JobContextDep,
    logger: structlog.BoundLogger = LoggerDep,
    database: SQLCipherDatabase = DatabaseDep,
):
    """Scan a project directory and save results to database.

    This endpoint uses AutoScanService to perform a comprehensive scan
    and saves the results to the database for later retrieval.
    """
    logger = logger.bind(job_id=job_context.job_id, operation="scan_project")
    logger.info("Starting project scan", project_path=request.directory)

    try:
        # Validate directory exists
        directory_path = Path(request.directory)
        if not directory_path.exists():
            raise ValidationError(f"Directory does not exist: {request.directory}")
        if not directory_path.is_dir():
            raise ValidationError(f"Path is not a directory: {request.directory}")

        # Start background scan task
        auto_scan_service = AutoScanService()
        background_tasks.add_task(
            _perform_project_scan_and_save,
            auto_scan_service,
            database,
            logger,
            job_context.job_id,
            str(directory_path.absolute()),
        )

        return create_job_response(
            job_id=job_context.job_id,
            job_status=JobStatus.RUNNING,
            message="Project scan started successfully",
        )

    except (ValidationError, ProcessingError) as e:
        logger.error("Scan project request failed", error=str(e))
        return create_error_response(
            error_type=type(e).__name__, message=str(e), code=e.error_code
        )
    except Exception as e:
        logger.error(
            "Unexpected error during project scan", error=str(e), exc_info=True
        )
        return create_error_response(
            error_type="InternalError",
            message="An unexpected error occurred",
            code="INTERNAL_ERROR",
        )


async def _perform_project_scan_and_save(
    auto_scan_service: AutoScanService,
    database: SQLCipherDatabase,
    logger: structlog.BoundLogger,
    job_id: str,
    project_path: str,
):
    """Background task to perform project scan and save to database."""
    try:
        logger.info("Performing project scan", project_path=project_path)

        # Perform the scan
        scan_result = await auto_scan_service.scan_project(project_path)

        # Save to database
        database.save_scan_result(scan_result, scan_result.scan_id)

        logger.info(
            "Project scan completed and saved to database",
            scan_id=scan_result.scan_id,
            total_mods=scan_result.total_mods,
            total_language_files=scan_result.total_language_files,
        )

    except Exception as e:
        logger.error("Failed to perform project scan", error=str(e), exc_info=True)


@router.post("/create-project")
async def create_project(
    request: dict,
    background_tasks: BackgroundTasks,
    job_context: JobContext = JobContextDep,
    logger: structlog.BoundLogger = LoggerDep,
    database: SQLCipherDatabase = DatabaseDep,
):
    """Create a new project from scan results.

    This endpoint creates a project using the ProjectService.
    """
    logger = logger.bind(job_id=job_context.job_id, operation="create_project")
    logger.info("Starting project creation", request=request)

    try:
        # Extract parameters from request
        scan_id = request.get("scan_id")
        name = request.get("name")
        version = request.get("version", "1.0.0")
        mc_version = request.get("mc_version", "1.20.1")
        loader = request.get("loader", "fabric")
        loader_version = request.get("loader_version", "0.15.0")
        project_type = request.get("project_type", "modpack")
        directory = request.get("directory")

        # Validate required parameters
        if not scan_id:
            raise ValidationError("scan_id is required")
        if not name:
            raise ValidationError("name is required")
        if not directory:
            raise ValidationError("directory is required")

        # Get scan result from database
        scan_result = database.get_scan_result(scan_id)
        if not scan_result:
            raise ValidationError(f"Scan result not found: {scan_id}")

        # Create project service and start background task
        project_service = ProjectService(database, logger)
        background_tasks.add_task(
            _perform_project_creation,
            project_service,
            logger,
            job_context.job_id,
            directory,
            ProjectType(project_type),
            name,
            version,
            mc_version,
            MinecraftLoader(loader),
            loader_version,
            scan_result,
        )

        return create_job_response(
            job_id=job_context.job_id,
            job_status=JobStatus.RUNNING,
            message="Project creation started successfully",
        )

    except (ValidationError, ProcessingError) as e:
        logger.error("Create project request failed", error=str(e))
        return create_error_response(
            error_type=type(e).__name__,
            message=str(e),
            code=getattr(e, "error_code", "VALIDATION_ERROR"),
        )
    except Exception as e:
        logger.error(
            "Unexpected error during project creation", error=str(e), exc_info=True
        )
        return create_error_response(
            error_type="InternalError",
            message="An unexpected error occurred",
            code="INTERNAL_ERROR",
        )


async def _perform_project_creation(
    project_service: ProjectService,
    logger: structlog.BoundLogger,
    job_id: str,
    directory: str,
    project_type: ProjectType,
    name: str,
    version: str,
    mc_version: str,
    loader: MinecraftLoader,
    loader_version: str,
    scan_result: dict,
):
    """Background task to perform project creation."""
    try:
        logger.info("Creating project", name=name, directory=directory)

        # Create the project
        project = await project_service.create_project(
            job_id=job_id,
            directory=directory,
            project_type=project_type,
            name=name,
            version=version,
            mc_version=mc_version,
            loader=loader,
            loader_version=loader_version,
            settings={"scan_result": scan_result},
        )

        logger.info("Project created successfully", project_id=project.id)

    except Exception as e:
        logger.error("Failed to create project", error=str(e), exc_info=True)


@router.get("/scan-results/{project_path:path}")
async def get_scan_results(
    project_path: str,
    logger: structlog.BoundLogger = LoggerDep,
    database: SQLCipherDatabase = DatabaseDep,
):
    """Get scan results for a specific project path."""
    logger = logger.bind(operation="get_scan_results", project_path=project_path)
    logger.info("Retrieving scan results")

    try:
        # Get scan results from database
        scan_results = database.get_scan_results_by_project_path(project_path)

        if not scan_results:
            return create_error_response(
                error_type="NotFound",
                message=f"No scan results found for project: {project_path}",
                code="SCAN_RESULTS_NOT_FOUND",
            )

        return {
            "success": True,
            "data": scan_results,
            "message": f"Found {len(scan_results)} scan result(s)",
        }

    except Exception as e:
        logger.error("Failed to retrieve scan results", error=str(e), exc_info=True)
        return create_error_response(
            error_type="InternalError",
            message="Failed to retrieve scan results",
            code="INTERNAL_ERROR",
        )


@router.get("/scan-results/latest/{project_path:path}")
async def get_latest_scan_result(
    project_path: str,
    logger: structlog.BoundLogger = LoggerDep,
    database: SQLCipherDatabase = DatabaseDep,
):
    """Get the latest scan result for a specific project path."""
    logger = logger.bind(operation="get_latest_scan_result", project_path=project_path)
    logger.info("Retrieving latest scan result")

    try:
        # Get latest scan result from database
        scan_result = database.get_latest_scan_result(project_path)

        if not scan_result:
            return create_error_response(
                error_type="NotFound",
                message=f"No scan results found for project: {project_path}",
                code="SCAN_RESULTS_NOT_FOUND",
            )

        return {
            "success": True,
            "data": scan_result,
            "message": "Latest scan result retrieved successfully",
        }

    except Exception as e:
        logger.error(
            "Failed to retrieve latest scan result", error=str(e), exc_info=True
        )
        return create_error_response(
            error_type="InternalError",
            message="Failed to retrieve latest scan result",
            code="INTERNAL_ERROR",
        )


@router.post("/extract")
async def extract_translations(
    request: ExtractRequest,
    background_tasks: BackgroundTasks,
    job_context: JobContext = JobContextDep,
    logger: structlog.BoundLogger = LoggerDep,
    state_machine: StateMachine = StateMachineDep,
    database: SQLCipherDatabase = DatabaseDep,
):
    """Extract translations from discovered language files.

    This endpoint processes the inventory from a previous scan and extracts
    all translation segments.
    """
    logger = logger.bind(job_id=job_context.job_id, operation="extract")
    logger.info("Starting translation extraction")

    try:
        # Validate inventory file exists
        inventory_path = Path(request.inventory_file)
        if not inventory_path.exists():
            raise ValidationError(
                f"Inventory file does not exist: {request.inventory_file}"
            )

        # Initialize context
        context = {
            "job_id": job_context.job_id,
            "inventory_file": request.inventory_file,
            "output_file": request.output_file,
            "locales": request.locales,
            "validate_keys": request.validate_keys,
        }

        # Transition to extracting state
        if not state_machine.can_transition(State.EXTRACTING, context):
            raise ProcessingError("Cannot start extraction: invalid state")

        state_machine.transition(State.EXTRACTING, context)

        # Start background extraction task
        extract_service = ExtractService(logger, state_machine, database)
        background_tasks.add_task(
            extract_service.extract_translations, job_context.job_id, request, context
        )

        return create_job_response(
            job_id=job_context.job_id,
            status=JobStatus.RUNNING,
            message="Extraction started successfully",
        )

    except (ValidationError, ProcessingError) as e:
        logger.error("Extract request failed", error=str(e))
        return create_error_response(
            error_type=type(e).__name__, message=str(e), code=e.error_code
        )
    except Exception as e:
        logger.error("Unexpected error during extraction", error=str(e), exc_info=True)
        return create_error_response(
            error_type="InternalError",
            message="An unexpected error occurred",
            code="INTERNAL_ERROR",
        )


@router.post("/build")
async def build_resource_pack(
    request: BuildRequest,
    background_tasks: BackgroundTasks,
    job_context: JobContext = JobContextDep,
    logger: structlog.BoundLogger = LoggerDep,
    state_machine: StateMachine = StateMachineDep,
    database: SQLCipherDatabase = DatabaseDep,
):
    """Build a Minecraft resource pack or overrides from translations.

    This endpoint creates a Minecraft resource pack or overrides directory
    from the provided translation segments.
    """
    logger = logger.bind(job_id=job_context.job_id, operation="build")
    logger.info("Starting resource pack build", mode=request.mode)

    try:
        # Validate segments file exists
        segments_path = Path(request.segments_file)
        if not segments_path.exists():
            raise ValidationError(
                f"Segments file does not exist: {request.segments_file}"
            )

        # Validate build mode
        valid_modes = ["resource_pack", "overrides"]
        if request.mode not in valid_modes:
            raise ValidationError(
                f"Invalid build mode: {request.mode}. Must be one of: {valid_modes}"
            )

        # Initialize context
        context = {
            "job_id": job_context.job_id,
            "segments_file": request.segments_file,
            "output_path": request.output_path,
            "mode": request.mode,
            "target_locales": request.target_locales,
            "pack_metadata": request.metadata,
        }

        # Transition to building state
        if not state_machine.can_transition(State.BUILDING, context):
            raise ProcessingError("Cannot start build: invalid state")

        state_machine.transition(State.BUILDING, context)

        # Start background build task
        build_service = BuildService(logger, state_machine, database)
        background_tasks.add_task(
            build_service.build_resource_pack, job_context.job_id, request, context
        )

        return create_job_response(
            job_id=job_context.job_id,
            status=JobStatus.RUNNING,
            message="Build started successfully",
        )

    except (ValidationError, ProcessingError) as e:
        logger.error("Build request failed", error=str(e))
        return create_error_response(
            error_type=type(e).__name__, message=str(e), code=e.error_code
        )
    except Exception as e:
        logger.error("Unexpected error during build", error=str(e), exc_info=True)
        return create_error_response(
            error_type="InternalError",
            message="An unexpected error occurred",
            code="INTERNAL_ERROR",
        )


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str, logger: structlog.BoundLogger = LoggerDep):
    """Get the status of a specific job."""
    logger = logger.bind(job_id=job_id, operation="status")

    try:
        # Get job context from cache
        from packages.backend_kit.dependencies import get_job_context, get_state_machine

        job_context = get_job_context(job_id)
        if not job_context:
            return create_error_response(
                error_type="NotFoundError",
                message=f"Job not found: {job_id}",
                code="JOB_NOT_FOUND",
            )

        state_machine = get_state_machine(job_id)
        current_state = state_machine.current_state
        context = state_machine.context

        # Map state to job status
        status_mapping = {
            State.IDLE: JobStatus.PENDING,
            State.SCANNING: JobStatus.RUNNING,
            State.EXTRACTING: JobStatus.RUNNING,
            State.VALIDATING: JobStatus.RUNNING,
            State.BUILDING: JobStatus.RUNNING,
            State.COMPLETED: JobStatus.COMPLETED,
            State.FAILED: JobStatus.FAILED,
            State.CANCELLED: JobStatus.CANCELLED,
        }

        job_status = status_mapping.get(current_state, JobStatus.UNKNOWN)

        return create_job_response(
            job_id=job_id,
            status=job_status,
            result=context.get("result"),
            message=context.get("message", f"Job is in {current_state.value} state"),
        )

    except Exception as e:
        logger.error("Error getting job status", error=str(e), exc_info=True)
        return create_error_response(
            error_type="InternalError",
            message="Failed to get job status",
            code="INTERNAL_ERROR",
        )


@router.post("/export")
async def export_language_pack(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    job_context: JobContext = JobContextDep,
    logger: structlog.BoundLogger = LoggerDep,
    state_machine: StateMachine = StateMachineDep,
    database: SQLCipherDatabase = DatabaseDep,
):
    """Export language pack from source directory.

    This endpoint exports language files from a source directory
    to various formats like ZIP or directory structure.
    """
    logger = logger.bind(job_id=job_context.job_id, operation="export")
    logger.info(
        "Starting language pack export",
        source=request.source_directory,
        output=request.output_directory,
        format=request.export_format,
    )

    try:
        # Validate source directory exists
        source_path = Path(request.source_directory)
        if not source_path.exists():
            raise ValidationError(
                f"Source directory does not exist: {request.source_directory}"
            )

        if not source_path.is_dir():
            raise ValidationError(
                f"Source path is not a directory: {request.source_directory}"
            )

        # Validate export format
        valid_formats = ["zip", "directory"]
        if request.export_format not in valid_formats:
            raise ValidationError(
                f"Invalid export format: {request.export_format}. Must be one of: {valid_formats}"
            )

        # Initialize context
        context = {
            "job_id": job_context.job_id,
            "source_directory": request.source_directory,
            "output_directory": request.output_directory,
            "export_format": request.export_format,
            "target_locales": request.target_locales,
            "include_patterns": request.include_patterns,
            "exclude_patterns": request.exclude_patterns,
            "compress_level": request.compress_level,
        }

        # Transition to exporting state
        if not state_machine.can_transition(State.EXPORTING, context):
            raise ProcessingError("Cannot start export: invalid state")

        state_machine.transition(State.EXPORTING, context)

        # Start background export task
        export_service = ExportService(logger, state_machine, database)
        background_tasks.add_task(
            export_service.export_language_pack, job_context.job_id, request, context
        )

        return create_job_response(
            job_id=job_context.job_id,
            status=JobStatus.RUNNING,
            message="Export started successfully",
        )

    except (ValidationError, ProcessingError) as e:
        logger.error("Export request failed", error=str(e))
        return create_error_response(
            error_type=type(e).__name__, message=str(e), code=e.error_code
        )
    except Exception as e:
        logger.error("Unexpected error during export", error=str(e), exc_info=True)
        return create_error_response(
            error_type="InternalError",
            message="An unexpected error occurred",
            code="INTERNAL_ERROR",
        )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str, logger: structlog.BoundLogger = LoggerDep):
    """Cancel a running job."""
    logger = logger.bind(job_id=job_id, operation="cancel")

    try:
        # Get job context and state machine
        from packages.backend_kit.dependencies import get_job_context, get_state_machine

        job_context = get_job_context(job_id)
        if not job_context:
            return create_error_response(
                error_type="NotFoundError",
                message=f"Job not found: {job_id}",
                code="JOB_NOT_FOUND",
            )

        state_machine = get_state_machine(job_id)
        context = state_machine.context
        context["cancelled"] = True

        # Try to transition to cancelled state
        if state_machine.can_transition(State.CANCELLED, context):
            state_machine.transition(State.CANCELLED, context)
            logger.info("Job cancelled successfully")

            return create_job_response(
                job_id=job_id,
                status=JobStatus.CANCELLED,
                message="Job cancelled successfully",
            )
        else:
            return create_error_response(
                error_type="ConflictError",
                message="Job cannot be cancelled in current state",
                code="CANNOT_CANCEL",
            )

    except Exception as e:
        logger.error("Error cancelling job", error=str(e), exc_info=True)
        return create_error_response(
            error_type="InternalError",
            message="Failed to cancel job",
            code="INTERNAL_ERROR",
        )
