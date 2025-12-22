import type { ProjectCreate } from '../models/ProjectCreate';
import type { ProjectRead } from '../models/ProjectRead';
import type { CancelablePromise } from '../core/CancelablePromise';
export declare class ProjectsService {
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
    static listProjectsV1ProjectsGet(page?: number, size?: number, status?: (string | null), search?: (string | null)): CancelablePromise<Array<ProjectRead>>;
    /**
     * 创建新项目
     * 创建新项目
     * @param requestBody
     * @returns ProjectRead Successful Response
     * @throws ApiError
     */
    static createProjectV1ProjectsPost(requestBody: ProjectCreate): CancelablePromise<ProjectRead>;
    /**
     * 获取项目详情
     * 获取项目详情
     * @param projectId
     * @returns ProjectRead Successful Response
     * @throws ApiError
     */
    static getProjectV1ProjectsProjectIdGet(projectId: string): CancelablePromise<ProjectRead>;
    /**
     * 更新项目信息
     * 更新项目信息 (通过 UseCase)
     * @param projectId
     * @param requestBody
     * @returns ProjectRead Successful Response
     * @throws ApiError
     */
    static updateProjectV1ProjectsProjectIdPatch(projectId: string, requestBody: Record<string, any>): CancelablePromise<ProjectRead>;
    /**
     * 删除项目
     * 删除项目 (通过 UseCase)
     * @param projectId
     * @returns any Successful Response
     * @throws ApiError
     */
    static deleteProjectV1ProjectsProjectIdDelete(projectId: string): CancelablePromise<Record<string, any>>;
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
    static getProjectStatsV1ProjectsProjectIdStatsGet(projectId: string): CancelablePromise<Record<string, any>>;
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
    static getProjectJobsV1ProjectsProjectIdJobsGet(projectId: string, page?: number, size?: number, status?: (string | null)): CancelablePromise<Record<string, any>>;
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
    static cloneProjectV1ProjectsProjectIdClonePost(projectId: string, requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
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
    static addExternalMappingV1ProjectsProjectIdExternalMappingsPost(projectId: string, requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
}
