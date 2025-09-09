/**
 * 补丁管理页面 - Minecraft 风格
 * 管理翻译补丁的创建、应用和回滚
 */

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import {
  MCPanel,
  MCButton,
  MCProgress,
  MCInput,
  MCTooltip,
  MCTabPanel,
  MCInventorySlot,
  MCInventoryGrid,
  MCItemTooltip,
  minecraftColors,
  typography,
  getRarityColor,
} from '../components/minecraft'

// 补丁类型
interface Patch {
  id: string
  name: string
  version: string
  description: string
  createdAt: Date
  appliedAt?: Date
  status: 'pending' | 'applied' | 'failed' | 'rollback'
  type: 'overlay' | 'jar_modify' | 'directory'
  targetLanguages: string[]
  affectedFiles: number
  totalEntries: number
  conflicts: number
  author: string
  size: string
}

// 补丁策略
type PatchPolicy = 'OVERLAY' | 'REPLACE' | 'MERGE' | 'CREATE_IF_MISSING'

const PatchesPage: React.FC = () => {
  const { t } = useTranslation(['mcStudio', 'minecraft'])

  const [patches, setPatches] = useState<Patch[]>([])
  const [selectedPatch, setSelectedPatch] = useState<Patch | null>(null)
  const [applyingPatch, setApplyingPatch] = useState(false)
  const [patchPolicy, setPatchPolicy] = useState<PatchPolicy>('OVERLAY')
  const [searchTerm, setSearchTerm] = useState('')

  // 模拟加载补丁
  useEffect(() => {
    const mockPatches: Patch[] = [
      {
        id: 'patch-001',
        name: 'Chinese Translation Pack v1.2',
        version: '1.2.0',
        description: 'Complete Chinese translation for all mods',
        createdAt: new Date('2024-01-15'),
        appliedAt: new Date('2024-01-16'),
        status: 'applied',
        type: 'overlay',
        targetLanguages: ['zh_cn', 'zh_tw'],
        affectedFiles: 156,
        totalEntries: 8432,
        conflicts: 0,
        author: 'TransHub Team',
        size: '2.3 MB',
      },
      {
        id: 'patch-002',
        name: 'Japanese Localization Update',
        version: '0.9.5',
        description: 'Updated Japanese translations for tech mods',
        createdAt: new Date('2024-01-18'),
        status: 'pending',
        type: 'jar_modify',
        targetLanguages: ['ja_jp'],
        affectedFiles: 42,
        totalEntries: 1256,
        conflicts: 3,
        author: 'Community',
        size: '856 KB',
      },
      {
        id: 'patch-003',
        name: 'Emergency Hotfix',
        version: '1.0.1',
        description: 'Fixes critical translation errors',
        createdAt: new Date('2024-01-20'),
        status: 'failed',
        type: 'directory',
        targetLanguages: ['en_us'],
        affectedFiles: 5,
        totalEntries: 32,
        conflicts: 12,
        author: 'System',
        size: '12 KB',
      },
    ]
    setPatches(mockPatches)
  }, [])

  // 应用补丁
  const applyPatch = async (patch: Patch) => {
    setApplyingPatch(true)

    // 模拟应用过程
    await new Promise(resolve => setTimeout(resolve, 2000))

    // 更新补丁状态
    setPatches(prev =>
      prev.map(p =>
        p.id === patch.id ? { ...p, status: 'applied' as const, appliedAt: new Date() } : p,
      ),
    )

    setApplyingPatch(false)
  }

  // 回滚补丁
  const rollbackPatch = async (patch: Patch) => {
    setApplyingPatch(true)

    await new Promise(resolve => setTimeout(resolve, 1500))

    setPatches(prev =>
      prev.map(p =>
        p.id === patch.id ? { ...p, status: 'rollback' as const, appliedAt: undefined } : p,
      ),
    )

    setApplyingPatch(false)
  }

  // 获取补丁稀有度
  const getPatchRarity = (patch: Patch): 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary' => {
    if (patch.conflicts > 10) return 'common'
    if (patch.conflicts > 5) return 'uncommon'
    if (patch.totalEntries > 5000) return 'legendary'
    if (patch.totalEntries > 2000) return 'epic'
    if (patch.totalEntries > 500) return 'rare'
    return 'uncommon'
  }

  // 获取状态颜色
  const getStatusColor = (status: Patch['status']) => {
    switch (status) {
      case 'applied':
        return minecraftColors.primary.emerald
      case 'pending':
        return minecraftColors.primary.gold
      case 'failed':
        return minecraftColors.primary.redstone
      case 'rollback':
        return minecraftColors.formatting['§7']
      default:
        return minecraftColors.ui.text.primary
    }
  }

  // 获取补丁图标
  const getPatchIcon = (type: Patch['type']) => {
    switch (type) {
      case 'overlay':
        return '📚'
      case 'jar_modify':
        return '🔧'
      case 'directory':
        return '📁'
      default:
        return '📦'
    }
  }

  // 过滤补丁
  const filteredPatches = patches.filter(
    patch =>
      patch.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      patch.description.toLowerCase().includes(searchTerm.toLowerCase()),
  )

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
          {t('mcStudio.features.modLocalization.title')}{' '}
          {t('common.labels.management', 'Management')}
        </h1>
        <p
          style={{
            fontSize: typography.fontSize.medium,
            fontFamily: typography.fontFamily.minecraft,
            color: minecraftColors.formatting['§7'],
          }}
        >
          Manage translation patches and apply them to your modpack
        </p>
      </motion.div>

      {/* 控制面板 */}
      <MCPanel variant='stone' title='Patch Control' style={{ marginBottom: '24px' }}>
        <div style={{ padding: '16px' }}>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            {/* 搜索框 */}
            <MCInput
              value={searchTerm}
              onChange={setSearchTerm}
              placeholder='Search patches...'
              type='search'
              fullWidth
              prefix={<span>🔍</span>}
            />

            {/* 创建新补丁 */}
            <MCButton variant='primary' icon={<span>➕</span>}>
              Create Patch
            </MCButton>

            {/* 导入补丁 */}
            <MCButton variant='default' icon={<span>📥</span>}>
              Import
            </MCButton>
          </div>

          {/* 策略选择 */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span
              style={{
                color: minecraftColors.ui.text.primary,
                fontSize: typography.fontSize.normal,
                fontFamily: typography.fontFamily.minecraft,
              }}
            >
              Policy:
            </span>
            {(['OVERLAY', 'REPLACE', 'MERGE', 'CREATE_IF_MISSING'] as PatchPolicy[]).map(policy => (
              <MCTooltip key={policy} content={`Apply patches using ${policy} strategy`}>
                <MCButton
                  variant={patchPolicy === policy ? 'primary' : 'default'}
                  size='small'
                  onClick={() => setPatchPolicy(policy)}
                >
                  {policy}
                </MCButton>
              </MCTooltip>
            ))}
          </div>
        </div>
      </MCPanel>

      {/* 补丁列表 */}
      <MCTabPanel
        tabs={[
          {
            id: 'all',
            label: 'All Patches',
            icon: '📦',
            content: <PatchList patches={filteredPatches} />,
          },
          {
            id: 'applied',
            label: 'Applied',
            icon: '✅',
            content: <PatchList patches={filteredPatches.filter(p => p.status === 'applied')} />,
          },
          {
            id: 'pending',
            label: 'Pending',
            icon: '⏳',
            content: <PatchList patches={filteredPatches.filter(p => p.status === 'pending')} />,
          },
          {
            id: 'failed',
            label: 'Failed',
            icon: '❌',
            content: <PatchList patches={filteredPatches.filter(p => p.status === 'failed')} />,
          },
        ]}
      />

      {/* 补丁详情弹窗 */}
      <AnimatePresence>
        {selectedPatch && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.75)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
            }}
            onClick={() => setSelectedPatch(null)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              onClick={e => e.stopPropagation()}
            >
              <MCPanel
                variant='planks'
                title={selectedPatch.name}
                closable
                onClose={() => setSelectedPatch(null)}
                width='600px'
              >
                <PatchDetails
                  patch={selectedPatch}
                  onApply={() => applyPatch(selectedPatch)}
                  onRollback={() => rollbackPatch(selectedPatch)}
                  isApplying={applyingPatch}
                />
              </MCPanel>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )

  // 补丁列表组件
  function PatchList({ patches: patchList }: { patches: Patch[] }) {
    return (
      <div style={{ padding: '16px' }}>
        {patchList.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: '32px',
              color: minecraftColors.formatting['§7'],
              fontSize: typography.fontSize.medium,
              fontFamily: typography.fontFamily.minecraft,
            }}
          >
            No patches found
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
              gap: '16px',
            }}
          >
            {patchList.map(patch => (
              <motion.div
                key={patch.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setSelectedPatch(patch)}
                style={{ cursor: 'pointer' }}
              >
                <MCPanel variant='dirt'>
                  <div style={{ padding: '12px' }}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        marginBottom: '8px',
                      }}
                    >
                      <span style={{ fontSize: '24px' }}>{getPatchIcon(patch.type)}</span>
                      <div style={{ flex: 1 }}>
                        <div
                          style={{
                            fontSize: typography.fontSize.medium,
                            color: getRarityColor(getPatchRarity(patch)),
                            fontFamily: typography.fontFamily.minecraft,
                          }}
                        >
                          {patch.name}
                        </div>
                        <div
                          style={{
                            fontSize: typography.fontSize.small,
                            color: minecraftColors.formatting['§7'],
                            fontFamily: typography.fontFamily.minecraft,
                          }}
                        >
                          v{patch.version} • {patch.size}
                        </div>
                      </div>
                      <div
                        style={{
                          padding: '2px 6px',
                          backgroundColor: getStatusColor(patch.status) + '20',
                          border: `1px solid ${getStatusColor(patch.status)}`,
                          color: getStatusColor(patch.status),
                          fontSize: typography.fontSize.tiny,
                          fontFamily: typography.fontFamily.minecraft,
                        }}
                      >
                        {patch.status.toUpperCase()}
                      </div>
                    </div>

                    <div
                      style={{
                        fontSize: typography.fontSize.small,
                        color: minecraftColors.ui.text.primary,
                        fontFamily: typography.fontFamily.minecraft,
                        marginBottom: '8px',
                      }}
                    >
                      {patch.description}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span
                        style={{
                          fontSize: typography.fontSize.tiny,
                          color: minecraftColors.formatting['§7'],
                          fontFamily: typography.fontFamily.minecraft,
                        }}
                      >
                        {patch.affectedFiles} files • {patch.totalEntries} entries
                      </span>
                      {patch.conflicts > 0 && (
                        <span
                          style={{
                            fontSize: typography.fontSize.tiny,
                            color: minecraftColors.primary.redstone,
                            fontFamily: typography.fontFamily.minecraft,
                          }}
                        >
                          ⚠ {patch.conflicts} conflicts
                        </span>
                      )}
                    </div>
                  </div>
                </MCPanel>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // 补丁详情组件
  function PatchDetails({
    patch,
    onApply,
    onRollback,
    isApplying,
  }: {
    patch: Patch
    onApply: () => void
    onRollback: () => void
    isApplying: boolean
  }) {
    return (
      <div style={{ padding: '24px' }}>
        {/* 基本信息 */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
            <div
              style={{
                fontSize: '48px',
                width: '64px',
                height: '64px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: minecraftColors.ui.background.secondary,
                border: `2px solid ${getRarityColor(getPatchRarity(patch))}`,
              }}
            >
              {getPatchIcon(patch.type)}
            </div>
            <div>
              <div
                style={{
                  fontSize: typography.fontSize.xlarge,
                  color: getRarityColor(getPatchRarity(patch)),
                  fontFamily: typography.fontFamily.minecraft,
                }}
              >
                {patch.name}
              </div>
              <div
                style={{
                  fontSize: typography.fontSize.normal,
                  color: minecraftColors.formatting['§7'],
                  fontFamily: typography.fontFamily.minecraft,
                }}
              >
                Version {patch.version} • By {patch.author}
              </div>
            </div>
          </div>

          <p
            style={{
              fontSize: typography.fontSize.normal,
              color: minecraftColors.ui.text.primary,
              fontFamily: typography.fontFamily.minecraft,
              marginBottom: '16px',
            }}
          >
            {patch.description}
          </p>
        </div>

        {/* 统计信息 */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '16px',
            marginBottom: '24px',
          }}
        >
          <InfoItem label='Type' value={patch.type} />
          <InfoItem label='Size' value={patch.size} />
          <InfoItem label='Affected Files' value={patch.affectedFiles} />
          <InfoItem label='Total Entries' value={patch.totalEntries} />
          <InfoItem label='Target Languages' value={patch.targetLanguages.join(', ')} />
          <InfoItem
            label='Conflicts'
            value={patch.conflicts}
            color={patch.conflicts > 0 ? minecraftColors.primary.redstone : undefined}
          />
          <InfoItem label='Created' value={patch.createdAt.toLocaleDateString()} />
          <InfoItem label='Applied' value={patch.appliedAt?.toLocaleDateString() || 'Never'} />
        </div>

        {/* 操作按钮 */}
        <div style={{ display: 'flex', gap: '12px' }}>
          {patch.status === 'pending' && (
            <MCButton
              variant='primary'
              fullWidth
              onClick={onApply}
              loading={isApplying}
              disabled={isApplying}
              icon={<span>✅</span>}
            >
              Apply Patch
            </MCButton>
          )}

          {patch.status === 'applied' && (
            <MCButton
              variant='danger'
              fullWidth
              onClick={onRollback}
              loading={isApplying}
              disabled={isApplying}
              icon={<span>↩️</span>}
            >
              Rollback
            </MCButton>
          )}

          {patch.status === 'failed' && (
            <MCButton
              variant='warning'
              fullWidth
              onClick={onApply}
              loading={isApplying}
              disabled={isApplying}
              icon={<span>🔄</span>}
            >
              Retry
            </MCButton>
          )}

          <MCButton variant='default' fullWidth icon={<span>📤</span>}>
            Export
          </MCButton>
        </div>
      </div>
    )
  }

  // 信息项组件
  function InfoItem({
    label,
    value,
    color,
  }: {
    label: string
    value: string | number
    color?: string
  }) {
    return (
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
            fontSize: typography.fontSize.normal,
            color: color || minecraftColors.ui.text.secondary,
            fontFamily: typography.fontFamily.minecraft,
          }}
        >
          {value}
        </div>
      </div>
    )
  }
}

export default PatchesPage
