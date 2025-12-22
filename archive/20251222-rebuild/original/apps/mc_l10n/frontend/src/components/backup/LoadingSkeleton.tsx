/**
 * 加载骨架屏组件
 * 提供各种场景的加载状态展示
 */

import React from 'react'
import { Box, Card, CardContent, Skeleton, Grid, Stack } from '@mui/material'
import { useTheme } from '@mui/material/styles'

interface LoadingSkeletonProps {
  variant?: 'card' | 'table' | 'list' | 'project' | 'translation' | 'dashboard'
  count?: number
  animation?: 'pulse' | 'wave' | false
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  variant = 'card',
  count = 1,
  animation = 'wave',
}) => {
  const theme = useTheme()

  const renderCardSkeleton = () => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box
          sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}
        >
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Skeleton variant='rounded' width={60} height={24} animation={animation} />
            <Skeleton variant='rounded' width={50} height={24} animation={animation} />
          </Box>
          <Skeleton variant='circular' width={24} height={24} animation={animation} />
        </Box>

        <Skeleton
          variant='text'
          sx={{ fontSize: '1.2rem', mb: 1 }}
          width='70%'
          animation={animation}
        />

        <Skeleton variant='text' sx={{ fontSize: '0.875rem' }} width='90%' animation={animation} />
        <Skeleton
          variant='text'
          sx={{ fontSize: '0.875rem', mb: 2 }}
          width='60%'
          animation={animation}
        />

        <Box sx={{ display: 'flex', gap: 0.5, mb: 2 }}>
          <Skeleton variant='rounded' width={40} height={20} animation={animation} />
          <Skeleton variant='rounded' width={45} height={20} animation={animation} />
          <Skeleton variant='rounded' width={35} height={20} animation={animation} />
        </Box>

        <Skeleton variant='text' sx={{ fontSize: '0.75rem' }} width='50%' animation={animation} />
      </CardContent>
    </Card>
  )

  const renderTableSkeleton = () => (
    <Card>
      <CardContent sx={{ p: 0 }}>
        {/* Table Header */}
        <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Skeleton variant='rectangular' width={20} height={20} animation={animation} />
            <Skeleton variant='text' width={120} animation={animation} />
            <Skeleton variant='text' width={200} animation={animation} />
            <Skeleton variant='text' width={150} animation={animation} />
            <Skeleton variant='text' width={80} animation={animation} />
            <Skeleton variant='text' width={100} animation={animation} />
            <Skeleton variant='text' width={60} animation={animation} />
          </Box>
        </Box>

        {/* Table Rows */}
        {Array.from({ length: count }).map((_, index) => (
          <Box
            key={index}
            sx={{
              p: 2,
              borderBottom: index < count - 1 ? `1px solid ${theme.palette.divider}` : 'none',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Skeleton variant='rectangular' width={20} height={20} animation={animation} />
              <Skeleton variant='text' width={150} animation={animation} />
              <Skeleton variant='text' width={250} animation={animation} />
              <Skeleton variant='text' width={200} animation={animation} />
              <Skeleton variant='rounded' width={60} height={24} animation={animation} />
              <Skeleton variant='rounded' width={80} height={24} animation={animation} />
              <Skeleton variant='text' width={100} animation={animation} />
            </Box>
          </Box>
        ))}
      </CardContent>
    </Card>
  )

  const renderListSkeleton = () => (
    <Card>
      <CardContent>
        {Array.from({ length: count }).map((_, index) => (
          <Box
            key={index}
            sx={{
              display: 'flex',
              alignItems: 'center',
              py: 1.5,
              borderBottom: index < count - 1 ? `1px solid ${theme.palette.divider}` : 'none',
            }}
          >
            <Skeleton
              variant='circular'
              width={40}
              height={40}
              sx={{ mr: 2 }}
              animation={animation}
            />
            <Box sx={{ flexGrow: 1 }}>
              <Skeleton variant='text' width='60%' animation={animation} />
              <Skeleton variant='text' width='40%' animation={animation} />
            </Box>
            <Skeleton variant='rounded' width={60} height={32} animation={animation} />
          </Box>
        ))}
      </CardContent>
    </Card>
  )

  const renderProjectSkeleton = () => (
    <Box>
      {/* Project Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box>
            <Skeleton
              variant='text'
              sx={{ fontSize: '2.5rem', mb: 1 }}
              width={200}
              animation={animation}
            />
            <Skeleton variant='text' sx={{ fontSize: '1rem' }} width={300} animation={animation} />
          </Box>
          <Skeleton variant='rounded' width={120} height={40} animation={animation} />
        </Box>

        {/* Stats Cards */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          {Array.from({ length: 4 }).map((_, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <Card>
                <CardContent sx={{ textAlign: 'center', py: 2 }}>
                  <Skeleton
                    variant='circular'
                    width={32}
                    height={32}
                    sx={{ mx: 'auto', mb: 1 }}
                    animation={animation}
                  />
                  <Skeleton
                    variant='text'
                    sx={{ fontSize: '1.5rem', mb: 0.5 }}
                    width={60}
                    animation={animation}
                  />
                  <Skeleton variant='text' width={80} animation={animation} />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Filter Section */}
        <Card sx={{ p: 3 }}>
          <Grid container spacing={3} alignItems='center'>
            <Grid item xs={12} md={4}>
              <Skeleton variant='rounded' height={56} animation={animation} />
            </Grid>
            <Grid item xs={12} sm={4} md={2}>
              <Skeleton variant='rounded' height={40} animation={animation} />
            </Grid>
            <Grid item xs={12} sm={4} md={2}>
              <Skeleton variant='rounded' height={40} animation={animation} />
            </Grid>
            <Grid item xs={12} sm={4} md={2}>
              <Skeleton variant='rounded' height={40} animation={animation} />
            </Grid>
            <Grid item xs={12} md={2}>
              <Skeleton variant='rounded' width={80} height={32} animation={animation} />
            </Grid>
          </Grid>
        </Card>
      </Box>
    </Box>
  )

  const renderTranslationSkeleton = () => (
    <Box>
      {/* Translation Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Box>
            <Skeleton
              variant='text'
              sx={{ fontSize: '2.5rem', mb: 1 }}
              width={180}
              animation={animation}
            />
            <Skeleton variant='text' sx={{ fontSize: '1rem' }} width={250} animation={animation} />
          </Box>
          <Stack direction='row' spacing={2}>
            <Skeleton variant='rounded' width={80} height={36} animation={animation} />
            <Skeleton variant='rounded' width={80} height={36} animation={animation} />
          </Stack>
        </Box>

        {/* Project Selector */}
        <Card sx={{ mb: 3 }}>
          <CardContent sx={{ py: 2 }}>
            <Skeleton variant='rounded' height={56} animation={animation} />
          </CardContent>
        </Card>

        {/* Stats Grid */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          {Array.from({ length: 4 }).map((_, index) => (
            <Grid item xs={6} sm={3} key={index}>
              <Card>
                <CardContent sx={{ textAlign: 'center', py: 2 }}>
                  <Skeleton
                    variant='circular'
                    width={24}
                    height={24}
                    sx={{ mx: 'auto', mb: 1 }}
                    animation={animation}
                  />
                  <Skeleton
                    variant='text'
                    sx={{ fontSize: '1.25rem', mb: 0.5 }}
                    width={50}
                    animation={animation}
                  />
                  <Skeleton variant='text' width={60} animation={animation} />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Translation Table */}
      {renderTableSkeleton()}
    </Box>
  )

  const renderDashboardSkeleton = () => (
    <Box>
      {/* Dashboard Header */}
      <Box sx={{ mb: 4 }}>
        <Skeleton
          variant='text'
          sx={{ fontSize: '2.5rem', mb: 1 }}
          width={250}
          animation={animation}
        />
        <Skeleton
          variant='text'
          sx={{ fontSize: '1rem', mb: 3 }}
          width={400}
          animation={animation}
        />
      </Box>

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {Array.from({ length: 6 }).map((_, index) => (
          <Grid item xs={12} sm={6} md={4} lg={2} key={index}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 3 }}>
                <Skeleton
                  variant='circular'
                  width={40}
                  height={40}
                  sx={{ mx: 'auto', mb: 2 }}
                  animation={animation}
                />
                <Skeleton
                  variant='text'
                  sx={{ fontSize: '1.5rem', mb: 1 }}
                  width={40}
                  animation={animation}
                />
                <Skeleton variant='text' width={60} animation={animation} />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Main Content Grid */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Skeleton
                variant='text'
                sx={{ fontSize: '1.25rem', mb: 2 }}
                width={150}
                animation={animation}
              />
              <Skeleton variant='rounded' height={300} animation={animation} />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Skeleton
                variant='text'
                sx={{ fontSize: '1.25rem', mb: 2 }}
                width={120}
                animation={animation}
              />
              {Array.from({ length: 5 }).map((_, index) => (
                <Box key={index} sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Skeleton
                    variant='circular'
                    width={32}
                    height={32}
                    sx={{ mr: 2 }}
                    animation={animation}
                  />
                  <Box sx={{ flexGrow: 1 }}>
                    <Skeleton variant='text' width='70%' animation={animation} />
                    <Skeleton variant='text' width='50%' animation={animation} />
                  </Box>
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )

  const renderSkeleton = () => {
    switch (variant) {
      case 'table':
        return renderTableSkeleton()
      case 'list':
        return renderListSkeleton()
      case 'project':
        return renderProjectSkeleton()
      case 'translation':
        return renderTranslationSkeleton()
      case 'dashboard':
        return renderDashboardSkeleton()
      case 'card':
      default:
        return (
          <Grid container spacing={3}>
            {Array.from({ length: count }).map((_, index) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
                {renderCardSkeleton()}
              </Grid>
            ))}
          </Grid>
        )
    }
  }

  return renderSkeleton()
}
