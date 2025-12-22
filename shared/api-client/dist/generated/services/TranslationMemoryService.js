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
    static vectorSearchV1TmSearchVectorPost(requestBody) {
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
    static listLibrariesV1TmGet(page = 1, size = 20, sourceLanguage, targetLanguage) {
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
    static createLibraryV1TmPost(requestBody) {
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
    static getLibraryV1TmLibraryIdGet(libraryId) {
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
    static updateLibraryV1TmLibraryIdPatch(libraryId, requestBody) {
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
    static deleteLibraryV1TmLibraryIdDelete(libraryId) {
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
    static listUnitsV1TmLibraryIdUnitsGet(libraryId, page = 1, size = 50, search) {
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
    static addUnitV1TmLibraryIdUnitsPost(libraryId, requestBody) {
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
    static lookupTmV1TmLookupPost(requestBody) {
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
    static importTmV1TmLibraryIdImportPost(libraryId, requestBody) {
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
    static exportTmV1TmLibraryIdExportGet(libraryId) {
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
