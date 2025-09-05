scan:128 HTML script tag executed
chunk-T6FA643O.js?v=02fb79dd:21580 Download the React DevTools for a better development experience: https://reactjs.org/link/react-devtools
storage.service.ts:284 FileStorageManager: Using localStorage fallback
index.ts:12 i18next: languageChanged zh-CN
index.ts:12 i18next: initialized {debug: true, initImmediate: true, ns: Array(1), defaultNS: Array(1), fallbackLng: Array(1), …}
App.tsx:38 🔄 App render - isInitialized: false isLoading: false
App.tsx:89 🔧 Setting up initialization effect...
App.tsx:54 🚀 Starting app initialization sequence...
App.tsx:57 📱 Initializing Tauri APIs...
tauriService.ts:34 Initializing Tauri service...
tauriService.ts:44 Not running in Tauri environment - this appears to be a web browser
initialize @ tauriService.ts:44
initializeTauri @ tauriService.ts:308
initApp @ App.tsx:58
（匿名） @ App.tsx:90
commitHookEffectListMount @ chunk-T6FA643O.js?v=02fb79dd:16936
commitPassiveMountOnFiber @ chunk-T6FA643O.js?v=02fb79dd:18184
commitPassiveMountEffects_complete @ chunk-T6FA643O.js?v=02fb79dd:18157
commitPassiveMountEffects_begin @ chunk-T6FA643O.js?v=02fb79dd:18147
commitPassiveMountEffects @ chunk-T6FA643O.js?v=02fb79dd:18137
flushPassiveEffectsImpl @ chunk-T6FA643O.js?v=02fb79dd:19518
flushPassiveEffects @ chunk-T6FA643O.js?v=02fb79dd:19475
performSyncWorkOnRoot @ chunk-T6FA643O.js?v=02fb79dd:18896
flushSyncCallbacks @ chunk-T6FA643O.js?v=02fb79dd:9135
commitRootImpl @ chunk-T6FA643O.js?v=02fb79dd:19460
commitRoot @ chunk-T6FA643O.js?v=02fb79dd:19305
finishConcurrentRender @ chunk-T6FA643O.js?v=02fb79dd:18833
performConcurrentWorkOnRoot @ chunk-T6FA643O.js?v=02fb79dd:18746
workLoop @ chunk-T6FA643O.js?v=02fb79dd:197
flushWork @ chunk-T6FA643O.js?v=02fb79dd:176
performWorkUntilDeadline @ chunk-T6FA643O.js?v=02fb79dd:384
App.tsx:61 ✅ Tauri APIs initialized successfully
App.tsx:64 💾 Initializing storage service...
storage.service.ts:284 FileStorageManager: Using localStorage fallback
App.tsx:68 ✅ Storage service initialized successfully
App.tsx:71 🏪 Initializing app store...
appStore.ts:174 🚀 Starting app initialization...
appStore.ts:178 📝 Setting loading state...
appStore.ts:185 ⏳ Performing quick initialization...
App.tsx:38 🔄 App render - isInitialized: false isLoading: true
appStore.ts:189 🌐 Testing backend connection...
appStore.ts:206 ✅ Backend health check passed: {status: 'healthy', service: 'mc-l10n-api', version: '1.0.0', environment: 'production', timestamp: '2024-12-30T12:00:00'}
appStore.ts:219 🔄 Checking for active scans...
appStore.ts:236 🔍 Active scans found: {success: true, data: Array(0)}
appStore.ts:263 📂 Loading project data...
appStore.ts:267 ✅ Completing initialization...
appStore.ts:274 🎉 App initialization completed successfully!
App.tsx:38 🔄 App render - isInitialized: true isLoading: false
tauriService.ts:57 isTauri check: {windowExists: true, tauriExists: false, tauriValue: undefined, result: false}
App.tsx:43 🔄 App already initialized, skipping...
baseApiService.ts:70  GET http://localhost:18000/api/v1/transhub/status 404 (Not Found)
request @ baseApiService.ts:70
get @ baseApiService.ts:204
getStatus @ transhubService.ts:101
（匿名） @ useTransHub.ts:41
（匿名） @ useTransHub.ts:218
commitHookEffectListMount @ chunk-T6FA643O.js?v=02fb79dd:16936
commitPassiveMountOnFiber @ chunk-T6FA643O.js?v=02fb79dd:18184
commitPassiveMountEffects_complete @ chunk-T6FA643O.js?v=02fb79dd:18157
commitPassiveMountEffects_begin @ chunk-T6FA643O.js?v=02fb79dd:18147
commitPassiveMountEffects @ chunk-T6FA643O.js?v=02fb79dd:18137
flushPassiveEffectsImpl @ chunk-T6FA643O.js?v=02fb79dd:19518
flushPassiveEffects @ chunk-T6FA643O.js?v=02fb79dd:19475
commitRootImpl @ chunk-T6FA643O.js?v=02fb79dd:19444
commitRoot @ chunk-T6FA643O.js?v=02fb79dd:19305
performSyncWorkOnRoot @ chunk-T6FA643O.js?v=02fb79dd:18923
flushSyncCallbacks @ chunk-T6FA643O.js?v=02fb79dd:9135
（匿名） @ chunk-T6FA643O.js?v=02fb79dd:18655
baseApiService.ts:144 API request failed: Error: Not Found
    at TransHubService.handleResponse (baseApiService.ts:107:15)
    at async TransHubService.request (baseApiService.ts:81:14)
    at async TransHubService.getStatus (transhubService.ts:101:24)
    at async useTransHub.ts:41:22
