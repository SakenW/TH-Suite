import { defineConfig, devices } from '@playwright/test'

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  // 测试目录
  testDir: './tests/e2e',
  
  // 全局设置文件
  globalSetup: './tests/e2e/global-setup.ts',
  globalTeardown: './tests/e2e/global-teardown.ts',
  
  // 每个测试文件的设置
  testIgnore: [
    '**/node_modules/**',
    '**/dist/**',
    '**/archived/**',
  ],
  
  // 全局超时设置
  timeout: 30 * 1000, // 30秒
  expect: {
    timeout: 5000, // 断言超时
  },
  
  // 失败重试
  retries: process.env.CI ? 2 : 0,
  
  // 并发设置
  workers: process.env.CI ? 1 : undefined,
  
  // 测试配置
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  
  // 报告器配置
  reporter: [
    ['list'],
    ['html', { outputFolder: 'test-results/playwright-report' }],
    ['json', { outputFile: 'test-results/playwright-results.json' }],
    ['junit', { outputFile: 'test-results/playwright-junit.xml' }],
    // GitHub Actions 专用报告器
    process.env.CI ? ['github'] : null,
  ].filter(Boolean),
  
  // 输出目录
  outputDir: 'test-results/playwright-artifacts',
  
  // 全局设置
  use: {
    // 基础URL
    baseURL: 'http://localhost:18001',
    
    // 浏览器设置
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    
    // 录制配置
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    
    // 导航超时
    navigationTimeout: 30 * 1000,
    actionTimeout: 10 * 1000,
  },
  
  // 项目配置 - 多浏览器测试
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // 移动端测试（可选）
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  
  // 开发服务器配置
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:18001',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000, // 2分钟
    stdout: 'ignore',
    stderr: 'pipe',
  },
})