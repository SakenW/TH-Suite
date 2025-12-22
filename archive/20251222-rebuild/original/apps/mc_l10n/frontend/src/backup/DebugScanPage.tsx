import React, { useState } from 'react'
import { Box, Button, Typography, Paper } from '@mui/material'
import { getScanService } from '../services'

export default function DebugScanPage() {
  const [scanId, setScanId] = useState<string>('')
  const [statusData, setStatusData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const startScan = async () => {
    try {
      setLoading(true)
      const scanService = getScanService()
      const result = await scanService.startScan({
        directory:
          '/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse/mods',
        incremental: false,
      })

      if (result.success && result.data) {
        setScanId(result.data.scan_id)
        console.log('扫描已启动:', result.data.scan_id)
        // 开始轮询
        pollStatus(result.data.scan_id)
      }
    } catch (error) {
      console.error('启动扫描失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const pollStatus = async (id: string) => {
    try {
      const scanService = getScanService()
      const result = await scanService.getScanStatus(id)
      console.log('状态响应:', result)

      if (result.success && result.data) {
        setStatusData(result.data)

        // 如果还在扫描中，继续轮询
        if (result.data.status === 'scanning' || result.data.status === 'running') {
          setTimeout(() => pollStatus(id), 1000)
        }
      }
    } catch (error) {
      console.error('获取状态失败:', error)
    }
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant='h4' gutterBottom>
        扫描调试页面
      </Typography>

      <Button variant='contained' onClick={startScan} disabled={loading} sx={{ mb: 3 }}>
        开始扫描
      </Button>

      {scanId && <Typography sx={{ mb: 2 }}>扫描ID: {scanId}</Typography>}

      {statusData && (
        <Paper sx={{ p: 2, backgroundColor: '#1a1a1a' }}>
          <Typography variant='h6' gutterBottom>
            扫描状态数据：
          </Typography>

          <Typography>状态: {statusData.status}</Typography>
          <Typography>
            进度: {statusData.processed_files} / {statusData.total_files} ({statusData.progress}%)
          </Typography>

          <Typography variant='h6' sx={{ mt: 2, color: '#FFD700' }}>
            新字段：
          </Typography>
          <Typography color={statusData.scan_phase ? 'success.main' : 'error.main'}>
            scan_phase: {statusData.scan_phase || '未返回'}
          </Typography>
          <Typography color={statusData.phase_text ? 'success.main' : 'error.main'}>
            phase_text: {statusData.phase_text || '未返回'}
          </Typography>
          <Typography color={statusData.current_batch ? 'success.main' : 'error.main'}>
            current_batch: {statusData.current_batch || '未返回'}
          </Typography>
          <Typography color={statusData.total_batches ? 'success.main' : 'error.main'}>
            total_batches: {statusData.total_batches || '未返回'}
          </Typography>
          <Typography color={statusData.batch_progress ? 'success.main' : 'error.main'}>
            batch_progress: {statusData.batch_progress || '未返回'}
          </Typography>
          <Typography color={statusData.files_per_second ? 'success.main' : 'error.main'}>
            files_per_second: {statusData.files_per_second || '未返回'}
          </Typography>

          <Typography variant='h6' sx={{ mt: 2 }}>
            完整数据：
          </Typography>
          <pre
            style={{
              backgroundColor: '#000',
              color: '#0f0',
              padding: '10px',
              overflow: 'auto',
              maxHeight: '400px',
            }}
          >
            {JSON.stringify(statusData, null, 2)}
          </pre>
        </Paper>
      )}
    </Box>
  )
}
