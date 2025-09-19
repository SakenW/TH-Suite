import { chromium, FullConfig } from '@playwright/test'

async function globalSetup(config: FullConfig) {
  console.log('🚀 启动全局测试设置...')
  
  // 检查开发服务器是否可用
  const browser = await chromium.launch()
  const page = await browser.newPage()
  
  try {
    // 等待应用启动
    await page.goto(config.webServer?.url || 'http://localhost:18001', {
      waitUntil: 'networkidle',
      timeout: 60000,
    })
    
    // 检查应用是否正常加载
    await page.waitForSelector('body', { timeout: 30000 })
    console.log('✅ 应用启动成功')
    
    // 可以在这里设置测试数据、清理缓存等
    await page.evaluate(() => {
      // 清理本地存储
      localStorage.clear()
      sessionStorage.clear()
    })
    
    console.log('✅ 测试环境准备完成')
  } catch (error) {
    console.error('❌ 全局设置失败:', error)
    throw error
  } finally {
    await browser.close()
  }
}

export default globalSetup