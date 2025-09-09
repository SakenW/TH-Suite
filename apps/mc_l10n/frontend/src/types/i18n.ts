// Type definitions for i18n translations

export interface CommonTranslations {
  common: {
    language: string
    loading: string
    error: string
    success: string
    cancel: string
    confirm: string
    save: string
    delete: string
    edit: string
    add: string
    remove: string
    close: string
    open: string
    yes: string
    no: string
  }
  actions: {
    start: string
    stop: string
    pause: string
    resume: string
    reset: string
    clear: string
    select: string
    selectAll: string
    deselectAll: string
    dragAndDrop: string
    dragFiles: string
    dropFiles: string
    selectFiles: string
    selectFolder: string
    upload: string
    download: string
    browse: string
    preview: string
    fullscreen: string
    minimize: string
    maximize: string
    collapse: string
    expand: string
  }
  navigation: {
    home: string
    back: string
    forward: string
    refresh: string
    search: string
    filter: string
    sort: string
    settings: string
    help: string
    about: string
  }
  workflow: {
    extraction: string
    translation: string
    synchronization: string
    processing: string
    analysis: string
  }
  settings: {
    general: string
    paths: string
    translation: string
    automation: string
    sourceLanguage: string
    targetLanguage: string
    autoTranslate: string
    qualityThreshold: string
    autoExtract: string
    autoSync: string
    backupBeforeSync: string
    extractInterval: string
  }
  status: {
    loading: string
    saving: string
    saved: string
    error: string
    success: string
    pending: string
    processing: string
    completed: string
    failed: string
    cancelled: string
    ready: string
    connecting: string
    connected: string
    disconnected: string
    scanning: string
    extracting: string
    checking: string
    submitting: string
    translating: string
    downloading: string
    backing: string
    writing: string
    verifying: string
  }
  messages: {
    noData: string
    networkError: string
    serverError: string
    validationError: string
    permissionDenied: string
    operationSuccess: string
    operationFailed: string
    confirmDelete: string
    unsavedChanges: string
    fileTypeNotSupported: string
    fileTooLarge: string
    uploadSuccess: string
    uploadFailed: string
    processingFile: string
    fileProcessed: string
  }
}

export interface McStudioTranslations {
  mcStudio: {
    title: string
    subtitle: string
    description: string
  }
  features: {
    modpackProcessing: {
      title: string
      description: string
      actions: {
        extract: string
        analyze: string
        process: string
      }
    }
    modLocalization: {
      title: string
      description: string
      actions: {
        scanMods: string
        extractTexts: string
        translateBatch: string
      }
    }
    resourcePackSupport: {
      title: string
      description: string
      actions: {
        loadPack: string
        extractTexts: string
        applyTranslations: string
      }
    }
    versionAdaptation: {
      title: string
      description: string
      versions: {
        java: string
        bedrock: string
        auto: string
      }
    }
  }
  workflow: {
    extraction: {
      status: {
        completed: string
        failed: string
      }
    }
    translation: {
      status: {
        checking: string
        submitting: string
        translating: string
        downloading: string
        completed: string
      }
    }
    synchronization: {
      status: {
        completed: string
      }
    }
  }
  settings: {
    paths: {
      title: string
      javaPath: string
      bedrockPath: string
      modsPath: string
      resourcePacksPath: string
    }
  }
}

// Declare module for react-i18next
declare module 'react-i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common'
    resources: {
      common: CommonTranslations
      mcStudio: McStudioTranslations
    }
  }
}
