/**
 * 段落统计响应模型
 */
export type SegmentsStatsResponse = {
    total: number;
    status_distribution: Record<string, number>;
};
