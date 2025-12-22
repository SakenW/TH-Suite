import type { ImportBatchRequest } from '../models/ImportBatchRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
export declare class IngestionTasksService {
    /**
     * 获取任务状态
     * 查询导入/导出任务状态
     * @param taskId
     * @returns any Successful Response
     * @throws ApiError
     */
    static getTaskStatusV1TasksTaskIdGet(taskId: string): CancelablePromise<Record<string, any>>;
    /**
     * 获取任务错误详情
     * 查询任务错误详情
     * @param taskId
     * @returns any Successful Response
     * @throws ApiError
     */
    static getTaskErrorsV1TasksTaskIdErrorsGet(taskId: string): CancelablePromise<Record<string, any>>;
    /**
     * 提交批量导入任务
     * 提交批量导入任务 (JSON Batch).
     *
     * 接收前端解析后的结构化数据，将其序列化为临时文件 (NDJSON)，
     * 然后创建后台导入任务进行处理。
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static submitImportBatchV1TasksImportPost(requestBody: ImportBatchRequest): CancelablePromise<Record<string, any>>;
}
