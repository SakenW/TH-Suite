/**
 * 登录请求模型
 */
export type LoginRequest = {
    /**
     * 用户名或邮箱
     */
    username_or_email: string;
    /**
     * 密码
     */
    password: string;
    /**
     * 租户ID（可选）
     */
    tenant_id?: (string | null);
};
