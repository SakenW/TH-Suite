import type { CancelablePromise } from '../core/CancelablePromise';
export declare class GlossariesService {
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
    static listGlossariesV1GlossariesGet(page?: number, size?: number, search?: (string | null), sourceLanguage?: (string | null), targetLanguage?: (string | null), domain?: (string | null)): CancelablePromise<Record<string, any>>;
    /**
     * 创建术语库
     * 创建术语库
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static createGlossaryV1GlossariesPost(requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
    /**
     * 获取术语库详情
     * 获取术语库详情
     * @param glossaryId
     * @returns any Successful Response
     * @throws ApiError
     */
    static getGlossaryV1GlossariesGlossaryIdGet(glossaryId: string): CancelablePromise<Record<string, any>>;
    /**
     * 更新术语库
     * 更新术语库
     * @param glossaryId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static updateGlossaryV1GlossariesGlossaryIdPatch(glossaryId: string, requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
    /**
     * 删除术语库
     * 删除术语库
     * @param glossaryId
     * @returns any Successful Response
     * @throws ApiError
     */
    static deleteGlossaryV1GlossariesGlossaryIdDelete(glossaryId: string): CancelablePromise<Record<string, any>>;
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
    static getGlossaryEntriesV1GlossariesGlossaryIdEntriesGet(glossaryId: string, page?: number, size?: number, search?: (string | null)): CancelablePromise<Record<string, any>>;
    /**
     * 添加术语条目
     * 添加术语条目
     * @param glossaryId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static addGlossaryEntryV1GlossariesGlossaryIdEntriesPost(glossaryId: string, requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
    /**
     * 术语查找
     * 术语查找
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static lookupGlossaryV1GlossariesLookupPost(requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
    /**
     * 获取语言回退链
     * 获取语言回退链
     * @returns any Successful Response
     * @throws ApiError
     */
    static getLocaleFallbacksV1GlossariesLocalesFallbacksGet(): CancelablePromise<Record<string, any>>;
    /**
     * 获取变体维度
     * 获取变体维度定义
     * @returns any Successful Response
     * @throws ApiError
     */
    static getVariantDimensionsV1GlossariesVariantsDimensionsGet(): CancelablePromise<Record<string, any>>;
}
