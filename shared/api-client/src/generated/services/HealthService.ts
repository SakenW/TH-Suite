/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class HealthService {
    /**
     * 健康检查
     * 健康检查接口 - 使用真实数据库连接（infra 级检查）
     *
     * - 这里使用 raw SQL 非常合理，因为它本身验证的是基础设施可用性：
     * - 连接池可用
     * - RLS 初始化不报错
     * - 当前 schema 存在
     * @returns any Successful Response
     * @throws ApiError
     */
    public static healthCheckV1HealthGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/health',
        });
    }
    /**
     * 就绪探针
     * K8s 就绪探针
     *
     * - 可用于检查关键表/扩展是否已创建
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readinessProbeV1ReadinessGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/readiness',
        });
    }
}
