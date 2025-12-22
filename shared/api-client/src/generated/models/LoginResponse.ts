/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserInfo } from './UserInfo';
/**
 * 登录响应模型
 */
export type LoginResponse = {
    /**
     * 访问令牌
     */
    access_token: string;
    /**
     * 刷新令牌
     */
    refresh_token: string;
    /**
     * 令牌类型
     */
    token_type?: string;
    /**
     * 访问令牌过期时间（秒）
     */
    expires_in: number;
    /**
     * 用户信息
     */
    user: UserInfo;
};

