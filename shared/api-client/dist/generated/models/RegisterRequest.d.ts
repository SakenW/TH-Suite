/**
 * 注册请求模型
 */
export type RegisterRequest = {
    /**
     * 用户名 (小写字母数字)
     */
    username: string;
    /**
     * 邮箱
     */
    email: string;
    /**
     * 密码
     */
    password: string;
    /**
     * 显示名称
     */
    display_name?: (string | null);
};
