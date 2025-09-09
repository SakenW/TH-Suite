import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import toast from 'react-hot-toast'
import { API_BASE_URL, buildApiUrl, API_ENDPOINTS } from '../config/api'

export interface AppSettings {
  theme: 'light' | 'dark' | 'auto'
  language: string
  autoSave: boolean
  backupEnabled: boolean
  maxRecentProjects: number
  defaultOutputPath: string
  logLevel: 'debug' | 'info' | 'warning' | 'error'
}

// 项目状态枚举
export enum ProjectState {
  NEW = 'NEW',
  RECOGNIZED = 'RECOGNIZED',
  RESOLVED = 'RESOLVED',
  READY_TO_DOWNLOAD = 'READY_TO_DOWNLOAD',
  NEED_UPLOAD = 'NEED_UPLOAD',
  DOWNLOADING = 'DOWNLOADING',
  UPLOADING = 'UPLOADING',
  WAITING_REMOTE = 'WAITING_REMOTE',
  READY_TO_BUILD = 'READY_TO_BUILD',
  BUILT = 'BUILT',
  FAILED = 'FAILED',
}

// 项目类型
export enum ProjectType {
  MODPACK = 'modpack',
  MOD = 'mod',
  RESOURCE_PACK = 'resource_pack',
}

// 项目标识
export interface ProjectIdentifier {
  type: ProjectType
  modpackName?: string
  modId?: string
  version: string
  mcVersion: string
  loader: string
  loaderVersion: string
}

// 识别报告
export interface RecognitionReport {
  projectId: string
  identifier: ProjectIdentifier
  contentFingerprint: string
  fileCount: number
  languageCount: number
  recognizedAt: string
  conflicts: Array<{
    path: string
    priority: number
    source: string
  }>
}

// 项目信息
export interface Project {
  id: string
  name: string
  path: string
  state: ProjectState
  identifier: ProjectIdentifier
  recognitionReport?: RecognitionReport
  createdAt: string
  lastModified: string
  metadata: Record<string, any>
}

export interface RecentProject {
  id: string
  name: string
  path: string
  lastOpened: string
  state: ProjectState
  type: ProjectType
}

// 扫描状态接口
export interface ScanState {
  scanId: string | null
  isScanning: boolean
  scanStatus: any | null
  scanResult: any | null
  scanDirectory: string | null
  progress: number
  currentFile: string | null
  startTime: number | null
}

export interface AppState {
  // Initialization
  isInitialized: boolean

  // Settings
  settings: AppSettings

  // Projects
  projects: Project[]
  currentProject: Project | null
  recentProjects: RecentProject[]

  // UI state
  sidebarOpen: boolean

  // Loading states
  isLoading: boolean
  loadingMessage: string

  // Scan state - 扫描状态管理
  scanState: ScanState

  // Actions
  initialize: () => Promise<void>
  updateSettings: (settings: Partial<AppSettings>) => void

  // Project management
  createProject: (identifier: ProjectIdentifier, path: string) => Promise<Project>
  loadProject: (projectId: string) => Promise<Project | null>
  updateProject: (projectId: string, updates: Partial<Project>) => void
  deleteProject: (projectId: string) => void
  setCurrentProject: (project: Project | null) => void

  // Project state transitions
  transitionProjectState: (projectId: string, newState: ProjectState) => void

  // Recent projects
  addRecentProject: (project: Omit<RecentProject, 'id' | 'lastOpened'>) => void
  removeRecentProject: (projectId: string) => void

  // UI actions
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setLoading: (loading: boolean, message?: string) => void

  // Scan actions - 扫描状态管理
  startScan: (scanId: string, directory: string) => void
  updateScanProgress: (progress: number, currentFile?: string, status?: any) => void
  completeScan: (result: any) => void
  cancelScan: () => void
  setScanStatus: (status: any) => void
  clearScan: () => void

  // Project state helpers
  hasActiveProject: () => boolean
  canShowProjectFeatures: () => boolean
  getCurrentProjectState: () => ProjectState | null
}

const defaultSettings: AppSettings = {
  theme: 'auto',
  language: 'en',
  autoSave: true,
  backupEnabled: true,
  maxRecentProjects: 10,
  defaultOutputPath: '',
  logLevel: 'info',
}

// 全局初始化锁，防止并发初始化
let isInitializing = false

