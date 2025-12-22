/**
 * 资产统计响应模型
 */
export type AssetStatsResponse = {
    segments: number;
    projects: number;
    languages: number;
    translations: number;
    last_updated: string;
};
