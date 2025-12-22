import type { CancelablePromise } from '../core/CancelablePromise';
export declare class AiUsageService {
    /**
     * 获取AI使用日志
     * 分页查询当前 tenant 的 AI 使用日志
     * @param page 页码
     * @param size 每页数量
     * @param startDate 开始时间
     * @param endDate 结束时间
     * @param model 按模型筛选
     * @param projectId 按项目筛选
     * @param jobId 按任务筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    static getAiUsageLogsV1AiUsageLogsGet(page?: number, size?: number, startDate?: (string | null), endDate?: (string | null), model?: (string | null), projectId?: (string | null), jobId?: (string | null)): CancelablePromise<Record<string, any>>;
    /**
     * 获取AI使用统计
     * 返回统计视图：按模型/variant 聚合 token 数、调用次数、费用
     * @param startDate 开始时间
     * @param endDate 结束时间
     * @param groupBy 分组方式
     * @param model 按模型筛选
     * @param projectId 按项目筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    static getAiUsageAggregatesV1AiUsageAggregatesGet(startDate?: (string | null), endDate?: (string | null), groupBy?: (string | null), model?: (string | null), projectId?: (string | null)): CancelablePromise<Record<string, any>>;
    /**
     * 获取项目AI使用
     * 某项目维度的 AI 使用情况
     * @param projectId
     * @param startDate 开始时间
     * @param endDate 结束时间
     * @param groupBy 分组方式
     * @returns any Successful Response
     * @throws ApiError
     */
    static getProjectAiUsageV1AiUsageProjectsProjectIdGet(projectId: string, startDate?: (string | null), endDate?: (string | null), groupBy?: (string | null)): CancelablePromise<Record<string, any>>;
    /**
     * 获取模型使用统计
     * 获取各模型使用统计
     * @param period 统计周期
     * @param limit 返回数量限制
     * @returns any Successful Response
     * @throws ApiError
     */
    static getModelUsageStatsV1AiUsageModelsUsageGet(period?: (string | null), limit?: (number | null)): CancelablePromise<Record<string, any>>;
    /**
     * 获取当前计费周期
     * 获取当前计费周期的AI使用情况
     * @returns any Successful Response
     * @throws ApiError
     */
    static getCurrentBillingCycleV1AiUsageBillingCurrentGet(): CancelablePromise<Record<string, any>>;
    /**
     * 获取AI使用预警
     * 获取AI使用预警和限额提醒
     * @returns any Successful Response
     * @throws ApiError
     */
    static getAiUsageAlertsV1AiUsageAlertsGet(): CancelablePromise<Record<string, any>>;
    /**
     * 导出AI使用报告
     * 导出AI使用报告
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static exportAiUsageReportV1AiUsageExportPost(requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
}
