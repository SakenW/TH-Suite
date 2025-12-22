import type { ProjectStatus } from './ProjectStatus';
/**
 * 查询项目响应模型。
 */
export type ProjectRead = {
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
    id: string;
    tenant_id: string;
    /**
     * 项目状态
     */
    status?: ProjectStatus;
    created_at: string;
    updated_at: string;
};
