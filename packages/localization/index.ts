/**
 * 通用本地化系统
 * 可被所有应用共享的多语言支持
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// 通用语言包类型定义
export interface CommonTranslations {
  common: {
    actions: {
      ok: string;
      cancel: string;
      confirm: string;
      save: string;
      delete: string;
      edit: string;
      add: string;
      remove: string;
      search: string;
      filter: string;
      sort: string;
      refresh: string;
      reset: string;
      close: string;
      open: string;
      browse: string;
      select: string;
      selectAll: string;
      deselectAll: string;
      clear: string;
      apply: string;
      export: string;
      import: string;
      download: string;
      upload: string;
      copy: string;
      paste: string;
      cut: string;
      undo: string;
      redo: string;
      back: string;
      next: string;
      previous: string;
      finish: string;
      start: string;
      stop: string;
      pause: string;
      resume: string;
      retry: string;
    };
    status: {
      loading: string;
      ready: string;
      processing: string;
      success: string;
      error: string;
      warning: string;
      info: string;
      pending: string;
      completed: string;
      failed: string;
      cancelled: string;
      unknown: string;
      online: string;
      offline: string;
      connected: string;
      disconnected: string;
      active: string;
      inactive: string;
      enabled: string;
      disabled: string;
    };
    messages: {
      confirmDelete: string;
      confirmCancel: string;
      saveSuccess: string;
      saveFailed: string;
      deleteSuccess: string;
      deleteFailed: string;
      loadingData: string;
      noData: string;
      noResults: string;
      errorOccurred: string;
      pleaseWait: string;
      processing: string;
      operationSuccess: string;
      operationFailed: string;
      invalidInput: string;
      required: string;
      optional: string;
    };
    labels: {
      name: string;
      description: string;
      type: string;
      status: string;
      date: string;
      time: string;
      createdAt: string;
      updatedAt: string;
      version: string;
      size: string;
      count: string;
      total: string;
      progress: string;
      percentage: string;
      duration: string;
      settings: string;
      preferences: string;
      language: string;
      theme: string;
      help: string;
      about: string;
      documentation: string;
      support: string;
    };
    time: {
      seconds: string;
      minutes: string;
      hours: string;
      days: string;
      weeks: string;
      months: string;
      years: string;
      ago: string;
      remaining: string;
      elapsed: string;
      estimated: string;
    };
    file: {
      file: string;
      files: string;
      folder: string;
      folders: string;
      size: string;
      path: string;
      extension: string;
      modified: string;
      created: string;
      selectFile: string;
      selectFolder: string;
      noFileSelected: string;
      noFolderSelected: string;
      dropFilesHere: string;
      browseFiles: string;
    };
    validation: {
      required: string;
      minLength: string;
      maxLength: string;
      minValue: string;
      maxValue: string;
      pattern: string;
      email: string;
      url: string;
      number: string;
      integer: string;
      alphanumeric: string;
      unique: string;
      exists: string;
    };
  };
  navigation: {
    home: string;
    dashboard: string;
    projects: string;
    files: string;
    settings: string;
    help: string;
    profile: string;
    logout: string;
    menu: string;
    back: string;
    forward: string;
  };
  errors: {
    generic: string;
    network: string;
    timeout: string;
    notFound: string;
    unauthorized: string;
    forbidden: string;
    serverError: string;
    badRequest: string;
    conflict: string;
    tooManyRequests: string;
    maintenance: string;
  };
}