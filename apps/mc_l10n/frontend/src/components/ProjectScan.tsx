import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
  FolderOpen,
  Scan,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Package,
  FileText,
  Globe,
  Settings,
  Loader2,
  RefreshCw
} from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { open } from '@tauri-apps/plugin-dialog';
import { useTranslation } from 'react-i18next';

interface ScanProgress {
  scan_id: string;
  phase: string;
  progress: number;
  message: string;
  current_file?: string;
  processed_files: number;
  total_files: number;
  estimated_remaining?: number;
  updated_at: string;
}

interface ModpackManifest {
  name: string;
  version: string;
  author?: string;
  description?: string;
  minecraft_version: string;
  loader: string;
  loader_version: string;
  platform: string;
  license?: string;
}

interface ModJarMetadata {
  mod_id: string;
  display_name: string;
  version: string;
  loader: string;
  authors: string[];
  homepage?: string;
  description?: string;
  environment: string;
}

interface LanguageResource {
  namespace: string;
  locale: string;
  source_path: string;
  source_type: string;
  key_count: number;
  priority: number;
}

interface ScanResult {
  scan_id: string;
  project_path: string;
  scan_started_at: string;
  scan_completed_at?: string;
  modpack_manifest?: ModpackManifest;
  mod_jars: ModJarMetadata[];
  language_resources: LanguageResource[];
  total_mods: number;
  total_language_files: number;
  total_translatable_keys: number;
  supported_locales: string[];
  warnings: string[];
  errors: string[];
}

interface ProjectScanProps {
  onScanComplete?: (result: ScanResult) => void;
  onCreateProject?: (result: ScanResult) => void;
}

