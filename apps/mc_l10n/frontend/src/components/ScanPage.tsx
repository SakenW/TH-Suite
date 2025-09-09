import React, { useState } from 'react'
import { fileService, ScanResult } from '../services/fileService'

const ScanPage: React.FC = () => {
  const [selectedPath, setSelectedPath] = useState<string>('')
  const [isScanning, setIsScanning] = useState(false)
  const [scanResult, setScanResult] = useState<ScanResult | null>(null)

  const handleSelectDirectory = async () => {
    try {
      const path = await fileService.selectDirectory()
      if (path) {
        setSelectedPath(path)
        setScanResult(null) // 清除之前的扫描结果
      }
    } catch (error) {
      console.error('Failed to select directory:', error)
    }
  }

  const handleStartScan = async () => {
    if (!selectedPath) return

    setIsScanning(true)
    try {
      const result = await fileService.scanDirectory(selectedPath)
      setScanResult(result)
    } catch (error) {
      console.error('Scan failed:', error)
    } finally {
      setIsScanning(false)
    }
  }

  const styles = {
    container: {
      padding: '20px',
      maxWidth: '1200px',
      margin: '0 auto',
    },
    card: {
      backgroundColor: 'white',
      borderRadius: '12px',
      padding: '24px',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
      marginBottom: '20px',
      border: '1px solid #E5E7EB',
    },
    title: {
      fontSize: '24px',
      fontWeight: '600',
      color: '#111827',
      marginBottom: '16px',
    },
    subtitle: {
      fontSize: '18px',
      fontWeight: '500',
      color: '#374151',
      marginBottom: '12px',
    },
    pathDisplay: {
      backgroundColor: '#F3F4F6',
      border: '1px solid #D1D5DB',
      borderRadius: '8px',
      padding: '12px',
      marginBottom: '16px',
      fontFamily: 'monospace',
      fontSize: '14px',
      color: '#374151',
      wordBreak: 'break-all' as const,
    },
    buttonGroup: {
      display: 'flex',
      gap: '12px',
      marginBottom: '20px',
    },
    button: (variant: 'primary' | 'secondary', disabled = false) => ({
      padding: '12px 24px',
      borderRadius: '8px',
      border: 'none',
      fontSize: '14px',
      fontWeight: '600',
      cursor: disabled ? 'not-allowed' : 'pointer',
      transition: 'all 0.2s ease',
      backgroundColor:
        variant === 'primary'
          ? disabled
            ? '#9CA3AF'
            : '#4F46E5'
          : disabled
            ? '#F3F4F6'
            : '#FFFFFF',
      color: variant === 'primary' ? 'white' : '#374151',
      border: variant === 'secondary' ? '1px solid #D1D5DB' : 'none',
      opacity: disabled ? 0.6 : 1,
    }),
    resultGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
      gap: '16px',
      marginTop: '20px',
    },
    resultCard: (color: string) => ({
      backgroundColor: 'white',
      border: `2px solid ${color}20`,
      borderLeft: `4px solid ${color}`,
      borderRadius: '8px',
      padding: '16px',
    }),
    resultTitle: {
      fontSize: '16px',
      fontWeight: '600',
      color: '#111827',
      marginBottom: '8px',
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
    },
    resultCount: (color: string) => ({
      backgroundColor: `${color}20`,
      color: color,
      padding: '4px 8px',
      borderRadius: '16px',
      fontSize: '12px',
      fontWeight: '600',
    }),
    fileList: {
      marginTop: '8px',
      fontSize: '14px',
      color: '#6B7280',
      maxHeight: '200px',
      overflowY: 'auto' as const,
    },
    fileName: {
      padding: '4px 0',
      borderBottom: '1px solid #F3F4F6',
    },
    errorList: {
      backgroundColor: '#FEF2F2',
      border: '1px solid #FECACA',
      borderRadius: '8px',
      padding: '12px',
      marginTop: '16px',
    },
    errorItem: {
      color: '#B91C1C',
      fontSize: '14px',
      padding: '4px 0',
    },
    loadingSpinner: {
      display: 'inline-block',
      width: '16px',
      height: '16px',
      border: '2px solid #E5E7EB',
      borderTopColor: '#4F46E5',
      borderRadius: '50%',
      animation: 'spin 1s linear infinite',
    },
  }

  return (
    <div style={styles.container}>
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>

      <div style={styles.card}>
        <h2 style={styles.title}>🔍 模组扫描</h2>
        <p style={{ color: '#6B7280', marginBottom: '20px' }}>
          选择包含 Minecraft 模组、资源包或整合包的目录进行扫描
        </p>

        <div style={styles.subtitle}>选择目录</div>

        {selectedPath ? (
          <div style={styles.pathDisplay}>📁 {selectedPath}</div>
        ) : (
          <div style={{ ...styles.pathDisplay, color: '#9CA3AF', fontStyle: 'italic' }}>
            未选择目录
          </div>
        )}

        <div style={styles.buttonGroup}>
          <button onClick={handleSelectDirectory} style={styles.button('primary')}>
            📂 选择目录
          </button>

          <button
            onClick={handleStartScan}
            disabled={!selectedPath || isScanning}
            style={styles.button('secondary', !selectedPath || isScanning)}
          >
            {isScanning ? (
              <>
                <span style={styles.loadingSpinner}></span>
                <span style={{ marginLeft: '8px' }}>扫描中...</span>
              </>
            ) : (
              '🚀 开始扫描'
            )}
          </button>
        </div>
      </div>

      {scanResult && (
        <div style={styles.card}>
          <h3 style={styles.title}>📊 扫描结果</h3>
          <p style={{ color: '#6B7280', marginBottom: '16px' }}>
            总计扫描文件: {scanResult.totalFiles} 个
          </p>

          <div style={styles.resultGrid}>
            {/* JAR 文件结果 */}
            <div style={styles.resultCard('#059669')}>
              <div style={styles.resultTitle}>
                🎮 JAR 文件
                <span style={styles.resultCount('#059669')}>{scanResult.jarFiles.length}</span>
              </div>
              <div style={styles.fileList}>
                {scanResult.jarFiles.length > 0 ? (
                  scanResult.jarFiles.slice(0, 10).map((file, index) => (
                    <div key={index} style={styles.fileName}>
                      📦 {fileService.getFileName(file.path)}
                      <span style={{ color: '#9CA3AF', fontSize: '12px', marginLeft: '8px' }}>
                        ({fileService.formatFileSize(file.size)})
                      </span>
                    </div>
                  ))
                ) : (
                  <div style={{ color: '#9CA3AF', fontStyle: 'italic' }}>未找到 JAR 文件</div>
                )}
                {scanResult.jarFiles.length > 10 && (
                  <div style={{ color: '#6B7280', fontSize: '12px', paddingTop: '8px' }}>
                    ... 还有 {scanResult.jarFiles.length - 10} 个文件
                  </div>
                )}
              </div>
            </div>

            {/* 语言文件结果 */}
            <div style={styles.resultCard('#DC2626')}>
              <div style={styles.resultTitle}>
                🌐 语言文件
                <span style={styles.resultCount('#DC2626')}>{scanResult.langFiles.length}</span>
              </div>
              <div style={styles.fileList}>
                {scanResult.langFiles.length > 0 ? (
                  scanResult.langFiles.slice(0, 10).map((file, index) => (
                    <div key={index} style={styles.fileName}>
                      📝 {fileService.getFileName(file.path)}
                      <span style={{ color: '#9CA3AF', fontSize: '12px', marginLeft: '8px' }}>
                        ({fileService.formatFileSize(file.size)})
                      </span>
                    </div>
                  ))
                ) : (
                  <div style={{ color: '#9CA3AF', fontStyle: 'italic' }}>未找到语言文件</div>
                )}
                {scanResult.langFiles.length > 10 && (
                  <div style={{ color: '#6B7280', fontSize: '12px', paddingTop: '8px' }}>
                    ... 还有 {scanResult.langFiles.length - 10} 个文件
                  </div>
                )}
              </div>
            </div>

            {/* 整合包文件结果 */}
            <div style={styles.resultCard('#7C2D12')}>
              <div style={styles.resultTitle}>
                📋 整合包文件
                <span style={styles.resultCount('#7C2D12')}>{scanResult.modpackFiles.length}</span>
              </div>
              <div style={styles.fileList}>
                {scanResult.modpackFiles.length > 0 ? (
                  scanResult.modpackFiles.slice(0, 10).map((file, index) => (
                    <div key={index} style={styles.fileName}>
                      📄 {fileService.getFileName(file.path)}
                      <span style={{ color: '#9CA3AF', fontSize: '12px', marginLeft: '8px' }}>
                        ({fileService.formatFileSize(file.size)})
                      </span>
                    </div>
                  ))
                ) : (
                  <div style={{ color: '#9CA3AF', fontStyle: 'italic' }}>未找到整合包配置文件</div>
                )}
                {scanResult.modpackFiles.length > 10 && (
                  <div style={{ color: '#6B7280', fontSize: '12px', paddingTop: '8px' }}>
                    ... 还有 {scanResult.modpackFiles.length - 10} 个文件
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 错误信息 */}
          {scanResult.errors && scanResult.errors.length > 0 && (
            <div style={styles.errorList}>
              <div style={{ fontWeight: '600', color: '#B91C1C', marginBottom: '8px' }}>
                ⚠️ 扫描过程中遇到的问题:
              </div>
              {scanResult.errors.map((error, index) => (
                <div key={index} style={styles.errorItem}>
                  • {error}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ScanPage
