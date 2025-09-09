/**
 * 服务容器实现 - 最优化版本
 * 轻量级依赖注入容器
 */

import { ServiceDefinition, ServiceRegistry } from './types'

class ServiceContainer {
  private services = new Map<string, ServiceDefinition>()
  private instances = new Map<string, any>()

  register<K extends keyof ServiceRegistry>(name: K, definition: ServiceRegistry[K]): void {
    this.services.set(name as string, definition)

    // 清除已有实例，确保重新创建
    if (this.instances.has(name as string)) {
      this.instances.delete(name as string)
    }
  }

  resolve<K extends keyof ServiceRegistry>(
    name: K,
  ): ServiceRegistry[K] extends ServiceDefinition<infer T> ? T : never {
    const serviceName = name as string

    const definition = this.services.get(serviceName)
    if (!definition) {
      throw new Error(`Service not registered: ${serviceName}`)
    }

    // 检查是否已有实例（单例模式）
    if (definition.singleton !== false && this.instances.has(serviceName)) {
      return this.instances.get(serviceName)
    }

    // 解析依赖
    const dependencies: any[] = []
    if (definition.dependencies) {
      for (const dep of definition.dependencies) {
        dependencies.push(this.resolve(dep as K))
      }
    }

    // 创建实例
    const instance = definition.factory(...dependencies)

    // 如果是单例，缓存实例
    if (definition.singleton !== false) {
      this.instances.set(serviceName, instance)
    }

    return instance
  }

  isRegistered(name: keyof ServiceRegistry): boolean {
    return this.services.has(name as string)
  }

  clear(): void {
    this.instances.clear()
    this.services.clear()
  }
}

// 创建全局服务容器实例
export const serviceContainer = new ServiceContainer()
