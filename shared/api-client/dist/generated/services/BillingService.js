import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class BillingService {
    /**
     * 获取余额
     * 获取当前租户余额
     * @returns BalanceResponse Successful Response
     * @throws ApiError
     */
    static getBalanceV1BillingBalanceGet() {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/billing/balance',
        });
    }
    /**
     * 获取账单流水
     * 获取账单流水记录
     * @param limit
     * @param offset
     * @returns BalanceResponse Successful Response
     * @throws ApiError
     */
    static getLedgerV1BillingLedgerGet(limit = 50, offset) {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/billing/ledger',
            query: {
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 充值余额 (Admin/Dev)
     * 手动充值接口（测试/管理员专用）
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static topUpBalanceV1BillingTopUpPost(requestBody) {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/billing/top-up',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
