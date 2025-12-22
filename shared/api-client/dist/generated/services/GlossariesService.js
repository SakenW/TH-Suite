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
    static listGlossariesV1GlossariesGet(page = 1, size = 20, search, sourceLanguage, targetLanguage, domain) {
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
    static createGlossaryV1GlossariesPost(requestBody) {
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
    static getGlossaryV1GlossariesGlossaryIdGet(glossaryId) {
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
    static updateGlossaryV1GlossariesGlossaryIdPatch(glossaryId, requestBody) {
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
    static deleteGlossaryV1GlossariesGlossaryIdDelete(glossaryId) {
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
    static getGlossaryEntriesV1GlossariesGlossaryIdEntriesGet(glossaryId, page = 1, size = 50, search) {
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
    static addGlossaryEntryV1GlossariesGlossaryIdEntriesPost(glossaryId, requestBody) {
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
    static lookupGlossaryV1GlossariesLookupPost(requestBody) {
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
    static getLocaleFallbacksV1GlossariesLocalesFallbacksGet() {
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
    static getVariantDimensionsV1GlossariesVariantsDimensionsGet() {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/glossaries/variants/dimensions',
        });
    }
}
