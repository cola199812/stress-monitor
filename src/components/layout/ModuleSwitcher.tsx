"use client"

import { useMemo } from "react"
import { usePathname, useRouter } from "next/navigation"
import { navSchema, matchModule } from "@/lib/nav"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export function ModuleSwitcher() {
  const pathname = usePathname()
  const router = useRouter()
  const current = matchModule(pathname || "")

  const items = useMemo(() => navSchema.map(m => ({ label: m.label, value: m.defaultRoute })), [])
  const currentValue = current?.defaultRoute

  return (
    <div className="flex items-center gap-[var(--space-xs)]">
      {/* <Button size="sm" variant="outline" onClick={() => currentValue && router.push(currentValue)}>
        {current?.label ?? "选择模块"}
      </Button> */}
      <Select value={currentValue} onValueChange={(v) => router.push(v)}>
        <SelectTrigger className="h-8 w-32 text-[length:var(--font-size-md)] px-2">
          <SelectValue placeholder="切换模块" />
        </SelectTrigger>
        <SelectContent>
          {items.map(i => (
            <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}