export const useAppStore = create<AppState>()(
  persist(
    immer((set, get) => ({
      // Initial state
      isInitialized: false,
      settings: defaultSettings,
      projects: [],
      currentProject: null,
      recentProjects: [],
      sidebarOpen: true,
      isLoading: false,
      loadingMessage: '',

      // Scan state - 初始扫描状态
      scanState: {
        scanId: null,
        isScanning: false,
        scanStatus: null,
        scanResult: null,
        scanDirectory: null,
        progress: 0,
        currentFile: null,
        startTime: null,
      },

      // Actions
      initialize: async () => {
        const { isInitialized } = get()
        if (isInitialized) {
          console.log('🔄 Already initialized, skipping...')
          return true
        }

        if (isInitializing) {
          console.log('🔄 Already initializing, skipping...')
          return false
        }

        isInitializing = true
        console.log('🚀 Starting app initialization...')

        try {
          // 第一步：设置加载状态
          console.log('📝 Setting loading state...')
          set(state => {
            state.isLoading = true
            state.loadingMessage = 'Initializing MC Studio...'
          })

          // 第二步：快速初始化检查
          console.log('⏳ Performing quick initialization...')
          await new Promise(resolve => setTimeout(resolve, 100)) // 仅100ms

          // 第三步：检查后端连接（快速超时，不阻塞启动）
          console.log('🌐 Testing backend connection...')
          try {
            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), 3000) // 3秒超时

            const response = await fetch(buildApiUrl(API_ENDPOINTS.HEALTH), {
              method: 'GET',
              signal: controller.signal,
              headers: {
                'Content-Type': 'application/json',
              },
            })

            clearTimeout(timeoutId)

            if (response.ok) {
              const healthData = await response.json()
              console.log('✅ Backend health check passed:', healthData)
            } else {
              console.warn('⚠️ Backend health check failed, but continuing...')
            }
          } catch (fetchError) {
            if (fetchError.name === 'AbortError') {
              console.warn('⏰ Backend connection timeout, but continuing...')
            } else {
              console.warn('⚠️ Backend connection failed, but continuing...', fetchError)
            }
          }

          // 第四步：检查后台活跃扫描任务
          console.log('🔄 Checking for active scans...')
          try {
            const controller2 = new AbortController()
            const timeoutId2 = setTimeout(() => controller2.abort(), 2000) // 2秒超时

            const activeScansResponse = await fetch(buildApiUrl(API_ENDPOINTS.ACTIVE_SCANS), {
              method: 'GET',
              signal: controller2.signal,
              headers: {
                'Content-Type': 'application/json',
              },
            })

            clearTimeout(timeoutId2)

            if (activeScansResponse.ok) {
              const activeScansData = await activeScansResponse.json()
              console.log('🔍 Active scans found:', activeScansData)

              // 恢复活跃扫描状态
              if (
                activeScansData.success &&
                activeScansData.data &&
                activeScansData.data.length > 0
              ) {
                const activeScans = activeScansData.data
                const runningScans = activeScans.filter((scan: any) => scan.status === 'scanning')

                if (runningScans.length > 0) {
                  const latestScan = runningScans[runningScans.length - 1]
                  console.log('🔄 Resuming active scan:', latestScan.id)

                  // 通知扫描页面恢复扫描状态
                  window.dispatchEvent(
                    new CustomEvent('resumeActiveScan', {
                      detail: {
                        scanId: latestScan.id,
                        status: latestScan,
                        directory: latestScan.directory || 'Unknown',
                      },
                    }),
                  )
                }
              }
            }
          } catch (scanCheckError) {
            console.log('ℹ️ No active scans to resume, continuing...')
          }

          // 第五步：加载项目数据（从本地存储）
          console.log('📂 Loading project data...')
          // 数据已通过 persist 中间件自动加载

          // 第五步：完成初始化
          console.log('✅ Completing initialization...')
          set(state => {
            state.isInitialized = true
            state.isLoading = false
            state.loadingMessage = ''
          })

          console.log('🎉 App initialization completed successfully!')
          toast.success('MC Studio initialized successfully')

          return true
        } catch (error) {
          console.error('❌ Failed to initialize app:', error)
          set(state => {
            state.isInitialized = false // 确保设置为 false
            state.isLoading = false
            state.loadingMessage = ''
          })
          toast.error(`Failed to initialize MC Studio: ${error.message || error}`)

          // 不抛出错误，让应用继续运行但显示错误状态
          return false
        } finally {
          // 重置初始化锁
          isInitializing = false
        }
      },

      updateSettings: newSettings => {
        set(state => {
          Object.assign(state.settings, newSettings)
        })
        toast.success('Settings updated')
      },

      // Project management
      createProject: async (identifier, path) => {
        const projectId = `project_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        const now = new Date().toISOString()

        const project: Project = {
          id: projectId,
          name: identifier.modpackName || identifier.modId || 'Unnamed Project',
          path,
          state: ProjectState.NEW,
          identifier,
          createdAt: now,
          lastModified: now,
          metadata: {},
        }

        set(state => {
          state.projects.push(project)
          state.currentProject = project
        })

        // Add to recent projects
        get().addRecentProject({
          name: project.name,
          path: project.path,
          state: project.state,
          type: project.identifier.type,
        })

        toast.success(`Project "${project.name}" created successfully`)
        return project
      },

      loadProject: async projectId => {
        const { projects } = get()
        const project = projects.find(p => p.id === projectId)

        if (project) {
          set(state => {
            state.currentProject = project
          })

          // Update recent projects
          get().addRecentProject({
            name: project.name,
            path: project.path,
            state: project.state,
            type: project.identifier.type,
          })
        }

        return project || null
      },

      updateProject: (projectId, updates) => {
        set(state => {
          const projectIndex = state.projects.findIndex(p => p.id === projectId)
          if (projectIndex !== -1) {
            Object.assign(state.projects[projectIndex], updates, {
              lastModified: new Date().toISOString(),
            })

            if (state.currentProject?.id === projectId) {
              Object.assign(state.currentProject, updates, {
                lastModified: new Date().toISOString(),
              })
            }
          }
        })
      },

      deleteProject: projectId => {
        set(state => {
          state.projects = state.projects.filter(p => p.id !== projectId)
          if (state.currentProject?.id === projectId) {
            state.currentProject = null
          }
        })

        get().removeRecentProject(projectId)
        toast.success('Project deleted successfully')
      },

      setCurrentProject: project => {
        set(state => {
          state.currentProject = project
        })
      },

      transitionProjectState: (projectId, newState) => {
        set(state => {
          const projectIndex = state.projects.findIndex(p => p.id === projectId)
          if (projectIndex !== -1) {
            state.projects[projectIndex].state = newState
            state.projects[projectIndex].lastModified = new Date().toISOString()

            if (state.currentProject?.id === projectId) {
              state.currentProject.state = newState
              state.currentProject.lastModified = new Date().toISOString()
            }
          }
        })
      },

      addRecentProject: project => {
        set(state => {
          const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
          const lastOpened = new Date().toISOString()

          const newProject: RecentProject = {
            ...project,
            id,
            lastOpened,
          }

          // Remove existing project with same path
          state.recentProjects = state.recentProjects.filter(
            (p: RecentProject) => p.path !== project.path,
          )

          // Add new project to the beginning
          state.recentProjects.unshift(newProject)

          // Limit to max recent projects
          if (state.recentProjects.length > state.settings.maxRecentProjects) {
            state.recentProjects = state.recentProjects.slice(0, state.settings.maxRecentProjects)
          }
        })
      },

      removeRecentProject: projectId => {
        set(state => {
          state.recentProjects = state.recentProjects.filter(
            (p: RecentProject) => p.id !== projectId,
          )
        })
      },

      // UI state management
      setLoading: (isLoading, message = '') => {
        set(state => {
          state.isLoading = isLoading
          state.loadingMessage = message
        })
      },

      toggleSidebar: () => {
        set(state => {
          state.sidebarOpen = !state.sidebarOpen
        })
      },

      setSidebarOpen: open => {
        set(state => {
          state.sidebarOpen = open
        })
      },

      // Scan state management - 扫描状态管理
      startScan: (scanId, directory) => {
        set(state => {
          state.scanState = {
            scanId,
            isScanning: true,
            scanStatus: null,
            scanResult: null,
            scanDirectory: directory,
            progress: 0,
            currentFile: null,
            startTime: Date.now(),
          }
        })
        console.log('📊 扫描开始:', { scanId, directory })
      },

      updateScanProgress: (progress, currentFile, status) => {
        set(state => {
          state.scanState.progress = progress
          if (currentFile !== undefined) {
            state.scanState.currentFile = currentFile
          }
          if (status !== undefined) {
            state.scanState.scanStatus = status
          }
        })
      },

      completeScan: result => {
        set(state => {
          state.scanState.isScanning = false
          state.scanState.scanResult = result
          state.scanState.progress = 100
        })
        console.log('✅ 扫描完成:', result)
      },

      cancelScan: () => {
        set(state => {
          state.scanState.isScanning = false
          state.scanState.progress = 0
          state.scanState.currentFile = null
        })
        console.log('❌ 扫描已取消')
      },

      setScanStatus: status => {
        set(state => {
          state.scanState.scanStatus = status
        })
      },

      clearScan: () => {
        set(state => {
          state.scanState = {
            scanId: null,
            isScanning: false,
            scanStatus: null,
            scanResult: null,
            scanDirectory: null,
            progress: 0,
            currentFile: null,
            startTime: null,
          }
        })
        console.log('🧹 扫描状态已清除')
      },

      // Project state helpers
      hasActiveProject: () => {
        const { currentProject } = get()
        return currentProject !== null
      },

      canShowProjectFeatures: () => {
        const { currentProject } = get()
        if (!currentProject) return false

        // Show project features for all states except NEW and FAILED
        const allowedStates = [
          ProjectState.RECOGNIZED,
          ProjectState.RESOLVED,
          ProjectState.READY_TO_DOWNLOAD,
          ProjectState.NEED_UPLOAD,
          ProjectState.DOWNLOADING,
          ProjectState.UPLOADING,
          ProjectState.WAITING_REMOTE,
          ProjectState.READY_TO_BUILD,
          ProjectState.BUILT,
        ]

        return allowedStates.includes(currentProject.state)
      },

      getCurrentProjectState: () => {
        const { currentProject } = get()
        return currentProject?.state || null
      },
    })),
    {
      name: 'mc-studio-app-store',
      partialize: state => ({
        settings: state.settings,
        recentProjects: state.recentProjects,
        sidebarOpen: state.sidebarOpen,
      }),
    },
  ),
)
