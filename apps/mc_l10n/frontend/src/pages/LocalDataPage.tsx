import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import {
  RefreshCw,
  Download,
  Database,
  BarChart3,
  ListOrdered,
  Link,
  Search,
  Filter,
  Globe,
  CheckCircle,
} from 'lucide-react'
import { apiService } from '@/services/apiService'

interface LocalEntry {
  local_id: number
  project_id: string
  source_type: string
  source_file: string
  source_locator: string
  source_lang_bcp47: string
  source_context: {
    modid: string
    namespace: string
    format: string
  }
  source_payload: {
    hash: string
    size: number
    locale: string
  }
  note: string
  created_at: string
  updated_at: string
}

interface MappingPlan {
  id: number
  source_file: string
  namespace: string
  language: string
  key_hash: string
  updated_at: string
}

interface OutboundQueue {
  id: number
  plan_id: number
  intent: string
  state: string
  namespace: string
  language: string
  updated_at: string
}

interface MappingLink {
  id: number
  local_entry_id: number
  plan_id: number
  state: string
  namespace: string
  language: string
  updated_at: string
}

interface Statistics {
  total_entries: number
  total_plans: number
  total_snapshots: number
  active_mappings: number
  unmapped_entries: number
  by_language: Record<string, number>
  outbound_queue: Record<string, number>
  link_states: Record<string, number>
}

