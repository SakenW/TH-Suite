/**
 * 创建项目请求模型。
 */
export type ProjectCreate = {
    /**
     * 项目名称
     */
    name: string;
    /**
     * 项目描述
     */
    description?: (string | null);
    /**
     * 源语言代码，如 zh-CN
     */
    source_language: string;
    /**
     * 目标语言代码列表，如 ['en-US', 'ja-JP']
     */
    target_languages: Array<string>;
};
