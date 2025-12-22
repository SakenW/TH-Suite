/**
 * Streaming utility for handling NDJSON + GZIP data.
 * Optimized for browser/webview environments (Stream API).
 */
export declare function streamNdjson<T>(response: Response): AsyncGenerator<T>;
export declare function createGzipNdjsonBody(data: Iterable<any> | AsyncIterable<any>): Promise<ReadableStream>;
