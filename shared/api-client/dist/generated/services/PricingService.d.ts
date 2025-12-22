import type { PricingQuoteResponse } from '../models/PricingQuoteResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
export declare class PricingService {
    /**
     * 获取报价
     * 获取翻译策略的预估报价。
     *
     * Args:
     * strategy: 策略标识, 例如 "openai:gpt-4o"
     * input_tokens: 预估输入 Token 数
     * output_tokens: 预估输出 Token 数
     * @param strategy
     * @param inputTokens
     * @param outputTokens
     * @returns PricingQuoteResponse Successful Response
     * @throws ApiError
     */
    static getQuoteV1PricingQuoteGet(strategy: string, inputTokens: number, outputTokens: number): CancelablePromise<PricingQuoteResponse>;
}
