"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useEffect, useState } from "react"
import http from "@/lib/http"
import { Skeleton } from "@/components/ui/skeleton"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart"
import {
  CartesianGrid,
  Line,
  LineChart as ReLineChart,
  XAxis,
  YAxis,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts"
import { Database, FileText, AlertTriangle, Beaker, TrendingUp, TrendingDown, Flame } from "lucide-react"
import { cn } from "@/lib/utils"

interface OverviewPanelProps {
  onNavigateToInjuryScreening: () => void
}

interface OverviewStats {
  systemLibrary: number
  collectionVolume: number
  injuryEvents: number
  chemicalStressors: number
}

interface TrendData {
  name: string
  新闻: number
  文献: number
  召回: number
}

interface CategoryData {
  name: string
  value: number
}

interface HotAlert {
  rank: number
  product: string
  adverseReaction: string
  eventCount: number
}

const PIE_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16']

export default function OverviewPanel({ onNavigateToInjuryScreening }: OverviewPanelProps) {
  const [stats, setStats] = useState<OverviewStats>({
    systemLibrary: 0,
    collectionVolume: 0,
    injuryEvents: 0,
    chemicalStressors: 0,
  })
  const [trendData, setTrendData] = useState<TrendData[]>([])
  const [categoryData, setCategoryData] = useState<CategoryData[]>([])
  const [hotAlerts, setHotAlerts] = useState<HotAlert[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadOverviewData()
  }, [])

  const loadOverviewData = async () => {
    setLoading(true)
    try {
      const [statsRes, trendRes, categoryRes, alertsRes] = await Promise.allSettled([
        http.get<any, any>('/dashboard/overview/stats'),
        http.get<any, any>('/dashboard/trend/daily', { params: { from: getMonthsAgo(6), to: getToday() } }),
        http.get<any, any>('/dashboard/overview/category-distribution'),
        http.get<any, any>('/dashboard/overview/hot-alerts'),
      ])

      if (statsRes.status === 'fulfilled' && statsRes.value) {
        setStats(statsRes.value)
      }
      if (trendRes.status === 'fulfilled' && trendRes.value) {
        setTrendData(trendRes.value)
      }
      if (categoryRes.status === 'fulfilled' && categoryRes.value?.items) {
        setCategoryData(categoryRes.value.items)
      }
      if (alertsRes.status === 'fulfilled' && alertsRes.value?.items) {
        setHotAlerts(alertsRes.value.items)
      }
    } catch (error) {
      console.error('Error loading overview data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getMonthsAgo = (months: number) => {
    const d = new Date()
    d.setMonth(d.getMonth() - months)
    return d.toISOString().split('T')[0]
  }
  const getToday = () => new Date().toISOString().split('T')[0]

  const StatCard = ({ 
    title, value, icon: Icon, clickable = false, onClick 
  }: { 
    title: string; value: number; icon: any; clickable?: boolean; onClick?: () => void
  }) => (
    <Card 
      className={cn(
        "relative overflow-hidden",
        clickable && "cursor-pointer hover:shadow-lg hover:border-primary/50 transition-all"
      )}
      onClick={clickable ? onClick : undefined}
    >
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-muted-foreground mb-1">{title}</p>
            <p className="text-3xl font-bold tracking-tight">{value.toLocaleString()}</p>
          </div>
          <div className="ml-4">
            <div className={cn(
              "w-12 h-12 rounded-full flex items-center justify-center",
              clickable ? "bg-orange-100" : "bg-primary/10"
            )}>
              <Icon className={cn("h-6 w-6", clickable ? "text-orange-600" : "text-primary")} />
            </div>
          </div>
        </div>
        {clickable && (
          <div className="absolute bottom-2 right-3 text-xs text-orange-600 font-medium">
            点击查看详情 →
          </div>
        )}
      </CardContent>
    </Card>
  )

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <Skeleton key={i} className="h-28" />)}
        </div>
        <Skeleton className="h-80" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 四个统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="系统资料库" value={stats.systemLibrary} icon={Database} />
        <StatCard title="标准化资料库" value={stats.collectionVolume} icon={FileText} />
        <StatCard 
          title="伤害事件数" value={stats.injuryEvents} icon={AlertTriangle}
          clickable onClick={onNavigateToInjuryScreening}
        />
        <StatCard title="候选化学应激源数" value={stats.chemicalStressors} icon={Beaker} />
      </div>

      {/* 采集趋势、产品类别饼图、热门预警Top5 并排 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 采集趋势折线图 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">近期事件趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer
              className="w-full h-64"
              config={{
                新闻: { label: "新闻", color: "hsl(var(--chart-1))" },
                文献: { label: "文献", color: "hsl(var(--chart-2))" },
                召回: { label: "召回", color: "hsl(var(--chart-3))" },
              }}
            >
              <ReLineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis tickLine={false} axisLine={false} width={30} fontSize={12} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <ChartLegend content={<ChartLegendContent />} />
                <Line type="monotone" dataKey="新闻" stroke="var(--color-新闻)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="文献" stroke="var(--color-文献)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="召回" stroke="var(--color-召回)" strokeWidth={2} dot={false} />
              </ReLineChart>
            </ChartContainer>
          </CardContent>
        </Card>

        {/* 产品类别分布饼图 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold" style={{ color: '#374677' }}>产品类别分布</CardTitle>
          </CardHeader>
          <CardContent>
            {categoryData.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-muted-foreground">暂无数据</div>
            ) : (
              <ResponsiveContainer width="100%" height={256}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="42%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={100}
                    paddingAngle={1}
                    dataKey="value"
                  >
                    {categoryData.map((_entry, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number, name: string) => [`${value}个产品`, name]} />
                  <Legend
                    layout="vertical"
                    verticalAlign="middle"
                    align="right"
                    iconSize={10}
                    wrapperStyle={{ paddingLeft: '10px' }}
                    formatter={(value: string, entry: any) => (
                      <span className="text-base py-2" style={{display: 'inline-block', fontSize: '15px'}}>{value} ({((entry.payload.value / categoryData.reduce((a, b) => a + b.value, 0)) * 100).toFixed(0)}%)</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* 热门预警 Top 5 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Flame className="h-4 w-4 text-orange-500" />
              热门预警 (Top 5)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {hotAlerts.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-muted-foreground">暂无数据</div>
            ) : (
              <div className="space-y-3">
                {hotAlerts.map((item) => (
                  <div key={item.rank} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors">
                    <div className={cn(
                      "flex items-center justify-center w-7 h-7 rounded-full font-bold text-xs flex-shrink-0",
                      item.rank === 1 && "bg-red-100 text-red-700",
                      item.rank === 2 && "bg-orange-100 text-orange-700",
                      item.rank === 3 && "bg-yellow-100 text-yellow-700",
                      item.rank > 3 && "bg-muted text-muted-foreground"
                    )}>
                      {item.rank}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">{item.product}</div>
                      <div className="text-xs text-muted-foreground truncate">{item.adverseReaction}</div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="font-bold text-sm text-primary">{item.eventCount}</div>
                      <div className="text-xs text-muted-foreground">事件</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
