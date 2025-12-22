import type { CancelablePromise } from '../core/CancelablePromise';
export declare class HealthService {
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
    static healthCheckV1HealthGet(): CancelablePromise<Record<string, any>>;
    /**
     * 就绪探针
     * K8s 就绪探针
     *
     * - 可用于检查关键表/扩展是否已创建
     * @returns any Successful Response
     * @throws ApiError
     */
    static readinessProbeV1ReadinessGet(): CancelablePromise<Record<string, any>>;
}
