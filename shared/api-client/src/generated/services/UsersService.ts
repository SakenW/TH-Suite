/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UsersService {
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
    public static listUsersV1UsersGet(
        page: number = 1,
        size: number = 20,
        search?: (string | null),
        role?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/',
            query: {
                'page': page,
                'size': size,
                'search': search,
                'role': role,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建用户
     * 创建用户（租户管理员用）
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createUserV1UsersPost(
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/users/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取用户详情
     * 获取用户基础资料
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getUserV1UsersUserIdGet(
        userId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/{user_id}',
            path: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新用户信息
     * 更新用户基础资料
     * @param userId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateUserV1UsersUserIdPatch(
        userId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/v1/users/{user_id}',
            path: {
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 删除用户
     * 删除用户
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteUserV1UsersUserIdDelete(
        userId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/users/{user_id}',
            path: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取用户会话
     * 查看该用户的活跃会话 (Not Implemented yet)
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getUserSessionsV1UsersUserIdSessionsGet(
        userId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/{user_id}/sessions',
            path: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 激活用户
     * 激活用户 (Shortcut for update status)
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static activateUserV1UsersUserIdActivatePost(
        userId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/users/{user_id}/activate',
            path: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 停用用户
     * 停用用户 (Shortcut for update status)
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deactivateUserV1UsersUserIdDeactivatePost(
        userId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/users/{user_id}/deactivate',
            path: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
