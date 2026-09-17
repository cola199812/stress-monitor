"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useEffect, useState, useRef, useMemo, useCallback } from "react"
import http from "@/lib/http"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowLeft, BookOpen, Lightbulb, Star } from "lucide-react"
import { cn } from "@/lib/utils"

interface RiskMatrixResultProps {
  productId: number
  adverseReactionId: number
  onBack: () => void
}

interface ChemicalStressorRisk {
  id: number
  nameCn: string
  cas: string
  xScore: number
  xRaw: number
  yScore: number
  yRaw: number
  zScore: number
  totalScore: number
  allScore: number
  riskLevel: 'low' | 'medium' | 'high'
  evidenceSufficiency: number
  evidenceCount: number
}

interface RiskMatrixData {
  productName: string
  adverseReactionName: string
  prr: number
  chiSquare: number
  signalLevel: string
  signalScore: number
  chemicalStressors: ChemicalStressorRisk[]
  recommendations: {
    sameLevelExplanation: string
    followUpSuggestions: string[]
  }
}

const riskLevelConfig = {
  low: { label: '低风险', color: 'bg-green-500 text-white' },
  medium: { label: '中等风险', color: 'bg-orange-400 text-white' },
  high: { label: '高风险', color: 'bg-red-500 text-white' },
}

