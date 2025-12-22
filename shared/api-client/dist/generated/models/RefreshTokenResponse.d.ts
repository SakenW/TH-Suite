/**
 * 刷新令牌响应模型
 */
export type RefreshTokenResponse = {
    /**
     * 新的访问令牌
     */
    access_token: string;
    /**
     * 新的刷新令牌
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
};
