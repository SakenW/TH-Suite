import type { ProviderInfoDTO } from '../models/ProviderInfoDTO';
import type { CancelablePromise } from '../core/CancelablePromise';
export declare class ProvidersService {
    /**
     * 获取服务商列表
     * 列出支持的翻译服务商及模型
     * @returns ProviderInfoDTO Successful Response
     * @throws ApiError
     */
    static listProvidersV1ProvidersGet(): CancelablePromise<Array<ProviderInfoDTO>>;
}
