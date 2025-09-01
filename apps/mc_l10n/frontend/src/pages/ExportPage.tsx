import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  LinearProgress,
  Alert,
  Checkbox,
  FormControlLabel,
  useTheme,
  alpha,
  Grid,
  Paper,
  Divider,
} from '@mui/material';
import {
  Download,
  FileText,
  Globe,
  Package,
  CheckCircle,
  AlertCircle,
  Play,
  Pause,
  Square,
  Trash2,
  FolderOpen,
  X,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  MinecraftCard,
  MinecraftButton,
  MinecraftBlock,
  ExperienceBar,
  ParticleEffect,
  Creeper,
} from '../components/MinecraftComponents';

import { useAppStore } from '@stores/appStore';
import { tauriService } from '@services';
import { useMcStudioTranslation } from '@hooks/useTranslation';
import { DirectorySelector } from '../components/DirectorySelector';
import { apiService, handleApiError, isJobCompleted, isJobRunning, type ExportRequest, type JobResponse } from '@/services/apiService';

interface LanguageFile {
  id: string;
  path: string;
  name: string;
  language: string;
  keys: number;
  size: number;
  selected: boolean;
}

interface ExportProgress {
  current: number;
  total: number;
  currentFile: string;
  status: 'idle' | 'scanning' | 'exporting' | 'paused' | 'completed' | 'error';
  exported: number;
  failed: number;
}

interface ExportOptions {
  format: 'json' | 'lang' | 'properties' | 'yaml';
  includeEmpty: boolean;
  sortKeys: boolean;
  createZip: boolean;
  preserveStructure: boolean;
}