export default function RiskMatrixResult({ productId, adverseReactionId, onBack }: RiskMatrixResultProps) {
  const [data, setData] = useState<RiskMatrixData | null>(null)
  const [loading, setLoading] = useState(true)

  // 3D rotation state
  const initialRotation = { x: -40, y: -40, z: -30 }
  const [rotation, setRotation] = useState(initialRotation)
  const [zoom, setZoom] = useState(1)
  const dragRef = useRef({ dragging: false, lastX: 0, lastY: 0 })

  useEffect(() => {
    loadRiskMatrixData()
  }, [productId, adverseReactionId])

  const loadRiskMatrixData = async () => {
    setLoading(true)
    try {
      const res = await http.get<any, any>(`/dashboard/risk-matrix/${productId}/${adverseReactionId}`)
      if (res) {
        setData(res)
      }
    } catch (error) {
      console.error('Error loading risk matrix data:', error)
    } finally {
      setLoading(false)
    }
  }

  const renderStars = (count: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <Star key={i} className={cn("h-3.5 w-3.5", i < count ? "fill-orange-400 text-orange-400" : "text-gray-300")} />
    ))
  }

  // 3D helpers
  const degToRad = (deg: number) => (deg * Math.PI) / 180
  const svgW = 700, svgH = 520
  const center3d = { x: 200, y: 320 }
  const unit3d = 72
  const perspective3d = 1100
  const levelLabels: Record<number, string> = { 1: '低（1）', 2: '中（2）', 3: '高（3）' }

  const rotatePoint = useCallback((point: { x: number; y: number; z: number }) => {
    let { x, y, z } = point
    const rx = degToRad(rotation.x), ry = degToRad(rotation.y), rz = degToRad(rotation.z)
    // X
    const y1 = y * Math.cos(rx) - z * Math.sin(rx)
    const z1 = y * Math.sin(rx) + z * Math.cos(rx)
    y = y1; z = z1
    // Y
    const x2 = x * Math.cos(ry) + z * Math.sin(ry)
    const z2 = -x * Math.sin(ry) + z * Math.cos(ry)
    x = x2; z = z2
    // Z
    const x3 = x * Math.cos(rz) - y * Math.sin(rz)
    const y3 = x * Math.sin(rz) + y * Math.cos(rz)
    x = x3; y = y3
    return { x, y, z }
  }, [rotation])

  const project3d = useCallback((point: { x: number; y: number; z: number }) => {
    const rotated = rotatePoint(point)
    const scale = perspective3d / (perspective3d - rotated.z * unit3d * zoom)
    return {
      x: center3d.x + rotated.x * unit3d * zoom * scale,
      y: center3d.y - rotated.y * unit3d * zoom * scale,
      z: rotated.z,
      scale,
    }
  }, [rotatePoint, zoom])

  // Pointer handlers for drag rotation
  const onPointerDown = useCallback((e: React.PointerEvent) => {
    dragRef.current = { dragging: true, lastX: e.clientX, lastY: e.clientY }
    e.currentTarget.setPointerCapture(e.pointerId)
  }, [])

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragRef.current.dragging) return
    const dx = e.clientX - dragRef.current.lastX
    const dy = e.clientY - dragRef.current.lastY
    dragRef.current.lastX = e.clientX
    dragRef.current.lastY = e.clientY
    setRotation(prev => ({
      ...prev,
      y: prev.y + dx * 0.55,
      x: Math.max(-84, Math.min(84, prev.x - dy * 0.55)),
    }))
  }, [])

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    dragRef.current.dragging = false
    try { e.currentTarget.releasePointerCapture(e.pointerId) } catch {}
  }, [])

  const onWheel3d = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    setZoom(prev => Math.max(0.62, Math.min(1.65, prev - e.deltaY * 0.001)))
  }, [])

  const resetView = useCallback(() => {
    setRotation(initialRotation)
    setZoom(1)
  }, [])

  // Build 3D content with depth sorting
  const cube3dContent = useMemo(() => {
    if (!data || data.chemicalStressors.length === 0) return null

    // Determine which cells contain stressors for highlighting
    const stressorCells = new Set<string>()
    data.chemicalStressors.forEach(cs => {
      stressorCells.add(`${cs.xScore}-${cs.yScore}-${cs.zScore}`)
    })

    const getRiskClass = (x: number, y: number, z: number) => {
      const score = x * y * z
      if (score >= 18) return 'high'
      if (score >= 8) return 'medium'
      return 'low'
    }

    const riskColors = {
      low: { normal: 'rgba(147,197,253,0.10)', highlight: 'rgba(96,165,250,0.72)', stroke: '#60a5fa' },
      medium: { normal: 'rgba(250,204,21,0.10)', highlight: 'rgba(250,204,21,0.72)', stroke: '#ca8a04' },
      high: { normal: 'rgba(248,113,113,0.10)', highlight: 'rgba(248,113,113,0.72)', stroke: '#dc2626' },
    }

    type FaceItem = { avgDepth: number; node: React.ReactNode }
    const faces: FaceItem[] = []

    // 27 cell faces
    for (let x = 1; x <= 3; x++) {
      for (let y = 1; y <= 3; y++) {
        for (let z = 1; z <= 3; z++) {
          const x0 = x - 1, x1a = x, y0 = y - 1, y1a = y, z0 = z - 1, z1a = z
          const risk = getRiskClass(x, y, z)
          const isHighlighted = stressorCells.has(`${x}-${y}-${z}`)
          const fill = isHighlighted ? riskColors[risk].highlight : riskColors[risk].normal
          const strokeColor = 'transparent'
          const strokeW = 0
          const kp = `cell-${x}-${y}-${z}`

          const faceDefs: [{ x: number; y: number; z: number }[], string][] = [
            [[{ x: x0, y: y0, z: z1a }, { x: x1a, y: y0, z: z1a }, { x: x1a, y: y1a, z: z1a }, { x: x0, y: y1a, z: z1a }], 'top'],
            [[{ x: x0, y: y0, z: z0 }, { x: x1a, y: y0, z: z0 }, { x: x1a, y: y1a, z: z0 }, { x: x0, y: y1a, z: z0 }], 'bot'],
            [[{ x: x0, y: y0, z: z0 }, { x: x1a, y: y0, z: z0 }, { x: x1a, y: y0, z: z1a }, { x: x0, y: y0, z: z1a }], 'front'],
            [[{ x: x0, y: y1a, z: z0 }, { x: x1a, y: y1a, z: z0 }, { x: x1a, y: y1a, z: z1a }, { x: x0, y: y1a, z: z1a }], 'back'],
            [[{ x: x0, y: y0, z: z0 }, { x: x0, y: y1a, z: z0 }, { x: x0, y: y1a, z: z1a }, { x: x0, y: y0, z: z1a }], 'left'],
            [[{ x: x1a, y: y0, z: z0 }, { x: x1a, y: y1a, z: z0 }, { x: x1a, y: y1a, z: z1a }, { x: x1a, y: y0, z: z1a }], 'right'],
          ]

          faceDefs.forEach(([pts, faceName]) => {
            const projected = pts.map(p => project3d(p))
            const avgDepth = projected.reduce((s, p) => s + p.z, 0) / projected.length
            const polyPts = projected.map(p => `${p.x},${p.y}`).join(' ')
            faces.push({
              avgDepth,
              node: <polygon key={`${kp}-${faceName}`} points={polyPts} fill={fill} stroke={strokeColor} strokeWidth={strokeW} />
            })
          })
        }
      }
    }

    faces.sort((a, b) => a.avgDepth - b.avgDepth)

    // Grid lines
    const gridLineElems: React.ReactNode[] = []
    const mkLine = (s: { x: number; y: number; z: number }, e: { x: number; y: number; z: number }, cls: string, k: string) => {
      const p1 = project3d(s), p2 = project3d(e)
      return <line key={k} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke={cls === 'grid' ? 'rgba(37,99,235,0.36)' : '#2563eb'}
        strokeWidth={cls === 'grid' ? 1.25 : 2.6} />
    }
    // for (let i = 1; i <= 2; i++) {
    //   gridLineElems.push(
    //     mkLine({ x: i, y: 0, z: 0 }, { x: i, y: 3, z: 0 }, 'grid', `g-bx-${i}`),
    //     mkLine({ x: 0, y: i, z: 0 }, { x: 3, y: i, z: 0 }, 'grid', `g-by-${i}`),
    //     mkLine({ x: i, y: 0, z: 3 }, { x: i, y: 3, z: 3 }, 'grid', `g-tx-${i}`),
    //     mkLine({ x: 0, y: i, z: 3 }, { x: 3, y: i, z: 3 }, 'grid', `g-ty-${i}`),
    //     mkLine({ x: i, y: 0, z: 0 }, { x: i, y: 0, z: 3 }, 'grid', `g-fx-${i}`),
    //     mkLine({ x: 0, y: 0, z: i }, { x: 3, y: 0, z: i }, 'grid', `g-fz-${i}`),
    //     mkLine({ x: 3, y: i, z: 0 }, { x: 3, y: i, z: 3 }, 'grid', `g-ry-${i}`),
    //     mkLine({ x: 3, y: 0, z: i }, { x: 3, y: 3, z: i }, 'grid', `g-rz-${i}`),
    //   )
    // }

    // Outer edges
    const corners: [number, number, number][] = [
      [0,0,0],[3,0,0],[3,3,0],[0,3,0],[0,0,3],[3,0,3],[3,3,3],[0,3,3],
    ]
    const edgeIdx = [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]]
    const outerEdges = edgeIdx.map(([a, b], idx) => {
      const c1 = corners[a], c2 = corners[b]
      return mkLine({ x: c1[0], y: c1[1], z: c1[2] }, { x: c2[0], y: c2[1], z: c2[2] }, 'edge', `oe-${idx}`)
    })

    // Axes with arrows
    const mkText = (pt: { x: number; y: number; z: number }, text: string, dx: number, dy: number,
      anchor: string, fontSize: number, fontWeight: number, fill: string, key: string) => {
      const p = project3d(pt)
      return <text key={key} x={p.x + dx} y={p.y + dy} textAnchor={anchor}
        fontSize={fontSize} fontWeight={fontWeight} fill={fill}>{text}</text>
    }

    const axisElems: React.ReactNode[] = []
    // X axis
    const axX1 = project3d({ x: -0.15, y: -0.38, z: 0 }), axX2 = project3d({ x: 3.55, y: -0.38, z: 0 })
    axisElems.push(<line key="ax-x" x1={axX1.x} y1={axX1.y} x2={axX2.x} y2={axX2.y}
      stroke="#2563eb" strokeWidth={3} markerEnd="url(#rm-arrow)" />)
    // Y axis
    const axY1 = project3d({ x: 3.18, y: -0.18, z: 0 }), axY2 = project3d({ x: 3.18, y: 3.58, z: 0 })
    axisElems.push(<line key="ax-y" x1={axY1.x} y1={axY1.y} x2={axY2.x} y2={axY2.y}
      stroke="#2563eb" strokeWidth={3} markerEnd="url(#rm-arrow)" />)
    // Z axis
    const axZ1 = project3d({ x: -0.38, y: -0.18, z: 0 }), axZ2 = project3d({ x: -0.38, y: -0.18, z: 3.55 })
    axisElems.push(<line key="ax-z" x1={axZ1.x} y1={axZ1.y} x2={axZ2.x} y2={axZ2.y}
      stroke="#2563eb" strokeWidth={3} markerEnd="url(#rm-arrow)" />)

    // Tick labels
    const tickElems: React.ReactNode[] = []
    for (let i = 1; i <= 3; i++) {
      tickElems.push(
        mkText({ x: i - 0.5, y: -0.55, z: 0 }, levelLabels[i], 0, 28, 'middle', 13, 700, '#334155', `tx-${i}`),
        mkText({ x: 3.35, y: i - 0.5, z: 0 }, levelLabels[i], 18, 6, 'start', 13, 700, '#334155', `ty-${i}`),
        mkText({ x: -0.55, y: -0.18, z: i - 0.5 }, levelLabels[i], -16, 6, 'end', 13, 700, '#334155', `tz-${i}`),
      )
    }

    // Axis labels
    tickElems.push(
      mkText({ x: 1.65, y: -0.9, z: 0 }, 'X 暴露潜势', 0, 56, 'middle', 15, 800, '#1d4ed8', 'al-x'),
      mkText({ x: 3.35, y: 3.7, z: 0 }, 'Y 伤害风险', 36, 6, 'start', 15, 800, '#1d4ed8', 'al-y'),
      mkText({ x: -0.48, y: -0.18, z: 3.72 }, 'Z 事件信号', -8, -16, 'end', 15, 800, '#1d4ed8', 'al-z'),
    )

    // Data points - group by position for overlap handling
    const posGroups: Record<string, ChemicalStressorRisk[]> = {}
    data.chemicalStressors.forEach(cs => {
      const key = `${cs.xScore}-${cs.yScore}-${cs.zScore}`
      if (!posGroups[key]) posGroups[key] = []
      posGroups[key].push(cs)
    })

    const pointColors = ['#111827', '#1E40AF', '#059669', '#D97706', '#DC2626']

    const getPointOffset = (cs: ChemicalStressorRisk) => {
      const key = `${cs.xScore}-${cs.yScore}-${cs.zScore}`
      const group = posGroups[key]
      if (group.length <= 1) return 0
      const sorted = [...group].sort((a, b) => (b.allScore || 0) - (a.allScore || 0))
      const posInGroup = sorted.findIndex(s => s.id === cs.id)
      return (posInGroup - (sorted.length - 1) / 2) * 18
    }

    const stressorPoints = data.chemicalStressors.map((cs, idx) => {
      const offY = getPointOffset(cs)
      const pt = project3d({ x: cs.xScore - 0.5, y: cs.yScore - 0.5, z: cs.zScore - 0.5 })
      
      // 判断是否在蓝色方块（低风险）中：totalScore 1-6
      const isInBlueCell = cs.totalScore >= 1 && cs.totalScore <= 6
      const textX = isInBlueCell ? pt.x - 12 : pt.x + 12
      const textAnchor = isInBlueCell ? 'end' : 'start'
      
      return (
        <g key={`pt-${cs.id}`}>
          <circle cx={pt.x} cy={pt.y + offY} r={6} fill={pointColors[idx % pointColors.length]} />
          <text x={textX} y={pt.y + 5 + offY} textAnchor={textAnchor} fontSize={12} fontWeight={700} fill="#1f2937">
            {cs.nameCn}
          </text>
        </g>
      )
    })

    const pointLines = data.chemicalStressors.slice(0, -1).map((cs, idx) => {
      const next = data.chemicalStressors[idx + 1]
      const p1 = project3d({ x: cs.xScore - 0.5, y: cs.yScore - 0.5, z: cs.zScore - 0.5 })
      const p2 = project3d({ x: next.xScore - 0.5, y: next.yScore - 0.5, z: next.zScore - 0.5 })
      return <line key={`pl-${idx}`} x1={p1.x} y1={p1.y + getPointOffset(cs)} x2={p2.x} y2={p2.y + getPointOffset(next)} stroke="#111827" strokeWidth={1.5} />
    })

    return { faces, gridLineElems, outerEdges, axisElems, tickElems, stressorPoints, pointLines }
  }, [data, project3d])

  // 3D Risk Matrix render
  const renderCube = () => {
    if (!cube3dContent) return null
    const { faces, gridLineElems, outerEdges, axisElems, tickElems, stressorPoints, pointLines } = cube3dContent

    return (
      <div className="w-full">
        <svg
          viewBox={`0 0 ${svgW} ${svgH}`}
          className="w-full h-auto"
          style={{ cursor: 'grab', userSelect: 'none', touchAction: 'none' }}
          role="img"
          aria-label="可拖动旋转的三维风险矩阵"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onDoubleClick={resetView}
          onWheel={onWheel3d}
        >
          <defs>
            <marker id="rm-arrow" markerWidth="14" markerHeight="14" refX="11" refY="7" orient="auto" markerUnits="strokeWidth">
              <path d="M2,2 L12,7 L2,12 Z" fill="#2563eb" />
            </marker>
          </defs>

          {faces.map(f => f.node)}
          {gridLineElems}
          {/* {outerEdges} */}
          {axisElems}
          {tickElems}
          {stressorPoints}

          {/* Legend */}
          <g transform={`translate(${svgW - 180}, ${svgH - 110})`}>
            <rect x="0" y="0" width="16" height="16" fill="rgba(96,165,250,0.65)" stroke="#60a5fa" strokeWidth={1.5} rx={2} />
            <text x="24" y="13" fontSize={12} fill="#334155" fontWeight={700}>1-6：低风险</text>
            <rect x="0" y="26" width="16" height="16" fill="rgba(250,204,21,0.65)" stroke="#ca8a04" strokeWidth={1.5} rx={2} />
            <text x="24" y="39" fontSize={12} fill="#334155" fontWeight={700}>8-12：中风险</text>
            <rect x="0" y="52" width="16" height="16" fill="rgba(248,113,113,0.65)" stroke="#dc2626" strokeWidth={1.5} rx={2} />
            <text x="24" y="65" fontSize={12} fill="#334155" fontWeight={700}>18-27：高风险</text>
          </g>
        </svg>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (!data) {
    return <div className="text-center py-16 text-muted-foreground">数据加载失败</div>
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          返回筛查
        </Button>
        <div>
          <h1 className="text-xl font-bold">风险评估结果</h1>
        </div>
      </div>

      {/* Top section: Table + 3D Cube */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Scoring Table */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-blue-700">{data.productName} × {data.adverseReactionName} | PRR: {data.prr} | χ²: {data.chiSquare}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/30">
                    <th className="text-left py-2.5 px-3 font-semibold text-blue-700">化学应激源</th>
                    <th className="text-center py-2.5 px-3 font-semibold text-blue-700">X轴暴露潜势</th>
                    <th className="text-center py-2.5 px-3 font-semibold text-blue-700">Y轴伤害风险</th>
                    <th className="text-center py-2.5 px-3 font-semibold text-blue-700">Z轴事件信号</th>
                    <th className="text-center py-2.5 px-3 font-semibold text-blue-700">综合得分<br/><span className="font-normal text-xs">(1-27)</span></th>
                    <th className="text-center py-2.5 px-3 font-semibold text-blue-700">风险等级</th>
                  </tr>
                </thead>
                <tbody>
                  {data.chemicalStressors.length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-8 text-muted-foreground">暂无化学应激源数据</td></tr>
                  ) : (
                    data.chemicalStressors.map((cs) => (
                      <tr key={cs.id} className="border-b hover:bg-blue-50/50 transition-colors">
                        <td className="py-3 px-3">
                          <div className="font-medium">{cs.nameCn}</div>
                          <div className="text-xs text-muted-foreground mt-0.5">CAS: {cs.cas || 'N/A'}</div>
                        </td>
                        <td className="py-3 px-3 text-center font-mono">
                          {cs.xScore} ({cs.xRaw > 0 ? cs.xRaw : '0'})
                        </td>
                        <td className="py-3 px-3 text-center font-mono">
                          {cs.yScore} ({cs.yRaw > 0 ? cs.yRaw.toFixed(2) : '0'})
                        </td>
                        <td className="py-3 px-3 text-center font-mono">{cs.zScore}</td>
                        <td className="py-3 px-3 text-center font-bold">
                          {(cs.totalScore).toFixed(2)} ({cs.allScore > 0 ? cs.allScore.toFixed(2) : '0'})
                        </td>
                        <td className="py-3 px-3 text-center">
                          <span className={cn(
                            "inline-block px-2.5 py-0.5 rounded text-xs font-bold",
                            riskLevelConfig[cs.riskLevel].color
                          )}>
                            {riskLevelConfig[cs.riskLevel].label}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* 3D Cube Visualization */}
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-base text-blue-700">
              三维风险矩阵 <span className="font-normal text-xs text-muted-foreground">(X-暴露潜势, Y-伤害风险, Z-事件信号)</span>
            </CardTitle>
            <Button variant="outline" size="sm" onClick={resetView} className="text-xs h-7">
              重置视角
            </Button>
          </CardHeader>
          <CardContent>
            {renderCube()}
          </CardContent>
        </Card>
      </div>

      {/* Bottom section: Explanation + Suggestions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 同等级解释 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-blue-600" />
              同等级解释
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm leading-relaxed whitespace-pre-line text-muted-foreground">
              {data.recommendations.sameLevelExplanation}
            </div>
          </CardContent>
        </Card>

        {/* 后续补充证据建议 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-orange-500" />
              后续补充证据建议
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-2 text-sm">
              {data.recommendations.followUpSuggestions.map((suggestion, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs flex items-center justify-center font-bold mt-0.5">
                    {idx + 1}
                  </span>
                  <span>{suggestion}</span>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
