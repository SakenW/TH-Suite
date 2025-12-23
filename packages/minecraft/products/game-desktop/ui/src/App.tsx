import { useState, useMemo, useEffect } from "react";
import { invoke } from "@tauri-apps/api/tauri";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import type { ScanResult, AssetFile } from "@transhub/core";

type Lang = 'en' | 'zh';

// Progress Payload Structure
interface ScanProgress {
    current: number;
    total: number;
    file: string;
}

const translations = {
    en: {
        title: "Minecraft Modpack Translator",
        greet_placeholder: "Enter a name...",
        greet_btn: "Test Connection",
        select_title: "Select Modpack",
        select_btn: "Select Root Directory",
        selected_label: "Selected:",
        language: "Language",
        scan_btn: "Scan for Resources",
        scan_result: "Scan Result",
        files: "Files",
        entries: "Total Entries",
        scanning: "Scanning...",
        no_assets: "No localization files found.",
        filter_label: "Filter by Filename:",
        filter_all: "All Files",
        close_panel: "Close",
        loading: "Loading content..."
    },
    zh: {
        title: "Minecraft 整合包翻译工具",
        greet_placeholder: "输入名称...",
        greet_btn: "测试连接",
        select_title: "选择整合包",
        select_btn: "选择整合包根目录",
        selected_label: "已选路径:",
        language: "语言",
        scan_btn: "扫描资源文件",
        scan_result: "扫描结果",
        files: "文件数",
        entries: "总词条数",
        scanning: "扫描中...",
        no_assets: "未发现任何语言文件 (assets/*/lang/*.json)",
        filter_label: "文件名过滤:",
        filter_all: "所有文件",
        close_panel: "关闭",
        loading: "正在读取内容..."
    }
};

