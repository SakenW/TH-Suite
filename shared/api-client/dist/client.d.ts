export interface ApiConfig {
    baseUrl: string;
    getToken?: () => Promise<string | null>;
}
export declare class TransHubClient {
    private config;
    constructor(config: ApiConfig);
    private getHeaders;
    fetch<T>(path: string, options?: RequestInit): Promise<T>;
    importSegments(jobId: string, segments: AsyncIterable<any> | Iterable<any>): Promise<any>;
    exportSegments(jobId: string): AsyncGenerator<any>;
}