const LocalDataPage: React.FC = () => {
  const [localEntries, setLocalEntries] = useState<LocalEntry[]>([])
  const [mappingPlans, setMappingPlans] = useState<MappingPlan[]>([])
  const [outboundQueue, setOutboundQueue] = useState<OutboundQueue[]>([])
  const [mappingLinks, setMappingLinks] = useState<MappingLink[]>([])
  const [statistics, setStatistics] = useState<Statistics>({
    total_entries: 0,
    total_plans: 0,
    total_snapshots: 0,
    active_mappings: 0,
    unmapped_entries: 0,
    by_language: {},
    outbound_queue: {},
    link_states: {},
  })
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedNamespace, setSelectedNamespace] = useState<string>('all')
  const [selectedLanguage, setSelectedLanguage] = useState<string>('all')
  const [selectedState, setSelectedState] = useState<string>('all')

  const fetchLocalEntries = async () => {
    try {
      const response = await apiService.getLocalEntries()
      setLocalEntries(response as LocalEntry[])
    } catch (error) {
      console.error('Failed to fetch local entries:', error)
    }
  }

  const fetchMappingPlans = async () => {
    try {
      const response = await apiService.getMappingPlans()
      setMappingPlans(response as MappingPlan[])
    } catch (error) {
      console.error('Failed to fetch mapping plans:', error)
    }
  }

  const fetchOutboundQueue = async () => {
    try {
      const response = await apiService.getOutboundQueue()
      setOutboundQueue(response as OutboundQueue[])
    } catch (error) {
      console.error('Failed to fetch outbound queue:', error)
    }
  }

  const fetchMappingLinks = async () => {
    try {
      const response = await apiService.getMappingLinks()
      setMappingLinks(response as MappingLink[])
    } catch (error) {
      console.error('Failed to fetch mapping links:', error)
    }
  }

  const fetchStatistics = async () => {
    try {
      const response = await apiService.getStatistics()
      setStatistics(response as Statistics)
    } catch (error) {
      console.error('Failed to fetch statistics:', error)
    }
  }

  const refreshAllData = async () => {
    setLoading(true)
    try {
      await Promise.all([
        fetchLocalEntries(),
        fetchMappingPlans(),
        fetchOutboundQueue(),
        fetchMappingLinks(),
        fetchStatistics(),
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleImportData = async () => {
    try {
      // 使用示例库存文件路径进行导入
      const inventoryFile = './sample_inventory.json'
      await apiService.importScanResults(inventoryFile, 'minecraft')
      await refreshAllData()
    } catch (error) {
      console.error('Failed to import data:', error)
    }
  }

  useEffect(() => {
    refreshAllData()
  }, [])

  const getStateColor = (state: string) => {
    switch (state.toLowerCase()) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'processing':
        return 'bg-blue-100 text-blue-800'
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'inactive':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const filteredEntries = localEntries.filter(entry => {
    const matchesSearch =
      entry.source_file.toLowerCase().includes(searchTerm.toLowerCase()) ||
      entry.source_context?.namespace?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      entry.source_payload?.hash?.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesNamespace =
      selectedNamespace === 'all' || entry.source_context?.namespace === selectedNamespace
    const matchesLanguage =
      selectedLanguage === 'all' || entry.source_lang_bcp47 === selectedLanguage
    return matchesSearch && matchesNamespace && matchesLanguage
  })

  const filteredPlans = mappingPlans.filter(plan => {
    const matchesSearch =
      plan.source_file.toLowerCase().includes(searchTerm.toLowerCase()) ||
      plan.namespace.toLowerCase().includes(searchTerm.toLowerCase()) ||
      plan.key_hash.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesNamespace = selectedNamespace === 'all' || plan.namespace === selectedNamespace
    const matchesLanguage = selectedLanguage === 'all' || plan.language === selectedLanguage
    return matchesSearch && matchesNamespace && matchesLanguage
  })

  const filteredQueue = outboundQueue.filter(item => {
    const matchesSearch =
      item.intent.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.namespace.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesNamespace = selectedNamespace === 'all' || item.namespace === selectedNamespace
    const matchesLanguage = selectedLanguage === 'all' || item.language === selectedLanguage
    const matchesState = selectedState === 'all' || item.state === selectedState
    return matchesSearch && matchesNamespace && matchesLanguage && matchesState
  })

  const filteredLinks = mappingLinks.filter(link => {
    const matchesNamespace = selectedNamespace === 'all' || link.namespace === selectedNamespace
    const matchesLanguage = selectedLanguage === 'all' || link.language === selectedLanguage
    const matchesState = selectedState === 'all' || link.state === selectedState
    return matchesNamespace && matchesLanguage && matchesState
  })

  return (
    <div className='min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100'>
      <div className='container mx-auto px-4 sm:px-6 lg:px-8 py-6'>
        {/* Header */}
        <div className='mb-8'>
          <div className='bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6'>
            <div className='flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4'>
              <div className='space-y-2'>
                <div className='flex items-center space-x-3'>
                  <div className='p-2 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg'>
                    <Database className='h-6 w-6 text-white' />
                  </div>
                  <h1 className='text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent'>
                    本地数据管理
                  </h1>
                </div>
                <p className='text-gray-600 text-lg'>管理和查看本地翻译数据、映射计划和同步队列</p>
              </div>
              <div className='flex items-center space-x-3'>
                <Button
                  onClick={refreshAllData}
                  disabled={loading}
                  variant='outline'
                  className='flex items-center space-x-2 bg-white/50 hover:bg-white/80 border-gray-200 shadow-sm transition-all duration-200'
                >
                  <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                  <span>刷新数据</span>
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className='space-y-8'>
          {/* Statistics Cards */}
          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
            <div className='bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 p-6 hover:shadow-xl transition-all duration-300'>
              <div className='flex items-center justify-between'>
                <div>
                  <p className='text-sm font-medium text-gray-600'>本地条目</p>
                  <p className='text-3xl font-bold text-blue-600'>{localEntries.length}</p>
                </div>
                <div className='p-3 bg-blue-100 rounded-lg'>
                  <Database className='h-6 w-6 text-blue-600' />
                </div>
              </div>
            </div>
            <div className='bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 p-6 hover:shadow-xl transition-all duration-300'>
              <div className='flex items-center justify-between'>
                <div>
                  <p className='text-sm font-medium text-gray-600'>映射计划</p>
                  <p className='text-3xl font-bold text-green-600'>{mappingPlans.length}</p>
                </div>
                <div className='p-3 bg-green-100 rounded-lg'>
                  <BarChart3 className='h-6 w-6 text-green-600' />
                </div>
              </div>
            </div>
            <div className='bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 p-6 hover:shadow-xl transition-all duration-300'>
              <div className='flex items-center justify-between'>
                <div>
                  <p className='text-sm font-medium text-gray-600'>同步队列</p>
                  <p className='text-3xl font-bold text-orange-600'>{outboundQueue.length}</p>
                </div>
                <div className='p-3 bg-orange-100 rounded-lg'>
                  <ListOrdered className='h-6 w-6 text-orange-600' />
                </div>
              </div>
            </div>
            <div className='bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 p-6 hover:shadow-xl transition-all duration-300'>
              <div className='flex items-center justify-between'>
                <div>
                  <p className='text-sm font-medium text-gray-600'>映射链接</p>
                  <p className='text-3xl font-bold text-purple-600'>{mappingLinks.length}</p>
                </div>
                <div className='p-3 bg-purple-100 rounded-lg'>
                  <Link className='h-6 w-6 text-purple-600' />
                </div>
              </div>
            </div>
          </div>

          {/* Action Bar */}
          <div className='bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 p-6'>
            <div className='flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4'>
              <div className='flex items-center space-x-4'>
                <Button
                  onClick={handleImportData}
                  className='flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl transition-all duration-200'
                >
                  <Download className='h-4 w-4' />
                  <span>导入数据</span>
                </Button>
              </div>
              <div className='text-sm text-gray-600 bg-gray-50 px-4 py-2 rounded-lg'>
                共 {localEntries.length} 个本地条目，{mappingPlans.length} 个映射计划
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <Tabs defaultValue='entries' className='space-y-6'>
            <TabsList className='grid w-full grid-cols-4 bg-white/80 backdrop-blur-sm border border-white/20 rounded-xl p-2 shadow-lg'>
              <TabsTrigger
                value='entries'
                className='flex items-center space-x-2 data-[state=active]:bg-blue-600 data-[state=active]:text-white data-[state=active]:shadow-md transition-all duration-200 rounded-lg'
              >
                <Database className='h-4 w-4' />
                <span>本地条目</span>
              </TabsTrigger>
              <TabsTrigger
                value='plans'
                className='flex items-center space-x-2 data-[state=active]:bg-green-600 data-[state=active]:text-white data-[state=active]:shadow-md transition-all duration-200 rounded-lg'
              >
                <BarChart3 className='h-4 w-4' />
                <span>映射计划</span>
              </TabsTrigger>
              <TabsTrigger
                value='queue'
                className='flex items-center space-x-2 data-[state=active]:bg-orange-600 data-[state=active]:text-white data-[state=active]:shadow-md transition-all duration-200 rounded-lg'
              >
                <ListOrdered className='h-4 w-4' />
                <span>同步队列</span>
              </TabsTrigger>
              <TabsTrigger
                value='links'
                className='flex items-center space-x-2 data-[state=active]:bg-purple-600 data-[state=active]:text-white data-[state=active]:shadow-md transition-all duration-200 rounded-lg'
              >
                <Link className='h-4 w-4' />
                <span>映射链接</span>
              </TabsTrigger>
            </TabsList>

            {/* Search and Filter */}
            <div className='bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 p-6'>
              <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
                <div className='space-y-3'>
                  <label className='text-sm font-semibold text-gray-700 flex items-center space-x-2'>
                    <Database className='h-4 w-4 text-blue-600' />
                    <span>搜索</span>
                  </label>
                  <div className='relative'>
                    <Database className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
                    <Input
                      placeholder='搜索文件名、命名空间或键哈希...'
                      value={searchTerm}
                      onChange={e => setSearchTerm(e.target.value)}
                      className='pl-10 border-gray-200 focus:border-blue-500 focus:ring-blue-500 rounded-lg shadow-sm'
                    />
                  </div>
                </div>
                <div className='space-y-3'>
                  <label className='text-sm font-semibold text-gray-700 flex items-center space-x-2'>
                    <BarChart3 className='h-4 w-4 text-green-600' />
                    <span>命名空间</span>
                  </label>
                  <Select value={selectedNamespace} onValueChange={setSelectedNamespace}>
                    <SelectTrigger className='border-gray-200 focus:border-green-500 focus:ring-green-500 rounded-lg shadow-sm'>
                      <SelectValue placeholder='选择命名空间' />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value='all'>所有命名空间</SelectItem>
                      {Array.from(
                        new Set(localEntries.map(e => e.source_context?.namespace).filter(Boolean)),
                      ).map(ns => (
                        <SelectItem key={ns} value={ns}>
                          {ns}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className='space-y-3'>
                  <label className='text-sm font-semibold text-gray-700 flex items-center space-x-2'>
                    <ListOrdered className='h-4 w-4 text-orange-600' />
                    <span>语言</span>
                  </label>
                  <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                    <SelectTrigger className='border-gray-200 focus:border-orange-500 focus:ring-orange-500 rounded-lg shadow-sm'>
                      <SelectValue placeholder='选择语言' />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value='all'>所有语言</SelectItem>
                      {Array.from(
                        new Set(localEntries.map(e => e.source_lang_bcp47).filter(Boolean)),
                      ).map(lang => (
                        <SelectItem key={lang} value={lang}>
                          {lang}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className='space-y-3'>
                  <label className='text-sm font-semibold text-gray-700 flex items-center space-x-2'>
                    <Link className='h-4 w-4 text-purple-600' />
                    <span>状态</span>
                  </label>
                  <Select value={selectedState} onValueChange={setSelectedState}>
                    <SelectTrigger className='border-gray-200 focus:border-purple-500 focus:ring-purple-500 rounded-lg shadow-sm'>
                      <SelectValue placeholder='选择状态' />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value='all'>所有状态</SelectItem>
                      <SelectItem value='pending'>待处理</SelectItem>
                      <SelectItem value='processing'>处理中</SelectItem>
                      <SelectItem value='completed'>已完成</SelectItem>
                      <SelectItem value='failed'>失败</SelectItem>
                      <SelectItem value='active'>活跃</SelectItem>
                      <SelectItem value='inactive'>非活跃</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Local Entries Tab */}
            <TabsContent value='entries' className='space-y-6'>
              <div className='bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-white/20 overflow-hidden'>
                <div className='bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-white/20'>
                  <div className='flex items-center justify-between'>
                    <h3 className='text-lg font-semibold text-gray-800 flex items-center space-x-2'>
                      <Database className='h-5 w-5 text-blue-600' />
                      <span>本地条目数据</span>
                      <span className='text-sm font-normal text-gray-600'>
                        ({filteredEntries.length} 条记录)
                      </span>
                    </h3>
                    <Button
                      onClick={handleImportData}
                      size='sm'
                      className='bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl transition-all duration-200'
                    >
                      <Download className='h-4 w-4 mr-2' />
                      <span>导入数据</span>
                    </Button>
                  </div>
                </div>
                <div className='p-6'>
                  {filteredEntries.length === 0 ? (
                    <div className='text-center py-16'>
                      <div className='p-6 bg-blue-100 rounded-full w-24 h-24 mx-auto mb-6 flex items-center justify-center'>
                        <Database className='h-12 w-12 text-blue-600' />
                      </div>
                      <h3 className='text-xl font-semibold text-gray-800 mb-3'>暂无本地条目数据</h3>
                      <p className='text-gray-600 mb-6 max-w-md mx-auto'>
                        点击下方按钮导入数据开始使用本地翻译管理功能
                      </p>
                      <Button
                        onClick={handleImportData}
                        className='bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl transition-all duration-200 px-8 py-3'
                      >
                        <Download className='h-5 w-5 mr-2' />
                        立即导入数据
                      </Button>
                    </div>
                  ) : (
                    <div className='overflow-hidden rounded-lg border border-gray-200'>
                      <Table>
                        <TableHeader>
                          <TableRow className='bg-gradient-to-r from-gray-50 to-gray-100'>
                            <TableHead className='font-semibold text-gray-700 py-4'>ID</TableHead>
                            <TableHead className='font-semibold text-gray-700 py-4'>
                              源文件
                            </TableHead>
                            <TableHead className='font-semibold text-gray-700 py-4'>
                              命名空间
                            </TableHead>
                            <TableHead className='font-semibold text-gray-700 py-4'>语言</TableHead>
                            <TableHead className='font-semibold text-gray-700 py-4'>
                              键哈希
                            </TableHead>
                            <TableHead className='font-semibold text-gray-700 py-4'>
                              更新时间
                            </TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {filteredEntries.map((entry, index) => (
                            <TableRow
                              key={entry.local_id}
                              className={`hover:bg-blue-50/50 transition-colors duration-200 ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}`}
                            >
                              <TableCell className='font-semibold text-blue-600 py-4'>
                                {entry.local_id}
                              </TableCell>
                              <TableCell className='max-w-xs py-4' title={entry.source_file}>
                                <div className='truncate text-gray-800 font-medium'>
                                  {entry.source_file}
                                </div>
                              </TableCell>
                              <TableCell className='py-4'>
                                <Badge className='bg-blue-100 text-blue-800 hover:bg-blue-200 border-blue-200 font-medium px-3 py-1'>
                                  {entry.source_context?.namespace}
                                </Badge>
                              </TableCell>
                              <TableCell className='py-4'>
                                <Badge className='bg-green-100 text-green-800 hover:bg-green-200 border-green-200 font-medium px-3 py-1'>
                                  {entry.source_lang_bcp47}
                                </Badge>
                              </TableCell>
                              <TableCell className='font-mono text-sm bg-gray-100 rounded-md px-3 py-2 text-gray-700'>
                                {entry.source_payload?.hash}
                              </TableCell>
                              <TableCell className='text-sm text-gray-600 py-4'>
                                {new Date(entry.updated_at).toLocaleString()}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>

            {/* Mapping Plans Tab */}
            <TabsContent value='plans' className='space-y-4'>
              <div className='bg-white rounded-lg shadow-sm border'>
                <div className='p-6 border-b'>
                  <div className='flex items-center justify-between'>
                    <h2 className='text-xl font-semibold text-gray-900'>映射计划</h2>
                    <span className='text-sm text-gray-500'>共 {filteredPlans.length} 条记录</span>
                  </div>
                </div>
                <div className='p-6'>
                  {filteredPlans.length === 0 ? (
                    <div className='text-center py-12'>
                      <BarChart3 className='h-12 w-12 text-gray-400 mx-auto mb-4' />
                      <h3 className='text-lg font-medium text-gray-900 mb-2'>暂无映射计划</h3>
                      <p className='text-gray-500'>映射计划将在数据导入后自动生成</p>
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>ID</TableHead>
                          <TableHead>源文件</TableHead>
                          <TableHead>命名空间</TableHead>
                          <TableHead>语言</TableHead>
                          <TableHead>键哈希</TableHead>
                          <TableHead>更新时间</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredPlans.map(plan => (
                          <TableRow key={plan.id}>
                            <TableCell className='font-medium'>{plan.id}</TableCell>
                            <TableCell className='max-w-xs truncate' title={plan.source_file}>
                              {plan.source_file}
                            </TableCell>
                            <TableCell>
                              <Badge variant='outline'>{plan.namespace}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant='secondary'>{plan.language}</Badge>
                            </TableCell>
                            <TableCell className='font-mono text-sm'>{plan.key_hash}</TableCell>
                            <TableCell className='text-sm text-gray-500'>
                              {new Date(plan.updated_at).toLocaleString()}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
              </div>
            </TabsContent>

            {/* Outbound Queue Tab */}
            <TabsContent value='queue' className='space-y-4'>
              <div className='bg-white rounded-lg shadow-sm border'>
                <div className='p-6 border-b'>
                  <div className='flex items-center justify-between'>
                    <h2 className='text-xl font-semibold text-gray-900'>同步队列</h2>
                    <span className='text-sm text-gray-500'>共 {filteredQueue.length} 条记录</span>
                  </div>
                </div>
                <div className='p-6'>
                  {filteredQueue.length === 0 ? (
                    <div className='text-center py-12'>
                      <ListOrdered className='h-12 w-12 text-gray-400 mx-auto mb-4' />
                      <h3 className='text-lg font-medium text-gray-900 mb-2'>暂无同步队列</h3>
                      <p className='text-gray-500'>同步队列将在有数据变更时自动生成</p>
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>队列ID</TableHead>
                          <TableHead>计划ID</TableHead>
                          <TableHead>意图</TableHead>
                          <TableHead>状态</TableHead>
                          <TableHead>命名空间</TableHead>
                          <TableHead>语言</TableHead>
                          <TableHead>更新时间</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredQueue.map(item => (
                          <TableRow key={item.id}>
                            <TableCell className='font-medium'>{item.id}</TableCell>
                            <TableCell>{item.plan_id}</TableCell>
                            <TableCell>
                              <Badge variant='outline'>{item.intent}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge className={getStateColor(item.state)}>{item.state}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant='outline'>{item.namespace}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant='secondary'>{item.language}</Badge>
                            </TableCell>
                            <TableCell className='text-sm text-gray-500'>
                              {new Date(item.updated_at).toLocaleString()}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
              </div>
            </TabsContent>

            {/* Mapping Links Tab */}
            <TabsContent value='links' className='space-y-4'>
              <div className='bg-white rounded-lg shadow-sm border'>
                <div className='p-6 border-b'>
                  <div className='flex items-center justify-between'>
                    <h2 className='text-xl font-semibold text-gray-900'>映射链接</h2>
                    <span className='text-sm text-gray-500'>共 {filteredLinks.length} 条记录</span>
                  </div>
                </div>
                <div className='p-6'>
                  {filteredLinks.length === 0 ? (
                    <div className='text-center py-12'>
                      <Link className='h-12 w-12 text-gray-400 mx-auto mb-4' />
                      <h3 className='text-lg font-medium text-gray-900 mb-2'>暂无映射链接</h3>
                      <p className='text-gray-500'>映射链接将在本地条目与计划关联时自动生成</p>
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>链接ID</TableHead>
                          <TableHead>本地条目ID</TableHead>
                          <TableHead>计划ID</TableHead>
                          <TableHead>状态</TableHead>
                          <TableHead>命名空间</TableHead>
                          <TableHead>语言</TableHead>
                          <TableHead>更新时间</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredLinks.map(link => (
                          <TableRow key={link.id}>
                            <TableCell className='font-medium'>{link.id}</TableCell>
                            <TableCell>{link.local_entry_id}</TableCell>
                            <TableCell>{link.plan_id}</TableCell>
                            <TableCell>
                              <Badge className={getStateColor(link.state)}>{link.state}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant='outline'>{link.namespace}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant='secondary'>{link.language}</Badge>
                            </TableCell>
                            <TableCell className='text-sm text-gray-500'>
                              {new Date(link.updated_at).toLocaleString()}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
              </div>
            </TabsContent>

            {/* Statistics Tab */}
            <TabsContent value='statistics' className='space-y-4'>
              <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
                <Card className='border-blue-200 bg-blue-50/50'>
                  <CardHeader className='pb-3'>
                    <div className='flex items-center justify-between'>
                      <CardTitle className='text-lg text-blue-800'>本地条目统计</CardTitle>
                      <Database className='h-5 w-5 text-blue-600' />
                    </div>
                  </CardHeader>
                  <CardContent className='space-y-3'>
                    <div className='flex justify-between items-center'>
                      <span className='text-blue-700 font-medium'>总条目数:</span>
                      <span className='text-2xl font-bold text-blue-800'>
                        {statistics.total_entries || 0}
                      </span>
                    </div>
                    {statistics.by_language &&
                      Object.entries(statistics.by_language).map(([lang, count]) => (
                        <div key={lang} className='flex justify-between items-center'>
                          <span className='text-blue-600'>{lang}:</span>
                          <span className='font-semibold text-blue-700'>{count}</span>
                        </div>
                      ))}
                  </CardContent>
                </Card>

                <Card className='border-orange-200 bg-orange-50/50'>
                  <CardHeader className='pb-3'>
                    <div className='flex items-center justify-between'>
                      <CardTitle className='text-lg text-orange-800'>同步队列统计</CardTitle>
                      <ListOrdered className='h-5 w-5 text-orange-600' />
                    </div>
                  </CardHeader>
                  <CardContent className='space-y-3'>
                    <div className='flex justify-between items-center'>
                      <span className='text-orange-700 font-medium'>总快照数:</span>
                      <span className='text-2xl font-bold text-orange-800'>
                        {statistics.total_snapshots || 0}
                      </span>
                    </div>
                    {statistics.outbound_queue &&
                      Object.entries(statistics.outbound_queue).map(([state, count]) => (
                        <div key={state} className='flex justify-between items-center'>
                          <span className='text-orange-600'>{state}:</span>
                          <span className='font-semibold text-orange-700'>{count}</span>
                        </div>
                      ))}
                  </CardContent>
                </Card>

                <Card className='border-purple-200 bg-purple-50/50'>
                  <CardHeader className='pb-3'>
                    <div className='flex items-center justify-between'>
                      <CardTitle className='text-lg text-purple-800'>映射链接统计</CardTitle>
                      <Link className='h-5 w-5 text-purple-600' />
                    </div>
                  </CardHeader>
                  <CardContent className='space-y-3'>
                    <div className='flex justify-between items-center'>
                      <span className='text-purple-700 font-medium'>活跃映射:</span>
                      <span className='text-2xl font-bold text-purple-800'>
                        {statistics.active_mappings || 0}
                      </span>
                    </div>
                    <div className='flex justify-between items-center'>
                      <span className='text-purple-700 font-medium'>未映射条目:</span>
                      <span className='text-xl font-bold text-purple-800'>
                        {statistics.unmapped_entries || 0}
                      </span>
                    </div>
                    {statistics.link_states &&
                      Object.entries(statistics.link_states).map(([state, count]) => (
                        <div key={state} className='flex justify-between items-center'>
                          <span className='text-purple-600'>{state}:</span>
                          <span className='font-semibold text-purple-700'>{count}</span>
                        </div>
                      ))}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}

export default LocalDataPage
