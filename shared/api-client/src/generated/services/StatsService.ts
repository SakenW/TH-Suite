/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AssetStatsResponse } from '../models/AssetStatsResponse';
import type { ProjectsStatsResponse } from '../models/ProjectsStatsResponse';
import type { SegmentsStatsResponse } from '../models/SegmentsStatsResponse';
import type { SystemStatusResponse } from '../models/SystemStatusResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StatsService {
    /**
     * Get Backend Asset Stats
     * 获取后端翻译内存资产统计
     * @returns AssetStatsResponse Successful Response
     * @throws ApiError
     */
    public static getBackendAssetStatsV1StatsAssetsBackendGet(): CancelablePromise<AssetStatsResponse> {
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
    public static getSystemDatabaseStatusV1StatsSystemDbGet(): CancelablePromise<SystemStatusResponse> {
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
    public static getSegmentsStatisticsV1StatsSegmentsStatsGet(): CancelablePromise<SegmentsStatsResponse> {
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
    public static getProjectsStatisticsV1StatsProjectsStatsGet(): CancelablePromise<ProjectsStatsResponse> {
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
    public static getLanguagesDistributionV1StatsLanguagesDistributionGet(): CancelablePromise<any> {
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
    public static getSystemOverviewV1StatsOverviewGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/stats/overview',
        });
    }
}