function App() {
    const [greetMsg, setGreetMsg] = useState("");
    const [name, setName] = useState("");
    const [lang, setLang] = useState<Lang>('zh');

    // Scan State
    const [selectedPath, setSelectedPath] = useState<string | null>(null);
    const [scanResult, setScanResult] = useState<ScanResult | null>(null);
    const [isScanning, setIsScanning] = useState(false);

    // Progress State
    const [scanProgress, setScanProgress] = useState<ScanProgress | null>(null);

    // Filter State
    const [filterName, setFilterName] = useState<string>("en_us");

    // Viewer State
    const [viewingAsset, setViewingAsset] = useState<AssetFile | null>(null);
    const [assetContent, setAssetContent] = useState<Record<string, string> | null>(null);

    const t = translations[lang];

    async function greet() {
        setGreetMsg(await invoke("greet", { name }));
    }

    async function handleSelectDirectory() {
        try {
            const result = await invoke<string>("select_directory");
            setSelectedPath(result);
            setScanResult(null); // Reset previous scan
            setScanProgress(null); // Reset progress
            setGreetMsg(`${t.selected_label} ${result}`);
        } catch (e) {
            console.error(e);
        }
    }

    async function handleScan() {
        if (!selectedPath) return;
        setIsScanning(true);
        setScanProgress(null);
        setScanResult(null);

        let unlisten: UnlistenFn | null = null;
        try {
            // Listen for progress events
            unlisten = await listen<ScanProgress>('scan-progress', (event) => {
                setScanProgress(event.payload);
            });

            const result = await invoke<ScanResult>("scan_modpack", { path: selectedPath });
            result.assets.sort((a, b) => a.modId.localeCompare(b.modId));
            setScanResult(result);
        } catch (e) {
            console.error("Scan failed:", e);
            setGreetMsg(`Error: ${e}`);
        } finally {
            setIsScanning(false);
            if (unlisten) unlisten();
        }
    }

    async function openAsset(asset: AssetFile) {
        setViewingAsset(asset);
        setAssetContent(null);
        try {
            const content = await invoke<Record<string, string>>("read_asset", { path: asset.path });
            setAssetContent(content);
        } catch (e) {
            console.error(e);
            alert("Failed to read file: " + e);
        }
    }

    const filteredAssets = useMemo(() => {
        if (!scanResult) return [];
        if (!filterName) return scanResult.assets;
        return scanResult.assets.filter(a => a.name.toLowerCase().includes(filterName.toLowerCase()));
    }, [scanResult, filterName]);

    return (
        <div className="container mx-auto p-4 dark:bg-zinc-950 dark:text-white min-h-screen font-sans flex relative">
            <div className={`flex-grow transition-all ${viewingAsset ? 'mr-96' : ''}`}>

                {/* Header */}
                <div className="flex justify-between items-center mb-6 border-b border-gray-200 dark:border-gray-800 pb-4">
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
                        {t.title}
                    </h1>
                    <div className="flex gap-2 text-sm">
                        <button onClick={() => setLang('en')} className={`px-3 py-1 rounded ${lang === 'en' ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-zinc-800'}`}>EN</button>
                        <button onClick={() => setLang('zh')} className={`px-3 py-1 rounded ${lang === 'zh' ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-zinc-800'}`}>中文</button>
                    </div>
                </div>

                {/* Main Action Area */}
                <div className="bg-white dark:bg-zinc-900 p-6 rounded-lg shadow-md border border-gray-200 dark:border-zinc-800 mb-6">
                    <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">{t.select_title}</h2>
                    <div className="flex gap-4 items-center mb-6">
                        <button
                            onClick={handleSelectDirectory}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium shadow-lg hover:shadow-xl transition-all active:scale-95"
                        >
                            {t.select_btn}
                        </button>
                        {selectedPath && (
                            <div className="flex-grow bg-gray-100 dark:bg-zinc-800 p-3 rounded text-sm font-mono truncate text-gray-600 dark:text-gray-400">
                                {selectedPath}
                            </div>
                        )}
                    </div>
                    {selectedPath && (
                        <div>
                            <button
                                onClick={handleScan}
                                disabled={isScanning}
                                className={`w-full py-4 rounded-lg text-lg font-bold shadow-md transition-all ${isScanning ? 'bg-gray-400 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-700 text-white hover:shadow-lg active:scale-98'}`}
                            >
                                {isScanning ? t.scanning : t.scan_btn}
                            </button>

                            {/* Progress Bar */}
                            {isScanning && scanProgress && (
                                <div className="mt-4">
                                    <div className="flex justify-between text-sm text-gray-600 dark:text-gray-300 mb-1">
                                        <span className="truncate max-w-[70%]">Scanning: {scanProgress.file}</span>
                                        <span className="font-mono">{scanProgress.current} / {scanProgress.total}</span>
                                    </div>
                                    <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 overflow-hidden">
                                        <div
                                            className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-out"
                                            style={{ width: `${scanProgress.total > 0 ? (scanProgress.current / scanProgress.total) * 100 : 0}%` }}
                                        ></div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Scan Results */}
                {scanResult && !isScanning && (
                    <div className="mt-8 animation-fade-in">
                        <div className="flex items-end justify-between mb-4">
                            <h2 className="text-2xl font-bold">{t.scan_result}</h2>

                            {/* Filter Control */}
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-medium">{t.filter_label}</span>
                                <input
                                    className="border rounded p-1 text-sm text-black dark:bg-zinc-800 dark:text-white dark:border-zinc-700"
                                    value={filterName}
                                    onChange={e => setFilterName(e.target.value)}
                                    placeholder="en_us"
                                />
                            </div>

                            <div className="text-gray-500 text-sm">
                                {t.files}: <span className="font-bold text-black dark:text-white">{scanResult.totalFiles}</span> &nbsp;|&nbsp;
                                {t.entries}: <span className="font-bold text-black dark:text-white">{scanResult.totalEntries}</span>
                            </div>
                        </div>

                        {filteredAssets.length === 0 ? (
                            <div className="p-8 text-center text-gray-500 bg-gray-50 dark:bg-zinc-900 rounded-lg border border-dashed border-gray-300">
                                {scanResult.assets.length > 0 ? "No files match filter" : t.no_assets}
                            </div>
                        ) : (
                            <div className="bg-white dark:bg-zinc-900 rounded-lg shadow border border-gray-200 dark:border-zinc-800 overflow-hidden">
                                <table className="w-full text-left text-sm">
                                    <thead className="bg-gray-50 dark:bg-zinc-950 text-gray-500 font-medium">
                                        <tr>
                                            <th className="p-3">Mod ID</th>
                                            <th className="p-3">File Name</th>
                                            <th className="p-3 text-right">Entries</th>
                                            <th className="p-3 text-gray-400">Original Path (Source)</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-100 dark:divide-zinc-800">
                                        {filteredAssets.map((asset, idx) => (
                                            <tr
                                                key={idx}
                                                onClick={() => openAsset(asset)}
                                                className={`cursor-pointer transition-colors ${viewingAsset === asset ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-gray-50 dark:hover:bg-zinc-800'}`}
                                            >
                                                <td className="p-3 font-semibold text-blue-600 dark:text-blue-400">{asset.modId}</td>
                                                <td className="p-3">{asset.name}</td>
                                                <td className="p-3 text-right font-mono">{asset.entryCount}</td>
                                                <td className="p-3 text-gray-400 text-xs truncate max-w-[200px]" title={asset.originalPath || asset.path}>
                                                    {asset.originalPath || asset.path}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Viewer Side Panel */}
            {viewingAsset && (
                <div className="fixed top-0 right-0 h-full w-96 bg-white dark:bg-zinc-900 shadow-2xl border-l border-gray-200 dark:border-zinc-800 overflow-hidden flex flex-col z-50 transform transition-transform">
                    <div className="p-4 border-b border-gray-200 dark:border-zinc-800 flex justify-between items-center bg-gray-50 dark:bg-zinc-950">
                        <div>
                            <h3 className="font-bold text-lg truncate w-64" title={viewingAsset.originalPath}>{viewingAsset.name}</h3>
                            <p className="text-xs text-gray-500">{viewingAsset.modId}</p>
                        </div>
                        <button
                            onClick={() => setViewingAsset(null)}
                            className="text-gray-500 hover:text-black dark:hover:text-white"
                        >
                            ✕
                        </button>
                    </div>
                    <div className="flex-grow overflow-auto p-4">
                        {!assetContent ? (
                            <div className="text-center text-gray-400 mt-10">{t.loading}</div>
                        ) : (
                            <div className="space-y-3">
                                {Object.entries(assetContent).map(([k, v], i) => (
                                    <div key={i} className="text-sm border-b border-gray-100 dark:border-zinc-800 pb-2">
                                        <div className="text-gray-400 font-mono text-xs break-all mb-1 select-all">{k}</div>
                                        <div className="text-gray-800 dark:text-gray-200 break-words select-all">{v}</div>
                                    </div>
                                ))}
                                {Object.keys(assetContent).length === 0 && (
                                    <div className="text-center text-gray-400 italic">Empty file</div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default App;
