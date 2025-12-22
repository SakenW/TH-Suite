import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ProvidersService {
    /**
     * 获取服务商列表
     * 列出支持的翻译服务商及模型
     * @returns ProviderInfoDTO Successful Response
     * @throws ApiError
     */
    static listProvidersV1ProvidersGet() {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/providers',
        });
    }
}
