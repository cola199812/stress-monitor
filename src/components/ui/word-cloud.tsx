"use client"

import { useEffect, useState } from 'react'
import ReactEChartsCore from 'echarts-for-react'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { TooltipComponent } from 'echarts/components'

echarts.use([CanvasRenderer, TooltipComponent])

type Word = { name: string; value: number }

export function WordCloud({ items }: { items: Word[] }) {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      if (typeof window === 'undefined') return
      try {
        await import('echarts-wordcloud')
      } catch {}
      if (mounted) setReady(true)
    })()
    return () => { mounted = false }
  }, [])

  const option = {
    tooltip: {},
    series: [
      {
        type: 'wordCloud',
        gridSize: 8,
        sizeRange: [14, 40],
        rotationRange: [-45, 90],
        shape: 'circle',
        textStyle: {
          color: () => {
            const hue = 200 + Math.round(Math.random() * 60)
            return `hsl(${hue} 80% 50%)`
          },
        },
        emphasis: {
          textStyle: {
            shadowBlur: 8,
            shadowColor: 'rgba(0,0,0,0.3)'
          }
        },
        data: items,
      }
    ]
  }

  if (!ready) {
    return <div style={{ height: 320, width: '100%' }} />
  }

  return (
    <ReactEChartsCore
      echarts={echarts as any}
      option={option as any}
      style={{ height: 320, width: '100%' }}
      notMerge
      lazyUpdate
    />
  )
}

