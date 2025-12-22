/**
 * Request for manual top-up.
 */
export type TopUpRequest = {
    amount_thbc: (number | string);
    reason?: string;
};
