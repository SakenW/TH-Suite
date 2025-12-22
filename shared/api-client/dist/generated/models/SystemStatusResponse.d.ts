/**
 * 系统状态响应模型
 */
export type SystemStatusResponse = {
    status: string;
    response_time: number;
    timestamp: string;
    db_size: string;
    active_connections: number;
};
