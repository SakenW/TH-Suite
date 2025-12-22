/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class GlossariesService {
    /**
     * 获取术语库列表
     * 获取术语库列表
     * @param page 页码
     * @param size 每页数量
     * @param search 搜索关键词
     * @param sourceLanguage 源语言筛选
     * @param targetLanguage 目标语言筛选
     * @param domain 按领域筛选
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listGlossariesV1GlossariesGet(
        page: number = 1,
        size: number = 20,
        search?: (string | null),
        sourceLanguage?: (string | null),
        targetLanguage?: (string | null),
        domain?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/glossaries/',
            query: {
                'page': page,
                'size': size,
                'search': search,
                'source_language': sourceLanguage,
                'target_language': targetLanguage,
                'domain': domain,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建术语库
     * 创建术语库
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createGlossaryV1GlossariesPost(
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/glossaries/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取术语库详情
     * 获取术语库详情
     * @param glossaryId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getGlossaryV1GlossariesGlossaryIdGet(
        glossaryId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/glossaries/{glossary_id}',
            path: {
                'glossary_id': glossaryId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新术语库
     * 更新术语库
     * @param glossaryId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateGlossaryV1GlossariesGlossaryIdPatch(
        glossaryId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/v1/glossaries/{glossary_id}',
            path: {
                'glossary_id': glossaryId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 删除术语库
     * 删除术语库
     * @param glossaryId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteGlossaryV1GlossariesGlossaryIdDelete(
        glossaryId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/glossaries/{glossary_id}',
            path: {
                'glossary_id': glossaryId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取术语条目
     * 获取术语条目列表
     * @param glossaryId
     * @param page 页码
     * @param size 每页数量
     * @param search 搜索关键词
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getGlossaryEntriesV1GlossariesGlossaryIdEntriesGet(
        glossaryId: string,
        page: number = 1,
        size: number = 50,
        search?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/glossaries/{glossary_id}/entries',
            path: {
                'glossary_id': glossaryId,
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
     * 添加术语条目
     * 添加术语条目
     * @param glossaryId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static addGlossaryEntryV1GlossariesGlossaryIdEntriesPost(
        glossaryId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/glossaries/{glossary_id}/entries',
            path: {
                'glossary_id': glossaryId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 术语查找
     * 术语查找
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static lookupGlossaryV1GlossariesLookupPost(
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/glossaries/lookup',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取语言回退链
     * 获取语言回退链
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getLocaleFallbacksV1GlossariesLocalesFallbacksGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/glossaries/locales/fallbacks',
        });
    }
    /**
     * 获取变体维度
     * 获取变体维度定义
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getVariantDimensionsV1GlossariesVariantsDimensionsGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/glossaries/variants/dimensions',
        });
    }
}
