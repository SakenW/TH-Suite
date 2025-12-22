/**
 * 补丁管理页面 - Minecraft 风格
 * 集成 Trans-Hub 补丁下载和应用功能
 */

import React, { useState } from 'react'
import { Box, Typography, Paper, Tab, Tabs } from '@mui/material'
import { motion } from 'framer-motion'
import { Package, Download, Upload, History, Settings } from 'lucide-react'
import { MinecraftBlock } from '../components/MinecraftComponents'
import { MinecraftCard } from '../components/minecraft/MinecraftCard'
import { MinecraftButton } from '../components/minecraft/MinecraftButton'
import { PatchManager } from '../components/PatchManager'
import { TransHubStatusBar } from '../components/TransHubStatusBar'
import { useTransHub } from '../hooks/useTransHub'
import { minecraftColors } from '../theme/minecraftTheme'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props
  return (
    <div hidden={value !== index} {...other}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

const PatchesPageMinecraft: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState(0)
  const { isConnected, refreshStatus } = useTransHub()

  return (
    <Box sx={{ p: 3 }}>
      {/* 页面标题和状态栏 */}
      <Box sx={{ mb: 4 }}>
        <Box
          sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}
        >
          <Box>
            <Typography
              variant='h4'
              sx={{
                fontFamily: '"Minecraft", monospace',
                color: '#FFFFFF',
                mb: 1,
                display: 'flex',
                alignItems: 'center',
                gap: 2,
              }}
            >
              <MinecraftBlock type='emerald' size={32} animated />
              补丁管理中心
            </Typography>
            <Typography variant='body2' sx={{ color: 'text.secondary' }}>
              下载、应用和管理 Trans-Hub 翻译补丁
            </Typography>
          </Box>
          <TransHubStatusBar showDetails={true} onStatusClick={() => refreshStatus()} />
        </Box>
      </Box>

      {/* 快速统计 */}
      <Box sx={{ mb: 3 }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <MinecraftCard variant='enchantment'>
            <Box sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-around' }}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography
                    variant='h4'
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      color: minecraftColors.emerald,
                    }}
                  >
                    12
                  </Typography>
                  <Typography variant='caption' color='text.secondary'>
                    可用补丁
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography
                    variant='h4'
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      color: minecraftColors.diamondBlue,
                    }}
                  >
                    8
                  </Typography>
                  <Typography variant='caption' color='text.secondary'>
                    已应用
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography
                    variant='h4'
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      color: minecraftColors.goldYellow,
                    }}
                  >
                    3
                  </Typography>
                  <Typography variant='caption' color='text.secondary'>
                    待更新
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography
                    variant='h4'
                    sx={{
                      fontFamily: '"Minecraft", monospace',
                      color: minecraftColors.iron,
                    }}
                  >
                    256 MB
                  </Typography>
                  <Typography variant='caption' color='text.secondary'>
                    总大小
                  </Typography>
                </Box>
              </Box>
            </Box>
          </MinecraftCard>
        </motion.div>
      </Box>

      {/* 选项卡 */}
      <Paper
        sx={{
          bgcolor: 'rgba(15, 23, 42, 0.8)',
          border: '2px solid #2A2A4E',
          borderRadius: 0,
        }}
      >
        <Tabs
          value={selectedTab}
          onChange={(e, v) => setSelectedTab(v)}
          sx={{
            borderBottom: '2px solid #2A2A4E',
            '& .MuiTab-root': {
              fontFamily: '"Minecraft", monospace',
              fontSize: '12px',
            },
          }}
        >
          <Tab label='可用补丁' icon={<Download size={16} />} iconPosition='start' />
          <Tab label='已安装' icon={<Package size={16} />} iconPosition='start' />
          <Tab label='创建补丁' icon={<Upload size={16} />} iconPosition='start' />
          <Tab label='历史记录' icon={<History size={16} />} iconPosition='start' />
          <Tab label='设置' icon={<Settings size={16} />} iconPosition='start' />
        </Tabs>

        {/* 可用补丁 */}
        <TabPanel value={selectedTab} index={0}>
          <PatchManager />
        </TabPanel>

        {/* 已安装补丁 */}
        <TabPanel value={selectedTab} index={1}>
          <Box sx={{ p: 3 }}>
            <Typography variant='h6' sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
              已安装的补丁
            </Typography>
            <MinecraftCard variant='inventory'>
              <Box sx={{ p: 2, textAlign: 'center', color: 'text.secondary' }}>
                <Typography>已安装的补丁将在这里显示</Typography>
              </Box>
            </MinecraftCard>
          </Box>
        </TabPanel>

        {/* 创建补丁 */}
        <TabPanel value={selectedTab} index={2}>
          <Box sx={{ p: 3 }}>
            <Typography variant='h6' sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
              创建新补丁
            </Typography>
            <MinecraftCard variant='crafting'>
              <Box sx={{ p: 3 }}>
                <Typography variant='body2' color='text.secondary' sx={{ mb: 2 }}>
                  从当前项目创建翻译补丁，以便分享或备份
                </Typography>
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <MinecraftButton
                    minecraftStyle='emerald'
                    startIcon={<Upload size={16} />}
                    disabled={!isConnected}
                  >
                    创建并上传
                  </MinecraftButton>
                  <MinecraftButton minecraftStyle='gold' startIcon={<Package size={16} />}>
                    导出到文件
                  </MinecraftButton>
                </Box>
              </Box>
            </MinecraftCard>
          </Box>
        </TabPanel>

        {/* 历史记录 */}
        <TabPanel value={selectedTab} index={3}>
          <Box sx={{ p: 3 }}>
            <Typography variant='h6' sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
              补丁应用历史
            </Typography>
            <MinecraftCard variant='chest'>
              <Box sx={{ p: 2, textAlign: 'center', color: 'text.secondary' }}>
                <Typography>补丁应用历史将在这里显示</Typography>
              </Box>
            </MinecraftCard>
          </Box>
        </TabPanel>

        {/* 设置 */}
        <TabPanel value={selectedTab} index={4}>
          <Box sx={{ p: 3 }}>
            <Typography variant='h6' sx={{ fontFamily: '"Minecraft", monospace', mb: 2 }}>
              补丁管理设置
            </Typography>
            <MinecraftCard variant='stone'>
              <Box sx={{ p: 3 }}>
                <Typography variant='body2' color='text.secondary'>
                  补丁管理相关设置
                </Typography>
                {/* 这里可以添加更多设置选项 */}
              </Box>
            </MinecraftCard>
          </Box>
        </TabPanel>
      </Paper>
    </Box>
  )
}

export default PatchesPageMinecraft
