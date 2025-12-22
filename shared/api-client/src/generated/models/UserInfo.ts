/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 用户信息模型
 */
export type UserInfo = {
    /**
     * 用户ID
     */
    id: string;
    /**
     * 邮箱
     */
    email: string;
    /**
     * 用户名
     */
    username: string;
    /**
     * 显示名称
     */
    display_name?: (string | null);
    /**
     * 用户角色（当前上下文）
     */
    role: string;
    /**
     * 当前租户ID
     */
    tenant_id?: (string | null);
    /**
     * 可访问的租户列表
     */
    available_tenants?: Array<Record<string, any>>;
    /**
     * 用户状态
     */
    status: string;
};

