"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useEffect, useState, useCallback } from "react"
import http from "@/lib/http"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowLeft, Search, RotateCcw, Download } from "lucide-react"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface InjuryEventScreeningProps {
  onNavigateToRiskMatrix: (productId: number, adverseReactionId: number) => void
  onBack: () => void
}

interface InjuryEvent {
  id: number
  productId: number
  productName: string
  adverseReactionId: number
  adverseReactionName: string
  eventCount: number
  prr: number
  chiSquare: number
  signalLevel: 'strong' | 'medium' | 'weak'
  signalScore: number
  hasRiskAssessment: boolean
}

const signalLevelMap = {
  strong: { label: '高', color: 'bg-red-500 text-white', dotColor: '#F35B58' },
  medium: { label: '中', color: 'bg-orange-400 text-white', dotColor: '#F9BE55' },
  weak: { label: '低', color: 'bg-blue-400 text-white', dotColor: '#73A0F5' },
}

export default function InjuryEventScreening({ onNavigateToRiskMatrix, onBack }: InjuryEventScreeningProps) {
  const [events, setEvents] = useState<InjuryEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)

  // Filter state
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [category, setCategory] = useState('全部')
  const [adverseReactionType, setAdverseReactionType] = useState('全部')
  const [categories, setCategories] = useState<string[]>([])
  const [adverseReactions, setAdverseReactions] = useState<string[]>([])

  useEffect(() => {
    loadFilters()
    loadInjuryEvents()
  }, [])

  const loadFilters = async () => {
    try {
      const res = await http.get<any, any>('/dashboard/injury-events/filters')
      if (res) {
        setCategories(res.categories || [])
        setAdverseReactions(res.adverseReactions || [])
      }
    } catch (error) {
      console.error('Error loading filters:', error)
    }
  }

  const loadInjuryEvents = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      if (category && category !== '全部') params.category = category
      if (adverseReactionType && adverseReactionType !== '全部') params.adverse_reaction_type = adverseReactionType

      const res = await http.get<any, any>('/dashboard/injury-events', { params })
      if (res?.items) {
        setEvents(res.items)
      }
    } catch (error) {
      console.error('Error loading injury events:', error)
    } finally {
      setLoading(false)
    }
  }, [dateFrom, dateTo, category, adverseReactionType])

  const handleSearch = () => { loadInjuryEvents() }
  const handleReset = () => {
    setDateFrom('')
    setDateTo('')
    setCategory('全部')
    setAdverseReactionType('全部')
    setTimeout(() => loadInjuryEvents(), 0)
  }

  const handleViewRiskAssessment = (event: InjuryEvent) => {
    onNavigateToRiskMatrix(event.productId, event.adverseReactionId)
  }

  // SVG bubble chart data
  const chartWidth = 480
  const chartHeight = 400
  const margin = { top: 30, right: 40, bottom: 50, left: 60 }
  const innerW = chartWidth - margin.left - margin.right
  const innerH = chartHeight - margin.top - margin.bottom

  // Log scale helpers
  const prrValues = events.map(e => e.prr).filter(v => v > 0)
  const chiValues = events.map(e => e.chiSquare).filter(v => v > 0)
  const prrMin = prrValues.length > 0 ? Math.max(0.1, Math.min(...prrValues) * 0.5) : 0.1
  const prrMax = prrValues.length > 0 ? Math.max(...prrValues) * 1.5 : 100
  const chiMin = chiValues.length > 0 ? Math.max(0.1, Math.min(...chiValues) * 0.5) : 0.1
  const chiMax = chiValues.length > 0 ? Math.max(...chiValues) * 1.5 : 1000

  const logScale = (val: number, min: number, max: number, rangeSize: number) => {
    if (val <= 0) val = min
    const logMin = Math.log10(Math.max(min, 0.01))
    const logMax = Math.log10(Math.max(max, 0.02))
    if (logMax === logMin) return rangeSize / 2
    return ((Math.log10(val) - logMin) / (logMax - logMin)) * rangeSize
  }

  const eventCounts = events.map(e => e.eventCount)
  const maxEvents = Math.max(...eventCounts, 1)
  
  // Get bubble radius based on event count (fixed pixel values)
  const getBubbleRadius = (count: number) => {
    if (count >= 100) return 20  // w-5 h-5 equivalent
    if (count >= 50) return 16    // w-4 h-4 equivalent
    if (count >= 10) return 12    // w-3 h-3 equivalent
    if (count >= 5) return 8     // w-2 h-2 equivalent
    return 4                      // w-1 h-1 equivalent
  }
  
  // Generate tick marks for log scale
  const getLogTicks = (min: number, max: number, axis: 'x' | 'y') => {
  // X轴：只显示 0.1, 1, 2
  if (axis === 'x') {
    return [1, 2];
  }
  // Y轴：只显示 0.1, 4
  if (axis === 'y') {
    return [0.1, 4];
  }
  return [];
};

  const prrTicks = getLogTicks(prrMin, prrMax, 'x')
  const chiTicks = getLogTicks(chiMin, chiMax, 'y')

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          返回总览
        </Button>
        <h1 className="text-xl font-bold">伤害事件筛查</h1>
      </div>

      {/* Filter bar */}
      <Card>
        <CardContent className="py-3 px-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground whitespace-nowrap">日期范围</span>
              <Input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="w-36 h-8" />
              <span className="text-sm text-muted-foreground">至</span>
              <Input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="w-36 h-8" />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground whitespace-nowrap">产品类别</span>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="w-32 h-8"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="全部">全部</SelectItem>
                  {categories.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground whitespace-nowrap">不良反应类型</span>
              <Select value={adverseReactionType} onValueChange={setAdverseReactionType}>
                <SelectTrigger className="w-32 h-8"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="全部">全部</SelectItem>
                  {adverseReactions.map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button size="sm" onClick={handleSearch} className="h-8">
              <Search className="h-3 w-3 mr-1" /> 查询
            </Button>
            <Button size="sm" variant="outline" onClick={handleReset} className="h-8">
              <RotateCcw className="h-3 w-3 mr-1" /> 重置
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Main content: Table + Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Table (3/5 width) */}
        <Card className="lg:col-span-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-blue-700">组合信号筛查结果</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <Skeleton className="h-80 mx-4 mb-4" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/30">
                      <th className="text-left py-2.5 px-3 font-semibold text-blue-700">产品</th>
                      <th className="text-left py-2.5 px-3 font-semibold text-blue-700">不良反应</th>
                      <th className="text-center py-2.5 px-3 font-semibold text-blue-700">事件数</th>
                      <th className="text-center py-2.5 px-3 font-semibold text-blue-700">PRR</th>
                      <th className="text-center py-2.5 px-3 font-semibold text-blue-700">χ²</th>
                      <th className="text-center py-2.5 px-3 font-semibold text-blue-700">信号等级</th>
                      <th className="text-center py-2.5 px-3 font-semibold text-blue-700">风险评估</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.length === 0 ? (
                      <tr><td colSpan={7} className="text-center py-8 text-muted-foreground">暂无数据</td></tr>
                    ) : (
                      events.map((event) => (
                        <tr 
                          key={event.id} 
                          className={cn(
                            "border-b hover:bg-blue-50/50 transition-colors",
                            event.hasRiskAssessment && "cursor-pointer",
                            selectedEventId === event.id && "bg-blue-50"
                          )}
                          onClick={() => {
                            setSelectedEventId(event.id)
                            if (event.hasRiskAssessment) {
                              handleViewRiskAssessment(event)
                            }
                          }}
                        >
                          <td className="py-2.5 px-3 font-medium">{event.productName}</td>
                          <td className="py-2.5 px-3">{event.adverseReactionName}</td>
                          <td className="py-2.5 px-3 text-center font-mono">{event.eventCount.toLocaleString()}</td>
                          <td className="py-2.5 px-3 text-center font-mono">{event.prr.toFixed(2)}</td>
                          <td className="py-2.5 px-3 text-center font-mono">{event.chiSquare.toFixed(2)}</td>
                          <td className="py-2.5 px-3 text-center">
                            <span className={cn(
                              "inline-block px-2.5 py-0.5 rounded text-xs font-bold",
                              signalLevelMap[event.signalLevel].color
                            )}>
                              {signalLevelMap[event.signalLevel].label}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            {event.hasRiskAssessment ? (
                              <Button
                                size="sm"
                                className="bg-blue-600 hover:bg-blue-700 text-white h-7 px-3"
                                onClick={(e) => { e.stopPropagation(); handleViewRiskAssessment(event) }}
                              >
                                查看
                              </Button>
                            ) : (
                              <span className="text-muted-foreground text-xs">无数据</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
                <div className="px-3 py-2 text-xs text-muted-foreground border-t">
                  注：PRR（比例报告比），χ²（卡方值）；信号等级依据PRR与χ²综合评估。
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* PRR-χ² Bubble Scatter Plot (2/5 width) */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-blue-700">PRR-χ² 信号分布图</CardTitle>
          </CardHeader>
          <CardContent>
            {events.length === 0 ? (
              <div className="h-80 flex items-center justify-center text-muted-foreground">暂无数据</div>
            ) : events.length < 3 ? (
              <div className="h-80 flex items-center justify-center text-muted-foreground">数据量不足，至少需要3条数据</div>
            ) : (
              <div className="flex items-start gap-6">
                {/* 散点图 */}
                <div className="flex-1 mt-8">
                  <svg width={chartWidth} height={chartHeight} className="overflow-visible">
                    <g transform={`translate(${margin.left},${margin.top})`}>
                      {/* Grid lines */}
                      

                      {/* PRR=2 reference line */}
                      {(() => {
                        const x = logScale(2, prrMin, prrMax, innerW)
                        return <line x1={x} y1={0} x2={x} y2={innerH} stroke="#9CA3AF" strokeDasharray="6,3" strokeWidth={1.5} />
                      })()}

                      {/* PRR=1 reference line */}
                      {(() => {
                        const x = logScale(1, prrMin, prrMax, innerW)
                        return <line x1={x} y1={0} x2={x} y2={innerH} stroke="#9CA3AF" strokeDasharray="6,3" strokeWidth={1.5} />
                      })()}
                      {/* χ²=4 reference line */}
                      {(() => {
                        const y = innerH - logScale(4, chiMin, chiMax, innerH)
                        return <line x1={0} y1={y} x2={innerW} y2={y} stroke="#9CA3AF" strokeDasharray="6,3" strokeWidth={1.5} />
                      })()}

                      {/* Axes */}
                      <line x1={0} y1={innerH} x2={innerW} y2={innerH} stroke="#374151" />
                      <line x1={0} y1={0} x2={0} y2={innerH} stroke="#374151" />

                      {/* X ticks */}
                      {prrTicks.map(tick => {
                        const x = logScale(tick, prrMin, prrMax, innerW)
                        return (
                          <g key={`xt-${tick}`}>
                            <line x1={x} y1={innerH} x2={x} y2={innerH + 4} stroke="#374151" />
                            <text x={x} y={innerH + 16} textAnchor="middle" fontSize={11} fill="#6B7280">{tick}</text>
                          </g>
                        )
                      })}

                      {/* Y ticks */}
                      {chiTicks.map(tick => {
                        const y = innerH - logScale(tick, chiMin, chiMax, innerH)
                        return (
                          <g key={`yt-${tick}`}>
                            <line x1={-4} y1={y} x2={0} y2={y} stroke="#374151" />
                            <text x={-8} y={y + 4} textAnchor="end" fontSize={11} fill="#6B7280">{tick}</text>
                          </g>
                        )
                      })}

                      {/* Axis labels */}
                      <text x={innerW / 2} y={innerH + 38} textAnchor="middle" fontSize={12} fill="#374151" fontWeight="bold">PRR（对数刻度）</text>
                      <text x={-innerH / 2} y={-42} textAnchor="middle" fontSize={12} fill="#374151" fontWeight="bold" transform="rotate(-90)">χ²（对数刻度）</text>

                      {/* Bubbles */}
                      {events.filter(event => event.eventCount >= 3).map(event => {
                        const cx = logScale(Math.max(event.prr, 0.1), prrMin, prrMax, innerW)
                        const cy = innerH - logScale(Math.max(event.chiSquare, 0.1), chiMin, chiMax, innerH)
                        const r = getBubbleRadius(event.eventCount)
                        const color = signalLevelMap[event.signalLevel].dotColor
                        const isSelected = selectedEventId === event.id
                        return (
                          <g key={event.id} className="cursor-pointer" onClick={() => {
                            setSelectedEventId(event.id)
                            if (event.hasRiskAssessment) {
                              handleViewRiskAssessment(event)
                            }
                          }}>
                            <circle
                              cx={cx} cy={cy} r={r}
                              fill={color} fillOpacity={0.7}
                              stroke={isSelected ? '#1D4ED8' : color}
                              strokeWidth={isSelected ? 3 : 1.5}
                            />
                            <title>{`${event.productName} - ${event.adverseReactionName}\nPRR: ${event.prr}\nχ²: ${event.chiSquare}\n事件数: ${event.eventCount}`}</title>
                          </g>
                        )
                      })}
                    </g>
                  </svg>
                  <div className="text-xs text-muted-foreground mt-2">
                    说明：点的大小表示事件数，颜色表示信号等级。
                  </div>
                </div>

                {/* 右侧图例 */}
                <div className="flex flex-col gap-6 pt-20 -ml-10">
                  {/* 信号等级 */}
                  <div>
                    <div className="text-sm font-semibold text-gray-700 mb-4">信号等级</div>
                    <div className="space-y-2 ml-5">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: '#F35B58' }} />
                        <span className="text-sm text-gray-600">高</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: '#F9BE55' }} />
                        <span className="text-sm text-gray-600">中</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: '#73A0F5' }} />
                        <span className="text-sm text-gray-600">低</span>
                      </div>
                    </div>
                  </div>

                  {/* 事件数（气泡大小） */}
                  <div>
                    <div className="text-sm font-semibold text-gray-700 mb-4">事件数（气泡大小）</div>
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <div className="w-10 flex justify-center">
                          <span className="w-2 h-2 rounded-full bg-gray-400 inline-block" />
                        </div>
                        <span className="text-sm text-gray-600">5</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-10 flex justify-center">
                          <span className="w-3 h-3 rounded-full bg-gray-400 inline-block" />
                        </div>
                        <span className="text-sm text-gray-600">10</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-10 flex justify-center">
                          <span className="w-4 h-4 rounded-full bg-gray-400 inline-block" />
                        </div>
                        <span className="text-sm text-gray-600">50</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-10 flex justify-center">
                          <span className="w-5 h-5 rounded-full bg-gray-400 inline-block" />
                        </div>
                        <span className="text-sm text-gray-600">100</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
