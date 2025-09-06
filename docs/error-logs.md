scanService.ts:34 🔍 ScanService: 完整API响应 {
  "success": true,
  "message": "扫描已开始: /mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse (使用统一扫描引擎)",
  "job_id": "d958869f-82d1-4716-b457-4066d2b315bf",
  "scan_id": "d958869f-82d1-4716-b457-4066d2b315bf"
}
useRealTimeProgress.ts:234 🔄 开始轮询扫描状态: d958869f-82d1-4716-b457-4066d2b315bf
useRealTimeProgress.ts:235 🔄 轮询URL将是: /scan-status/d958869f-82d1-4716-b457-4066d2b315bf
useRealTimeProgress.ts:255 🚀 执行第一次轮询...
useRealTimeProgress.ts:130 📌 [pollStatus] 开始执行 - scanId: d958869f-82d1-4716-b457-4066d2b315bf, isPolling: true
useRealTimeProgress.ts:143 🔄 [useRealTimeProgress] Polling status for scan: d958869f-82d1-4716-b457-4066d2b315bf
scanService.ts:88 🔍 获取扫描状态: d958869f-82d1-4716-b457-4066d2b315bf
scanService.ts:89 🔍 请求URL: /api/v1/scan-status/d958869f-82d1-4716-b457-4066d2b315bf
useRealTimeProgress.ts:278 ⏱️ 已设置定时轮询，间隔: 800ms
scanService.ts:93 🔍 扫描状态响应: {
  "success": true,
  "data": {
    "scan_id": "d958869f-82d1-4716-b457-4066d2b315bf",
    "target_path": "/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse",
    "incremental": true,
    "status": "scanning",
    "progress": 0,
    "processed_files": 0,
    "total_files": 10,
    "statistics": {
      "total_mods": 0,
      "total_language_files": 0,
      "total_keys": 0
    },
    "started_at": "2024-01-01T00:00:00Z"
  }
}
useRealTimeProgress.ts:148 📊 [useRealTimeProgress] Status response: {success: true, data: {…}}
useRealTimeProgress.ts:155 ✅ [useRealTimeProgress] New status: {status: 'scanning', progress: 0, processed_files: 0, total_files: 10, current_file: ''}
ScanPageMinecraft.tsx:47 📊 Status update: {scan_id: 'd958869f-82d1-4716-b457-4066d2b315bf', status: 'scanning', progress: 0, total_files: 10, processed_files: 0, …}
useRealTimeProgress.ts:267 ⏰ 定时轮询触发 (间隔: 1600ms)
useRealTimeProgress.ts:130 📌 [pollStatus] 开始执行 - scanId: d958869f-82d1-4716-b457-4066d2b315bf, isPolling: true
useRealTimeProgress.ts:143 🔄 [useRealTimeProgress] Polling status for scan: d958869f-82d1-4716-b457-4066d2b315bf
scanService.ts:88 🔍 获取扫描状态: d958869f-82d1-4716-b457-4066d2b315bf
scanService.ts:89 🔍 请求URL: /api/v1/scan-status/d958869f-82d1-4716-b457-4066d2b315bf
scanService.ts:93 🔍 扫描状态响应: {
  "success": true,
  "data": {
    "scan_id": "d958869f-82d1-4716-b457-4066d2b315bf",
    "target_path": "/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse",
    "incremental": true,
    "status": "scanning",
    "progress": 80,
    "processed_files": 8,
    "total_files": 10,
    "statistics": {
      "total_mods": 0,
      "total_language_files": 0,
      "total_keys": 0
    },
    "started_at": "2024-01-01T00:00:00Z"
  }
}
useRealTimeProgress.ts:148 📊 [useRealTimeProgress] Status response: {success: true, data: {…}}
useRealTimeProgress.ts:155 ✅ [useRealTimeProgress] New status: {status: 'scanning', progress: 80, processed_files: 8, total_files: 10, current_file: ''}
ScanPageMinecraft.tsx:47 📊 Status update: {scan_id: 'd958869f-82d1-4716-b457-4066d2b315bf', status: 'scanning', progress: 80, total_files: 10, processed_files: 8, …}
useRealTimeProgress.ts:267 ⏰ 定时轮询触发 (间隔: 1600ms)
useRealTimeProgress.ts:130 📌 [pollStatus] 开始执行 - scanId: d958869f-82d1-4716-b457-4066d2b315bf, isPolling: true
useRealTimeProgress.ts:143 🔄 [useRealTimeProgress] Polling status for scan: d958869f-82d1-4716-b457-4066d2b315bf
scanService.ts:88 🔍 获取扫描状态: d958869f-82d1-4716-b457-4066d2b315bf
scanService.ts:89 🔍 请求URL: /api/v1/scan-status/d958869f-82d1-4716-b457-4066d2b315bf
scanService.ts:93 🔍 扫描状态响应: {
  "success": true,
  "data": {
    "scan_id": "d958869f-82d1-4716-b457-4066d2b315bf",
    "target_path": "/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse",
    "incremental": true,
    "status": "completed",
    "progress": 100,
    "processed_files": 10,
    "total_files": 10,
    "statistics": {
      "total_mods": 0,
      "total_language_files": 0,
      "total_keys": 0
    },
    "started_at": "2024-01-01T00:00:00Z"
  }
}
useRealTimeProgress.ts:148 📊 [useRealTimeProgress] Status response: {success: true, data: {…}}
useRealTimeProgress.ts:155 ✅ [useRealTimeProgress] New status: {status: 'completed', progress: 100, processed_files: 10, total_files: 10, current_file: ''}
ScanPageMinecraft.tsx:47 📊 Status update: {scan_id: 'd958869f-82d1-4716-b457-4066d2b315bf', status: 'completed', progress: 100, total_files: 10, processed_files: 10, …}
ScanPageMinecraft.tsx:50 ✅ Scan complete: {scan_id: 'd958869f-82d1-4716-b457-4066d2b315bf', mods: Array(0), language_files: Array(0), statistics: {…}}
useRealTimeProgress.ts:264 ⏹️ 轮询已停止，不再安排下次轮询
