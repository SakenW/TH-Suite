/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiKeyLoginRequest } from '../models/ApiKeyLoginRequest';
import type { LoginRequest } from '../models/LoginRequest';
import type { LoginResponse } from '../models/LoginResponse';
import type { LogoutResponse } from '../models/LogoutResponse';
import type { RefreshTokenRequest } from '../models/RefreshTokenRequest';
import type { RefreshTokenResponse } from '../models/RefreshTokenResponse';
import type { RegisterRequest } from '../models/RegisterRequest';
import type { RegisterResponse } from '../models/RegisterResponse';
import type { UserInfo } from '../models/UserInfo';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthService {
    /**
     * 用户注册 (个人空间)
     * 注册新用户并创建个人空间 (Personal Workspace)
     * @param requestBody
     * @returns RegisterResponse Successful Response
     * @throws ApiError
     */
    public static registerV1AuthRegisterPost(
        requestBody: RegisterRequest,
    ): CancelablePromise<RegisterResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/auth/register',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 密码登录
     * 用户名/邮箱 + 密码登录，生成 access_token + refresh_token
     *
     * Args:
     * request: 登录请求，包含 username/email 和 password
     * uow: 工作单元（提供事务和RLS）
     * auth_use_cases: 认证用例实例
     *
     * Returns:
     * 包含 access_token, refresh_token, user_info 的响应
     *
     * Raises:
     * HTTPException: 认证失败时返回401错误
     * @param requestBody
     * @returns LoginResponse Successful Response
     * @throws ApiError
     */
    public static loginPasswordV1AuthLoginPasswordPost(
        requestBody: LoginRequest,
    ): CancelablePromise<LoginResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/auth/login/password',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * API Key登录
     * 用 API Key 换 JWT，面向服务端集成
     * @param requestBody
     * @returns LoginResponse Successful Response
     * @throws ApiError
     */
    public static loginApiKeyV1AuthLoginApiKeyPost(
        requestBody: ApiKeyLoginRequest,
    ): CancelablePromise<LoginResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/auth/login/api-key',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 刷新令牌
     * 用 refresh_token 换新 access_token
     *
     * Args:
     * request: 刷新令牌请求
     * uow: 工作单元（提供事务和RLS）
     * auth_use_cases: 认证用例实例
     *
     * Returns:
     * 包含新 access_token 的响应
     *
     * Raises:
     * HTTPException: 令牌刷新失败时返回401错误
     * @param requestBody
     * @returns RefreshTokenResponse Successful Response
     * @throws ApiError
     */
    public static refreshTokenV1AuthTokenRefreshPost(
        requestBody: RefreshTokenRequest,
    ): CancelablePromise<RefreshTokenResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/auth/token/refresh',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 登出
     * 失效当前 token / 会话
     *
     * Args:
     * token: 访问令牌
     * uow: 工作单元（提供事务和RLS）
     * auth_use_cases: 认证用例实例
     *
     * Returns:
     * 登出成功响应
     *
     * Raises:
     * HTTPException: 令牌无效时返回401错误
     * @returns LogoutResponse Successful Response
     * @throws ApiError
     */
    public static logoutV1AuthLogoutPost(): CancelablePromise<LogoutResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/auth/logout',
        });
    }
    /**
     * 获取当前用户信息
     * 返回当前用户信息与租户信息
     *
     * Args:
     * token: 访问令牌
     * uow: 工作单元（提供事务和RLS）
     * auth_use_cases: 认证用例实例
     *
     * Returns:
     * 用户信息响应
     *
     * Raises:
     * HTTPException: 令牌无效时返回401错误
     * @returns UserInfo Successful Response
     * @throws ApiError
     */
    public static getCurrentUserV1AuthMeGet(): CancelablePromise<UserInfo> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/auth/me',
        });
    }
    /**
     * 请求重置密码
     * 发起重置密码，生成 reset token
     *
     * Args:
     * email: 用户邮箱
     * uow: 工作单元（提供事务和RLS）
     *
     * Returns:
     * 重置请求响应
     * @param email
     * @returns any Successful Response
     * @throws ApiError
     */
    public static requestPasswordResetV1AuthPasswordResetRequestPost(
        email: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/auth/password/reset/request',
            query: {
                'email': email,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 确认重置密码
     * 用 reset token 更新密码
     *
     * Args:
     * reset_token: 重置令牌
     * new_password: 新密码
     * uow: 工作单元（提供事务和RLS）
     *
     * Returns:
     * 密码重置响应
     * @param resetToken
     * @param newPassword
     * @returns any Successful Response
     * @throws ApiError
     */
    public static confirmPasswordResetV1AuthPasswordResetConfirmPost(
        resetToken: string,
        newPassword: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/auth/password/reset/confirm',
            query: {
                'reset_token': resetToken,
                'new_password': newPassword,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
