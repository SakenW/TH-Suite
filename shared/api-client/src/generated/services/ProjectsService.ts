/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectCreate } from '../models/ProjectCreate';
import type { ProjectRead } from '../models/ProjectRead';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ProjectsService {
    /**
     * 获取项目列表
     * 获取项目列表 (通过 UseCase)
     * @param page 页码
     * @param size 每页数量
     * @param status 按状态筛选
     * @param search 搜索关键词
     * @returns ProjectRead Successful Response
     * @throws ApiError
     */
    public static listProjectsV1ProjectsGet(
        page: number = 1,
        size: number = 20,
        status?: (string | null),
        search?: (string | null),
    ): CancelablePromise<Array<ProjectRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/projects/',
            query: {
                'page': page,
                'size': size,
                'status': status,
                'search': search,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建新项目
     * 创建新项目
     * @param requestBody
     * @returns ProjectRead Successful Response
     * @throws ApiError
     */
    public static createProjectV1ProjectsPost(
        requestBody: ProjectCreate,
    ): CancelablePromise<ProjectRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/projects/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取项目详情
     * 获取项目详情
     * @param projectId
     * @returns ProjectRead Successful Response
     * @throws ApiError
     */
    public static getProjectV1ProjectsProjectIdGet(
        projectId: string,
    ): CancelablePromise<ProjectRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新项目信息
     * 更新项目信息 (通过 UseCase)
     * @param projectId
     * @param requestBody
     * @returns ProjectRead Successful Response
     * @throws ApiError
     */
    public static updateProjectV1ProjectsProjectIdPatch(
        projectId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<ProjectRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/v1/projects/{project_id}',
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
     * 删除项目
     * 删除项目 (通过 UseCase)
     * @param projectId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteProjectV1ProjectsProjectIdDelete(
        projectId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取项目统计
     * 获取项目统计信息（通过 UseCases）
     *
     * Args:
     * project_id: 项目ID
     * uow: 工作单元
     *
     * Returns:
     * 项目统计信息
     * @param projectId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getProjectStatsV1ProjectsProjectIdStatsGet(
        projectId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/projects/{project_id}/stats',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取项目任务列表
     * 获取项目下的任务列表（通过 UseCases）
     *
     * Args:
     * project_id: 项目ID
     * page: 页码
     * size: 每页数量
     * status: 按状态筛选
     * uow: 工作单元
     *
     * Returns:
     * 任务列表响应
     * @param projectId
     * @param page 页码
     * @param size 每页数量
     * @param status 按状态筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getProjectJobsV1ProjectsProjectIdJobsGet(
        projectId: string,
        page: number = 1,
        size: number = 20,
        status?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/projects/{project_id}/jobs',
            path: {
                'project_id': projectId,
            },
            query: {
                'page': page,
                'size': size,
                'status': status,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 克隆项目
     * 克隆项目（通过 UseCases）
     *
     * Args:
     * project_id: 源项目ID
     * clone_data: 克隆参数
     * uow: 工作单元
     *
     * Returns:
     * 克隆结果响应
     * @param projectId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static cloneProjectV1ProjectsProjectIdClonePost(
        projectId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/projects/{project_id}/clone',
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
     * 添加外部系统映射
     * 添加外部系统映射（通过 UseCases）
     *
     * Args:
     * project_id: 项目ID
     * mapping_data: 外部映射数据
     * uow: 工作单元
     *
     * Returns:
     * 映射结果响应
     * @param projectId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static addExternalMappingV1ProjectsProjectIdExternalMappingsPost(
        projectId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/projects/{project_id}/external-mappings',
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
}
