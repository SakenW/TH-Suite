import { streamNdjson, createGzipNdjsonBody } from './streaming';
export class TransHubClient {
    constructor(config) {
        Object.defineProperty(this, "config", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: config
        });
    }
    async getHeaders(contentType = 'application/json') {
        const headers = new Headers({
            'Content-Type': contentType,
        });
        if (this.config.getToken) {
            const token = await this.config.getToken();
            if (token) {
                headers.set('Authorization', `Bearer ${token}`);
            }
        }
        return headers;
    }
    async fetch(path, options = {}) {
        const url = `${this.config.baseUrl}${path}`;
        const headers = await this.getHeaders(options.headers); // Simple merge logic needed for real usage
        // Merge headers
        if (options.headers) {
            const incoming = new Headers(options.headers);
            incoming.forEach((v, k) => headers.set(k, v));
        }
        const res = await fetch(url, { ...options, headers });
        if (!res.ok) {
            let errorBody;
            try {
                errorBody = await res.json();
            }
            catch {
                errorBody = await res.text();
            }
            throw new Error(`API Error ${res.status}: ${JSON.stringify(errorBody)}`);
        }
        // Handle void responses
        if (res.status === 204)
            return null;
        return res.json();
    }
    // Specialized Streaming Methods
    async importSegments(jobId, segments) {
        const url = `${this.config.baseUrl}/jobs/${jobId}/segments/import`;
        const headers = await this.getHeaders('application/x-ndjson');
        headers.set('Content-Encoding', 'gzip');
        const body = await createGzipNdjsonBody(segments);
        // Note: fetch() with ReadableStream body requires HTTP/2 or specific browser versions (Duplex).
        // In Tauri (WebView), this likely works, or falls back to sending fully buffered blob if needed.
        // For robust implementation in pure browser, check duplex: 'half' support.
        const res = await fetch(url, {
            method: 'POST',
            headers,
            body: body, // TypeScript DOM types might complain about ReadableStream body
            // @ts-ignore
            duplex: 'half'
        });
        if (!res.ok)
            throw new Error(`Import failed: ${res.status}`);
        return res.json();
    }
    async *exportSegments(jobId) {
        const url = `${this.config.baseUrl}/jobs/${jobId}/segments/export?compress=true`;
        const headers = await this.getHeaders();
        const res = await fetch(url, { headers });
        if (!res.ok)
            throw new Error(`Export failed: ${res.status}`);
        yield* streamNdjson(res);
    }
}
