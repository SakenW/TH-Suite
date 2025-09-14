/**
 * 测试导入是否正常工作
 */

// 测试主要服务导入
try {
  console.log('Testing service imports...')
  
  // 基础服务导入测试
  import('./services/index.ts').then(() => {
    console.log('✅ services/index.ts - OK')
  }).catch(err => {
    console.error('❌ services/index.ts - ERROR:', err.message)
  })
  
  // API服务导入测试
  import('./services/api/index.ts').then(() => {
    console.log('✅ services/api/index.ts - OK')
  }).catch(err => {
    console.error('❌ services/api/index.ts - ERROR:', err.message)
  })
  
  // 单独测试各个API服务
  import('./services/api/BaseApiClient.ts').then(() => {
    console.log('✅ BaseApiClient - OK')
  }).catch(err => {
    console.error('❌ BaseApiClient - ERROR:', err.message)
  })
  
  import('./services/api/ProjectApiService.ts').then(() => {
    console.log('✅ ProjectApiService - OK')
  }).catch(err => {
    console.error('❌ ProjectApiService - ERROR:', err.message)
  })
  
  import('./services/api/ScanApiService.ts').then(() => {
    console.log('✅ ScanApiService - OK')
  }).catch(err => {
    console.error('❌ ScanApiService - ERROR:', err.message)
  })
  
  console.log('Import tests completed!')
  
} catch (error) {
  console.error('Failed to run import tests:', error)
}