/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TenantCreateDTO } from '../models/TenantCreateDTO';
import type { TenantUpdateDTO } from '../models/TenantUpdateDTO';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TenantsService {
    /**
     * 获取当前租户信息
     * 返回当前 tenant 的基础配置
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCurrentTenantV1TenantsCurrentGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/tenants/current',
        });
    }
    /**
     * 更新当前租户信息
     * 租户管理员修改部分资料
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateCurrentTenantV1TenantsCurrentPut(
        requestBody: TenantUpdateDTO,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/tenants/current',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取租户列表 (Admin)
     * 全局管理：多租户列表
     * @param page 页码
     * @param size 每页数量
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listAllTenantsV1TenantsAdminGet(
        page: number = 1,
        size: number = 20,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/tenants/admin/',
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
     * 创建租户（管理员）
     * 创建新租户
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createTenantV1TenantsAdminPost(
        requestBody: TenantCreateDTO,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/tenants/admin/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新特定租户 (Admin)
     * 全局管理：更新指定租户
     * @param tenantId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateTenantByIdV1TenantsAdminTenantIdPatch(
        tenantId: string,
        requestBody: TenantUpdateDTO,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/v1/tenants/admin/{tenant_id}',
            path: {
                'tenant_id': tenantId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
