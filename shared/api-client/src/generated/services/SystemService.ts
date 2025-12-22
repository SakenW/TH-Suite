/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SystemService {
    /**
     * 获取系统配置
     * 查看当前系统配置（只暴露安全字段）
     * @param category 按分类筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getSystemConfigsV1SystemConfigsGet(
        category?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/system/configs',
            query: {
                'category': category,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 详细健康检查
     * 详细的系统健康检查
     * @returns any Successful Response
     * @throws ApiError
     */
    public static detailedHealthCheckV1SystemHealthDetailedGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/system/health/detailed',
        });
    }
    /**
     * 获取审计日志
     * 查询审计日志（谁在什么时候对哪些资源做了什么）
     * @param page 页码
     * @param size 每页数量
     * @param startDate 开始时间
     * @param endDate 结束时间
     * @param userId 按用户筛选
     * @param resourceType 按资源类型筛选
     * @param action 按操作类型筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAuditEventsV1SystemAuditEventsGet(
        page: number = 1,
        size: number = 50,
        startDate?: (string | null),
        endDate?: (string | null),
        userId?: (string | null),
        resourceType?: (string | null),
        action?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/system/audit-events',
            query: {
                'page': page,
                'size': size,
                'start_date': startDate,
                'end_date': endDate,
                'user_id': userId,
                'resource_type': resourceType,
                'action': action,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取分区配置
     * 查看分区配置与维护事件（内部/运维面板用）
     * @param tableName 按表筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getPartitionConfigsV1SystemPartitionsGet(
        tableName?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/system/partitions',
            query: {
                'table_name': tableName,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取迁移状态
     * 返回 alembic 当前版本 / head 版本对比信息
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getMigrationStatusV1SystemMigrationsGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/system/migrations',
        });
    }
    /**
     * 获取系统指标
     * 获取系统性能指标
     * @param metricType 指标类型
     * @param startTime 开始时间
     * @param endTime 结束时间
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getSystemMetricsV1SystemMetricsGet(
        metricType?: (string | null),
        startTime?: (string | null),
        endTime?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/system/metrics',
            query: {
                'metric_type': metricType,
                'start_time': startTime,
                'end_time': endTime,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取外部系统配置
     * 获取外部系统集成配置
     * @param systemType 按系统类型筛选
     * @param status 按状态筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getExternalSystemsV1SystemExternalSystemsGet(
        systemType?: (string | null),
        status?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/system/external-systems',
            query: {
                'system_type': systemType,
                'status': status,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 测试外部系统连接
     * 测试外部系统连接
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static testExternalConnectionV1SystemTestConnectionPost(
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/system/test-connection',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取系统版本信息
     * 获取系统版本信息
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getSystemVersionV1SystemVersionGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/system/version',
        });
    }
    /**
     * 获取缓存状态
     * 获取缓存系统状态
     * @param cacheType 按缓存类型筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCacheStatusV1SystemCacheStatusGet(
        cacheType?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/system/cache/status',
            query: {
                'cache_type': cacheType,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
