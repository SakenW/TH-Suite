import React from 'react';
import ProjectScan from '../components/ProjectScan';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAppStore, ProjectType, ProjectIdentifier } from '../stores/appStore';

interface ScanResult {
  scan_id: string;
  project_path: string;
  scan_started_at: string;
  scan_completed_at?: string;
  modpack_manifest?: any;
  mod_jars: any[];
  language_resources: any[];
  total_mods: number;
  total_language_files: number;
  total_translatable_keys: number;
  supported_locales: string[];
  warnings: string[];
  errors: string[];
}

const ScanPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const { createProject, setCurrentProject } = useAppStore();

  const handleScanComplete = (result: ScanResult) => {
    console.log('Scan completed:', result);
    // 扫描完成后，数据已经保存在扫描结果中，等待用户创建项目
  };

  const handleCreateProject = async (result: ScanResult) => {
    console.log('Creating project from scan result:', result);
    
    try {
      // 从扫描结果创建项目标识符
      const identifier: ProjectIdentifier = {
        type: result.modpack_manifest ? ProjectType.MODPACK : ProjectType.MOD,
        modpackName: result.modpack_manifest?.name || undefined,
        modId: result.mod_jars[0]?.mod_id || undefined,
        version: result.modpack_manifest?.version || result.mod_jars[0]?.version || '1.0.0',
        mcVersion: result.modpack_manifest?.minecraft?.version || '1.20.1',
        loader: result.modpack_manifest?.dependencies?.forge ? 'forge' : 
                result.modpack_manifest?.dependencies?.fabric ? 'fabric' : 'unknown',
        loaderVersion: result.modpack_manifest?.dependencies?.forge || 
                      result.modpack_manifest?.dependencies?.fabric || 'unknown'
      };
      
      // 创建项目并保存扫描结果到metadata中
      const project = await createProject(identifier, result.project_path);
      
      // 将扫描结果保存到项目的metadata中
      project.metadata = {
        scanResult: result,
        totalMods: result.total_mods,
        totalLanguageFiles: result.total_language_files,
        totalTranslatableKeys: result.total_translatable_keys,
        supportedLocales: result.supported_locales,
        warnings: result.warnings,
        errors: result.errors
      };
      
      setCurrentProject(project);
      
      // 项目创建成功后跳转到项目页面
      navigate('/projects');
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">{t('welcome.quickActions.scan.title')}</h1>
        <p className="text-muted-foreground">
          {t('welcome.newProject.description')}
        </p>
      </div>
      
      <ProjectScan 
        onScanComplete={handleScanComplete}
        onCreateProject={handleCreateProject}
      />
    </div>
  );
};

export default ScanPage;