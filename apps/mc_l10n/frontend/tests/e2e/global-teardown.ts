async function globalTeardown() {
  console.log('🧹 执行全局测试清理...')
  
  // 在这里可以清理测试数据、关闭服务等
  // 例如：清理测试数据库、删除临时文件等
  
  console.log('✅ 全局清理完成')
}

export default globalTeardown