/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PricingQuoteResponse } from '../models/PricingQuoteResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PricingService {
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
    public static getQuoteV1PricingQuoteGet(
        strategy: string,
        inputTokens: number,
        outputTokens: number,
    ): CancelablePromise<PricingQuoteResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/pricing/quote',
            query: {
                'strategy': strategy,
                'input_tokens': inputTokens,
                'output_tokens': outputTokens,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
