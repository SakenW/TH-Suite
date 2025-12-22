import type { BalanceResponse } from '../models/BalanceResponse';
import type { TopUpRequest } from '../models/TopUpRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
export declare class BillingService {
    /**
     * 获取余额
     * 获取当前租户余额
     * @returns BalanceResponse Successful Response
     * @throws ApiError
     */
    static getBalanceV1BillingBalanceGet(): CancelablePromise<BalanceResponse>;
    /**
     * 获取账单流水
     * 获取账单流水记录
     * @param limit
     * @param offset
     * @returns BalanceResponse Successful Response
     * @throws ApiError
     */
    static getLedgerV1BillingLedgerGet(limit?: number, offset?: number): CancelablePromise<BalanceResponse>;
    /**
     * 充值余额 (Admin/Dev)
     * 手动充值接口（测试/管理员专用）
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    static topUpBalanceV1BillingTopUpPost(requestBody: TopUpRequest): CancelablePromise<any>;
}
