/**
 * Minecraft 风格组件展示页面
 * 展示优化后的 Tailwind CSS + Minecraft 主题效果
 */

import React, { useState, useEffect } from 'react'
import { Card, Row, Col, Divider, Space, Typography, Switch, Tooltip } from 'antd'
import { 
  MCCard, 
  MCButton, 
  MCProgress, 
  MCStatus, 
  MCBadge, 
  MCFloatingButton 
} from '../components/minecraft/MCEnhanced'
import { 
  PlayCircleOutlined, 
  PauseCircleOutlined, 
  HeartOutlined,
  ThunderboltOutlined,
  FireOutlined,
  StarOutlined,
  SettingOutlined
} from '@ant-design/icons'
import { motion, AnimatePresence } from 'framer-motion'

const { Title, Text, Paragraph } = Typography

const MinecraftShowcase: React.FC = () => {
  const [expProgress, setExpProgress] = useState(65)
  const [healthProgress, setHealthProgress] = useState(85)
  const [manaProgress, setManaProgress] = useState(40)
  const [isAnimating, setIsAnimating] = useState(true)
  const [showEffects, setShowEffects] = useState(true)

  // 模拟进度条动画
  useEffect(() => {
    if (!isAnimating) return

    const interval = setInterval(() => {
      setExpProgress(prev => (prev >= 100 ? 0 : prev + 2))
      setHealthProgress(prev => (prev <= 0 ? 100 : prev - 1))
      setManaProgress(prev => (prev >= 100 ? 0 : prev + 3))
    }, 150)

    return () => clearInterval(interval)
  }, [isAnimating])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-green-50 to-yellow-50 mc-grid-bg">
      {/* 浮动操作按钮 */}
      <MCFloatingButton
        icon={<SettingOutlined />}
        tooltip="设置"
        onClick={() => console.log('设置')}
      />

      <div className="container mx-auto p-6">
        {/* 标题区域 */}
        <motion.div
          initial={{ opacity: 0, y: -30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-8"
        >
          <Title level={1} className="neon-glow text-mc-emerald mb-4">
            🎮 Minecraft 风格组件展示
          </Title>
          <Paragraph className="text-lg text-gray-600 mb-6">
            基于 Tailwind CSS 和 Ant Design 的现代化 Minecraft 主题组件库
          </Paragraph>
          
          {/* 控制开关 */}
          <Space size="large" className="mb-8">
            <Tooltip title="切换动画效果">
              <Space>
                <Text>动画效果</Text>
                <Switch 
                  checked={isAnimating} 
                  onChange={setIsAnimating}
                  checkedChildren="开启"
                  unCheckedChildren="关闭"
                />
              </Space>
            </Tooltip>
            <Tooltip title="切换特殊效果">
              <Space>
                <Text>特殊效果</Text>
                <Switch 
                  checked={showEffects} 
                  onChange={setShowEffects}
                  checkedChildren="显示"
                  unCheckedChildren="隐藏"
                />
              </Space>
            </Tooltip>
          </Space>
        </motion.div>

        {/* 卡片展示区域 */}
        <Row gutter={[24, 24]} className="mb-8">
          <Col xs={24} md={8}>
            <MCCard 
              title="🏰 像素化卡片" 
              variant="pixel"
              glow={showEffects}
            >
              <div className="space-y-4">
                <Text>这是一个具有像素化边框和方块阴影效果的卡片。</Text>
                <MCButton variant="block" type="primary">
                  像素按钮
                </MCButton>
              </div>
            </MCCard>
          </Col>

          <Col xs={24} md={8}>
            <MCCard 
              title="💎 玻璃效果卡片" 
              variant="glass"
              className={showEffects ? 'animate-float' : ''}
            >
              <div className="space-y-4">
                <Text>具有毛玻璃效果和浮动动画的现代卡片。</Text>
                <MCButton variant="glow" type="success">
                  发光按钮
                </MCButton>
              </div>
            </MCCard>
          </Col>

          <Col xs={24} md={8}>
            <MCCard 
              title="🌟 浮动卡片" 
              variant="floating"
            >
              <div className="space-y-4">
                <Text>带有浮动动画效果的交互式卡片。</Text>
                <MCButton variant="default" type="warning">
                  默认按钮
                </MCButton>
              </div>
            </MCCard>
          </Col>
        </Row>

        {/* 进度条展示区域 */}
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <Card className="mb-8 minecraft-card">
            <Title level={3} className="mb-6">📊 进度条组件</Title>
            
            <Row gutter={[24, 24]}>
              <Col xs={24} md={8}>
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <ThunderboltOutlined className="text-mc-emerald" />
                    <Text strong>经验值</Text>
                  </div>
                  <MCProgress 
                    percent={expProgress} 
                    variant="exp" 
                    animated={isAnimating}
                    glow={showEffects}
                  />
                </div>
              </Col>

              <Col xs={24} md={8}>
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <HeartOutlined className="text-mc-redstone" />
                    <Text strong>生命值</Text>
                  </div>
                  <MCProgress 
                    percent={healthProgress} 
                    variant="health" 
                    animated={isAnimating}
                  />
                </div>
              </Col>

              <Col xs={24} md={8}>
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <FireOutlined className="text-mc-lapis" />
                    <Text strong>魔法值</Text>
                  </div>
                  <MCProgress 
                    percent={manaProgress} 
                    variant="mana" 
                    animated={isAnimating}
                  />
                </div>
              </Col>
            </Row>
          </Card>
        </motion.div>

        {/* 状态指示器展示 */}
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <Card className="mb-8 minecraft-card">
            <Title level={3} className="mb-6">🔴 状态指示器</Title>
            
            <div className="responsive-flex">
              <MCStatus type="success" text="在线" animated={isAnimating} />
              <MCStatus type="error" text="错误" animated={isAnimating} />
              <MCStatus type="warning" text="警告" animated={isAnimating} />
              <MCStatus type="info" text="信息" animated={isAnimating} />
              <MCStatus type="loading" text="加载中" animated={isAnimating} />
            </div>
          </Card>
        </motion.div>

        {/* 徽章展示 */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          <Card className="mb-8 minecraft-card">
            <Title level={3} className="mb-6">🏆 成就徽章</Title>
            
            <div className="responsive-flex">
              <MCBadge type="achievement" animated={isAnimating}>
                首次启动
              </MCBadge>
              <MCBadge type="level" animated={isAnimating}>
                等级 42
              </MCBadge>
              <MCBadge type="rare" animated={isAnimating}>
                稀有物品
              </MCBadge>
              <MCBadge type="epic" animated={isAnimating}>
                史诗装备
              </MCBadge>
              <MCBadge type="legendary" animated={isAnimating}>
                传说神器
              </MCBadge>
            </div>
          </Card>
        </motion.div>

        {/* 按钮样式展示 */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.8 }}
        >
          <Card className="mb-8 minecraft-card">
            <Title level={3} className="mb-6">🎯 按钮变体</Title>
            
            <div className="space-y-6">
              {/* 按钮类型 */}
              <div>
                <Text strong className="block mb-3">按钮类型：</Text>
                <div className="responsive-flex">
                  <MCButton type="primary">主要按钮</MCButton>
                  <MCButton type="secondary">次要按钮</MCButton>
                  <MCButton type="success">成功按钮</MCButton>
                  <MCButton type="warning">警告按钮</MCButton>
                  <MCButton type="danger">危险按钮</MCButton>
                </div>
              </div>

              <Divider />

              {/* 按钮变体 */}
              <div>
                <Text strong className="block mb-3">按钮变体：</Text>
                <div className="responsive-flex">
                  <MCButton variant="default" type="primary">默认样式</MCButton>
                  <MCButton variant="block" type="primary">方块样式</MCButton>
                  <MCButton variant="pixel" type="primary">像素样式</MCButton>
                  <MCButton variant="glow" type="primary">发光样式</MCButton>
                </div>
              </div>

              <Divider />

              {/* 按钮尺寸 */}
              <div>
                <Text strong className="block mb-3">按钮尺寸：</Text>
                <div className="responsive-flex">
                  <MCButton size="small" type="primary">小按钮</MCButton>
                  <MCButton size="medium" type="primary">中按钮</MCButton>
                  <MCButton size="large" type="primary">大按钮</MCButton>
                </div>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* 动画效果展示 */}
        <AnimatePresence>
          {showEffects && (
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -50 }}
              transition={{ duration: 0.6 }}
            >
              <Card className="mb-8 minecraft-card">
                <Title level={3} className="mb-6">✨ 特殊效果</Title>
                
                <Row gutter={[24, 24]}>
                  <Col xs={24} md={6}>
                    <div className="p-4 rounded-block border-2 border-mc-emerald bg-mc-emerald/10 animate-glow text-center">
                      <Text strong>发光效果</Text>
                    </div>
                  </Col>
                  
                  <Col xs={24} md={6}>
                    <div className="p-4 rounded-pixel mc-block-shadow bg-gradient-to-br from-mc-gold/20 to-mc-gold/10 text-center animate-diamond-sparkle">
                      <Text strong>钻石闪烁</Text>
                    </div>
                  </Col>
                  
                  <Col xs={24} md={6}>
                    <div className="p-4 rounded-block bg-mc-redstone/20 text-center animate-redstone-pulse">
                      <Text strong>红石脉冲</Text>
                    </div>
                  </Col>
                  
                  <Col xs={24} md={6}>
                    <div className="p-4 rounded-block holographic text-center">
                      <Text strong>全息效果</Text>
                    </div>
                  </Col>
                </Row>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Tailwind 工具类展示 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 1.0 }}
        >
          <Card className="minecraft-card">
            <Title level={3} className="mb-6">🎨 Tailwind 工具类</Title>
            
            <div className="space-y-6">
              {/* 网格背景 */}
              <div>
                <Text strong className="block mb-3">网格背景：</Text>
                <div className="h-20 w-full mc-grid-bg rounded-block border-2 border-gray-300 flex items-center justify-center">
                  <Text>16x16 网格背景</Text>
                </div>
              </div>

              {/* 像素完美渲染 */}
              <div>
                <Text strong className="block mb-3">像素完美渲染：</Text>
                <div className="pixel-perfect">
                  <img 
                    src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAdgAAAHYBTnsmCAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAAmSURBVBiVY/z//z8DLQAjIyMDLQAjIyMDLQAjIyMDLQAjIyMDLQAABgIAAcwAAgAAAAASUVORK5CYII="
                    alt="像素图标"
                    className="w-16 h-16 border-2 border-mc-stone"
                    style={{ imageRendering: 'pixelated' }}
                  />
                </div>
              </div>

              {/* 响应式布局 */}
              <div>
                <Text strong className="block mb-3">响应式网格：</Text>
                <div className="responsive-grid">
                  {[1, 2, 3, 4].map(i => (
                    <div 
                      key={i}
                      className="p-4 bg-mc-emerald/10 border border-mc-emerald/30 rounded-block text-center"
                    >
                      <Text>网格项 {i}</Text>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}

export default MinecraftShowcase