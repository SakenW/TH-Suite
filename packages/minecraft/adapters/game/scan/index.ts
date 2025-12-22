
export interface ScanOptions {
    rootPath: string;
    depth?: number;
}

export interface ScanResult {
    files: string[];
}

export async function scanGameAssets(options: ScanOptions): Promise<ScanResult> {
    // Implementation will use FS abstraction
    console.log(`Scanning ${options.rootPath}`);
    return { files: [] };
}
