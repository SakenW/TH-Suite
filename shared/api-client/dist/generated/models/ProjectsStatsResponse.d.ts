/**
 * 项目统计响应模型
 */
export type ProjectsStatsResponse = {
    total: number;
    status_distribution: Record<string, number>;
};
