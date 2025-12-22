/**
 * 批量导入请求
 */
export type ImportBatchRequest = {
    type: string;
    data: Array<Record<string, any>>;
    metadata?: (Record<string, any> | null);
};
