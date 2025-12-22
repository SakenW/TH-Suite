import type { TenantCreateDTO } from '../models/TenantCreateDTO';
import type { TenantUpdateDTO } from '../models/TenantUpdateDTO';
import type { CancelablePromise } from '../core/CancelablePromise';
export declare class TenantsService {
    /**
     * 获取当前租户信息
     * 返回当前 tenant 的基础配置
     * @returns any Successful Response
     * @throws ApiError
     */
    static getCurrentTenantV1TenantsCurrentGet(): CancelablePromise<Record<string, any>>;
    /**
     * 更新当前租户信息
     * 租户管理员修改部分资料
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static updateCurrentTenantV1TenantsCurrentPut(requestBody: TenantUpdateDTO): CancelablePromise<Record<string, any>>;
    /**
     * 获取租户列表 (Admin)
     * 全局管理：多租户列表
     * @param page 页码
     * @param size 每页数量
     * @returns any Successful Response
     * @throws ApiError
     */
    static listAllTenantsV1TenantsAdminGet(page?: number, size?: number): CancelablePromise<Record<string, any>>;
    /**
     * 创建租户（管理员）
     * 创建新租户
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static createTenantV1TenantsAdminPost(requestBody: TenantCreateDTO): CancelablePromise<Record<string, any>>;
    /**
     * 更新特定租户 (Admin)
     * 全局管理：更新指定租户
     * @param tenantId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static updateTenantByIdV1TenantsAdminTenantIdPatch(tenantId: string, requestBody: TenantUpdateDTO): CancelablePromise<Record<string, any>>;
}
