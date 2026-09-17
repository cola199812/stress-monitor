"use client";

import React, { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Trash2, Search, FileUp } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import http from "@/lib/http";
import { formatDateYMD } from "@/lib/utils";
import CollectionSidebar from "./collection-sidebar";

interface RecallItem {
  id: string;
  source: string;
  searchKeyword: string;
  manufacturer: string;
  manufacturer_original: string;
  productName: string;
  productName_original: string;
  description: string;
  description_original: string;
  defect: string;
  defect_original: string;
  hazard: string;
  hazard_original: string;
  publishedAt: string | null;
  url: string;
}

interface RecallCollectionProps {
  categories: any[];
  products: any[];
  types: any[];
}

export default function RecallCollection({ categories, products, types }: RecallCollectionProps) {
  const [items, setItems] = useState<RecallItem[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [isCrawling, setIsCrawling] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("__all__");
  const [selectedProduct, setSelectedProduct] = useState<string>("__all__");
  const [selectedAllergen, setSelectedAllergen] = useState<string>("__all__");
  const [allergens, setAllergens] = useState<any[]>([]);
  const itemsPerPage = 10;
  const translateCacheRef = useRef<Map<string, string>>(new Map());

  const filteredProducts = selectedCategory && selectedCategory !== "__all__"
    ? (() => {
        const categoryTypes = types?.filter(t => t.categoryId === selectedCategory) || [];
        const typeIds = categoryTypes.map(t => t.id);
        return products?.filter(p => typeIds.includes(p.categoryId)) || [];
      })()
    : (products || []);

  const loadAllergens = (params?: { categoryId?: string; productId?: string }) => {
    http.get('/allergens', { params })
      .then((res: any) => {
        setAllergens(res?.items || []);
      })
      .catch((error) => {
        console.error('[Allergens] 加载失败:', error);
        setAllergens([]);
      });
  };

  useEffect(() => {
    if (selectedProduct && selectedProduct !== "__all__") {
      loadAllergens({ productId: selectedProduct });
    } else if (selectedCategory && selectedCategory !== "__all__") {
      loadAllergens({ categoryId: selectedCategory });
    } else {
      setAllergens([]);
    }
  }, [selectedCategory, selectedProduct]);

  const loadFilteredData = () => {
    setLoadingItems(true);
    const params: any = { page: 1, pageSize: 100 };
    
    if (selectedAllergen && selectedAllergen !== "__all__") {
      const allergenObj = allergens?.find(a => a.id === selectedAllergen);
      if (allergenObj) {
        params.searchKeyword = allergenObj.name;
      }
    } else if (selectedProduct && selectedProduct !== "__all__") {
      const productObj = products?.find(p => p.id === selectedProduct);
      if (productObj) {
        params.searchKeyword = productObj.name;
      }
    } else if (selectedCategory && selectedCategory !== "__all__") {
      const selectedCat = categories?.find(c => c.id === selectedCategory);
      if (selectedCat) {
        params.searchKeyword = selectedCat.name;
      }
    }
    
    http.get('/recall/filter', { params })
      .then(async (res: any) => {
        const list = (res?.items || []) as any[];
        const texts: string[] = [];
        const pushText = (t?: string) => {
          const v = (t || '').trim();
          if (v && !translateCacheRef.current.has(v)) texts.push(v);
        };
        list.forEach((x) => {
          pushText(x.manufacturer);
          pushText(x.productName);
          pushText(x.description);
        });
        
        if (texts.length > 0) {
          try {
            const r: any = await http.post('/knowledge/translate', { texts, to: 'zh-CN' });
            const arr = (r && (r as any).items ? (r as any).items : []) as string[];
            texts.forEach((src, i) => {
              const zh = arr[i] || src;
              translateCacheRef.current.set(src, zh);
            });
          } catch {}
        }

        const mapped: RecallItem[] = list.map((x: any) => {
          const tr = (s?: string) => {
            const v = (s || '').trim();
            return v ? (translateCacheRef.current.get(v) || v) : v;
          };
          return {
            id: x.id,
            source: x.source,
            searchKeyword: x.searchKeyword,
            manufacturer: tr(x.manufacturer),
            manufacturer_original: x.manufacturer,
            productName: tr(x.productName),
            productName_original: x.productName,
            description: tr(x.description),
            description_original: x.description,
            defect: tr(x.defect),
            defect_original: x.defect,
            hazard: tr(x.hazard),
            hazard_original: x.hazard,
            publishedAt: formatDateYMD(x.time) ||
              formatDateYMD(x.publishDate) ||
              formatDateYMD(x.publishTime) ||
              x.time || x.publishDate || x.publishTime || null,
            url: x.link,
          };
        });
        setItems(mapped);
        setCurrentPage(1);
      })
      .finally(() => setLoadingItems(false));
  };

  const handleCrawl = () => {
    const recallInput = searchInput.trim();
    if (!recallInput) {
      alert('请输入关键词');
      return;
    }
    
    const recallKeywords = recallInput.split(/[、；;，,|\s]+/).map(k => k.trim()).filter(Boolean);
    setIsCrawling(true);
    
    http.post('/recall/crawl-to-filter', { 
      keywords: recallKeywords,
      sources: [],
      max_pages: 1
    }, { timeout: 120000 })
      .then(() => {
        loadFilteredData();
      })
      .catch((error) => {
        console.error('[Recall Crawl] 爬取失败:', error);
        alert('召回爬取失败: ' + (error.message || '未知错误'));
      })
      .finally(() => {
        setIsCrawling(false);
      });
  };

  const handleDelete = (id: string) => {
    http.delete(`/recall/${id}`).catch(() => {}).finally(() => {
      setItems(prev => prev.filter(x => x.id !== id));
    });
  };

  const total = items.length;
  const indexOfLast = currentPage * itemsPerPage;
  const indexOfFirst = indexOfLast - itemsPerPage;
  const currentItems = items.slice(indexOfFirst, indexOfLast);

  return (
    <div className="container mx-auto px-4 pt-4 pb-8 h-full flex flex-col overflow-hidden">
      <div className="flex items-center gap-3 mb-4 flex-shrink-0">
        <CollectionSidebar />
        
        <Input
          placeholder="请输入搜索关键词..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleCrawl();
            }
          }}
          className="w-[300px]"
        />
            <Button 
              onClick={handleCrawl}
              disabled={isCrawling}
              className="whitespace-nowrap"
            >
              {isCrawling ? '爬取中...' : '采集'}
            </Button>
            <Button variant="outline" className="whitespace-nowrap" disabled title="功能开发中">
              <Search className="h-4 w-4 mr-2" />
              高级检索
            </Button>
            <Button variant="outline" className="whitespace-nowrap" disabled title="功能开发中">
              <FileUp className="h-4 w-4 mr-2" />
              导入文件
            </Button>
          </div>

      {isCrawling && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground bg-blue-50 dark:bg-blue-950 p-3 rounded-md mb-4 flex-shrink-0">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
          <span>正在爬取数据，请稍候...</span>
        </div>
      )}

      <div className="flex gap-6 flex-1 overflow-hidden">
        <div className="w-50 flex-shrink-0 space-y-4 bg-card border rounded-lg p-4 overflow-y-auto">
              <h3 className="text-lg font-semibold">数据筛选</h3>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">产品类别</label>
                <Select 
                  value={selectedCategory} 
                  onValueChange={(val) => {
                    setSelectedCategory(val);
                    setSelectedProduct("__all__");
                    setSelectedAllergen("__all__");
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择产品类别" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">全部类别</SelectItem>
                    {categories?.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id}>{cat.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">产品</label>
                <Select 
                  value={selectedProduct}
                  onValueChange={(val) => {
                    setSelectedProduct(val);
                    setSelectedAllergen("__all__");
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择产品" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">全部产品</SelectItem>
                    {filteredProducts?.map((product) => (
                      <SelectItem key={product.id} value={product.id}>{product.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">过敏原</label>
                <Select
                  value={selectedAllergen}
                  onValueChange={(val) => setSelectedAllergen(val)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择过敏原" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">全部过敏原</SelectItem>
                    {allergens?.map((allergen) => (
                      <SelectItem key={allergen.id} value={allergen.id}>{allergen.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

          <Button className="w-full" onClick={loadFilteredData}>
            查询
          </Button>
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <Card className="flex-1 flex flex-col overflow-hidden">
            <CardHeader className="flex-shrink-0">
              <CardTitle>召回明细数据</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto">
              {loadingItems ? (
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
                </div>
              ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[200px]">产品名称</TableHead>
                          <TableHead className="w-[120px]">搜索关键词</TableHead>
                          <TableHead className="w-[150px]">生产厂家</TableHead>
                          <TableHead className="w-[200px]">产品描述</TableHead>
                          <TableHead className="w-[150px]">产品缺陷</TableHead>
                          <TableHead className="w-[150px]">危害</TableHead>
                          <TableHead className="w-[100px]">时间</TableHead>
                          <TableHead className="w-[200px]">来源/操作</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {currentItems.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                              暂无数据，请选择筛选条件后点击查询
                            </TableCell>
                          </TableRow>
                        ) : (
                          currentItems.map(item => (
                            <TableRow key={item.id}>
                              <TableCell className="truncate" title={item.productName}>
                                {item.productName}
                              </TableCell>
                              <TableCell>{item.searchKeyword}</TableCell>
                              <TableCell className="truncate" title={item.manufacturer}>
                                {item.manufacturer}
                              </TableCell>
                              <TableCell className="truncate" title={item.description}>
                                {item.description}
                              </TableCell>
                              <TableCell className="truncate" title={item.defect}>
                                {item.defect}
                              </TableCell>
                              <TableCell className="truncate" title={item.hazard}>
                                {item.hazard}
                              </TableCell>
                              <TableCell>{item.publishedAt || '-'}</TableCell>
                              <TableCell>
                                <div className="flex gap-2">
                                  {item.url && (
                                    <Button variant="link" size="sm" asChild>
                                      <a href={item.url} target="_blank" rel="noopener noreferrer">
                                        查看
                                      </a>
                                    </Button>
                                  )}
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleDelete(item.id)}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  )}
                  
              {total > itemsPerPage && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-muted-foreground">
                    共 {total} 条，第 {currentPage} / {Math.ceil(total / itemsPerPage)} 页
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                    >上一页</Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => (p * itemsPerPage < total ? p + 1 : p))}
                      disabled={currentPage * itemsPerPage >= total}
                    >下一页</Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
