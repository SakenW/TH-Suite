import type { AssetStatsResponse } from '../models/AssetStatsResponse';
import type { ProjectsStatsResponse } from '../models/ProjectsStatsResponse';
import type { SegmentsStatsResponse } from '../models/SegmentsStatsResponse';
import type { SystemStatusResponse } from '../models/SystemStatusResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
export declare class StatsService {
    /**
     * Get Backend Asset Stats
     * 获取后端翻译内存资产统计
     * @returns AssetStatsResponse Successful Response
     * @throws ApiError
     */
    static getBackendAssetStatsV1StatsAssetsBackendGet(): CancelablePromise<AssetStatsResponse>;
    /**
     * Get System Database Status
     * 获取系统数据库状态
     * @returns SystemStatusResponse Successful Response
     * @throws ApiError
     */
    static getSystemDatabaseStatusV1StatsSystemDbGet(): CancelablePromise<SystemStatusResponse>;
    /**
     * Get Segments Statistics
     * 获取段落详细统计
     * @returns SegmentsStatsResponse Successful Response
     * @throws ApiError
     */
    static getSegmentsStatisticsV1StatsSegmentsStatsGet(): CancelablePromise<SegmentsStatsResponse>;
    /**
     * Get Projects Statistics
     * 获取项目详细统计
     * @returns ProjectsStatsResponse Successful Response
     * @throws ApiError
     */
    static getProjectsStatisticsV1StatsProjectsStatsGet(): CancelablePromise<ProjectsStatsResponse>;
    /**
     * Get Languages Distribution
     * 获取语言分布统计
     * @returns any Successful Response
     * @throws ApiError
     */
    static getLanguagesDistributionV1StatsLanguagesDistributionGet(): CancelablePromise<any>;
    /**
     * Get System Overview
     * 获取系统概览
     * @returns any Successful Response
     * @throws ApiError
     */
    static getSystemOverviewV1StatsOverviewGet(): CancelablePromise<any>;
}
