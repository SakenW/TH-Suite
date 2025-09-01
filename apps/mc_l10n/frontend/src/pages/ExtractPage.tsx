import React, { useState, useCallback } from 'react';
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
} from '@mui/material';
import {
  Archive,
  FolderOpen,
  Download,
  Play,
  Pause,
  Square,
  FileText,
  Image,
  Music,
  Trash2,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';

import { useAppStore } from '@stores/appStore';
import { tauriService, FILE_FILTERS } from '@services';
import { apiService } from '@services/apiService';

interface ExtractSource {
  id: string;
  path: string;
  name: string;
  size: number;
  type: 'jar' | 'zip' | 'rar' | '7z' | 'other';
}

interface ExtractItem {
  id: string;
  path: string;
  name: string;
  type: 'texture' | 'model' | 'sound' | 'lang' | 'data' | 'other';
  size: number;
  selected: boolean;
}

interface ExtractProgress {
  current: number;
  total: number;
  currentFile: string;
  status: 'idle' | 'analyzing' | 'extracting' | 'paused' | 'completed' | 'error';
  extracted: number;
  failed: number;
}

function ExtractPage() {
  const theme = useTheme();
  const { addRecentProject } = useAppStore();
  
  const [extractSources, setExtractSources] = useState<ExtractSource[]>([]);
  const [extractItems, setExtractItems] = useState<ExtractItem[]>([]);
  const [extractProgress, setExtractProgress] = useState<ExtractProgress>({
    current: 0,
    total: 0,
    currentFile: '',
    status: 'idle',
    extracted: 0,
    failed: 0,
  });
  const [extractOptions, setExtractOptions] = useState({
    preserveStructure: true,
    overwriteExisting: false,
    createSubfolders: true,
    filterByType: false,
    selectedTypes: ['texture', 'model', 'sound', 'lang', 'data'],
  });
  const [outputDirectory, setOutputDirectory] = useState('');

  const handleAddSources = useCallback(async () => {
    try {
      const selectedFiles = await tauriService.selectFiles({
        title: 'Select Archive Files to Extract',
        filters: [
          FILE_FILTERS.JAR,
          FILE_FILTERS.ZIP,
          { name: 'Archive Files', extensions: ['rar', '7z', 'tar', 'gz'] },
          FILE_FILTERS.ALL,
        ],
      });
      
      if (selectedFiles.length > 0) {
        const newSources: ExtractSource[] = selectedFiles.map(filePath => {
          const name = filePath.split(/[\\/]/).pop() || 'Unknown';
          const extension = name.split('.').pop()?.toLowerCase() || 'other';
          const type = ['jar', 'zip', 'rar', '7z'].includes(extension) ? extension as any : 'other';
          
          return {
            id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            path: filePath,
            name,
            size: Math.floor(Math.random() * 10000000), // Mock size
            type,
          };
        });
        
        setExtractSources(prev => [...prev, ...newSources]);
        toast.success(`Added ${selectedFiles.length} archive file(s)`);
      }
    } catch (error) {
      console.error('Failed to select files:', error);
      toast.error('Failed to select files');
    }
  }, []);

  const handleRemoveSource = useCallback((sourceId: string) => {
    setExtractSources(prev => prev.filter(source => source.id !== sourceId));
    // Clear items if this was the analyzed source
    setExtractItems([]);
  }, []);

  const handleSelectOutputDirectory = useCallback(async () => {
    try {
      const selectedPath = await tauriService.selectDirectory({
        title: 'Select Output Directory',
      });
      
      if (selectedPath) {
        setOutputDirectory(selectedPath);
      }
    } catch (error) {
      console.error('Failed to select output directory:', error);
      toast.error('Failed to select output directory');
    }
  }, []);

  const handleAnalyzeSources = useCallback(async () => {
    if (extractSources.length === 0) {
      toast.error('Please add at least one archive file');
      return;
    }

    try {
      setExtractProgress(prev => ({ ...prev, status: 'analyzing' }));
      setExtractItems([]);
      
      // Create mock inventory for now - in a real implementation, this would come from scan results
      const mockInventory = {
        items: extractSources.flatMap(source => [
          {
            id: `${source.id}-lang-1`,
            path: `${source.path}/assets/minecraft/lang/en_us.json`,
            name: 'en_us.json',
            type: 'lang',
            size: Math.floor(Math.random() * 50000),
            locale: 'en_us',
            metadata: { source: source.name }
          },
          {
            id: `${source.id}-lang-2`,
            path: `${source.path}/assets/minecraft/lang/zh_cn.json`,
            name: 'zh_cn.json',
            type: 'lang',
            size: Math.floor(Math.random() * 50000),
            locale: 'zh_cn',
            metadata: { source: source.name }
          }
        ])
      };
      
      setExtractProgress(prev => ({ 
        ...prev, 
        total: mockInventory.items.length,
        currentFile: 'Starting extraction analysis...'
      }));
      
      // Call the real API
      const response = await apiService.extractTranslations({
        inventory: mockInventory,
        target_locales: ['en_us', 'zh_cn'],
        include_metadata: true
      });
      
      if (response.success && response.data) {
        // Convert API response to ExtractItem format
        const extractItems: ExtractItem[] = mockInventory.items.map(item => ({
          id: item.id,
          path: item.path,
          name: item.name,
          type: item.type as any,
          size: item.size,
          selected: true
        }));
        
        setExtractItems(extractItems);
        setExtractProgress(prev => ({ 
          ...prev, 
          status: 'idle', 
          currentFile: `Analysis completed! Found ${extractItems.length} items.`,
          current: extractItems.length
        }));
        
        toast.success(`Analysis completed! Found ${extractItems.length} extractable items.`);
      } else {
        throw new Error(response.error?.message || 'Failed to analyze sources');
      }
    } catch (error) {
      console.error('Analysis failed:', error);
      setExtractProgress(prev => ({ ...prev, status: 'error' }));
      toast.error(`Analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }, [extractSources, extractProgress.status]);

  const handleStartExtraction = useCallback(async () => {
    const selectedItems = extractItems.filter(item => item.selected);
    
    if (selectedItems.length === 0) {
      toast.error('Please select at least one item to extract');
      return;
    }

    if (!outputDirectory) {
      toast.error('Please select an output directory');
      return;
    }

    try {
      setExtractProgress(prev => ({ 
        ...prev, 
        status: 'extracting',
        total: selectedItems.length,
        current: 0,
        extracted: 0,
        failed: 0,
      }));
      
      for (let i = 0; i < selectedItems.length; i++) {
        if (extractProgress.status === 'paused') {
          break;
        }
        
        const item = selectedItems[i];
        
        // Simulate extraction
        await new Promise(resolve => setTimeout(resolve, 100));
        
        const success = Math.random() > 0.1; // 90% success rate
        
        setExtractProgress(prev => ({
          ...prev,
          current: i + 1,
          currentFile: `Extracting ${item.name}...`,
          extracted: prev.extracted + (success ? 1 : 0),
          failed: prev.failed + (success ? 0 : 1),
        }));
      }
      
      setExtractProgress(prev => ({ 
        ...prev, 
        status: 'completed', 
        currentFile: `Extraction completed! ${prev.extracted} extracted, ${prev.failed} failed.`,
      }));
      
      // Add to recent projects
      addRecentProject({
        name: `Extract - ${new Date().toLocaleDateString()}`,
        path: outputDirectory,
        type: 'extract',
      });
      
      toast.success(`Extraction completed! ${extractProgress.extracted} files extracted.`);
    } catch (error) {
      console.error('Extraction failed:', error);
      setExtractProgress(prev => ({ ...prev, status: 'error' }));
      toast.error('Extraction failed');
    }
  }, [extractItems, outputDirectory, extractProgress.status, extractProgress.extracted, addRecentProject]);

  const handlePauseExtraction = useCallback(() => {
    setExtractProgress(prev => ({ ...prev, status: 'paused' }));
  }, []);

  const handleStopExtraction = useCallback(() => {
    setExtractProgress({
      current: 0,
      total: 0,
      currentFile: '',
      status: 'idle',
      extracted: 0,
      failed: 0,
    });
  }, []);

  const handleToggleItemSelection = useCallback((itemId: string) => {
    setExtractItems(prev => prev.map(item => 
      item.id === itemId ? { ...item, selected: !item.selected } : item
    ));
  }, []);

  const handleSelectAllItems = useCallback((selected: boolean) => {
    setExtractItems(prev => prev.map(item => ({ ...item, selected })));
  }, []);

  const handleFilterByType = useCallback((type: string, selected: boolean) => {
    setExtractItems(prev => prev.map(item => 
      item.type === type ? { ...item, selected } : item
    ));
  }, []);

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'texture':
        return <Image size={16} />;
      case 'model':
        return <Archive size={16} />;
      case 'sound':
        return <Music size={16} />;
      case 'lang':
      case 'data':
        return <FileText size={16} />;
      default:
        return <FileText size={16} />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'texture':
        return '#2196f3';
      case 'model':
        return '#4caf50';
      case 'sound':
        return '#ff9800';
      case 'lang':
        return '#9c27b0';
      case 'data':
        return '#f44336';
      default:
        return '#757575';
    }
  };

  const getArchiveIcon = (type: string) => {
    return <Archive size={20} />;
  };

  const isAnalyzing = extractProgress.status === 'analyzing';
  const isExtracting = extractProgress.status === 'extracting';
  const isPaused = extractProgress.status === 'paused';
  const isCompleted = extractProgress.status === 'completed';
  const hasError = extractProgress.status === 'error';
  const isWorking = isAnalyzing || isExtracting;

  const selectedItemsCount = extractItems.filter(item => item.selected).length;
  const typeGroups = extractItems.reduce((acc, item) => {
    acc[item.type] = (acc[item.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        padding: 3,
        backgroundColor: theme.palette.background.default,
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Typography
          variant="h4"
          sx={{
            fontWeight: 700,
            color: theme.palette.text.primary,
            marginBottom: 1,
          }}
        >
          Extract Resources
        </Typography>
        <Typography
          variant="body1"
          sx={{
            color: theme.palette.text.secondary,
            marginBottom: 3,
          }}
        >
          Extract resources from JAR files, ZIP archives, and other compressed formats
        </Typography>
      </motion.div>

      {/* Archive Sources */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <Card sx={{ marginBottom: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ marginBottom: 2, fontWeight: 600 }}>
              Archive Sources
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 2, marginBottom: 2 }}>
              <Button
                variant="outlined"
                startIcon={<Archive size={18} />}
                onClick={handleAddSources}
                disabled={isWorking}
              >
                Add Archive Files
              </Button>
              
              {extractSources.length > 0 && (
                <Button
                  variant="contained"
                  startIcon={<Download size={18} />}
                  onClick={handleAnalyzeSources}
                  disabled={isWorking}
                >
                  Analyze Archives
                </Button>
              )}
            </Box>

            {extractSources.length === 0 ? (
              <Alert severity="info">
                No archive files added. Click "Add Archive Files" to select JAR, ZIP, or other archive files.
              </Alert>
            ) : (
              <List>
                {extractSources.map((source) => (
                  <ListItem
                    key={source.id}
                    sx={{
                      border: `1px solid ${theme.palette.divider}`,
                      borderRadius: 1,
                      marginBottom: 1,
                    }}
                    secondaryAction={
                      <IconButton
                        edge="end"
                        onClick={() => handleRemoveSource(source.id)}
                        disabled={isWorking}
                        sx={{ color: theme.palette.error.main }}
                      >
                        <Trash2 size={18} />
                      </IconButton>
                    }
                  >
                    <ListItemIcon>
                      {getArchiveIcon(source.type)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {source.name}
                          </Typography>
                          <Chip
                            label={source.type.toUpperCase()}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.7rem', height: 20 }}
                          />
                        </Box>
                      }
                      secondary={
                        <Typography variant="caption" color="text.secondary">
                          {source.path} • {(source.size / 1024 / 1024).toFixed(1)} MB
                        </Typography>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Extract Options */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <Card sx={{ marginBottom: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ marginBottom: 2, fontWeight: 600 }}>
              Extract Options
            </Typography>
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, marginBottom: 3 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={extractOptions.preserveStructure}
                    onChange={(e) => setExtractOptions(prev => ({ ...prev, preserveStructure: e.target.checked }))}
                    disabled={isWorking}
                  />
                }
                label="Preserve directory structure"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={extractOptions.overwriteExisting}
                    onChange={(e) => setExtractOptions(prev => ({ ...prev, overwriteExisting: e.target.checked }))}
                    disabled={isWorking}
                  />
                }
                label="Overwrite existing files"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={extractOptions.createSubfolders}
                    onChange={(e) => setExtractOptions(prev => ({ ...prev, createSubfolders: e.target.checked }))}
                    disabled={isWorking}
                  />
                }
                label="Create subfolders by type"
              />
            </Box>

            <TextField
              label="Output Directory"
              value={outputDirectory}
              onClick={handleSelectOutputDirectory}
              placeholder="Click to select output directory"
              InputProps={{
                readOnly: true,
                endAdornment: (
                  <IconButton onClick={handleSelectOutputDirectory} disabled={isWorking}>
                    <FolderOpen size={18} />
                  </IconButton>
                ),
              }}
              fullWidth
              disabled={isWorking}
            />
          </CardContent>
        </Card>
      </motion.div>

      {/* Progress */}
      <AnimatePresence>
        {(isWorking || isPaused || isCompleted || hasError) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Card sx={{ marginBottom: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, marginBottom: 2 }}>
                  {isExtracting && (
                    <>
                      <Button
                        variant="outlined"
                        startIcon={<Pause size={18} />}
                        onClick={handlePauseExtraction}
                      >
                        Pause
                      </Button>
                      <Button
                        variant="outlined"
                        color="error"
                        startIcon={<Square size={18} />}
                        onClick={handleStopExtraction}
                      >
                        Stop
                      </Button>
                    </>
                  )}
                  
                  {isCompleted && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CheckCircle size={20} color={theme.palette.success.main} />
                      <Typography variant="body2" color="success.main" sx={{ fontWeight: 500 }}>
                        Extraction completed!
                      </Typography>
                    </Box>
                  )}
                  
                  {hasError && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <AlertCircle size={20} color={theme.palette.error.main} />
                      <Typography variant="body2" color="error.main" sx={{ fontWeight: 500 }}>
                        Extraction failed!
                      </Typography>
                    </Box>
                  )}
                </Box>

                <Box sx={{ marginBottom: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', marginBottom: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {extractProgress.currentFile}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {extractProgress.current} / {extractProgress.total}
                      {isExtracting && ` • ${extractProgress.extracted} extracted, ${extractProgress.failed} failed`}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={extractProgress.total > 0 ? (extractProgress.current / extractProgress.total) * 100 : 0}
                    sx={{ height: 8, borderRadius: 4 }}
                    color={hasError ? 'error' : isCompleted ? 'success' : 'primary'}
                  />
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Extract Items */}
      <AnimatePresence>
        {extractItems.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
          >
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Extractable Items ({extractItems.length})
                  </Typography>
                  
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button
                      size="small"
                      onClick={() => handleSelectAllItems(true)}
                      disabled={isWorking}
                    >
                      Select All
                    </Button>
                    <Button
                      size="small"
                      onClick={() => handleSelectAllItems(false)}
                      disabled={isWorking}
                    >
                      Select None
                    </Button>
                    <Button
                      variant="contained"
                      startIcon={<Download size={18} />}
                      onClick={handleStartExtraction}
                      disabled={isWorking || selectedItemsCount === 0 || !outputDirectory}
                    >
                      Extract Selected ({selectedItemsCount})
                    </Button>
                  </Box>
                </Box>
                
                {/* Type filters */}
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, marginBottom: 2 }}>
                  {Object.entries(typeGroups).map(([type, count]) => (
                    <Chip
                      key={type}
                      label={`${type} (${count})`}
                      size="small"
                      onClick={() => {
                        const typeItems = extractItems.filter(item => item.type === type);
                        const allSelected = typeItems.every(item => item.selected);
                        handleFilterByType(type, !allSelected);
                      }}
                      sx={{
                        backgroundColor: alpha(getTypeColor(type), 0.1),
                        color: getTypeColor(type),
                        cursor: 'pointer',
                        textTransform: 'capitalize',
                      }}
                      disabled={isWorking}
                    />
                  ))}
                </Box>
                
                <List sx={{ maxHeight: 400, overflow: 'auto' }}>
                  {extractItems.map((item, index) => (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.02 }}
                    >
                      <ListItem
                        sx={{
                          border: `1px solid ${theme.palette.divider}`,
                          borderRadius: 1,
                          marginBottom: 1,
                          backgroundColor: item.selected ? alpha(theme.palette.primary.main, 0.05) : 'transparent',
                        }}
                        secondaryAction={
                          <Checkbox
                            checked={item.selected}
                            onChange={() => handleToggleItemSelection(item.id)}
                            disabled={isWorking}
                          />
                        }
                      >
                        <ListItemIcon sx={{ color: getTypeColor(item.type) }}>
                          {getFileIcon(item.type)}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                {item.name}
                              </Typography>
                              <Chip
                                label={item.type}
                                size="small"
                                sx={{
                                  backgroundColor: alpha(getTypeColor(item.type), 0.1),
                                  color: getTypeColor(item.type),
                                  fontSize: '0.7rem',
                                  height: 20,
                                }}
                              />
                            </Box>
                          }
                          secondary={
                            <Typography variant="caption" color="text.secondary">
                              {item.path} • {(item.size / 1024).toFixed(1)} KB
                            </Typography>
                          }
                        />
                      </ListItem>
                    </motion.div>
                  ))}
                </List>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </Box>
  );
}

export default ExtractPage;