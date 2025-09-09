#!/bin/bash
# 批量更新前端中硬编码的 API URL

echo "📝 批量替换硬编码的 API URL..."

# 定义文件列表
FILES=(
  "../frontend/src/components/ProjectScan.tsx"
  "../frontend/src/pages/ScanPageOptimal.tsx"
  "../frontend/src/stores/appStore.ts"
  "../frontend/src/layouts/MCLayout.tsx"
)

# 备份原文件
echo "📂 创建备份..."
for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    cp "$file" "$file.bak"
    echo "  ✅ 备份: $file.bak"
  fi
done

# 在每个文件开头添加 import 语句（如果不存在）
for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    # 检查是否已有 import
    if ! grep -q "import.*config/api" "$file"; then
      # 在第一个 import 语句后添加
      sed -i "/^import/a import { API_BASE_URL, buildApiUrl, API_ENDPOINTS } from '../config/api';" "$file"
      echo "  ➕ 添加 import: $file"
    fi
  fi
done

# 替换硬编码的 URL
echo "🔄 替换 URL..."
for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    # 替换健康检查 URL
    sed -i "s|'http://localhost:18000/health'|buildApiUrl(API_ENDPOINTS.HEALTH)|g" "$file"
    
    # 替换扫描项目 URL
    sed -i "s|'http://localhost:18000/api/v1/scan-project'|buildApiUrl(API_ENDPOINTS.SCAN_PROJECT)|g" "$file"
    
    # 替换扫描结果 URL
    sed -i "s|\`http://localhost:18000/api/v1/scan-result/\${scanId}\`|buildApiUrl(API_ENDPOINTS.SCAN_RESULT(scanId))|g" "$file"
    
    # 替换活动扫描 URL
    sed -i "s|'http://localhost:18000/api/v1/scans/active'|buildApiUrl(API_ENDPOINTS.ACTIVE_SCANS)|g" "$file"
    
    # 替换扫描状态 URL（特殊处理硬编码的 ID）
    sed -i "s|'http://localhost:18000/api/v1/scan-status/[^']*'|buildApiUrl(API_ENDPOINTS.SCAN_STATUS('0a5172e0-30c6-4ade-9fb6-331ccc409ed4'))|g" "$file"
    
    echo "  ✅ 替换完成: $file"
  fi
done

echo "✨ 所有文件已更新完成！"
echo ""
echo "⚠️  注意事项："
echo "1. 请检查文件确保 import 路径正确"
echo "2. 如果需要还原，使用 .bak 备份文件"
echo "3. 记得删除不需要的备份文件"