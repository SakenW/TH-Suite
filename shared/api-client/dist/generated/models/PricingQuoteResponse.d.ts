/**
 * Response for pricing quote.
 */
export type PricingQuoteResponse = {
    strategy: string;
    total_cost: string;
    currency: string;
    unit_price_input: string;
    unit_price_output: string;
    is_estimated?: boolean;
};