handleError @ baseApiService.ts:144
request @ baseApiService.ts:92
await in request
get @ baseApiService.ts:204
getStatus @ transhubService.ts:101
（匿名） @ useTransHub.ts:41
（匿名） @ useTransHub.ts:218
commitHookEffectListMount @ chunk-T6FA643O.js?v=02fb79dd:16936
commitPassiveMountOnFiber @ chunk-T6FA643O.js?v=02fb79dd:18184
commitPassiveMountEffects_complete @ chunk-T6FA643O.js?v=02fb79dd:18157
commitPassiveMountEffects_begin @ chunk-T6FA643O.js?v=02fb79dd:18147
commitPassiveMountEffects @ chunk-T6FA643O.js?v=02fb79dd:18137
flushPassiveEffectsImpl @ chunk-T6FA643O.js?v=02fb79dd:19518
flushPassiveEffects @ chunk-T6FA643O.js?v=02fb79dd:19475
commitRootImpl @ chunk-T6FA643O.js?v=02fb79dd:19444
commitRoot @ chunk-T6FA643O.js?v=02fb79dd:19305
performSyncWorkOnRoot @ chunk-T6FA643O.js?v=02fb79dd:18923
flushSyncCallbacks @ chunk-T6FA643O.js?v=02fb79dd:9135
（匿名） @ chunk-T6FA643O.js?v=02fb79dd:18655
tauriService.ts:57 isTauri check: {windowExists: true, tauriExists: false, tauriValue: undefined, result: false}
tauriService.ts:57 isTauri check: {windowExists: true, tauriExists: false, tauriValue: undefined, result: false}
tauriService.ts:57 isTauri check: {windowExists: true, tauriExists: false, tauriValue: undefined, result: false}
scanService.ts:34 🔍 ScanService: 完整API响应 {
  "success": true,
  "data": {
    "scan_id": "285bad31-6445-489c-84b2-aa6def88c2b4",
    "task_id": "285bad31-6445-489c-84b2-aa6def88c2b4",
    "status": "started"
  },
  "scan_id": "285bad31-6445-489c-84b2-aa6def88c2b4",
  "task_id": "285bad31-6445-489c-84b2-aa6def88c2b4",
  "status": "started",
  "message": "扫描任务已启动",
  "target_path": "/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse",
  "game_type": "minecraft"
}
useRealTimeProgress.ts:234 🔄 开始轮询扫描状态: 285bad31-6445-489c-84b2-aa6def88c2b4
useRealTimeProgress.ts:235 🔄 轮询URL将是: /scan-status/285bad31-6445-489c-84b2-aa6def88c2b4
useRealTimeProgress.ts:255 🚀 执行第一次轮询...
useRealTimeProgress.ts:130 📌 [pollStatus] 开始执行 - scanId: 285bad31-6445-489c-84b2-aa6def88c2b4, isPolling: true
useRealTimeProgress.ts:143 🔄 [useRealTimeProgress] Polling status for scan: 285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:87 🔍 获取扫描状态: 285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:88 🔍 请求URL: /api/scan/progress/285bad31-6445-489c-84b2-aa6def88c2b4
useRealTimeProgress.ts:278 ⏱️ 已设置定时轮询，间隔: 800ms
tauriService.ts:57 isTauri check: {windowExists: true, tauriExists: false, tauriValue: undefined, result: false}
scanService.ts:92 🔍 扫描状态响应: {
  "success": true,
  "data": {
    "status": "scanning",
    "progress": 0.4444444444444444,
    "current_step": "扫描: alexsmobs-1.18.6.jar",
    "processed_files": 1,
    "total_files": 225,
    "statistics": {},
    "current_file": "扫描: alexsmobs-1.18.6.jar",
    "total_mods": 0,
    "total_language_files": 0,
    "total_keys": 0
  }
}
useRealTimeProgress.ts:148 📊 [useRealTimeProgress] Status response: {success: true, data: {…}}
useRealTimeProgress.ts:155 ✅ [useRealTimeProgress] New status: {status: 'scanning', progress: 0.4444444444444444, processed_files: 1, total_files: 225, current_file: '扫描: alexsmobs-1.18.6.jar'}
ScanPageMinecraft.tsx:47 📊 Status update: {scan_id: '285bad31-6445-489c-84b2-aa6def88c2b4', status: 'scanning', progress: 0.4444444444444444, total_files: 225, processed_files: 1, …}
tauriService.ts:57 isTauri check: {windowExists: true, tauriExists: false, tauriValue: undefined, result: false}
useRealTimeProgress.ts:267 ⏰ 定时轮询触发 (间隔: 1600ms)
useRealTimeProgress.ts:130 📌 [pollStatus] 开始执行 - scanId: 285bad31-6445-489c-84b2-aa6def88c2b4, isPolling: true
useRealTimeProgress.ts:143 🔄 [useRealTimeProgress] Polling status for scan: 285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:87 🔍 获取扫描状态: 285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:88 🔍 请求URL: /api/scan/progress/285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:92 🔍 扫描状态响应: {
  "success": true,
  "data": {
    "status": "scanning",
    "progress": 16.88888888888889,
    "current_step": "扫描: ColdSweat-2.2.5.1.jar",
    "processed_files": 38,
    "total_files": 225,
    "statistics": {},
    "current_file": "扫描: ColdSweat-2.2.5.1.jar",
    "total_mods": 0,
    "total_language_files": 0,
    "total_keys": 0
  }
}
useRealTimeProgress.ts:148 📊 [useRealTimeProgress] Status response: {success: true, data: {…}}
useRealTimeProgress.ts:155 ✅ [useRealTimeProgress] New status: {status: 'scanning', progress: 16.88888888888889, processed_files: 38, total_files: 225, current_file: '扫描: ColdSweat-2.2.5.1.jar'}
ScanPageMinecraft.tsx:47 📊 Status update: {scan_id: '285bad31-6445-489c-84b2-aa6def88c2b4', status: 'scanning', progress: 16.88888888888889, total_files: 225, processed_files: 38, …}
tauriService.ts:57 isTauri check: {windowExists: true, tauriExists: false, tauriValue: undefined, result: false}
useRealTimeProgress.ts:267 ⏰ 定时轮询触发 (间隔: 1600ms)
useRealTimeProgress.ts:130 📌 [pollStatus] 开始执行 - scanId: 285bad31-6445-489c-84b2-aa6def88c2b4, isPolling: true
useRealTimeProgress.ts:143 🔄 [useRealTimeProgress] Polling status for scan: 285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:87 🔍 获取扫描状态: 285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:88 🔍 请求URL: /api/scan/progress/285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:92 🔍 扫描状态响应: {
  "success": true,
  "data": {
    "status": "scanning",
    "progress": 51.11111111111111,
    "current_step": "扫描: ImmersivePetroleum-1.18.2-4.2.0-25.jar",
    "processed_files": 115,
    "total_files": 225,
    "statistics": {},
    "current_file": "扫描: ImmersivePetroleum-1.18.2-4.2.0-25.jar",
    "total_mods": 0,
    "total_language_files": 0,
    "total_keys": 0
  }
}
useRealTimeProgress.ts:148 📊 [useRealTimeProgress] Status response: {success: true, data: {…}}
useRealTimeProgress.ts:155 ✅ [useRealTimeProgress] New status: {status: 'scanning', progress: 51.11111111111111, processed_files: 115, total_files: 225, current_file: '扫描: ImmersivePetroleum-1.18.2-4.2.0-25.jar'}
ScanPageMinecraft.tsx:47 📊 Status update: {scan_id: '285bad31-6445-489c-84b2-aa6def88c2b4', status: 'scanning', progress: 51.11111111111111, total_files: 225, processed_files: 115, …}
tauriService.ts:57 isTauri check: {windowExists: true, tauriExists: false, tauriValue: undefined, result: false}
useRealTimeProgress.ts:267 ⏰ 定时轮询触发 (间隔: 1600ms)
useRealTimeProgress.ts:130 📌 [pollStatus] 开始执行 - scanId: 285bad31-6445-489c-84b2-aa6def88c2b4, isPolling: true
useRealTimeProgress.ts:143 🔄 [useRealTimeProgress] Polling status for scan: 285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:87 🔍 获取扫描状态: 285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:88 🔍 请求URL: /api/scan/progress/285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:92 🔍 扫描状态响应: {
  "success": true,
  "data": {
    "status": "scanning",
    "progress": 87.55555555555556,
    "current_step": "扫描: supermartijn642configlib-1.1.6-forge-mc1.18.jar",
    "processed_files": 197,
    "total_files": 225,
    "statistics": {},
    "current_file": "扫描: supermartijn642configlib-1.1.6-forge-mc1.18.jar",
    "total_mods": 0,
    "total_language_files": 0,
    "total_keys": 0
  }
}
useRealTimeProgress.ts:148 📊 [useRealTimeProgress] Status response: {success: true, data: {…}}
useRealTimeProgress.ts:155 ✅ [useRealTimeProgress] New status: {status: 'scanning', progress: 87.55555555555556, processed_files: 197, total_files: 225, current_file: '扫描: supermartijn642configlib-1.1.6-forge-mc1.18.jar'}
ScanPageMinecraft.tsx:47 📊 Status update: {scan_id: '285bad31-6445-489c-84b2-aa6def88c2b4', status: 'scanning', progress: 87.55555555555556, total_files: 225, processed_files: 197, …}
tauriService.ts:57 isTauri check: {windowExists: true, tauriExists: false, tauriValue: undefined, result: false}
tauriService.ts:57 isTauri check: {windowExists: true, tauriExists: false, tauriValue: undefined, result: false}
useRealTimeProgress.ts:267 ⏰ 定时轮询触发 (间隔: 1600ms)
useRealTimeProgress.ts:130 📌 [pollStatus] 开始执行 - scanId: 285bad31-6445-489c-84b2-aa6def88c2b4, isPolling: true
useRealTimeProgress.ts:143 🔄 [useRealTimeProgress] Polling status for scan: 285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:87 🔍 获取扫描状态: 285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:88 🔍 请求URL: /api/scan/progress/285bad31-6445-489c-84b2-aa6def88c2b4
scanService.ts:92 🔍 扫描状态响应: {
  "success": true,
  "data": {
    "status": "completed",
    "progress": 100,
    "current_step": "扫描完成",
    "processed_files": 225,
    "total_files": 225,
    "statistics": {
      "total_mods": 225,
      "total_language_files": 1060,
      "total_keys": 25573
    },
    "current_file": "扫描完成",
    "total_mods": 225,
    "total_language_files": 1060,
    "total_keys": 25573,
    "result": {
      "success": true,
      "statistics": {
        "total_mods": 0,
        "total_language_files": 0,
        "total_keys": 0,
        "total_entries": 0
      },
      "entries": {},
      "errors": [],
      "warnings": []
    }
  }
}
useRealTimeProgress.ts:148 📊 [useRealTimeProgress] Status response: {success: true, data: {…}}
useRealTimeProgress.ts:155 ✅ [useRealTimeProgress] New status: {status: 'completed', progress: 100, processed_files: 225, total_files: 225, current_file: '扫描完成'}
ScanPageMinecraft.tsx:47 📊 Status update: {scan_id: '285bad31-6445-489c-84b2-aa6def88c2b4', status: 'completed', progress: 100, total_files: 225, processed_files: 225, …}
tauriService.ts:57 isTauri check: {windowExists: true, tauriExists: false, tauriValue: undefined, result: false}
baseApiService.ts:70  GET http://localhost:18000/scan-results/285bad31-6445-489c-84b2-aa6def88c2b4 404 (Not Found)
request @ baseApiService.ts:70
get @ baseApiService.ts:204
getResults @ scanService.ts:122
（匿名） @ useRealTimeProgress.ts:182
await in （匿名）
poll @ useRealTimeProgress.ts:268
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
baseApiService.ts:144 API request failed: Error: Not Found
    at BaseApiService.handleResponse (baseApiService.ts:107:15)
    at async BaseApiService.request (baseApiService.ts:81:14)
    at async ScanService.getResults (scanService.ts:122:24)
    at async useRealTimeProgress.ts:182:36
handleError @ baseApiService.ts:144
request @ baseApiService.ts:92
await in request
get @ baseApiService.ts:204
getResults @ scanService.ts:122
（匿名） @ useRealTimeProgress.ts:182
await in （匿名）
poll @ useRealTimeProgress.ts:268
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
setTimeout
poll @ useRealTimeProgress.ts:273
useRealTimeProgress.ts:264 ⏹️ 轮询已停止，不再安排下次轮询
