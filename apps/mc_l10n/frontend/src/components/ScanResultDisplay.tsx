import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Chip,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Alert,
  AlertTitle,
  Button,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  ExpandMore,
  Package,
  FileText,
  Globe,
  Warning,
  Error,
  CheckCircle,
  Folder,
  Code,
  Language,
  Settings,
  Info,
  Refresh
} from '@mui/icons-material';
import { motion } from 'framer-motion';

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

interface ScanResultDisplayProps {
  scanResult: ScanResult;
  onRescan?: () => void;
  compact?: boolean;
}

const ScanResultDisplay: React.FC<ScanResultDisplayProps> = ({ 
  scanResult, 
  onRescan, 
  compact = false 
}) => {
  const [expandedPanel, setExpandedPanel] = useState<string | false>('overview');

  const handleAccordionChange = (panel: string) => (
    event: React.SyntheticEvent, 
    isExpanded: boolean
  ) => {
    setExpandedPanel(isExpanded ? panel : false);
  };

  const formatDuration = (startTime: string, endTime?: string) => {
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const duration = Math.round((end.getTime() - start.getTime()) / 1000);
    
    if (duration < 60) {
      return `${duration}秒`;
    } else {
      const minutes = Math.floor(duration / 60);
      const seconds = duration % 60;
      return `${minutes}分${seconds}秒`;
    }
  };

  const getStatusColor = () => {
    if (scanResult.errors.length > 0) return 'error';
    if (scanResult.warnings.length > 0) return 'warning';
    return 'success';
  };

  const getStatusIcon = () => {
    if (scanResult.errors.length > 0) return <Error />;
    if (scanResult.warnings.length > 0) return <Warning />;
    return <CheckCircle />;
  };

  if (compact) {
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {getStatusIcon()}
              <Box>
                <Typography variant="subtitle1" fontWeight={600}>
                  扫描结果
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {scanResult.total_mods} 个模组 • {scanResult.total_language_files} 个语言文件
                </Typography>
              </Box>
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip 
                label={`${scanResult.total_translatable_keys} 个翻译键`} 
                size="small" 
                color="primary" 
              />
              {onRescan && (
                <Tooltip title="重新扫描">
                  <IconButton size="small" onClick={onRescan}>
                    <Refresh />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {getStatusIcon()}
              <Typography variant="h6" component="div">
                项目扫描结果
              </Typography>
              <Chip 
                label={getStatusColor() === 'success' ? '扫描成功' : 
                       getStatusColor() === 'warning' ? '有警告' : '有错误'}
                color={getStatusColor()}
                size="small"
              />
            </Box>
          }
          action={
            onRescan && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<Refresh />}
                onClick={onRescan}
              >
                重新扫描
              </Button>
            )
          }
        />
        
        <CardContent>
          {/* 概览信息 */}
          <Accordion 
            expanded={expandedPanel === 'overview'} 
            onChange={handleAccordionChange('overview')}
          >
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Info />
                <Typography variant="subtitle1">概览信息</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" color="text.secondary">项目路径</Typography>
                    <Typography variant="body1" sx={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                      {scanResult.project_path}
                    </Typography>
                  </Box>
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" color="text.secondary">扫描时间</Typography>
                    <Typography variant="body1">
                      {formatDuration(scanResult.scan_started_at, scanResult.scan_completed_at)}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Card variant="outlined" sx={{ textAlign: 'center', p: 2 }}>
                        <Package color="primary" sx={{ mb: 1 }} />
                        <Typography variant="h4" color="primary">
                          {scanResult.total_mods}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          模组数量
                        </Typography>
                      </Card>
                    </Grid>
                    <Grid item xs={6}>
                      <Card variant="outlined" sx={{ textAlign: 'center', p: 2 }}>
                        <FileText color="secondary" sx={{ mb: 1 }} />
                        <Typography variant="h4" color="secondary">
                          {scanResult.total_language_files}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          语言文件
                        </Typography>
                      </Card>
                    </Grid>
                    <Grid item xs={12}>
                      <Card variant="outlined" sx={{ textAlign: 'center', p: 2 }}>
                        <Language color="success" sx={{ mb: 1 }} />
                        <Typography variant="h4" color="success.main">
                          {scanResult.total_translatable_keys}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          可翻译键值
                        </Typography>
                      </Card>
                    </Grid>
                  </Grid>
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>

          {/* 模组包信息 */}
          {scanResult.modpack_manifest && (
            <Accordion 
              expanded={expandedPanel === 'modpack'} 
              onChange={handleAccordionChange('modpack')}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Package />
                  <Typography variant="subtitle1">模组包信息</Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">名称</Typography>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                      {scanResult.modpack_manifest.name}
                    </Typography>
                    
                    <Typography variant="body2" color="text.secondary">版本</Typography>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                      {scanResult.modpack_manifest.version}
                    </Typography>
                    
                    {scanResult.modpack_manifest.author && (
                      <>
                        <Typography variant="body2" color="text.secondary">作者</Typography>
                        <Typography variant="body1" sx={{ mb: 2 }}>
                          {scanResult.modpack_manifest.author}
                        </Typography>
                      </>
                    )}
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">Minecraft 版本</Typography>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                      {scanResult.modpack_manifest.minecraft_version}
                    </Typography>
                    
                    <Typography variant="body2" color="text.secondary">模组加载器</Typography>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                      {scanResult.modpack_manifest.loader} {scanResult.modpack_manifest.loader_version}
                    </Typography>
                    
                    <Typography variant="body2" color="text.secondary">平台</Typography>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                      {scanResult.modpack_manifest.platform}
                    </Typography>
                  </Grid>
                  {scanResult.modpack_manifest.description && (
                    <Grid item xs={12}>
                      <Typography variant="body2" color="text.secondary">描述</Typography>
                      <Typography variant="body1">
                        {scanResult.modpack_manifest.description}
                      </Typography>
                    </Grid>
                  )}
                </Grid>
              </AccordionDetails>
            </Accordion>
          )}

          {/* 模组列表 */}
          {scanResult.mod_jars.length > 0 && (
            <Accordion 
              expanded={expandedPanel === 'mods'} 
              onChange={handleAccordionChange('mods')}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Settings />
                  <Typography variant="subtitle1">
                    模组列表 ({scanResult.mod_jars.length})
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <List>
                  {scanResult.mod_jars.map((mod, index) => (
                    <React.Fragment key={mod.mod_id}>
                      <ListItem>
                        <ListItemIcon>
                          <Code />
                        </ListItemIcon>
                        <ListItemText
                          primary={mod.display_name}
                          secondary={
                            <Box>
                              <Typography variant="caption" display="block">
                                ID: {mod.mod_id} • 版本: {mod.version}
                              </Typography>
                              <Typography variant="caption" display="block">
                                作者: {mod.authors.join(', ')}
                              </Typography>
                              {mod.description && (
                                <Typography variant="caption" display="block">
                                  {mod.description}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Chip label={mod.loader} size="small" />
                          <Chip label={mod.environment} size="small" variant="outlined" />
                        </Box>
                      </ListItem>
                      {index < scanResult.mod_jars.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          )}

          {/* 支持的语言 */}
          {scanResult.supported_locales.length > 0 && (
            <Accordion 
              expanded={expandedPanel === 'locales'} 
              onChange={handleAccordionChange('locales')}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Globe />
                  <Typography variant="subtitle1">
                    支持的语言 ({scanResult.supported_locales.length})
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {scanResult.supported_locales.map((locale) => (
                    <Chip key={locale} label={locale} variant="outlined" />
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          )}

          {/* 警告和错误 */}
          {(scanResult.warnings.length > 0 || scanResult.errors.length > 0) && (
            <Accordion 
              expanded={expandedPanel === 'issues'} 
              onChange={handleAccordionChange('issues')}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Warning />
                  <Typography variant="subtitle1">
                    问题和警告 ({scanResult.warnings.length + scanResult.errors.length})
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                {scanResult.errors.length > 0 && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    <AlertTitle>错误 ({scanResult.errors.length})</AlertTitle>
                    <List dense>
                      {scanResult.errors.map((error, index) => (
                        <ListItem key={index}>
                          <ListItemText primary={error} />
                        </ListItem>
                      ))}
                    </List>
                  </Alert>
                )}
                
                {scanResult.warnings.length > 0 && (
                  <Alert severity="warning">
                    <AlertTitle>警告 ({scanResult.warnings.length})</AlertTitle>
                    <List dense>
                      {scanResult.warnings.map((warning, index) => (
                        <ListItem key={index}>
                          <ListItemText primary={warning} />
                        </ListItem>
                      ))}
                    </List>
                  </Alert>
                )}
              </AccordionDetails>
            </Accordion>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default ScanResultDisplay;