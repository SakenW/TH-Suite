/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class JobsService {
    /**
     * 获取任务列表
     * 获取任务列表 (通过 UseCase)
     * @param page 页码
     * @param size 每页数量
     * @param projectId 按项目筛选
     * @param status 按状态筛选
     * @param jobType 按类型筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listJobsV1JobsGet(
        page: number = 1,
        size: number = 20,
        projectId?: (string | null),
        status?: (string | null),
        jobType?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/jobs/',
            query: {
                'page': page,
                'size': size,
                'project_id': projectId,
                'status': status,
                'job_type': jobType,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建项目任务
     * 创建项目任务 (通过 UseCase)
     * @param projectId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createJobV1JobsProjectsProjectIdJobsPost(
        projectId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/jobs/projects/{project_id}/jobs',
            path: {
                'project_id': projectId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取任务详情
     * 获取任务详情 (通过 UseCase)
     * @param jobId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getJobV1JobsJobIdGet(
        jobId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/jobs/{job_id}',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新任务信息
     * 更新任务信息 (通过 UseCase)
     * @param jobId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateJobV1JobsJobIdPatch(
        jobId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/v1/jobs/{job_id}',
            path: {
                'job_id': jobId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新任务状态
     * 状态流转（created → running → completed …）
     *
     * Args:
     * job_id: 任务ID
     * status_data: 状态数据，包含：
     * - status: 新状态
     * - reason: 状态变更原因
     * - metadata: 其他元数据
     * uow: 工作单元（提供事务和RLS）
     *
     * Returns:
     * 状态更新响应
     * @param jobId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateJobStatusV1JobsJobIdStatusPost(
        jobId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/jobs/{job_id}/status',
            path: {
                'job_id': jobId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 分配任务
     * 分配任务给用户/角色
     * @param jobId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static assignJobV1JobsJobIdAssignmentsPost(
        jobId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/jobs/{job_id}/assignments',
            path: {
                'job_id': jobId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取任务分配
     * 获取任务的分配信息
     * @param jobId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getJobAssignmentsV1JobsJobIdAssignmentsGet(
        jobId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/jobs/{job_id}/assignments',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 取消任务分配
     * 取消任务分配
     * @param jobId
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static removeJobAssignmentV1JobsJobIdAssignmentsUserIdDelete(
        jobId: string,
        userId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/jobs/{job_id}/assignments/{user_id}',
            path: {
                'job_id': jobId,
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取任务片段
     * 获取任务下的片段列表
     * @param jobId
     * @param page 页码
     * @param size 每页数量
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getJobSegmentsV1JobsJobIdSegmentsGet(
        jobId: string,
        page: number = 1,
        size: number = 50,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/jobs/{job_id}/segments',
            path: {
                'job_id': jobId,
            },
            query: {
                'page': page,
                'size': size,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 批量更新片段
     * 批量更新 segments 的状态（例如：批量 approve）
     *
     * Args:
     * job_id: 任务ID
     * update_data: 批量更新数据，包含：
     * - segment_ids: 片段ID列表
     * - status: 新状态
     * - metadata: 其他元数据
     * uow: 工作单元（提供事务和RLS）
     *
     * Returns:
     * 批量更新结果响应
     * @param jobId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static bulkUpdateSegmentsV1JobsJobIdSegmentsBulkUpdatePost(
        jobId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/jobs/{job_id}/segments/bulk-update',
            path: {
                'job_id': jobId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 导入任务片段 (Stream GZIP)
     * 导入任务片段 (高吞吐流式接口)
     *
     * Headers:
     * Content-Encoding: gzip (Required)
     * Content-Type: application/x-ndjson (Required)
     * X-Idempotency-Key: (Optional)
     *
     * Returns:
     * 202 Accepted { "task_id": "...", "accepted_at": "..." }
     * @param jobId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static importJobSegmentsV1JobsJobIdSegmentsImportPost(
        jobId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/jobs/{job_id}/segments/import',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 触发预翻译 (TM/AI)
     * 手动触发预翻译流程。
     *
     * Available Strategies:
     * - 'tm_only' (默认): 仅使用翻译记忆库
     * - 'tm_then_mt': 先查 TM，无匹配则使用机器翻译
     *
     * Body: { "strategy": "..." }
     * @param jobId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static triggerPreTranslationV1JobsJobIdActionsPreTranslatePost(
        jobId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/jobs/{job_id}/actions/pre-translate',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 导出任务片段 (Stream GZIP)
     * 导出任务片段 (流式下载)
     *
     * Returns:
     * application/x-ndjson (Content-Encoding: gzip if compress=True)
     * @param jobId
     * @param compress 是否开启GZIP压缩
     * @returns any Successful Response
     * @throws ApiError
     */
    public static exportJobSegmentsV1JobsJobIdSegmentsExportGet(
        jobId: string,
        compress: boolean = true,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/jobs/{job_id}/segments/export',
            path: {
                'job_id': jobId,
            },
            query: {
                'compress': compress,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
