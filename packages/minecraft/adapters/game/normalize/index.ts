
export interface LocalizationFile {
    path: string;
    content: Record<string, string>;
}

export function normalize(file: LocalizationFile) {
    // Logic to flatten keys or parse format
    return Object.entries(file.content).map(([key, value]) => ({
        key,
        value,
        original: value
    }));
}
