export type TMSearchRequest = {
    /**
     * Text to search for
     */
    query: string;
    /**
     * Source language code (e.g. en)
     */
    source_lang: string;
    /**
     * Target language code (e.g. zh)
     */
    target_lang: string;
    /**
     * Max results to return
     */
    limit?: number;
    /**
     * Minimum similarity score
     */
    min_score?: number;
    /**
     * Optional tenant override (usually from auth)
     */
    tenant_id?: (string | null);
};
