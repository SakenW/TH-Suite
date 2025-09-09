/**
 * 进度组件测试页面
 * 用于展示和测试实时进度组件的各种状态
 */

import React, { useState, useEffect } from 'react'
import { Box, Button, Typography, Stack, Paper, Chip } from '@mui/material'
import { Play, RotateCcw } from 'lucide-react'
import RealTimeProgressIndicator from '../components/common/RealTimeProgressIndicator'

interface MockScanState {
  progress: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  processed_files: number
  total_files: number
  total_mods: number
  total_language_files: number
  total_keys: number
  current_file?: string
  error?: string
}

const mockFiles = [
  '/mods/create-1.19.2.jar',
  '/mods/jei-1.19.2-11.6.0.1019.jar',
  '/mods/botania-1.19.2-440.jar',
  '/mods/twilightforest-1.19.2-4.2.1518.jar',
  '/mods/thermal-expansion-1.19.2-9.2.2.jar',
  '/resourcepacks/faithful32x/pack.mcmeta',
  '/resourcepacks/faithful32x/assets/minecraft/lang/en_us.json',
  '/resourcepacks/faithful32x/assets/minecraft/lang/zh_cn.json',
]

export default function ProgressTestPage() {
  const [mockState, setMockState] = useState<MockScanState>({
    progress: 0,
    status: 'pending',
    processed_files: 0,
    total_files: 8,
    total_mods: 0,
    total_language_files: 0,
    total_keys: 0,
  })

  const [isRunning, setIsRunning] = useState(false)
  const [startTime, setStartTime] = useState<Date | null>(null)

  // 模拟扫描进度
  useEffect(() => {
    if (!isRunning) return

    const interval = setInterval(() => {
      setMockState(prev => {
        if (prev.status === 'completed' || prev.status === 'failed') {
          setIsRunning(false)
          return prev
        }

        const nextProgress = Math.min(prev.progress + Math.random() * 15, 100)
        const nextProcessedFiles = Math.floor((nextProgress / 100) * prev.total_files)

        // 模拟发现模组和语言文件
        let nextMods = prev.total_mods
        let nextLanguageFiles = prev.total_language_files
        let nextKeys = prev.total_keys

        if (nextProcessedFiles > prev.processed_files) {
          const newFiles = nextProcessedFiles - prev.processed_files
          nextMods += Math.floor(Math.random() * newFiles * 0.6) // 60% 概率是模组
          nextLanguageFiles += Math.floor(Math.random() * newFiles * 0.8) // 80% 概率有语言文件
          nextKeys += Math.floor(Math.random() * 200 * newFiles) // 每个文件平均200个键
        }

        const nextStatus = nextProgress >= 100 ? 'completed' : 'running'
        const currentFile =
          nextStatus === 'running' && nextProcessedFiles < mockFiles.length
            ? mockFiles[nextProcessedFiles]
            : undefined

        return {
          ...prev,
          progress: nextProgress,
          status: nextStatus,
          processed_files: nextProcessedFiles,
          total_mods: nextMods,
          total_language_files: nextLanguageFiles,
          total_keys: nextKeys,
          current_file: currentFile,
        }
      })
    }, 800)

    return () => clearInterval(interval)
  }, [isRunning])

  const startMockScan = () => {
    setMockState({
      progress: 0,
      status: 'running',
      processed_files: 0,
      total_files: 8,
      total_mods: 0,
      total_language_files: 0,
      total_keys: 0,
      current_file: mockFiles[0],
    })
    setStartTime(new Date())
    setIsRunning(true)
  }

  const resetMockScan = () => {
    setMockState({
      progress: 0,
      status: 'pending',
      processed_files: 0,
      total_files: 8,
      total_mods: 0,
      total_language_files: 0,
      total_keys: 0,
    })
    setStartTime(null)
    setIsRunning(false)
  }

  const simulateError = () => {
    setMockState(prev => ({
      ...prev,
      status: 'failed',
      error: '模拟错误：文件访问权限不足',
    }))
    setIsRunning(false)
  }

  const cancelScan = () => {
    setMockState(prev => ({
      ...prev,
      status: 'cancelled',
    }))
    setIsRunning(false)
  }

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Typography variant='h4' gutterBottom sx={{ mb: 4, textAlign: 'center' }}>
        🎮 实时进度组件测试页面
      </Typography>

      {/* 控制面板 */}
      <Paper sx={{ p: 3, mb: 4, borderRadius: 3 }}>
        <Typography variant='h6' gutterBottom>
          🎛️ 测试控制面板
        </Typography>

        <Stack direction='row' spacing={2} flexWrap='wrap' sx={{ mb: 2 }}>
          <Button
            variant='contained'
            startIcon={<Play size={18} />}
            onClick={startMockScan}
            disabled={isRunning}
            color='success'
          >
            启动模拟扫描
          </Button>

          <Button
            variant='outlined'
            startIcon={<RotateCcw size={18} />}
            onClick={resetMockScan}
            color='info'
          >
            重置状态
          </Button>

          <Button variant='outlined' onClick={simulateError} disabled={!isRunning} color='error'>
            模拟错误
          </Button>

          <Button variant='outlined' onClick={cancelScan} disabled={!isRunning} color='warning'>
            取消扫描
          </Button>
        </Stack>

        {/* 当前状态显示 */}
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Chip
            label={`状态: ${mockState.status}`}
            color={
              mockState.status === 'completed'
                ? 'success'
                : mockState.status === 'failed'
                  ? 'error'
                  : mockState.status === 'cancelled'
                    ? 'warning'
                    : mockState.status === 'running'
                      ? 'info'
                      : 'default'
            }
          />
          <Chip label={`进度: ${Math.round(mockState.progress)}%`} variant='outlined' />
          <Chip
            label={`文件: ${mockState.processed_files}/${mockState.total_files}`}
            variant='outlined'
          />
          <Chip label={`模组: ${mockState.total_mods}`} variant='outlined' />
        </Box>
      </Paper>

      {/* 实时进度组件展示 */}
      <Box sx={{ mb: 4 }}>
        <Typography variant='h6' gutterBottom>
          📊 实时进度组件 - 完整模式
        </Typography>

        <RealTimeProgressIndicator
          scanId='test-scan-001'
          progress={mockState.progress}
          status={mockState.status}
          currentFile={mockState.current_file}
          statistics={{
            total_files: mockState.total_files,
            processed_files: mockState.processed_files,
            total_mods: mockState.total_mods,
            total_language_files: mockState.total_language_files,
            total_keys: mockState.total_keys,
          }}
          error={mockState.error}
          startTime={startTime || undefined}
          onCancel={cancelScan}
          animated={true}
          compact={false}
          showDetails={true}
        />
      </Box>

      {/* 紧凑模式展示 */}
      <Box sx={{ mb: 4 }}>
        <Typography variant='h6' gutterBottom>
          📊 实时进度组件 - 紧凑模式
        </Typography>

        <Paper sx={{ borderRadius: 2 }}>
          <RealTimeProgressIndicator
            scanId='test-scan-002'
            progress={mockState.progress}
            status={mockState.status}
            currentFile={mockState.current_file}
            statistics={{
              total_files: mockState.total_files,
              processed_files: mockState.processed_files,
              total_mods: mockState.total_mods,
              total_language_files: mockState.total_language_files,
              total_keys: mockState.total_keys,
            }}
            error={mockState.error}
            startTime={startTime || undefined}
            onCancel={cancelScan}
            animated={true}
            compact={true}
            showDetails={true}
          />
        </Paper>
      </Box>

      {/* 特性说明 */}
      <Paper sx={{ p: 3, borderRadius: 3, backgroundColor: 'rgba(0, 188, 212, 0.05)' }}>
        <Typography variant='h6' gutterBottom color='primary'>
          ✨ 增强功能特性
        </Typography>

        <Box component='ul' sx={{ pl: 2, color: 'text.secondary' }}>
          <li>
            <strong>平滑动画进度条</strong>：使用 framer-motion 实现流畅的进度更新动画
          </li>
          <li>
            <strong>实时文件显示</strong>：显示当前正在处理的文件，带有动态效果
          </li>
          <li>
            <strong>丰富的统计信息</strong>：实时显示文件、模组、语言文件、翻译条目数量
          </li>
          <li>
            <strong>自适应状态指示</strong>：根据扫描状态显示不同的颜色和图标
          </li>
          <li>
            <strong>预估剩余时间</strong>：基于处理速度计算完成时间（实际扫描时）
          </li>
          <li>
            <strong>错误状态显示</strong>：优雅地显示扫描错误和异常情况
          </li>
          <li>
            <strong>紧凑/详细模式</strong>：支持两种显示模式，适应不同界面需求
          </li>
          <li>
            <strong>交互式操作</strong>：支持取消扫描等用户操作
          </li>
        </Box>
      </Paper>
    </Box>
  )
}
