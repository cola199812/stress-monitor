"use client"

import { useEffect, useMemo, useState } from "react"
import { useProductStore } from "@/store/useProductStore"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Separator } from "@/components/ui/separator"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { navSchema, matchModule } from "@/lib/nav"
import { ThemeSwitcher } from "./theme-switcher"
import { Plus, MoreHorizontal, Edit2, Trash2, BarChart, FileText, MessageSquare } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function HeaderBar() {
  const { categories, products, header, setCategory, setProduct, setKeywordInput, rehydrateFromLocal, createCategory, updateCategory, deleteCategory, createProduct, updateProduct, deleteProduct, fetchAll } = useProductStore()
  const [open, setOpen] = useState(false)
  const pathname = usePathname()
  const router = useRouter()

  const productsByCat = useMemo(() => {
    const map: Record<string, typeof products> = {}
    products.forEach((p) => {
      map[p.categoryId] ||= []
      map[p.categoryId].push(p)
    })
    return map
  }, [products])

  useEffect(() => {
    // 客户端挂载后从本地恢复 UI 状态，然后拉取后端数据
    rehydrateFromLocal()
    fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 仅按当前模块预取，且同一模块只预取一次，避免高频预取
  // 在 effect 内安全读取 window，避免 SSR 阶段读取 undefined
  useEffect(() => {
    const mod = matchModule(pathname || "")
    if (!mod) return
    const w = typeof window !== 'undefined' ? (window as any) : null
    if (!w) return
    w.__prefetchedModuleRef = w.__prefetchedModuleRef || { current: undefined }
    const prefetchedModuleRef = w.__prefetchedModuleRef as { current?: string }
    if (prefetchedModuleRef.current === mod.id) return
    prefetchedModuleRef.current = mod.id
    const routes = [mod.defaultRoute, ...mod.children.map(c => c.href)].filter(Boolean) as string[]
    Array.from(new Set(routes)).forEach((r) => router.prefetch(r))
  }, [pathname, router])

  useEffect(() => {
    // 同步输入框显示
    setTempKeyword(header?.keywordInput || '')
  }, [header?.keywordInput])

  const [tempKeyword, setTempKeyword] = useState(header?.keywordInput || '')
  const saveKeyword = async () => {
    // 标准化拆分（支持 '、' '；' ';' ',' '，' '|' 空格）
    const split = (v: string) => {
      const replaced = (v || '').replace(/[、；;，,|\s]+/g, '\u0001')
      const arr = replaced.split('\u0001').map(s => s.trim()).filter(Boolean)
      return Array.from(new Set(arr.map(s => s.toLowerCase())))
    }

    const newArr = split(tempKeyword)
    const oldArr = split(header?.keywordInput || '')
    const same = newArr.length === oldArr.length && newArr.every((v, i) => v === oldArr[i])

    // 永远更新本地输入框状态
    setKeywordInput(tempKeyword)

    // 如果一致则不请求
    if (same) return

    // 不一致才调用后端：将标准化后的关键词按原始大小写无法还原，这里用去重后的原始分隔结果
    const originalSplit = (v: string) => {
      const replaced = (v || '').replace(/[、；;，,|\s]+/g, '\u0001')
      const arr = replaced.split('\u0001').map(s => s.trim()).filter(Boolean)
      return Array.from(new Set(arr))
    }
    const keywords = originalSplit(tempKeyword)

    // 需要产品 ID
    const prodId = header.product?.id
    if (!prodId) return

    try {
      await useProductStore.getState().updateProduct(prodId, { keywords })
    } catch (e) {
      // 静默处理错误('更新关键词失败', e)
    }
  }

  // 内联编辑状态
  const [editingCatId, setEditingCatId] = useState<string | null>(null)
  const [editingCatName, setEditingCatName] = useState("")
  const [isAddingCategory, setIsAddingCategory] = useState(false)
  const [newCategoryName, setNewCategoryName] = useState("")
  
  // 产品编辑状态
  const [editingProdId, setEditingProdId] = useState<string | null>(null)
  const [editingProdName, setEditingProdName] = useState("")
  const [isAddingProduct, setIsAddingProduct] = useState(false)
  const [newProductName, setNewProductName] = useState("")

  // 编辑功能
  const startEditCategory = (cat: any) => {
    setEditingCatId(cat.id)
    setEditingCatName(cat.name)
  }

  const saveEditCategory = async () => {
    if (!editingCatName.trim() || !editingCatId) return
    try {
      await updateCategory(editingCatId, editingCatName.trim())
      setEditingCatId(null)
      setEditingCatName("")
    } catch (error) {
      // 静默处理错误('更新类别失败:', error)
      // 失败时不关闭编辑状态，让用户重试
    }
  }

  const cancelEditCategory = () => {
    setEditingCatId(null)
    setEditingCatName("")
  }

  const handleDeleteCategory = async (catId: string) => {
    try {
      await deleteCategory(catId)
    } catch (error) {
      // 静默处理错误('删除类别失败:', error)
      // 删除失败的处理可以在这里添加提示
    }
  }

  const addNewCategory = async () => {
    const trimmed = newCategoryName.trim()
    if (!trimmed) {
      cancelAddCategory()
      return
    }
    try {
      await createCategory(trimmed)
      setIsAddingCategory(false)
      setNewCategoryName("")
    } catch (error) {
      // 静默处理错误('新增类别失败:', error)
      // 失败时不关闭新增状态，让用户重试
    }
  }

  const cancelAddCategory = () => {
    setIsAddingCategory(false)
    setNewCategoryName("")
  }

  // 产品编辑功能
  const startEditProduct = (prod: any) => {
    setEditingProdId(prod.id)
    setEditingProdName(prod.name)
  }

  const saveEditProduct = async () => {
    if (!editingProdName.trim() || !editingProdId) return
    try {
      await updateProduct(editingProdId, { name: editingProdName.trim() })
      setEditingProdId(null)
      setEditingProdName("")
    } catch (error) {
      // 静默处理错误('更新产品失败:', error)
      // 失败时不关闭编辑状态，让用户重试
    }
  }

  const cancelEditProduct = () => {
    setEditingProdId(null)
    setEditingProdName("")
  }

  const handleDeleteProduct = async (prodId: string) => {
    try {
      await deleteProduct(prodId)
    } catch (error) {
      // 静默处理错误('删除产品失败:', error)
      // 删除失败的处理可以在这里添加提示
    }
  }

  const addNewProduct = async () => {
    const trimmed = newProductName.trim()
    if (!trimmed) {
      cancelAddProduct()
      return
    }
    try {
      const categoryId = header?.category?.id || categories?.[0]?.id
      if (!categoryId) {
        // 静默处理错误('没有可用的类别')
        return
      }
      await createProduct({ categoryId, name: trimmed, keywords: [] })
      setIsAddingProduct(false)
      setNewProductName("")
    } catch (error) {
      // 静默处理错误('新增产品失败:', error)
      // 失败时不关闭新增状态，让用户重试
    }
  }

  const cancelAddProduct = () => {
    setIsAddingProduct(false)
    setNewProductName("")
  }

  return (
    <div className="w-full border-b bg-background/80 backdrop-blur-sm">
      <div className="container mx-auto h-14 flex items-center gap-10 px-[var(--space-sm)]">
        {/* 左侧：系统名称 */}
        <Link href="/" prefetch className="shrink-0 inline-flex items-center gap-2">
          <span className="text-[length:var(--font-size-xl)] font-[number:var(--font-weight-semibold)] bg-clip-text text-transparent bg-[linear-gradient(90deg,var(--grad-from),var(--grad-mid),var(--grad-to))]">
            化学应激源高关联伤害信息监测系统
          </span>
        </Link>

        {/* 中间：四个 Feature */}
        <nav className="ml-20 hidden md:flex items-center gap-10">
          <TopLink href="/qa" active={(pathname === "/") || (pathname?.startsWith && pathname.startsWith("/qa"))}> 
            <MessageSquare className="h-7 w-7" />
            <span>知识问答</span>
          </TopLink>
          <TopLink href="/dashboard" active={pathname?.startsWith && pathname.startsWith("/dashboard")}> 
            <BarChart className="h-7 w-7" />
            <span>数据看板</span>
          </TopLink>
          <TopLink href="/collect/literature" active={pathname?.startsWith && pathname.startsWith("/collect")}> 
            <FileText className="h-7 w-7" />
            <span>信息采集</span>
          </TopLink>
          <TopLink href="/info-management" active={pathname?.startsWith && pathname.startsWith("/info-management")}> 
            <BarChart className="h-7 w-7" />
            <span>信息管理</span>
          </TopLink>
        </nav>

        {/* 右侧：登录、注册 */}
        <div className="ml-10 hidden md:flex items-center gap-[var(--space-sm)]">
          <Button variant="ghost" className="h-7 text-[length:var(--font-size-lg)]">登录</Button>
          <Button className="h-7 text-[length:var(--font-size-lg)] bg-[linear-gradient(90deg,var(--grad-from),var(--grad-mid),var(--grad-to))] text-primary-foreground">注册</Button>
        </div>
      </div>
    </div>
  )
}

function TopLink({ href, active, children }: { href: string; active?: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      prefetch
      className={cn(
        "inline-flex items-center gap-2 px-1 py-2 text-[15px] transition-colors",
        active ? "text-primary font-medium" : "text-foreground/80 hover:text-primary"
      )}
    >
      {children}
    </Link>
  )
}


