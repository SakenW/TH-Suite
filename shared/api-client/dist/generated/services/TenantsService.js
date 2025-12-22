import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TenantsService {
    /**
     * 获取当前租户信息
     * 返回当前 tenant 的基础配置
     * @returns any Successful Response
     * @throws ApiError
     */
    static getCurrentTenantV1TenantsCurrentGet() {
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
    static updateCurrentTenantV1TenantsCurrentPut(requestBody) {
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
    static listAllTenantsV1TenantsAdminGet(page = 1, size = 20) {
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
    static createTenantV1TenantsAdminPost(requestBody) {
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
    static updateTenantByIdV1TenantsAdminTenantIdPatch(tenantId, requestBody) {
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
