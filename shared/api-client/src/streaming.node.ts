
import { Readable } from 'stream';
import zlib from 'zlib';

export async function* streamNdjson<T>(response: any): AsyncGenerator<T> {
    // Node.js implementation using 'readline' or simple split
    // For verification script simplicity, we just assume text response for now
    // or implement a proper node stream reader if needed.
    // However, verify-upload.ts mainly tests UPLOAD, so we focus on createGzipNdjsonBody
    throw new Error("NodeJS streamNdjson not fully implemented for verification script yet");
}

export async function createGzipNdjsonBody(data: Iterable<any> | AsyncIterable<any>): Promise<Readable> {
    const encoder = new Readable({
        read() { }
    });

    const gzip = zlib.createGzip();
    const output = encoder.pipe(gzip);

    (async () => {
        try {
            for await (const item of data) {
                encoder.push(JSON.stringify(item) + '\n');
            }
            encoder.push(null);
        } catch (err) {
            encoder.destroy(err as any);
        }
    })();

    return output;
}
