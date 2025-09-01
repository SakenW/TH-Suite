import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
  CircularProgress,
  useTheme,
  alpha,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Badge,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  FileText,
  Eye,
  Download,
  RefreshCw,
  Search,
  Filter,
  Calendar,
  User,
  Lock,
  Key,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Database,
  Activity,
  Settings,
} from 'lucide-react';
import { ExpandMore } from '@mui/icons-material';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { useAppStore } from '@stores/appStore';
import { apiService } from '@services/apiService';
import { useMcStudioTranslation } from '@hooks/useTranslation';

interface IntegrityCheckResult {
  id: string;
  file_path: string;
  expected_hash: string;
  actual_hash: string;
  is_valid: boolean;
  check_time: string;
  algorithm: string;
  file_size: number;
}

interface LicenseRecord {
  id: string;
  asset_id: string;
  source_platform: string;
  project_id: string;
  file_id: string;
  license_type: string;
  license_url?: string;
  attribution_required: boolean;
  commercial_use_allowed: boolean;
  modification_allowed: boolean;
  redistribution_allowed: boolean;
  recorded_at: string;
  metadata: Record<string, any>;
}

interface AuditLogEntry {
  id: string;
  event_id: string;
  event_type: string;
  user_id?: string;
  project_id?: string;
  resource_type: string;
  resource_id: string;
  action: string;
  result: string;
  ip_address?: string;
  user_agent?: string;
  details: Record<string, any>;
  timestamp: string;
  signature?: string;
}

interface SecurityStats {
  total_integrity_checks: number;
  failed_integrity_checks: number;
  total_license_records: number;
  total_audit_logs: number;
  last_security_scan: string;
}

