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

export function CategoryProductManager() {
  const { categories, products, header, setCategory, setProduct, rehydrateFromLocal, createCategory, updateCategory, deleteCategory, createProduct, updateProduct, deleteProduct, fetchAll } = useProductStore()
  const [open, setOpen] = useState(false)

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
      // 静默处理错误('更新类别失败:', error)
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

  // 产品编辑状态
  const [editingProdId, setEditingProdId] = useState<string | null>(null)
  const [editingProdName, setEditingProdName] = useState("")
  const [isAddingProduct, setIsAddingProduct] = useState(false)
  const [newProductName, setNewProductName] = useState("")

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
    }
  }
  const addNewProduct = async () => {
    const trimmed = newProductName.trim()
    if (!trimmed) {
      cancelAddProduct()
      return
    }
    try {
      const categoryId = header.category?.id || categories[0]?.id
      if (!categoryId) {
        // 静默处理错误('没有可用的类别')
        return
      }
      await createProduct({ categoryId, name: trimmed, keywords: [] })
      setIsAddingProduct(false)
      setNewProductName("")
    } catch (error) {
      // 静默处理错误('新增产品失败:', error)
    }
  }
  const cancelAddProduct = () => {
    setIsAddingProduct(false)
    setNewProductName("")
  }

  return (
    <Popover open={open} onOpenChange={(newOpen) => {
      setOpen(newOpen)
      if (!newOpen) {
        setIsAddingCategory(false)
        setNewCategoryName("")
        setEditingCatId(null)
        setEditingCatName("")
        setIsAddingProduct(false)
        setNewProductName("")
        setEditingProdId(null)
        setEditingProdName("")
      }
    }}>
      <PopoverTrigger asChild>
        <Button variant="ghost" className="h-8 px-[var(--space-sm)] py-1 text-[length:var(--font-size-md)]">
          {header.category?.name || '选择类别'}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[720px] p-0" align="start">
        <div className="grid grid-cols-2">
          {/* 左：类别 */}
          <div className="p-2 border-r">
            <Command>
              <CommandInput placeholder="搜索类别" />
              <CommandList>
                <CommandEmpty>无结果</CommandEmpty>
                <CommandGroup>
                  {categories.map((c) => (
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
                          onSelect={() => setCategory(c.id)} 
                          className={cn(
                            "flex items-center justify-between group px-2 py-1.5 hover:bg-accent/50 cursor-pointer rounded-[var(--radius-sm)]",
                            header.category?.id===c.id && "bg-primary/10 text-primary"
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
                  ))}

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

          {/* 右：产品 */}
          <div className="p-2">
            <Command>
              <CommandInput placeholder="搜索产品" />
              <CommandList>
                <CommandEmpty>暂无产品</CommandEmpty>
                <CommandGroup>
                  {(header.category ? productsByCat[header.category.id] || [] : products).map((p) => (
                    <div key={p.id}>
                      {editingProdId === p.id ? (
                        <CommandItem className="p-0 cursor-text">
                          <Input
                            value={editingProdName}
                            onChange={(e) => setEditingProdName(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') { e.preventDefault(); saveEditProduct() }
                              if (e.key === 'Escape') { e.preventDefault(); cancelEditProduct() }
                            }}
                            onBlur={saveEditProduct}
                            autoFocus
                            className="h-auto border-0 focus-visible:ring-0 bg-transparent px-2 py-1.5 text-[length:var(--font-size-sm)] font-[number:var(--font-weight-medium)]"
                          />
                        </CommandItem>
                      ) : (
                        <CommandItem 
                          onSelect={() => { setProduct(p.id); setOpen(false) }}
                          className="flex items-center justify-between group px-2 py-1.5 hover:bg-accent/50 cursor-pointer rounded-[var(--radius-sm)]"
                        >
                          <span className="text-[length:var(--font-size-sm)] font-[number:var(--font-weight-medium)]">{p.name}</span>
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
                              <DropdownMenuItem onClick={() => startEditProduct(p)} className="text-[length:var(--font-size-xs)] px-2 py-1">
                                <Edit2 className="h-3 w-3 mr-1.5" /> 修改
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleDeleteProduct(p.id)} className="text-destructive text-[length:var(--font-size-xs)] px-2 py-1">
                                <Trash2 className="h-3 w-3 mr-1.5" /> 删除
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </CommandItem>
                      )}
                    </div>
                  ))}

                  {/* 新增产品 */}
                  {isAddingProduct ? (
                    <CommandItem className="p-0 cursor-text">
                      <Input
                        placeholder="输入产品名称"
                        value={newProductName}
                        onChange={(e) => setNewProductName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') { e.preventDefault(); addNewProduct() }
                          if (e.key === 'Escape') { e.preventDefault(); cancelAddProduct() }
                        }}
                        onBlur={(e) => {
                          if (e.target.value.trim()) { addNewProduct() } else { cancelAddProduct() }
                        }}
                        autoFocus
                        className="h-auto border-0 focus-visible:ring-0 bg-transparent px-2 py-1.5 text-[length:var(--font-size-sm)] font-[number:var(--font-weight-medium)] placeholder:text-muted-foreground"
                      />
                    </CommandItem>
                  ) : (
                    <CommandItem 
                      onSelect={() => setIsAddingProduct(true)}
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


