/**
 * 注册响应模型
 */
export type RegisterResponse = {
    /**
     * 用户ID
     */
    user_id: string;
    /**
     * 用户名
     */
    username: string;
    /**
     * 租户ID
     */
    tenant_id: string;
    /**
     * 租户标识
     */
    tenant_slug: string;
    /**
     * 显示名称
     */
    display_name?: (string | null);
};
