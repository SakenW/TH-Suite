import type { TMSearchRequest } from '../models/TMSearchRequest';
import type { TMSearchResponse } from '../models/TMSearchResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
export declare class TranslationMemoryService {
    /**
     * 向量检索 (Semantic Search)
     * 语义检索 TM (Vector Search)
     * 使用 pgvector 进行余弦相似度匹配。
     * @param requestBody
     * @returns TMSearchResponse Successful Response
     * @throws ApiError
     */
    static vectorSearchV1TmSearchVectorPost(requestBody: TMSearchRequest): CancelablePromise<TMSearchResponse>;
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
    static listLibrariesV1TmGet(page?: number, size?: number, sourceLanguage?: (string | null), targetLanguage?: (string | null)): CancelablePromise<Record<string, any>>;
    /**
     * 创建TM库
     * 创建新的 TM 库
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static createLibraryV1TmPost(requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
    /**
     * 获取TM库详情
     * 获取指定 TM 库详情
     * @param libraryId
     * @returns any Successful Response
     * @throws ApiError
     */
    static getLibraryV1TmLibraryIdGet(libraryId: string): CancelablePromise<Record<string, any>>;
    /**
     * 更新TM库
     * 更新 TM 库信息
     * @param libraryId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static updateLibraryV1TmLibraryIdPatch(libraryId: string, requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
    /**
     * 删除TM库
     * 删除 TM 库
     * @param libraryId
     * @returns any Successful Response
     * @throws ApiError
     */
    static deleteLibraryV1TmLibraryIdDelete(libraryId: string): CancelablePromise<Record<string, any>>;
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
    static listUnitsV1TmLibraryIdUnitsGet(libraryId: string, page?: number, size?: number, search?: (string | null)): CancelablePromise<Record<string, any>>;
    /**
     * 添加TM条目
     * 向指定 TM 库添加条目
     * @param libraryId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static addUnitV1TmLibraryIdUnitsPost(libraryId: string, requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
    /**
     * TM查找
     * 模糊匹配查找 (Concordance Search)
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static lookupTmV1TmLookupPost(requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
    /**
     * TM导入
     * 导入 TMX 到指定库
     * @param libraryId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static importTmV1TmLibraryIdImportPost(libraryId: string, requestBody: Record<string, any>): CancelablePromise<Record<string, any>>;
    /**
     * TM导出
     * 导出 TM 库为 TMX
     * @param libraryId
     * @returns any Successful Response
     * @throws ApiError
     */
    static exportTmV1TmLibraryIdExportGet(libraryId: string): CancelablePromise<Record<string, any>>;
}
