import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class IngestionTasksService {
    /**
     * 获取任务状态
     * 查询导入/导出任务状态
     * @param taskId
     * @returns any Successful Response
     * @throws ApiError
     */
    static getTaskStatusV1TasksTaskIdGet(taskId) {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/tasks/{task_id}',
            path: {
                'task_id': taskId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取任务错误详情
     * 查询任务错误详情
     * @param taskId
     * @returns any Successful Response
     * @throws ApiError
     */
    static getTaskErrorsV1TasksTaskIdErrorsGet(taskId) {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/tasks/{task_id}/errors',
            path: {
                'task_id': taskId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
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
    static submitImportBatchV1TasksImportPost(requestBody) {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/tasks/import',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
