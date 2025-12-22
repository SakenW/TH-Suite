
export async function* streamNdjson<T>(response: Response): AsyncGenerator<T> {
    const body = response.body;
    if (!body) throw new Error('Response body is empty');

    let stream = body;
    const encoding = response.headers.get('Content-Encoding');
    if (encoding === 'gzip' && 'DecompressionStream' in globalThis) {
        // @ts-ignore
        const decompressor = new DecompressionStream('gzip');
        stream = body.pipeThrough(decompressor);
    }

    const reader = stream.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.trim()) {
                    yield JSON.parse(line);
                }
            }
        }
        if (buffer.trim()) {
            yield JSON.parse(buffer);
        }
    } finally {
        reader.releaseLock();
    }
}

export async function createGzipNdjsonBody(data: Iterable<any> | AsyncIterable<any>): Promise<ReadableStream> {
    // @ts-ignore
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const encoder = new TextEncoder();

    (async () => {
        try {
            for await (const item of data) {
                const line = JSON.stringify(item) + '\n';
                await writer.write(encoder.encode(line));
            }
            await writer.close();
        } catch (err) {
            await writer.abort(err);
        }
    })();

    let outputStream = readable;

    if ('CompressionStream' in globalThis) {
        // @ts-ignore
        const compressor = new CompressionStream('gzip');
        outputStream = readable.pipeThrough(compressor);
    } else {
        console.warn('CompressionStream not supported, sending uncompressed data.');
    }

    return outputStream;
}
