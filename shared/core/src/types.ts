export interface AssetFile {
    path: string;      // Path in CACHE (absolute or relative to cache root)
    originalPath: string; // e.g. "mods/Botania.jar!/assets/..."
    modId: string;     // e.g. "botania"
    name: string;      // e.g. "en_us.json"
    entryCount: number;
}

export interface ScanResult {
    appId: string;
    rootPath: string;
    totalFiles: number;
    totalEntries: number;
    assets: AssetFile[];
}
