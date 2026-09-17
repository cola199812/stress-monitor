"use client"

import { useEffect } from "react"
import { usePathname } from "next/navigation"
import { useProductStore } from "@/store/useProductStore"

export function RouteFeatureSync() {
  const pathname = usePathname()
  const { setFeatureName, header } = useProductStore()

  useEffect(() => {
    // 基于路径精确设定功能名，避免跨组误判
    let name = ''
    if (pathname?.startsWith('/collect/literature')) name = '文献采集'
    else if (pathname?.startsWith('/collect/toxicity')) name = '毒性数据采集'
    else if (pathname?.startsWith('/collect/news')) name = '新闻采集'
    else if (pathname?.startsWith('/collect/recall')) name = '召回采集'
    else if (pathname?.startsWith('/collect')) name = '数据采集'
    else if (pathname?.startsWith('/opinion')) name = '舆情分析'
    else if (pathname === '/dashboard') name = '数据看板'
    else if (pathname === '/qa') name = '知识问答'

    if (name && header && header.featureName !== name) {
      setFeatureName(name)
    }
  }, [pathname, setFeatureName, header])

  return null
}


