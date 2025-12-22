import type { QuotaBucketDTO } from './QuotaBucketDTO';
/**
 * Response for balance check.
 */
export type BalanceResponse = {
    tenant_id: string;
    balance_thbc: string;
    currency?: string;
    quota_buckets?: Array<QuotaBucketDTO>;
    is_frozen?: boolean;
};
