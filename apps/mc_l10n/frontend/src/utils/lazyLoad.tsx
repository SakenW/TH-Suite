import React, { lazy, Suspense, ComponentType } from 'react';
import { MinecraftLoader } from '@components/minecraft';
import { Box } from '@mui/material';

/**
 * 懒加载组件包装器
 * 提供统一的加载状态显示
 */
export function lazyLoad<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  fallback?: React.ReactNode
) {
  const LazyComponent = lazy(importFunc);

  return (props: React.ComponentProps<T>) => (
    <Suspense
      fallback={
        fallback || (
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: '400px',
              width: '100%'
            }}
          >
            <MinecraftLoader variant="blocks" size="large" />
          </Box>
        )
      }
    >
      <LazyComponent {...props} />
    </Suspense>
  );
}

/**
 * 预加载组件
 * 在空闲时间预先加载组件以提高性能
 */
export function preloadComponent(
  importFunc: () => Promise<any>
) {
  if ('requestIdleCallback' in window) {
    requestIdleCallback(() => {
      importFunc();
    });
  } else {
    // Fallback for browsers that don't support requestIdleCallback
    setTimeout(() => {
      importFunc();
    }, 1);
  }
}

/**
 * 批量预加载组件
 */
export function preloadComponents(
  importFuncs: Array<() => Promise<any>>
) {
  importFuncs.forEach(preloadComponent);
}

/**
 * 带重试的懒加载
 * 当加载失败时自动重试
 */
export function lazyLoadWithRetry<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  retries = 3,
  delay = 1000
) {
  const retryImport = async (): Promise<{ default: T }> => {
    try {
      return await importFunc();
    } catch (error) {
      if (retries > 0) {
        await new Promise(resolve => setTimeout(resolve, delay));
        return retryImport();
      }
      throw error;
    }
  };

  return lazyLoad(retryImport);
}

/**
 * 条件懒加载
 * 根据条件决定是否懒加载组件
 */
export function conditionalLazyLoad<T extends ComponentType<any>>(
  condition: boolean,
  importFunc: () => Promise<{ default: T }>,
  Component: T
) {
  if (condition) {
    return lazyLoad(importFunc);
  }
  return Component;
}

/**
 * 延迟加载
 * 在指定延迟后加载组件
 */
export function delayedLoad<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  delay: number = 300
) {
  return lazyLoad(() => 
    new Promise<{ default: T }>(resolve => {
      setTimeout(() => {
        importFunc().then(resolve);
      }, delay);
    })
  );
}