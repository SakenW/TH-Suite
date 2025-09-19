import { test, expect } from '@playwright/test'

test.describe('TH-Suite MC L10n App', () => {
  test.beforeEach(async ({ page }) => {
    // 导航到应用主页
    await page.goto('/')
  })

  test('应用正常启动并显示主界面', async ({ page }) => {
    // 检查页面标题
    await expect(page).toHaveTitle(/TH-Suite MC L10n/i)
    
    // 检查主要UI元素
    await expect(page.locator('[data-testid="app-header"]')).toBeVisible()
    await expect(page.locator('[data-testid="main-content"]')).toBeVisible()
  })

  test('顶部状态栏显示正确信息', async ({ page }) => {
    // 等待状态栏加载
    await page.waitForSelector('[data-testid="top-status-bar"]')
    
    // 检查连接状态
    const connectionStatus = page.locator('[data-testid="connection-status"]')
    await expect(connectionStatus).toBeVisible()
    
    // 检查系统指标
    const systemMetrics = page.locator('[data-testid="system-metrics"]')
    await expect(systemMetrics).toBeVisible()
  })

  test('导航菜单功能正常', async ({ page }) => {
    // 检查导航菜单项
    const menuItems = [
      { text: '欢迎', path: '/' },
      { text: '项目管理', path: '/projects' },
      { text: '扫描中心', path: '/scan' },
      { text: '同步中心', path: '/sync' },
      { text: '构建中心', path: '/build' },
      { text: '设置', path: '/settings' },
    ]

    for (const item of menuItems) {
      const menuLink = page.locator(`text="${item.text}"`)
      await menuLink.click()
      
      // 验证URL变化
      await expect(page).toHaveURL(new RegExp(item.path))
      
      // 验证页面内容加载
      await expect(page.locator('main')).toBeVisible()
    }
  })

  test('项目扫描流程', async ({ page }) => {
    // 导航到扫描页面
    await page.goto('/scan')
    
    // 选择项目目录按钮
    const selectDirButton = page.locator('[data-testid="select-directory"]')
    await expect(selectDirButton).toBeVisible()
    
    // 开始扫描按钮
    const startScanButton = page.locator('[data-testid="start-scan"]')
    await expect(startScanButton).toBeVisible()
    
    // 扫描结果区域
    const scanResults = page.locator('[data-testid="scan-results"]')
    await expect(scanResults).toBeVisible()
  })

  test('设置页面配置保存', async ({ page }) => {
    // 导航到设置页面
    await page.goto('/settings')
    
    // 等待设置表单加载
    await page.waitForSelector('[data-testid="settings-form"]')
    
    // 修改设置项
    const langSelect = page.locator('[data-testid="language-select"]')
    await langSelect.click()
    await page.locator('text="English"').click()
    
    // 保存设置
    const saveButton = page.locator('[data-testid="save-settings"]')
    await saveButton.click()
    
    // 验证保存成功消息
    await expect(page.locator('text="设置已保存"')).toBeVisible()
  })

  test('响应式设计在不同屏幕尺寸下工作正常', async ({ page }) => {
    // 测试桌面尺寸
    await page.setViewportSize({ width: 1920, height: 1080 })
    await expect(page.locator('[data-testid="sidebar"]')).toBeVisible()
    
    // 测试平板尺寸
    await page.setViewportSize({ width: 768, height: 1024 })
    await expect(page.locator('[data-testid="mobile-menu"]')).toBeVisible()
    
    // 测试手机尺寸
    await page.setViewportSize({ width: 375, height: 667 })
    await expect(page.locator('[data-testid="mobile-header"]')).toBeVisible()
  })

  test('键盘导航无障碍功能', async ({ page }) => {
    // 使用Tab键导航
    await page.keyboard.press('Tab')
    
    // 检查焦点是否正确
    const focusedElement = page.locator(':focus')
    await expect(focusedElement).toBeVisible()
    
    // 继续Tab导航
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    
    // 使用Enter键激活
    await page.keyboard.press('Enter')
  })

  test('错误处理和用户反馈', async ({ page }) => {
    // 模拟网络错误
    await page.route('**/api/**', route => route.abort())
    
    // 导航到需要API调用的页面
    await page.goto('/projects')
    
    // 验证错误消息显示
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible()
    
    // 验证重试按钮
    const retryButton = page.locator('[data-testid="retry-button"]')
    await expect(retryButton).toBeVisible()
  })

  test('数据持久化功能', async ({ page }) => {
    // 在设置页面更改配置
    await page.goto('/settings')
    
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await themeToggle.click()
    
    // 刷新页面
    await page.reload()
    
    // 验证设置是否保持
    await expect(page.locator('[data-testid="dark-theme"]')).toBeVisible()
  })

  test('性能指标在合理范围内', async ({ page }) => {
    // 开始性能监控
    const startTime = Date.now()
    
    await page.goto('/')
    
    // 等待页面完全加载
    await page.waitForLoadState('networkidle')
    
    const loadTime = Date.now() - startTime
    
    // 验证加载时间小于3秒
    expect(loadTime).toBeLessThan(3000)
    
    // 检查内存使用
    const performanceEntries = await page.evaluate(() => {
      return performance.getEntriesByType('navigation')
    })
    
    expect(performanceEntries).toBeDefined()
  })
})