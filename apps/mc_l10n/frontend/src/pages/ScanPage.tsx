import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAppStore, ProjectType, ProjectIdentifier } from '../stores/appStore'
import {
  MCPanel,
  MCButton,
  MCProgress,
  MCInput,
  MCTooltip,
  MCTabPanel,
  MCInventoryGrid,
  minecraftColors,
  typography,
} from '../components/minecraft'
import ProjectScan from '../components/ProjectScan'

interface ScanResult {
  scan_id: string
  project_path: string
  scan_started_at: string
  scan_completed_at?: string
  modpack_manifest?: any
  mod_jars: any[]
  language_resources: any[]
  total_mods: number
  total_language_files: number
  total_translatable_keys: number
  supported_locales: string[]
  warnings: string[]
  errors: string[]
}

const ScanPage: React.FC = () => {
  const { t } = useTranslation(['mcStudio', 'minecraft'])
  const navigate = useNavigate()
  const { createProject, setCurrentProject } = useAppStore()

  const [scanResult, setScanResult] = useState<ScanResult | null>(null)
  const [isCreatingProject, setIsCreatingProject] = useState(false)

  const handleScanComplete = (result: ScanResult) => {
    console.log('Scan completed:', result)
    setScanResult(result)
  }

  const handleCreateProject = async (result: ScanResult) => {
    console.log('Creating project from scan result:', result)
    setIsCreatingProject(true)

    try {
      const identifier: ProjectIdentifier = {
        type: result.modpack_manifest ? ProjectType.MODPACK : ProjectType.MOD,
        modpackName: result.modpack_manifest?.name || undefined,
        modId: result.mod_jars[0]?.mod_id || undefined,
        version: result.modpack_manifest?.version || result.mod_jars[0]?.version || '1.0.0',
        mcVersion: result.modpack_manifest?.minecraft?.version || '1.20.1',
        loader: result.modpack_manifest?.dependencies?.forge
          ? 'forge'
          : result.modpack_manifest?.dependencies?.fabric
            ? 'fabric'
            : 'unknown',
        loaderVersion:
          result.modpack_manifest?.dependencies?.forge ||
          result.modpack_manifest?.dependencies?.fabric ||
          'unknown',
      }

      const project = await createProject(identifier, result.project_path)

      project.metadata = {
        scanResult: result,
        totalMods: result.total_mods,
        totalLanguageFiles: result.total_language_files,
        totalTranslatableKeys: result.total_translatable_keys,
        supportedLocales: result.supported_locales,
        warnings: result.warnings,
        errors: result.errors,
      }

      setCurrentProject(project)
      navigate('/projects')
    } catch (error) {
      console.error('Failed to create project:', error)
    } finally {
      setIsCreatingProject(false)
    }
  }

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* 页面标题 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          marginBottom: '24px',
          textAlign: 'center',
        }}
      >
        <h1
          style={{
            fontSize: typography.fontSize.huge,
            fontFamily: typography.fontFamily.minecraft,
            color: minecraftColors.ui.text.secondary,
            textShadow: '3px 3px 0px rgba(0, 0, 0, 0.5)',
            marginBottom: '8px',
          }}
        >
          {t('scan.title')}
        </h1>
        <p
          style={{
            fontSize: typography.fontSize.medium,
            fontFamily: typography.fontFamily.minecraft,
            color: minecraftColors.formatting['§7'],
          }}
        >
          {t('mcStudio.welcome.newProject.description')}
        </p>
      </motion.div>

      {/* 扫描组件（MC风格包装） */}
      <MCPanel variant='stone' title={t('scan.selectPath')} style={{ marginBottom: '24px' }}>
        <ProjectScan onScanComplete={handleScanComplete} onCreateProject={handleCreateProject} />
      </MCPanel>

      {/* 扫描结果显示 */}
      <AnimatePresence>
        {scanResult && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <MCPanel variant='planks' title={t('scan.results')}>
              <div style={{ padding: '16px' }}>
                {/* 统计信息 */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '16px',
                    marginBottom: '24px',
                  }}
                >
                  <StatCard
                    label={t('scan.stats.totalMods')}
                    value={scanResult.total_mods}
                    icon='📦'
                    color={minecraftColors.primary.emerald}
                  />
                  <StatCard
                    label={t('scan.stats.languageFiles')}
                    value={scanResult.total_language_files}
                    icon='📄'
                    color={minecraftColors.primary.diamond}
                  />
                  <StatCard
                    label={t('scan.stats.translatableKeys')}
                    value={scanResult.total_translatable_keys}
                    icon='🔑'
                    color={minecraftColors.primary.gold}
                  />
                  <StatCard
                    label={t('scan.stats.supportedLanguages')}
                    value={scanResult.supported_locales.length}
                    icon='🌐'
                    color={minecraftColors.primary.redstone}
                  />
                </div>

                {/* 创建项目按钮 */}
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <MCButton
                    onClick={() => handleCreateProject(scanResult)}
                    variant='primary'
                    size='large'
                    loading={isCreatingProject}
                    disabled={isCreatingProject}
                    icon={<span>🎮</span>}
                  >
                    {t('scan.createProject')}
                  </MCButton>
                </div>
              </div>
            </MCPanel>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// 统计卡片组件
interface StatCardProps {
  label: string
  value: number | string
  icon: string
  color: string
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon, color }) => (
  <div
    style={{
      padding: '16px',
      backgroundColor: minecraftColors.ui.background.secondary,
      border: `2px solid ${color}`,
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
    }}
  >
    <div
      style={{
        fontSize: '32px',
        width: '48px',
        height: '48px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: color + '20',
      }}
    >
      {icon}
    </div>
    <div>
      <div
        style={{
          fontSize: typography.fontSize.small,
          color: minecraftColors.formatting['§7'],
          fontFamily: typography.fontFamily.minecraft,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: typography.fontSize.xlarge,
          color: minecraftColors.ui.text.secondary,
          fontFamily: typography.fontFamily.minecraft,
          fontWeight: typography.fontWeight.bold,
        }}
      >
        {value}
      </div>
    </div>
  </div>
)

export default ScanPage