function ExportPage() {
  const theme = useTheme();
  const { t } = useMcStudioTranslation();
  const { addRecentProject, currentProject } = useAppStore();
  
  const [sourceDirectory, setSourceDirectory] = useState('');
  const [outputDirectory, setOutputDirectory] = useState('');
  const [languageFiles, setLanguageFiles] = useState<LanguageFile[]>([]);
  const [exportProgress, setExportProgress] = useState<ExportProgress>({
    current: 0,
    total: 0,
    currentFile: '',
    status: 'idle',
    exported: 0,
    failed: 0,
  });
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    format: 'json',
    includeEmpty: false,
    sortKeys: true,
    createZip: true,
    preserveStructure: true,
  });
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [exportResult, setExportResult] = useState<any>(null);

  // 当组件加载或当前项目变化时，自动设置源目录并加载语言文件
  useEffect(() => {
    if (currentProject?.path) {
      setSourceDirectory(currentProject.path);
      // 自动扫描语言文件
      handleScanLanguageFiles();
    }
  }, [currentProject]);



  const handleScanLanguageFiles = useCallback(async () => {
    // 如果有当前项目，从项目的扫描结果中获取语言文件
    if (currentProject?.metadata?.scanResult) {
      try {
        setExportProgress(prev => ({ ...prev, status: 'scanning' }));
        setLanguageFiles([]);
        
        const scanResult = currentProject.metadata.scanResult;
        const languageResources = scanResult.language_resources || [];
        
        const files: LanguageFile[] = languageResources.map((resource: any, index: number) => ({
          id: resource.locale || `file_${index}`,
          path: resource.file_path || resource.path,
          name: resource.file_name || resource.name || `${resource.locale || 'unknown'}.json`,
          language: resource.display_name || resource.locale || 'Unknown',
          keys: resource.key_count || resource.keys || 0,
          size: resource.file_size || resource.size || 0,
          selected: true,
        }));
        
        // 模拟扫描过程
        for (let i = 0; i < files.length; i++) {
          await new Promise(resolve => setTimeout(resolve, 100));
          setExportProgress(prev => ({
            ...prev,
            current: i + 1,
            total: files.length,
            currentFile: `Loading ${files[i].name}...`,
          }));
        }
        
        setLanguageFiles(files);
        setExportProgress(prev => ({ 
          ...prev, 
          status: 'idle', 
          currentFile: `Found ${files.length} language files`,
        }));
        
        toast.success(`Found ${files.length} language files from project`);
        return;
      } catch (error) {
        console.error('Failed to load project language files:', error);
        toast.error('Failed to load project language files');
      }
    }
    
    // 如果没有当前项目，要求选择源目录
    if (!sourceDirectory) {
      toast.error('Please select a source directory or open a project first');
      return;
    }

    try {
      setExportProgress(prev => ({ ...prev, status: 'scanning' }));
      setLanguageFiles([]);
      
      // TODO: 实现真实的目录扫描逻辑
      // 这里可以调用后端API来扫描指定目录的语言文件
      
      toast.error('Directory scanning not implemented yet. Please open a project first.');
      setExportProgress(prev => ({ ...prev, status: 'error' }));
    } catch (error) {
      console.error('Scan failed:', error);
      setExportProgress(prev => ({ ...prev, status: 'error' }));
      toast.error('Scan failed');
    }
  }, [sourceDirectory, currentProject]);

  const handleStartExport = useCallback(async () => {
    const selectedFiles = languageFiles.filter(f => f.selected).map(f => f.path);
    
    if (selectedFiles.length === 0) {
      toast.error('Please select at least one language file to export');
      return;
    }

    if (!outputDirectory) {
      toast.error('Please select an output directory');
      return;
    }

    try {
      setExportProgress(prev => ({ 
        ...prev, 
        status: 'exporting',
        total: selectedFiles.length,
        current: 0,
        exported: 0,
        failed: 0,
      }));
      
      const request: ExportRequest = {
        source_directory: sourceDirectory,
        output_directory: outputDirectory,
        export_format: exportOptions.createZip ? 'zip' : 'directory',
        target_locales: languageFiles.filter(f => f.selected).map(f => f.language),
        include_patterns: selectedFiles.map(path => path.split('/').pop() || '*.json'),
        exclude_patterns: [],
        compress_level: 6,
      };
      
      const response = await apiService.exportLanguagePack(request);
      if (!response.success || !response.data) {
        throw new Error(response.error?.message || 'Failed to start export');
      }
      const jobResponse = response.data;
      setCurrentJobId(jobResponse.job_id);
      
      // Poll for job status
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await apiService.getJobStatus(jobResponse.job_id);
          if (!statusResponse.success || !statusResponse.data) {
            throw new Error(statusResponse.error?.message || 'Failed to get job status');
          }
          const status = statusResponse.data;
          
          setExportProgress(prev => ({
            ...prev,
            current: status.progress?.current || 0,
            total: status.progress?.total || selectedFiles.length,
            currentFile: status.progress?.currentFile || '',
            exported: status.progress?.completed || 0,
            failed: status.progress?.failed || 0,
          }));
          
          if (isJobCompleted(status.status)) {
            clearInterval(pollInterval);
            setCurrentJobId(null);
            
            if (status.status === 'completed') {
              setExportProgress(prev => ({ 
                ...prev, 
                status: 'completed',
                currentFile: `Export completed! ${status.progress?.completed || 0} exported, ${status.progress?.failed || 0} failed.`,
              }));
              
              setExportResult(status.result);
              
              // Add to recent projects
              addRecentProject({
                name: `Language Export - ${new Date().toLocaleDateString()}`,
                path: outputDirectory,
                type: 'export',
              });
              
              toast.success(`Export completed! ${status.progress?.completed || 0} files exported.`);
            } else {
              setExportProgress(prev => ({ ...prev, status: 'error' }));
              toast.error(status.error || 'Export failed');
            }
          }
        } catch (error) {
          clearInterval(pollInterval);
          console.error('Error polling job status:', error);
          toast.error(handleApiError(error));
          setExportProgress(prev => ({ ...prev, status: 'error' }));
          setCurrentJobId(null);
        }
      }, 1000);
      
    } catch (error) {
      console.error('Export failed:', error);
      toast.error(handleApiError(error));
      setExportProgress(prev => ({ ...prev, status: 'error' }));
      setCurrentJobId(null);
    }
  }, [languageFiles, outputDirectory, sourceDirectory, exportOptions, currentJobId, addRecentProject]);

   const handleCancelExport = useCallback(async () => {
     if (!currentJobId) return;
     
     try {
       await apiService.cancelJob(currentJobId);
       setExportProgress(prev => ({ ...prev, status: 'idle' }));
       setCurrentJobId(null);
       // 安全调用toast.info，避免TypeError
        if (typeof toast.info === 'function') {
          toast.info('Export cancelled');
        } else {
          toast.success('Export cancelled');
        }
     } catch (error) {
       console.error('Failed to cancel export:', error);
       toast.error(handleApiError(error));
     }
   }, [currentJobId]);

   const handleOpenOutputDirectory = useCallback(async () => {
     if (!outputDirectory) return;
     
     try {
       await tauriService.openPath(outputDirectory);
     } catch (error) {
       console.error('Failed to open output directory:', error);
       toast.error('Failed to open output directory');
     }
   }, [outputDirectory]);

  const handleToggleFileSelection = useCallback((fileId: string) => {
    setLanguageFiles(prev => prev.map(file => 
      file.id === fileId ? { ...file, selected: !file.selected } : file
    ));
  }, []);

  const handleSelectAll = useCallback(() => {
    setLanguageFiles(prev => prev.map(file => ({ ...file, selected: true })));
  }, []);

  const handleDeselectAll = useCallback(() => {
    setLanguageFiles(prev => prev.map(file => ({ ...file, selected: false })));
  }, []);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const selectedCount = languageFiles.filter(file => file.selected).length;
  const totalKeys = languageFiles.filter(file => file.selected).reduce((sum, file) => sum + file.keys, 0);
  const totalSize = languageFiles.filter(file => file.selected).reduce((sum, file) => sum + file.size, 0);

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 2, mb: 2 }}>
        <Creeper size={32} onExplode={() => toast.success('欢迎使用 Minecraft 翻译工具！')} />
        <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
          {t('export.title', 'Export Language Packs')}
        </Typography>
        <Creeper size={32} onExplode={() => toast.success('点击苦力怕试试看！')} />
      </Box>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        {t('export.description', 'Export language files from Minecraft resource packs, mods, or custom projects. Choose your source directory, select the languages you want to export, and download them in your preferred format.')}
      </Typography>

      <Grid container spacing={3}>
        {/* Source Directory Selection */}
        <Grid item xs={12} md={6}>
          <MinecraftCard variant="inventory">
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <MinecraftBlock type="grass" size={20} />
                {t('export.source.title', 'Source Directory')}
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <DirectorySelector
                  value={sourceDirectory}
                  onChange={setSourceDirectory}
                  placeholder={t('export.source.placeholder', 'Select source directory...')}
                />
              </Box>
              
              <MinecraftButton
                variant="primary"
                onClick={handleScanLanguageFiles}
                disabled={!sourceDirectory || exportProgress.status === 'scanning'}
                size="large"
              >
                {exportProgress.status === 'scanning'
                  ? t('export.scanning', 'Scanning...')
                  : t('export.scanFiles', 'Scan Language Files')
                }
              </MinecraftButton>
            </CardContent>
          </MinecraftCard>
        </Grid>

        {/* Output Selection */}
        <Grid item xs={12} md={6}>
          <MinecraftCard variant="crafting">
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <MinecraftBlock type="diamond" size={20} />
                {t('export.output.title', 'Output Settings')}
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <DirectorySelector
                  label={t('export.output.title', 'Output Settings')}
                  value={outputDirectory}
                  onChange={setOutputDirectory}
                  placeholder={t('export.output.placeholder', 'Select output directory...')}
                />
              </Box>
              
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>{t('export.format', 'Export Format')}</InputLabel>
                <Select
                  value={exportOptions.format}
                  label={t('export.format', 'Export Format')}
                  onChange={(e) => setExportOptions(prev => ({ ...prev, format: e.target.value as any }))}
                >
                  <MenuItem value="json">JSON</MenuItem>
                  <MenuItem value="lang">Lang</MenuItem>
                  <MenuItem value="properties">Properties</MenuItem>
                  <MenuItem value="yaml">YAML</MenuItem>
                </Select>
              </FormControl>
              
              <Box>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={exportOptions.createZip}
                      onChange={(e) => setExportOptions(prev => ({ ...prev, createZip: e.target.checked }))}
                    />
                  }
                  label={t('export.createZip', 'Create ZIP archive')}
                />
              </Box>
            </CardContent>
          </MinecraftCard>
        </Grid>

        {/* Language Files List */}
        {languageFiles.length > 0 && (
          <Grid item xs={12}>
            <MinecraftCard variant="inventory" glowing={selectedCount > 0}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <MinecraftBlock type="gold" size={20} animated={selectedCount > 0} />
                    {t('export.files.title', 'Language Files')}
                  </Typography>
                  
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <MinecraftButton size="small" variant="secondary" onClick={handleSelectAll}>
                      {t('common.selectAll', 'Select All')}
                    </MinecraftButton>
                    <MinecraftButton size="small" variant="secondary" onClick={handleDeselectAll}>
                      {t('common.deselectAll', 'Deselect All')}
                    </MinecraftButton>
                  </Box>
                </Box>
                
                {selectedCount > 0 && (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    {t('export.selection.summary', 
                      `Selected ${selectedCount} files with ${totalKeys} keys (${formatFileSize(totalSize)})`,
                      { count: selectedCount, keys: totalKeys, size: formatFileSize(totalSize) }
                    )}
                  </Alert>
                )}
                
                <List>
                  {languageFiles.map((file) => (
                    <ListItem
                      key={file.id}
                      sx={{
                        border: 1,
                        borderColor: 'divider',
                        borderRadius: 1,
                        mb: 1,
                        bgcolor: file.selected ? alpha(theme.palette.primary.main, 0.05) : 'transparent',
                      }}
                    >
                      <ListItemIcon>
                        <Checkbox
                          checked={file.selected}
                          onChange={() => handleToggleFileSelection(file.id)}
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="subtitle1">{file.language}</Typography>
                            <Chip label={file.name} size="small" variant="outlined" />
                          </Box>
                        }
                        secondary={
                          <Typography variant="body2" color="text.secondary">
                            {file.keys} keys • {formatFileSize(file.size)} • {file.path}
                          </Typography>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </MinecraftCard>
          </Grid>
        )}

        {/* Export Progress */}
        {exportProgress.status !== 'idle' && (
          <Grid item xs={12}>
            <MinecraftCard variant="default" glowing={exportProgress.status === 'exporting'}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <MinecraftBlock type="iron" size={20} animated={exportProgress.status === 'exporting'} />
                  {t('export.progress.title', 'Export Progress')}
                </Typography>
                
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">{exportProgress.currentFile}</Typography>
                    <Typography variant="body2">
                      {exportProgress.current} / {exportProgress.total}
                    </Typography>
                  </Box>
                  <ExperienceBar
                    progress={exportProgress.total > 0 ? (exportProgress.current / exportProgress.total) * 100 : 0}
                    level={exportProgress.exported}
                    animated={exportProgress.status === 'exporting'}
                  />
                </Box>
                
                {exportProgress.status === 'completed' && (
                  <Alert severity="success" sx={{ mb: 2 }}>
                    {t('export.progress.completed', 
                      `Export completed! ${exportProgress.exported} files exported successfully.`,
                      { exported: exportProgress.exported }
                    )}
                  </Alert>
                )}
                
                {exportProgress.status === 'error' && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    {t('export.progress.error', 'Export failed. Please try again.')}
                  </Alert>
                )}
              </CardContent>
            </MinecraftCard>
          </Grid>
        )}

        {/* Export Actions */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3, bgcolor: alpha(theme.palette.primary.main, 0.05) }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">
                {t('export.actions.title', 'Ready to Export?')}
              </Typography>
              
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <MinecraftButton
                  variant="primary"
                  size="large"
                  onClick={handleStartExport}
                  disabled={
                    selectedCount === 0 || 
                    !outputDirectory || 
                    exportProgress.status === 'exporting'
                  }
                >
                  {exportProgress.status === 'exporting'
                    ? t('export.exporting', 'Exporting...')
                    : t('export.startExport', 'Start Export')
                  }
                </MinecraftButton>
                
                {exportProgress.status === 'exporting' && (
                  <MinecraftButton
                    variant="danger"
                    size="large"
                    onClick={handleCancelExport}
                  >
                    {t('export.cancel', 'Cancel')}
                  </MinecraftButton>
                )}
                
                {exportProgress.status === 'completed' && (
                  <MinecraftButton
                    variant="secondary"
                    size="large"
                    onClick={handleOpenOutputDirectory}
                  >
                    {t('export.openOutputDirectory', 'Open Output Directory')}
                  </MinecraftButton>
                )}
                
                {/* 装饰性方块和苦力怕 */}
                <Box sx={{ display: 'flex', gap: 1, ml: 2, alignItems: 'center' }}>
                  <MinecraftBlock type="grass" size={16} />
                  <MinecraftBlock type="stone" size={16} />
                  <MinecraftBlock type="diamond" size={16} />
                  <Creeper size={20} onExplode={() => toast.success('苦力怕爆炸了！💥')} />
                  <Creeper size={16} onExplode={() => toast.success('小苦力怕也爆炸了！')} />
                </Box>
              </Box>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default ExportPage;