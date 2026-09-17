"use client"

import Link from "next/link"
import { useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"
import { matchModule } from "@/lib/nav"
import { cn } from "@/lib/utils"

export function ModuleTabs() {
  const pathname = usePathname()
  const router = useRouter()
  const mod = matchModule(pathname)
  if (!mod) return null

  const current = mod.children.find((p) => p.href === pathname)?.href

  // 渲染后根据路径做重定向，避免在 render 阶段产生副作用
  useEffect(() => {
    if (pathname === mod.basePath && mod.defaultRoute) {
      router.replace(mod.defaultRoute)
    }
  }, [pathname, mod.basePath, mod.defaultRoute, router])

  return (
    <div className="flex items-center gap-[var(--space-xs)]">
      {mod.children.map((p) => (
        <Link key={p.href} href={p.href} prefetch>
          <span
            className={cn(
              "px-[var(--space-sm)] py-1.5 text-[length:var(--font-size-sm)] rounded-full cursor-pointer",
              current === p.href ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"
            )}
          >
            {p.label}
          </span>
        </Link>
      ))}
    </div>
  )
}


