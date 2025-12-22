import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StatsService {
    /**
     * Get Backend Asset Stats
     * 获取后端翻译内存资产统计
     * @returns AssetStatsResponse Successful Response
     * @throws ApiError
     */
    static getBackendAssetStatsV1StatsAssetsBackendGet() {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/stats/assets/backend',
        });
    }
    /**
     * Get System Database Status
     * 获取系统数据库状态
     * @returns SystemStatusResponse Successful Response
     * @throws ApiError
     */
    static getSystemDatabaseStatusV1StatsSystemDbGet() {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/stats/system/db',
        });
    }
    /**
     * Get Segments Statistics
     * 获取段落详细统计
     * @returns SegmentsStatsResponse Successful Response
     * @throws ApiError
     */
    static getSegmentsStatisticsV1StatsSegmentsStatsGet() {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/stats/segments/stats',
        });
    }
    /**
     * Get Projects Statistics
     * 获取项目详细统计
     * @returns ProjectsStatsResponse Successful Response
     * @throws ApiError
     */
    static getProjectsStatisticsV1StatsProjectsStatsGet() {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/stats/projects/stats',
        });
    }
    /**
     * Get Languages Distribution
     * 获取语言分布统计
     * @returns any Successful Response
     * @throws ApiError
     */
    static getLanguagesDistributionV1StatsLanguagesDistributionGet() {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/stats/languages/distribution',
        });
    }
    /**
     * Get System Overview
     * 获取系统概览
     * @returns any Successful Response
     * @throws ApiError
     */
    static getSystemOverviewV1StatsOverviewGet() {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/stats/overview',
        });
    }
}