function SecurityPage() {
  const theme = useTheme();
  const { t } = useMcStudioTranslation();
  const { currentProject } = useAppStore();
  
  // 状态管理
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState({
    stats: false,
    integrity: false,
    licenses: false,
    audit: false,
  });
  
  // 数据状态
  const [securityStats, setSecurityStats] = useState<SecurityStats | null>(null);
  const [integrityResults, setIntegrityResults] = useState<IntegrityCheckResult[]>([]);
  const [licenseRecords, setLicenseRecords] = useState<LicenseRecord[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  
  // 过滤和搜索
  const [integrityFilter, setIntegrityFilter] = useState<'all' | 'valid' | 'invalid'>('all');
  const [licenseFilter, setLicenseFilter] = useState<string>('all');
  const [auditFilter, setAuditFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  
  // 对话框状态
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const [selectedLicense, setSelectedLicense] = useState<LicenseRecord | null>(null);
  
  // 加载安全统计
  const loadSecurityStats = async () => {
    setLoading(prev => ({ ...prev, stats: true }));
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));
      setSecurityStats({
        total_integrity_checks: 156,
        failed_integrity_checks: 3,
        total_license_records: 89,
        total_audit_logs: 1247,
        last_security_scan: new Date().toISOString(),
      });
    } catch (error) {
      toast.error(t('security.messages.loadStatsFailed'));
    } finally {
      setLoading(prev => ({ ...prev, stats: false }));
    }
  };
  
  // 加载完整性检查结果
  const loadIntegrityResults = async () => {
    setLoading(prev => ({ ...prev, integrity: true }));
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 800));
      const mockResults: IntegrityCheckResult[] = [
        {
          id: '1',
          file_path: '/assets/textures/block/stone.png',
          expected_hash: 'a1b2c3d4e5f6',
          actual_hash: 'a1b2c3d4e5f6',
          is_valid: true,
          check_time: new Date().toISOString(),
          algorithm: 'SHA256',
          file_size: 2048,
        },
        {
          id: '2',
          file_path: '/assets/models/block/furnace.json',
          expected_hash: 'x1y2z3a4b5c6',
          actual_hash: 'x1y2z3a4b5c7',
          is_valid: false,
          check_time: new Date().toISOString(),
          algorithm: 'SHA256',
          file_size: 1024,
        },
      ];
      setIntegrityResults(mockResults);
    } catch (error) {
      toast.error(t('security.messages.loadIntegrityFailed'));
    } finally {
      setLoading(prev => ({ ...prev, integrity: false }));
    }
  };
  
  // 加载许可记录
  const loadLicenseRecords = async () => {
    setLoading(prev => ({ ...prev, licenses: true }));
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 600));
      const mockLicenses: LicenseRecord[] = [
        {
          id: '1',
          asset_id: 'texture_pack_001',
          source_platform: 'curseforge',
          project_id: 'project_123',
          file_id: 'file_456',
          license_type: 'MIT',
          license_url: 'https://opensource.org/licenses/MIT',
          attribution_required: false,
          commercial_use_allowed: true,
          modification_allowed: true,
          redistribution_allowed: true,
          recorded_at: new Date().toISOString(),
          metadata: { author: 'TestUser', version: '1.0.0' },
        },
      ];
      setLicenseRecords(mockLicenses);
    } catch (error) {
      toast.error(t('security.messages.loadLicensesFailed'));
    } finally {
      setLoading(prev => ({ ...prev, licenses: false }));
    }
  };
  
  // 加载审计日志
  const loadAuditLogs = async () => {
    setLoading(prev => ({ ...prev, audit: true }));
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 700));
      const mockLogs: AuditLogEntry[] = [
        {
          id: '1',
          event_id: 'evt_001',
          event_type: 'build',
          user_id: 'user_123',
          project_id: currentProject?.id || 'project_456',
          resource_type: 'project',
          resource_id: 'res_789',
          action: 'create_build',
          result: 'success',
          ip_address: '192.168.1.100',
          user_agent: 'MC-Studio/1.0.0',
          details: { build_type: 'release', target: 'java' },
          timestamp: new Date().toISOString(),
          signature: 'sig_abc123',
        },
      ];
      setAuditLogs(mockLogs);
    } catch (error) {
      toast.error(t('security.messages.loadAuditFailed'));
    } finally {
      setLoading(prev => ({ ...prev, audit: false }));
    }
  };
  
  // 执行完整性检查
  const runIntegrityCheck = async () => {
    if (!currentProject) {
      toast.error(t('security.messages.noProject'));
      return;
    }
    
    setLoading(prev => ({ ...prev, integrity: true }));
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 2000));
      toast.success(t('security.messages.integrityCheckComplete'));
      await loadIntegrityResults();
    } catch (error) {
      toast.error(t('security.messages.integrityCheckFailed'));
    } finally {
      setLoading(prev => ({ ...prev, integrity: false }));
    }
  };
  
  useEffect(() => {
    loadSecurityStats();
    loadIntegrityResults();
    loadLicenseRecords();
    loadAuditLogs();
  }, []);
  
  // 过滤数据
  const filteredIntegrityResults = integrityResults.filter(result => {
    if (integrityFilter === 'valid' && !result.is_valid) return false;
    if (integrityFilter === 'invalid' && result.is_valid) return false;
    if (searchTerm && !result.file_path.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });
  
  const filteredLicenseRecords = licenseRecords.filter(record => {
    if (licenseFilter !== 'all' && record.license_type !== licenseFilter) return false;
    if (searchTerm && !record.asset_id.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });
  
  const filteredAuditLogs = auditLogs.filter(log => {
    if (auditFilter !== 'all' && log.event_type !== auditFilter) return false;
    if (searchTerm && !log.action.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });
  
  const getStatusIcon = (isValid: boolean) => {
    return isValid ? (
      <CheckCircle size={20} color={theme.palette.success.main} />
    ) : (
      <XCircle size={20} color={theme.palette.error.main} />
    );
  };
  
  const getResultChip = (result: string) => {
    const color = result === 'success' ? 'success' : result === 'failure' ? 'error' : 'default';
    return <Chip label={result} color={color} size="small" />;
  };
  
  return (
    <Box sx={{ p: 3 }}>
      {/* 页面标题 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <Shield size={32} color={theme.palette.primary.main} />
          <Box sx={{ ml: 2 }}>
            <Typography variant="h4" component="h1" gutterBottom>
              {t('security.title')}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {t('security.description')}
            </Typography>
          </Box>
        </Box>
        
        {!currentProject && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {t('security.messages.noProject')}
          </Alert>
        )}
      </motion.div>
      
      {/* 安全统计概览 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography variant="h6" color="primary">
                      {securityStats?.total_integrity_checks || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t('security.stats.totalChecks')}
                    </Typography>
                  </Box>
                  <ShieldCheck size={24} color={theme.palette.primary.main} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography variant="h6" color="error">
                      {securityStats?.failed_integrity_checks || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t('security.stats.failedChecks')}
                    </Typography>
                  </Box>
                  <ShieldAlert size={24} color={theme.palette.error.main} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography variant="h6" color="info">
                      {securityStats?.total_license_records || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t('security.stats.licenseRecords')}
                    </Typography>
                  </Box>
                  <FileText size={24} color={theme.palette.info.main} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography variant="h6" color="secondary">
                      {securityStats?.total_audit_logs || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t('security.stats.auditLogs')}
                    </Typography>
                  </Box>
                  <Activity size={24} color={theme.palette.secondary.main} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </motion.div>
      
      {/* 主要内容区域 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <Card>
          <CardContent>
            {/* 标签页 */}
            <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)} sx={{ mb: 3 }}>
              <Tab
                icon={<ShieldCheck size={20} />}
                label={t('security.tabs.integrity')}
                iconPosition="start"
              />
              <Tab
                icon={<FileText size={20} />}
                label={t('security.tabs.licenses')}
                iconPosition="start"
              />
              <Tab
                icon={<Activity size={20} />}
                label={t('security.tabs.audit')}
                iconPosition="start"
              />
            </Tabs>
            
            {/* 搜索和过滤 */}
            <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
              <TextField
                size="small"
                placeholder={t('security.search.placeholder')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: <Search size={20} />,
                }}
                sx={{ minWidth: 200 }}
              />
              
              {activeTab === 0 && (
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>{t('security.filters.status')}</InputLabel>
                  <Select
                    value={integrityFilter}
                    onChange={(e) => setIntegrityFilter(e.target.value as any)}
                    label={t('security.filters.status')}
                  >
                    <MenuItem value="all">{t('security.filters.all')}</MenuItem>
                    <MenuItem value="valid">{t('security.filters.valid')}</MenuItem>
                    <MenuItem value="invalid">{t('security.filters.invalid')}</MenuItem>
                  </Select>
                </FormControl>
              )}
              
              {activeTab === 1 && (
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>{t('security.filters.license')}</InputLabel>
                  <Select
                    value={licenseFilter}
                    onChange={(e) => setLicenseFilter(e.target.value)}
                    label={t('security.filters.license')}
                  >
                    <MenuItem value="all">{t('security.filters.all')}</MenuItem>
                    <MenuItem value="MIT">MIT</MenuItem>
                    <MenuItem value="GPL">GPL</MenuItem>
                    <MenuItem value="Apache">Apache</MenuItem>
                  </Select>
                </FormControl>
              )}
              
              {activeTab === 2 && (
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>{t('security.filters.eventType')}</InputLabel>
                  <Select
                    value={auditFilter}
                    onChange={(e) => setAuditFilter(e.target.value)}
                    label={t('security.filters.eventType')}
                  >
                    <MenuItem value="all">{t('security.filters.all')}</MenuItem>
                    <MenuItem value="build">{t('security.filters.build')}</MenuItem>
                    <MenuItem value="upload">{t('security.filters.upload')}</MenuItem>
                    <MenuItem value="download">{t('security.filters.download')}</MenuItem>
                  </Select>
                </FormControl>
              )}
              
              {activeTab === 0 && (
                <Button
                  variant="contained"
                  startIcon={<RefreshCw size={16} />}
                  onClick={runIntegrityCheck}
                  disabled={loading.integrity || !currentProject}
                >
                  {loading.integrity ? (
                    <CircularProgress size={16} />
                  ) : (
                    t('security.actions.runCheck')
                  )}
                </Button>
              )}
            </Box>
            
            {/* 完整性检查结果 */}
            {activeTab === 0 && (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('security.integrity.status')}</TableCell>
                      <TableCell>{t('security.integrity.filePath')}</TableCell>
                      <TableCell>{t('security.integrity.algorithm')}</TableCell>
                      <TableCell>{t('security.integrity.fileSize')}</TableCell>
                      <TableCell>{t('security.integrity.checkTime')}</TableCell>
                      <TableCell align="right">{t('security.actions.actions')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {loading.integrity ? (
                      <TableRow>
                        <TableCell colSpan={6} align="center">
                          <CircularProgress />
                        </TableCell>
                      </TableRow>
                    ) : filteredIntegrityResults.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} align="center">
                          {t('security.messages.noData')}
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredIntegrityResults.map((result) => (
                        <TableRow key={result.id}>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {getStatusIcon(result.is_valid)}
                              <Chip
                                label={result.is_valid ? t('security.status.valid') : t('security.status.invalid')}
                                color={result.is_valid ? 'success' : 'error'}
                                size="small"
                              />
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                              {result.file_path}
                            </Typography>
                          </TableCell>
                          <TableCell>{result.algorithm}</TableCell>
                          <TableCell>{(result.file_size / 1024).toFixed(1)} KB</TableCell>
                          <TableCell>{new Date(result.check_time).toLocaleString()}</TableCell>
                          <TableCell align="right">
                            <Tooltip title={t('security.actions.viewDetails')}>
                              <IconButton size="small">
                                <Eye size={16} />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
            
            {/* 许可记录 */}
            {activeTab === 1 && (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('security.license.assetId')}</TableCell>
                      <TableCell>{t('security.license.platform')}</TableCell>
                      <TableCell>{t('security.license.type')}</TableCell>
                      <TableCell>{t('security.license.permissions')}</TableCell>
                      <TableCell>{t('security.license.recordedAt')}</TableCell>
                      <TableCell align="right">{t('security.actions.actions')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {loading.licenses ? (
                      <TableRow>
                        <TableCell colSpan={6} align="center">
                          <CircularProgress />
                        </TableCell>
                      </TableRow>
                    ) : filteredLicenseRecords.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} align="center">
                          {t('security.messages.noData')}
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredLicenseRecords.map((record) => (
                        <TableRow key={record.id}>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                              {record.asset_id}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={record.source_platform} size="small" />
                          </TableCell>
                          <TableCell>
                            <Chip label={record.license_type} color="primary" size="small" />
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                              {record.commercial_use_allowed && (
                                <Chip label={t('security.license.commercial')} size="small" color="success" />
                              )}
                              {record.modification_allowed && (
                                <Chip label={t('security.license.modify')} size="small" color="info" />
                              )}
                              {record.redistribution_allowed && (
                                <Chip label={t('security.license.redistribute')} size="small" color="secondary" />
                              )}
                            </Box>
                          </TableCell>
                          <TableCell>{new Date(record.recorded_at).toLocaleString()}</TableCell>
                          <TableCell align="right">
                            <Tooltip title={t('security.actions.viewLicense')}>
                              <IconButton size="small" onClick={() => setSelectedLicense(record)}>
                                <Eye size={16} />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
            
            {/* 审计日志 */}
            {activeTab === 2 && (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('security.audit.eventType')}</TableCell>
                      <TableCell>{t('security.audit.action')}</TableCell>
                      <TableCell>{t('security.audit.result')}</TableCell>
                      <TableCell>{t('security.audit.resource')}</TableCell>
                      <TableCell>{t('security.audit.timestamp')}</TableCell>
                      <TableCell align="right">{t('security.actions.actions')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {loading.audit ? (
                      <TableRow>
                        <TableCell colSpan={6} align="center">
                          <CircularProgress />
                        </TableCell>
                      </TableRow>
                    ) : filteredAuditLogs.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} align="center">
                          {t('security.messages.noData')}
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredAuditLogs.map((log) => (
                        <TableRow key={log.id}>
                          <TableCell>
                            <Chip label={log.event_type} size="small" />
                          </TableCell>
                          <TableCell>{log.action}</TableCell>
                          <TableCell>{getResultChip(log.result)}</TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {log.resource_type}: {log.resource_id}
                            </Typography>
                          </TableCell>
                          <TableCell>{new Date(log.timestamp).toLocaleString()}</TableCell>
                          <TableCell align="right">
                            <Tooltip title={t('security.actions.viewLog')}>
                              <IconButton size="small" onClick={() => setSelectedLog(log)}>
                                <Eye size={16} />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      </motion.div>
      
      {/* 审计日志详情对话框 */}
      <Dialog
        open={!!selectedLog}
        onClose={() => setSelectedLog(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{t('security.dialogs.auditDetails')}</DialogTitle>
        <DialogContent>
          {selectedLog && (
            <Box sx={{ mt: 1 }}>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">{t('security.audit.eventId')}</Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', mb: 2 }}>
                    {selectedLog.event_id}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">{t('security.audit.eventType')}</Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    {selectedLog.event_type}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">{t('security.audit.userId')}</Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    {selectedLog.user_id || t('security.audit.anonymous')}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">{t('security.audit.ipAddress')}</Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    {selectedLog.ip_address || '-'}
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="subtitle2">{t('security.audit.details')}</Typography>
                  <Paper variant="outlined" sx={{ p: 2, mt: 1, bgcolor: 'grey.50' }}>
                    <pre style={{ margin: 0, fontSize: '0.875rem' }}>
                      {JSON.stringify(selectedLog.details, null, 2)}
                    </pre>
                  </Paper>
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedLog(null)}>
            {t('common.actions.close')}
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* 许可记录详情对话框 */}
      <Dialog
        open={!!selectedLicense}
        onClose={() => setSelectedLicense(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{t('security.dialogs.licenseDetails')}</DialogTitle>
        <DialogContent>
          {selectedLicense && (
            <Box sx={{ mt: 1 }}>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">{t('security.license.assetId')}</Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', mb: 2 }}>
                    {selectedLicense.asset_id}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">{t('security.license.type')}</Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    {selectedLicense.license_type}
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="subtitle2">{t('security.license.url')}</Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    {selectedLicense.license_url ? (
                      <a href={selectedLicense.license_url} target="_blank" rel="noopener noreferrer">
                        {selectedLicense.license_url}
                      </a>
                    ) : (
                      '-'
                    )}
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="subtitle2">{t('security.license.permissions')}</Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                    <Chip
                      label={t('security.license.commercial')}
                      color={selectedLicense.commercial_use_allowed ? 'success' : 'error'}
                      size="small"
                    />
                    <Chip
                      label={t('security.license.modify')}
                      color={selectedLicense.modification_allowed ? 'success' : 'error'}
                      size="small"
                    />
                    <Chip
                      label={t('security.license.redistribute')}
                      color={selectedLicense.redistribution_allowed ? 'success' : 'error'}
                      size="small"
                    />
                    <Chip
                      label={t('security.license.attribution')}
                      color={selectedLicense.attribution_required ? 'warning' : 'success'}
                      size="small"
                    />
                  </Box>
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedLicense(null)}>
            {t('common.actions.close')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default SecurityPage;