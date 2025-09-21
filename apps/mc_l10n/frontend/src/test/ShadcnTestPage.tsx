import React from 'react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Badge } from '../components/ui/badge'
import { Separator } from '../components/ui/separator'

/**
 * 测试页面：验证shadcn/ui组件是否正常工作
 */
export const ShadcnTestPage: React.FC = () => {
  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-2">shadcn/ui 组件测试</h1>
        <p className="text-gray-600">验证所有核心组件是否正常工作</p>
      </div>

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>按钮组件测试</CardTitle>
          <CardDescription>测试不同类型的按钮</CardDescription>
        </CardHeader>
        <CardContent className="space-x-4">
          <Button>默认按钮</Button>
          <Button variant="destructive">危险按钮</Button>
          <Button variant="outline">轮廓按钮</Button>
          <Button variant="secondary">次要按钮</Button>
          <Button variant="ghost">幽灵按钮</Button>
          <Button variant="link">链接按钮</Button>
          <Button size="lg">大按钮</Button>
          <Button size="sm">小按钮</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>表单组件测试</CardTitle>
          <CardDescription>测试输入框和选择器</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="test-input">测试输入框</Label>
            <Input id="test-input" placeholder="请输入内容..." />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="test-select">测试选择器</Label>
            <Select>
              <SelectTrigger>
                <SelectValue placeholder="请选择一个选项" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="option1">选项 1</SelectItem>
                <SelectItem value="option2">选项 2</SelectItem>
                <SelectItem value="option3">选项 3</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>标签页组件测试</CardTitle>
          <CardDescription>测试Tabs组件</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="tab1" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="tab1">标签页 1</TabsTrigger>
              <TabsTrigger value="tab2">标签页 2</TabsTrigger>
              <TabsTrigger value="tab3">标签页 3</TabsTrigger>
            </TabsList>
            <TabsContent value="tab1" className="mt-4">
              <Card>
                <CardContent className="pt-6">
                  <p>这是标签页 1 的内容</p>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="tab2" className="mt-4">
              <Card>
                <CardContent className="pt-6">
                  <p>这是标签页 2 的内容</p>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="tab3" className="mt-4">
              <Card>
                <CardContent className="pt-6">
                  <p>这是标签页 3 的内容</p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>其他组件测试</CardTitle>
          <CardDescription>测试徽章等组件</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex space-x-2">
            <Badge>默认徽章</Badge>
            <Badge variant="secondary">次要徽章</Badge>
            <Badge variant="destructive">危险徽章</Badge>
            <Badge variant="outline">轮廓徽章</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}