const ProjectScan: React.FC<ProjectScanProps> = ({ onScanComplete, onCreateProject }) => {
  const { t } = useTranslation();
  const [selectedPath, setSelectedPath] = useState<string>('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState<ScanProgress | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  
  // 检测是否在Tauri环境中
  const isTauri = typeof window !== 'undefined' && '__TAURI__' in window;

  // 监听扫描进度事件
  useEffect(() => {
    const unlisten = listen<ScanProgress>('scan-progress', (event) => {
      setScanProgress(event.payload);
      
      // 扫描完成时获取结果
      if (event.payload.phase === 'completed') {
        handleGetScanResult(event.payload.scan_id);
      }
    });

    return () => {
      unlisten.then(fn => fn());
    };
  }, []);

  const handleSelectPath = async () => {
    try {
      // 检查是否在Tauri环境中
      const isTauri = '__TAURI__' in window;
      
      if (isTauri) {
        // Tauri环境：使用原生文件选择器
        const selected = await open({
          directory: true,
          multiple: false,
          title: t('scan.selectProjectPath')
        });
        
        if (selected && typeof selected === 'string') {
          setSelectedPath(selected);
        }
      } else {
        // Web环境：使用输入框让用户手动输入路径
        const path = prompt(t('scan.enterProjectPath') || '请输入项目路径:');
        if (path && path.trim()) {
          setSelectedPath(path.trim());
        }
      }
    } catch (error) {
      console.error('Failed to select path:', error);
    }
  };

  const handleStartScan = async () => {
    if (!selectedPath) return;
    
    try {
      setIsScanning(true);
      setScanProgress(null);
      setScanResult(null);
      
      // 检查是否在Tauri环境中
      const isTauri = '__TAURI__' in window;
      
      if (isTauri) {
        // Tauri环境：使用本地扫描
        await invoke('start_project_scan', { projectPath: selectedPath });
      } else {
        // Web环境：使用HTTP API回退
        await handleWebScan();
      }
    } catch (error) {
      console.error('Failed to start scan:', error);
      setIsScanning(false);
    }
  };

  const handleWebScan = async () => {
    try {
      const response = await fetch('http://localhost:18000/api/v1/scan-project', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ directory: selectedPath }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const scanId = data.scan_id;

      // 启动真实的进度监控
      monitorWebScanProgress(scanId);
    } catch (error) {
      console.error('Web scan failed:', error);
      setIsScanning(false);
      
      // 创建一个模拟的扫描结果用于展示
      const mockResult: ScanResult = {
        scan_id: 'mock-scan-' + Date.now(),
        project_path: selectedPath,
        scan_started_at: new Date().toISOString(),
        scan_completed_at: new Date().toISOString(),
        modpack_manifest: null,
        mod_jars: [],
        language_resources: [],
        total_mods: 0,
        total_language_files: 0,
        total_translatable_keys: 0,
        supported_locales: [],
        warnings: [`无法连接到后端服务 (${error})`],
        errors: ['扫描失败: 请确保后端服务正在运行或使用Tauri桌面应用'],
      };
      
      setScanResult(mockResult);
      setIsScanning(false);
    }
  };

  const monitorWebScanProgress = async (scanId: string) => {
    const pollInterval = 1000; // 1秒轮询一次
    let attempts = 0;
    const maxAttempts = 300; // 最多5分钟
    
    const poll = async () => {
      try {
        const response = await fetch(`http://localhost:18000/api/v1/scan-result/${scanId}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.data) {
          const scanData = result.data;
          
          // 更新进度显示
          if (scanData.status === 'completed') {
            // 扫描完成
            setScanResult(scanData);
            setIsScanning(false);
            
            if (onScanComplete) {
              onScanComplete(scanData);
            }
            return;
          } else if (scanData.status === 'scanning') {
            // 更新进度
            const progress = Math.min((scanData.processed_files || 0) / Math.max(scanData.total_files || 1, 1) * 100, 99);
            
            setScanProgress({
              scan_id: scanId,
              phase: 'scanning',
              progress: progress,
              message: `正在扫描... (${scanData.processed_files || 0}/${scanData.total_files || 0})`,
              current_file: scanData.current_file || '',
              processed_files: scanData.processed_files || 0,
              total_files: scanData.total_files || 0,
              estimated_remaining: scanData.total_files ? Math.max(scanData.total_files - (scanData.processed_files || 0), 0) : undefined,
              updated_at: new Date().toISOString(),
            });
          }
        }
        
        attempts++;
        if (attempts < maxAttempts && scanData?.status !== 'completed') {
          setTimeout(poll, pollInterval);
        } else if (attempts >= maxAttempts) {
          console.error('扫描超时');
          setIsScanning(false);
        }
      } catch (error) {
        console.error('获取扫描进度失败:', error);
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, pollInterval * 2); // 出错时延长轮询间隔
        } else {
          setIsScanning(false);
        }
      }
    };
    
    // 开始轮询
    setTimeout(poll, 1000); // 1秒后开始第一次轮询
  };

  const simulateWebScanProgress = async (taskId: string) => {
    const phases = [
      { phase: 'detecting_project_type', progress: 10, message: '检测项目类型...' },
      { phase: 'scanning_modpack', progress: 30, message: '扫描模组包清单...' },
      { phase: 'scanning_mods', progress: 60, message: '扫描模组JAR文件...' },
      { phase: 'scanning_language_resources', progress: 80, message: '扫描语言资源...' },
      { phase: 'completed', progress: 100, message: '扫描完成' },
    ];

    for (const phaseData of phases) {
      setScanProgress({
        scan_id: taskId,
        phase: phaseData.phase,
        progress: phaseData.progress,
        message: phaseData.message,
        current_file: undefined,
        processed_files: Math.floor(phaseData.progress / 10),
        total_files: 10,
        estimated_remaining: phaseData.progress < 100 ? Math.floor((100 - phaseData.progress) / 10) : undefined,
        updated_at: new Date().toISOString(),
      });

      if (phaseData.phase === 'completed') {
        // 创建最终结果
        const finalResult: ScanResult = {
          scan_id: taskId,
          project_path: selectedPath,
          scan_started_at: new Date(Date.now() - 5000).toISOString(),
          scan_completed_at: new Date().toISOString(),
          modpack_manifest: null,
          mod_jars: [],
          language_resources: [],
          total_mods: 0,
          total_language_files: 0,
          total_translatable_keys: 0,
          supported_locales: [],
          warnings: ['这是Web模式下的模拟扫描结果'],
          errors: [],
        };
        
        setScanResult(finalResult);
        setIsScanning(false);
        
        if (onScanComplete) {
          onScanComplete(finalResult);
        }
        break;
      }

      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  };

  const handleGetScanResult = async (scanId: string) => {
    try {
      const result = await invoke<ScanResult>('get_scan_result', { scan_id: scanId });
      setScanResult(result);
      setIsScanning(false);
      
      if (onScanComplete) {
        onScanComplete(result);
      }
    } catch (error) {
      console.error('Failed to get scan result:', error);
      setIsScanning(false);
    }
  };

  const handleCreateProject = async () => {
    if (!scanResult) return;
    
    try {
      await invoke('create_project_from_scan', { scanResult });
      
      if (onCreateProject) {
        onCreateProject(scanResult);
      }
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  };

  const getPhaseDisplayName = (phase: string) => {
    const phaseMap: Record<string, string> = {
      'detecting_project_type': t('scan.phase.detectingProjectType'),
      'scanning_modpack': t('scan.phase.scanningModpack'),
      'scanning_mods': t('scan.phase.scanningMods'),
      'scanning_language_resources': t('scan.phase.scanningLanguageResources'),
      'generating_statistics': t('scan.phase.generatingStatistics'),
      'validation': t('scan.phase.validation'),
      'completed': t('scan.phase.completed')
    };
    return phaseMap[phase] || phase;
  };

  const formatDuration = (startTime: string, endTime?: string) => {
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const duration = Math.round((end.getTime() - start.getTime()) / 1000);
    
    if (duration < 60) {
      return `${duration}s`;
    } else {
      const minutes = Math.floor(duration / 60);
      const seconds = duration % 60;
      return `${minutes}m ${seconds}s`;
    }
  };

  return (
    <div className="space-y-6">
      {/* 路径选择和扫描控制 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 justify-between">
            <div className="flex items-center gap-2">
              <Scan className="h-5 w-5" />
              {t('scan.title')}
            </div>
            <Badge variant={isTauri ? "default" : "secondary"}>
              {isTauri ? "桌面模式" : "Web模式"}
            </Badge>
          </CardTitle>
          {!isTauri && (
            <div className="text-sm text-muted-foreground">
              💡 提示：使用 <code>npm run tauri:dev</code> 启动桌面应用以获得完整的本地扫描功能
            </div>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleSelectPath}
              className="flex items-center gap-2"
              disabled={isScanning}
            >
              <FolderOpen className="h-4 w-4" />
              {isTauri ? t('scan.selectPath') : '输入路径'}
            </Button>
            <div className="flex-1 px-3 py-2 bg-muted rounded-md text-sm">
              {selectedPath || t('scan.noPathSelected')}
            </div>
          </div>
          
          <div className="flex gap-2">
            <Button
              onClick={handleStartScan}
              disabled={!selectedPath || isScanning}
              className="flex items-center gap-2"
            >
              {isScanning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
{isScanning ? 
                (isTauri ? t('scan.scanning') : '扫描中 (Web模式)') : 
                (isTauri ? t('scan.startScan') : '开始扫描 (Web模式)')
              }
            </Button>
            
            {scanResult && (
              <Button
                onClick={handleCreateProject}
                variant="default"
                className="flex items-center gap-2"
              >
                <Package className="h-4 w-4" />
                {t('scan.createProject')}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 扫描进度 */}
      {scanProgress && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              {t('scan.progress')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>{getPhaseDisplayName(scanProgress.phase)}</span>
                <span>{Math.round(scanProgress.progress)}%</span>
              </div>
              <Progress value={scanProgress.progress} className="w-full" />
            </div>
            
            <div className="text-sm text-muted-foreground">
              {scanProgress.message}
            </div>
            
            {scanProgress.current_file && (
              <div className="text-xs text-muted-foreground">
                {t('scan.currentFile')}: {scanProgress.current_file}
              </div>
            )}
            
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>
                {t('scan.processedFiles')}: {scanProgress.processed_files}/{scanProgress.total_files}
              </span>
              {scanProgress.estimated_remaining && (
                <span>
                  {t('scan.estimatedRemaining')}: {scanProgress.estimated_remaining}s
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 扫描结果 */}
      {scanResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              {t('scan.results')}
            </CardTitle>
            <div className="text-sm text-muted-foreground">
              {t('scan.completedIn')}: {formatDuration(scanResult.scan_started_at, scanResult.scan_completed_at)}
            </div>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="overview">{t('scan.tabs.overview')}</TabsTrigger>
                <TabsTrigger value="modpack">{t('scan.tabs.modpack')}</TabsTrigger>
                <TabsTrigger value="mods">{t('scan.tabs.mods')}</TabsTrigger>
                <TabsTrigger value="languages">{t('scan.tabs.languages')}</TabsTrigger>
              </TabsList>
              
              <TabsContent value="overview" className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold">{scanResult.total_mods}</div>
                    <div className="text-sm text-muted-foreground">{t('scan.stats.totalMods')}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{scanResult.total_language_files}</div>
                    <div className="text-sm text-muted-foreground">{t('scan.stats.languageFiles')}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{scanResult.total_translatable_keys}</div>
                    <div className="text-sm text-muted-foreground">{t('scan.stats.translatableKeys')}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{scanResult.supported_locales.length}</div>
                    <div className="text-sm text-muted-foreground">{t('scan.stats.supportedLanguages')}</div>
                  </div>
                </div>
                
                <Separator />
                
                <div className="space-y-2">
                  <h4 className="font-medium">{t('scan.supportedLanguages')}</h4>
                  <div className="flex flex-wrap gap-1">
                    {scanResult.supported_locales.map(locale => (
                      <Badge key={locale} variant="secondary">{locale}</Badge>
                    ))}
                  </div>
                </div>
                
                {/* 警告和错误 */}
                {scanResult.warnings.length > 0 && (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="font-medium mb-1">{t('scan.warnings')}</div>
                      <ul className="list-disc list-inside text-sm space-y-1">
                        {scanResult.warnings.map((warning, index) => (
                          <li key={index}>{warning}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}
                
                {scanResult.errors.length > 0 && (
                  <Alert variant="destructive">
                    <XCircle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="font-medium mb-1">{t('scan.errors')}</div>
                      <ul className="list-disc list-inside text-sm space-y-1">
                        {scanResult.errors.map((error, index) => (
                          <li key={index}>{error}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}
              </TabsContent>
              
              <TabsContent value="modpack" className="space-y-4">
                {scanResult.modpack_manifest ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium">{t('scan.modpack.name')}</label>
                        <div className="text-sm text-muted-foreground">{scanResult.modpack_manifest.name}</div>
                      </div>
                      <div>
                        <label className="text-sm font-medium">{t('scan.modpack.version')}</label>
                        <div className="text-sm text-muted-foreground">{scanResult.modpack_manifest.version}</div>
                      </div>
                      <div>
                        <label className="text-sm font-medium">{t('scan.modpack.author')}</label>
                        <div className="text-sm text-muted-foreground">{scanResult.modpack_manifest.author || 'N/A'}</div>
                      </div>
                      <div>
                        <label className="text-sm font-medium">{t('scan.modpack.minecraftVersion')}</label>
                        <div className="text-sm text-muted-foreground">{scanResult.modpack_manifest.minecraft_version}</div>
                      </div>
                      <div>
                        <label className="text-sm font-medium">{t('scan.modpack.loader')}</label>
                        <div className="text-sm text-muted-foreground">
                          {scanResult.modpack_manifest.loader} {scanResult.modpack_manifest.loader_version}
                        </div>
                      </div>
                      <div>
                        <label className="text-sm font-medium">{t('scan.modpack.platform')}</label>
                        <div className="text-sm text-muted-foreground">{scanResult.modpack_manifest.platform}</div>
                      </div>
                    </div>
                    
                    {scanResult.modpack_manifest.description && (
                      <div>
                        <label className="text-sm font-medium">{t('scan.modpack.description')}</label>
                        <div className="text-sm text-muted-foreground mt-1">{scanResult.modpack_manifest.description}</div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    {t('scan.modpack.notFound')}
                  </div>
                )}
              </TabsContent>
              
              <TabsContent value="mods" className="space-y-4">
                <ScrollArea className="h-96">
                  <div className="space-y-2">
                    {scanResult.mod_jars.map((mod, index) => (
                      <Card key={index} className="p-4">
                        <div className="flex justify-between items-start">
                          <div className="space-y-1">
                            <div className="font-medium">{mod.display_name}</div>
                            <div className="text-sm text-muted-foreground">{mod.mod_id} v{mod.version}</div>
                            <div className="text-xs text-muted-foreground">
                              {mod.loader} • {mod.environment}
                            </div>
                            {mod.authors.length > 0 && (
                              <div className="text-xs text-muted-foreground">
                                {t('scan.mod.authors')}: {mod.authors.join(', ')}
                              </div>
                            )}
                          </div>
                          <Badge variant="outline">{mod.loader}</Badge>
                        </div>
                        {mod.description && (
                          <div className="text-sm text-muted-foreground mt-2">{mod.description}</div>
                        )}
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>
              
              <TabsContent value="languages" className="space-y-4">
                <ScrollArea className="h-96">
                  <div className="space-y-2">
                    {scanResult.language_resources.map((resource, index) => (
                      <Card key={index} className="p-4">
                        <div className="flex justify-between items-start">
                          <div className="space-y-1">
                            <div className="font-medium">{resource.namespace}</div>
                            <div className="text-sm text-muted-foreground">
                              {resource.locale} • {resource.key_count} {t('scan.language.keys')}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {t('scan.language.source')}: {resource.source_type}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">{resource.locale}</Badge>
                            <Badge variant="secondary">{resource.priority}</Badge>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ProjectScan;