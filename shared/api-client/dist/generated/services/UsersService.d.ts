import type { CancelablePromise } from '../core/CancelablePromise';
export declare class UsersService {
    /**
     * 获取用户列表
     * 列出当前租户下的用户（tenant-scoped）
     * @param page 页码
     * @param size 每页数量
     * @param search 搜索关键词
     * @param role 按角色筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    static listUsersV1UsersGet(page?: number, size?: number, search?: (string | null), role?: (string | null)): CancelablePromise<Record<string, any>>;
    /**
     * 创建用户
     * 创建用户（租户管理员用）
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static createUserV1UsersPost(requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
    /**
     * 获取用户详情
     * 获取用户基础资料
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    static getUserV1UsersUserIdGet(userId: string): CancelablePromise<Record<string, any>>;
    /**
     * 更新用户信息
     * 更新用户基础资料
     * @param userId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static updateUserV1UsersUserIdPatch(userId: string, requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
    /**
     * 删除用户
     * 删除用户
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    static deleteUserV1UsersUserIdDelete(userId: string): CancelablePromise<Record<string, any>>;
    /**
     * 获取用户会话
     * 查看该用户的活跃会话 (Not Implemented yet)
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    static getUserSessionsV1UsersUserIdSessionsGet(userId: string): CancelablePromise<Record<string, any>>;
    /**
     * 激活用户
     * 激活用户 (Shortcut for update status)
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    static activateUserV1UsersUserIdActivatePost(userId: string): CancelablePromise<Record<string, any>>;
    /**
     * 停用用户
     * 停用用户 (Shortcut for update status)
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    static deactivateUserV1UsersUserIdDeactivatePost(userId: string): CancelablePromise<Record<string, any>>;
}
