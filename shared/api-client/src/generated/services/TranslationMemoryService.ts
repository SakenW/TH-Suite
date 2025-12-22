/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TMSearchRequest } from '../models/TMSearchRequest';
import type { TMSearchResponse } from '../models/TMSearchResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TranslationMemoryService {
    /**
     * 向量检索 (Semantic Search)
     * 语义检索 TM (Vector Search)
     * 使用 pgvector 进行余弦相似度匹配。
     * @param requestBody
     * @returns TMSearchResponse Successful Response
     * @throws ApiError
     */
    public static vectorSearchV1TmSearchVectorPost(
        requestBody: TMSearchRequest,
    ): CancelablePromise<TMSearchResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/tm/search/vector',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取TM库列表
     * 获取当前租户的 TM 库列表
     * @param page 页码
     * @param size 每页数量
     * @param sourceLanguage 源语言筛选
     * @param targetLanguage 目标语言筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listLibrariesV1TmGet(
        page: number = 1,
        size: number = 20,
        sourceLanguage?: (string | null),
        targetLanguage?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/tm/',
            query: {
                'page': page,
                'size': size,
                'source_language': sourceLanguage,
                'target_language': targetLanguage,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建TM库
     * 创建新的 TM 库
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createLibraryV1TmPost(
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/tm/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取TM库详情
     * 获取指定 TM 库详情
     * @param libraryId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getLibraryV1TmLibraryIdGet(
        libraryId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/tm/{library_id}',
            path: {
                'library_id': libraryId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新TM库
     * 更新 TM 库信息
     * @param libraryId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateLibraryV1TmLibraryIdPatch(
        libraryId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/v1/tm/{library_id}',
            path: {
                'library_id': libraryId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 删除TM库
     * 删除 TM 库
     * @param libraryId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteLibraryV1TmLibraryIdDelete(
        libraryId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/tm/{library_id}',
            path: {
                'library_id': libraryId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取TM条目列表
     * 查询该 TM 库下的条目
     * @param libraryId
     * @param page 页码
     * @param size 每页数量
     * @param search 搜索关键词
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listUnitsV1TmLibraryIdUnitsGet(
        libraryId: string,
        page: number = 1,
        size: number = 50,
        search?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/tm/{library_id}/units',
            path: {
                'library_id': libraryId,
            },
            query: {
                'page': page,
                'size': size,
                'search': search,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 添加TM条目
     * 向指定 TM 库添加条目
     * @param libraryId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static addUnitV1TmLibraryIdUnitsPost(
        libraryId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/tm/{library_id}/units',
            path: {
                'library_id': libraryId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * TM查找
     * 模糊匹配查找 (Concordance Search)
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static lookupTmV1TmLookupPost(
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/tm/lookup',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * TM导入
     * 导入 TMX 到指定库
     * @param libraryId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static importTmV1TmLibraryIdImportPost(
        libraryId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/tm/{library_id}/import',
            path: {
                'library_id': libraryId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * TM导出
     * 导出 TM 库为 TMX
     * @param libraryId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static exportTmV1TmLibraryIdExportGet(
        libraryId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/tm/{library_id}/export',
            path: {
                'library_id': libraryId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
