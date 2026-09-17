"use client"

import { useEffect, useMemo, useState } from "react"
import { useProductStore } from "@/store/useProductStore"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Plus, MoreHorizontal, Edit2, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"
import http from "@/lib/http"

// 过敏原类型定义
type Allergen = {
  id: string
  categoryId: string
  name: string
  description?: string
}

export function CategoryAllergenManager() {
  const { categories, products, header, setCategory, setAllergen, rehydrateFromLocal, createCategory, updateCategory, deleteCategory, fetchAll } = useProductStore()
  const [open, setOpen] = useState(false)
  const [allergens, setAllergens] = useState<Allergen[]>([])
  const selectedAllergen = header?.allergen
  const [leftMode, setLeftMode] = useState<'categories' | 'products'>('categories')
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null)
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null)

  const allergensByCat = useMemo(() => {
    const map: Record<string, Allergen[]> = {}
    allergens.forEach((a) => {
      map[a.categoryId] ||= []
      map[a.categoryId].push(a)
    })
    return map
  }, [allergens])

  // 获取过敏原列表
  const fetchAllergens = async (params?: { categoryId?: string; productId?: string }) => {
    try {
      const response: any = await http.get('/allergens', { params })
      setAllergens(response?.items || [])
    } catch (error) {
      // 静默处理错误
    }
  }

  useEffect(() => {
    // 客户端挂载后从本地恢复 UI 状态，然后拉取后端数据
    rehydrateFromLocal()
    fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 当选择类别变化时，默认右侧显示该类别下的过敏原
  useEffect(() => {
    if (!open) return
    if (leftMode === 'categories' && selectedCategoryId) {
      fetchAllergens({ categoryId: selectedCategoryId })
    }
  }, [open, leftMode, selectedCategoryId])

  // 当选择产品变化时，右侧显示该产品包含的过敏原
  useEffect(() => {
    if (!open) return
    if (leftMode === 'products' && selectedProductId) {
      fetchAllergens({ productId: selectedProductId })
    }
  }, [open, leftMode, selectedProductId])

  // 类别编辑状态
  const [editingCatId, setEditingCatId] = useState<string | null>(null)
  const [editingCatName, setEditingCatName] = useState("")
  const [isAddingCategory, setIsAddingCategory] = useState(false)
  const [newCategoryName, setNewCategoryName] = useState("")

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
      // 静默处理错误
    }
  }
  const cancelEditCategory = () => {
    setEditingCatId(null)
    setEditingCatName("")
  }
  const handleDeleteCategory = async (catId: string) => {
    try {
      await deleteCategory(catId)
      // 删除类别后重新获取过敏原
      await fetchAllergens()
    } catch (error) {
      // 静默处理错误('删除类别失败:', error)
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
    }
  }
  const cancelAddCategory = () => {
    setIsAddingCategory(false)
    setNewCategoryName("")
  }

  // 过敏原编辑状态
  const [editingAllergenId, setEditingAllergenId] = useState<string | null>(null)
  const [editingAllergenName, setEditingAllergenName] = useState("")
  const [isAddingAllergen, setIsAddingAllergen] = useState(false)
  const [newAllergenName, setNewAllergenName] = useState("")

  const startEditAllergen = (allergen: Allergen) => {
    setEditingAllergenId(allergen.id)
    setEditingAllergenName(allergen.name)
  }
  const saveEditAllergen = async () => {
    if (!editingAllergenName.trim() || !editingAllergenId) return
    try {
      await http.patch(`/allergens/${editingAllergenId}`, { 
        name: editingAllergenName.trim() 
      })
      setEditingAllergenId(null)
      setEditingAllergenName("")
      await fetchAllergens()
    } catch (error) {
      // 静默处理错误('更新过敏原失败:', error)
    }
  }
  const cancelEditAllergen = () => {
    setEditingAllergenId(null)
    setEditingAllergenName("")
  }
  const handleDeleteAllergen = async (allergenId: string) => {
    try {
      await http.delete(`/allergens/${allergenId}`)
      await fetchAllergens()
    } catch (error) {
      // 静默处理错误('删除过敏原失败:', error)
    }
  }
  const addNewAllergen = async () => {
    const trimmed = newAllergenName.trim()
    if (!trimmed) {
      cancelAddAllergen()
      return
    }
    try {
      await http.post('/allergens', { 
        name: trimmed 
      })
      setIsAddingAllergen(false)
      setNewAllergenName("")
      await fetchAllergens()
    } catch (error) {
      // 静默处理错误('新增过敏原失败:', error)
    }
  }
  const cancelAddAllergen = () => {
    setIsAddingAllergen(false)
    setNewAllergenName("")
  }

  const handleSelectAllergen = (allergen: Allergen) => {
    setAllergen(allergen)
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={(newOpen) => {
      setOpen(newOpen)
      if (!newOpen) {
        setIsAddingCategory(false)
        setNewCategoryName("")
        setEditingCatId(null)
        setEditingCatName("")
        setIsAddingAllergen(false)
        setNewAllergenName("")
        setEditingAllergenId(null)
        setEditingAllergenName("")
      }
    }}>
      <PopoverTrigger asChild>
        <Button variant="ghost" className="h-8 px-[var(--space-sm)] py-1 text-[length:var(--font-size-md)]">
          {header?.category?.name || '选择类别'}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[720px] p-0" align="start">
        <div className="grid grid-cols-2">
          {/* 左：类别 或 产品（固定高度，可滚动）*/}
          <div className="p-2 border-r max-h-[360px] overflow-auto">
            <Command>
              <CommandInput placeholder={leftMode === 'categories' ? '搜索类别' : '搜索产品'} />
              <CommandList>
                <CommandEmpty>无结果</CommandEmpty>
                <CommandGroup>
                  {leftMode === 'categories' ? (
                    categories.map((c) => (
                      <div key={c.id}>
                        {editingCatId === c.id ? (
                          <CommandItem className="p-0 cursor-text">
                            <Input
                              value={editingCatName}
                              onChange={(e) => setEditingCatName(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') { e.preventDefault(); saveEditCategory() }
                                if (e.key === 'Escape') { e.preventDefault(); cancelEditCategory() }
                              }}
                              onBlur={saveEditCategory}
                              autoFocus
                              className="h-auto border-0 focus-visible:ring-0 bg-transparent px-2 py-1.5 text-[length:var(--font-size-sm)] font-[number:var(--font-weight-medium)]"
                            />
                          </CommandItem>
                        ) : (
                          <CommandItem 
                            onSelect={() => { setCategory(c.id); setSelectedCategoryId(c.id); setLeftMode('categories'); /* 单击：右侧显示该类别过敏原 */ fetchAllergens({ categoryId: c.id }) }}
                            onDoubleClick={() => { setCategory(c.id); setSelectedCategoryId(c.id); setLeftMode('products'); setSelectedProductId(null) }}
                            className={cn(
                              "flex items-center justify-between group px-2 py-1.5 hover:bg-accent/50 cursor-pointer rounded-[var(--radius-sm)]",
                              header?.category?.id===c.id && "bg-primary/10 text-primary"
                            )}
                          >
                            <span className="text-[length:var(--font-size-sm)] font-[number:var(--font-weight-medium)]">{c.name}</span>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100 hover:bg-white/20 transition-all"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <MoreHorizontal className="h-3.5 w-3.5" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end" className="w-24">
                                <DropdownMenuItem onClick={() => startEditCategory(c)} className="text-[length:var(--font-size-xs)] px-2 py-1">
                                  <Edit2 className="h-3 w-3 mr-1.5" /> 修改
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleDeleteCategory(c.id)} className="text-destructive text-[length:var(--font-size-xs)] px-2 py-1">
                                  <Trash2 className="h-3 w-3 mr-1.5" /> 删除
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </CommandItem>
                        )}
                      </div>
                    ))
                  ) : (
                    // 产品模式：显示选中类别下的产品
                    (products.filter(p => !selectedCategoryId || p.categoryId === selectedCategoryId)).map((p) => (
                      <CommandItem
                        key={p.id}
                        onSelect={() => { setSelectedProductId(p.id); fetchAllergens({ productId: p.id }) }}
                        className="flex items-center justify-between group px-2 py-1.5 hover:bg-accent/50 cursor-pointer rounded-[var(--radius-sm)]"
                      >
                        <span className="text-[length:var(--font-size-sm)] font-[number:var(--font-weight-medium)]">{p.name}</span>
                      </CommandItem>
                    ))
                  )}

                  {/* 新增类别 */}
                  {isAddingCategory ? (
                    <CommandItem className="p-0 cursor-text">
                      <Input
                        placeholder="输入类别名称"
                        value={newCategoryName}
                        onChange={(e) => setNewCategoryName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') { e.preventDefault(); addNewCategory() }
                          if (e.key === 'Escape') { e.preventDefault(); cancelAddCategory() }
                        }}
                        onBlur={(e) => {
                          if (e.target.value.trim()) { addNewCategory() } else { cancelAddCategory() }
                        }}
                        autoFocus
                        className="h-auto border-0 focus-visible:ring-0 bg-transparent px-2 py-1.5 text-[length:var(--font-size-sm)] font-[number:var(--font-weight-medium)] placeholder:text-muted-foreground"
                      />
                    </CommandItem>
                  ) : (
                    <CommandItem 
                      onSelect={() => setIsAddingCategory(true)}
                      className="flex items-center justify-center px-2 py-1.5 text-muted-foreground hover:text-foreground hover:bg-accent/30 cursor-pointer rounded-[var(--radius-sm)] transition-colors"
                    >
                      <Plus className="h-4 w-4" />
                    </CommandItem>
                  )}
                </CommandGroup>
              </CommandList>
            </Command>
          </div>

          {/* 右：过敏原（固定高度，可滚动）*/}
          <div className="p-2 max-h-[360px] overflow-auto">
            <Command>
              <CommandInput placeholder="搜索过敏原" />
              <CommandList>
                <CommandEmpty>暂无过敏原</CommandEmpty>
                <CommandGroup>
                  {(
                    (leftMode === 'products' && selectedProductId)
                      ? allergens
                      : (header?.category ? (allergensByCat[header.category.id] || allergens) : allergens)
                  ).map((a) => (
                    <div key={a.id}>
                      {editingAllergenId === a.id ? (
                        <CommandItem className="p-0 cursor-text">
                          <Input
                            value={editingAllergenName}
                            onChange={(e) => setEditingAllergenName(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') { e.preventDefault(); saveEditAllergen() }
                              if (e.key === 'Escape') { e.preventDefault(); cancelEditAllergen() }
                            }}
                            onBlur={saveEditAllergen}
                            autoFocus
                            className="h-auto border-0 focus-visible:ring-0 bg-transparent px-2 py-1.5 text-[length:var(--font-size-sm)] font-[number:var(--font-weight-medium)]"
                          />
                        </CommandItem>
                      ) : (
                        <CommandItem 
                          onSelect={() => handleSelectAllergen(a)}
                          className={cn(
                            "flex items-center justify-between group px-2 py-1.5 hover:bg-accent/50 cursor-pointer rounded-[var(--radius-sm)]",
                            selectedAllergen?.id === a.id && "bg-primary/10 text-primary"
                          )}
                        >
                          <span className="text-[length:var(--font-size-sm)] font-[number:var(--font-weight-medium)]">{a.name}</span>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100 hover:bg-white/20 transition-all"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <MoreHorizontal className="h-3.5 w-3.5" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-24">
                              <DropdownMenuItem onClick={() => startEditAllergen(a)} className="text-[length:var(--font-size-xs)] px-2 py-1">
                                <Edit2 className="h-3 w-3 mr-1.5" /> 修改
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleDeleteAllergen(a.id)} className="text-destructive text-[length:var(--font-size-xs)] px-2 py-1">
                                <Trash2 className="h-3 w-3 mr-1.5" /> 删除
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </CommandItem>
                      )}
                    </div>
                  ))}

                  {/* 新增过敏原 */}
                  {isAddingAllergen ? (
                    <CommandItem className="p-0 cursor-text">
                      <Input
                        placeholder="输入过敏原名称"
                        value={newAllergenName}
                        onChange={(e) => setNewAllergenName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') { e.preventDefault(); addNewAllergen() }
                          if (e.key === 'Escape') { e.preventDefault(); cancelAddAllergen() }
                        }}
                        onBlur={(e) => {
                          if (e.target.value.trim()) { addNewAllergen() } else { cancelAddAllergen() }
                        }}
                        autoFocus
                        className="h-auto border-0 focus-visible:ring-0 bg-transparent px-2 py-1.5 text-[length:var(--font-size-sm)] font-[number:var(--font-weight-medium)] placeholder:text-muted-foreground"
                      />
                    </CommandItem>
                  ) : (
                    <CommandItem 
                      onSelect={() => setIsAddingAllergen(true)}
                      className="flex items-center justify-center px-2 py-1.5 text-muted-foreground hover:text-foreground hover:bg-accent/30 cursor-pointer rounded-[var(--radius-sm)] transition-colors"
                    >
                      <Plus className="h-4 w-4" />
                    </CommandItem>
                  )}
                </CommandGroup>
              </CommandList>
            </Command>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
