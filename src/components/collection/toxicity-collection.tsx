"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Trash2, Search, FileUp } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import http from "@/lib/http";
import CollectionSidebar from "./collection-sidebar";

interface ToxicityItem {
  id: string;
  name: string;
  search_keyword: string;
  rtecs_number: string;
  cas_number: string;
  chemical_name: string;
  molecular_formula: string;
  molecular_weight: string;
  compound_descriptor: string;
  compound_descriptor_zh: string;
  health_hazards: any[];
  publishedAt: string;
}

interface ToxicityCollectionProps {
  categories: any[];
  products: any[];
  types: any[];
}

export default function ToxicityCollection({ categories, products, types }: ToxicityCollectionProps) {
  const [items, setItems] = useState<ToxicityItem[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [isCrawling, setIsCrawling] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("__all__");
  const [selectedProduct, setSelectedProduct] = useState<string>("__all__");
  const [selectedAllergen, setSelectedAllergen] = useState<string>("__all__");
  const [allergens, setAllergens] = useState<any[]>([]);
  const itemsPerPage = 10;

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
    
    http.get('/toxicity/search', { params })
      .then((res: any) => {
        const list = res?.items || [];
        const mapped: ToxicityItem[] = list.map((x: any) => ({
          id: x.id,
          name: x.name,
          search_keyword: x.search_keyword,
          rtecs_number: x.rtecs_number,
          cas_number: x.cas_number,
          chemical_name: x.chemical_name,
          molecular_formula: x.molecular_formula,
          molecular_weight: x.molecular_weight,
          compound_descriptor: x.compound_descriptor,
          compound_descriptor_zh: x.compound_descriptor_zh,
          health_hazards: x.health_hazards || [],
          publishedAt: x.created_at,
        }));
        setItems(mapped);
        setCurrentPage(1);
      })
      .catch((error) => {
        console.error('[Toxicity] 加载失败:', error);
      })
      .finally(() => setLoadingItems(false));
  };

  const handleCrawl = () => {
    const inputKeyword = searchInput.trim();
    if (!inputKeyword) {
      alert('请输入搜索关键词');
      return;
    }
    
    const crawlKeywords = inputKeyword.split(/[、；;，,|\s]+/).map(k => k.trim()).filter(Boolean);
    if (crawlKeywords.length === 0) {
      alert('请输入有效的搜索关键词');
      return;
    }
    
    setIsCrawling(true);
    
    http.post('/toxicity/crawl', { 
      keywordsOverride: crawlKeywords 
    }, { timeout: 120000 })
      .then((res: any) => {
        console.log('[Toxicity Crawl] 爬取完成，返回结果:', res);
        loadFilteredData();
      })
      .catch((error) => {
        console.error('[Toxicity Crawl] 爬取失败:', error);
        alert('毒性数据爬取失败: ' + (error.message || '未知错误'));
      })
      .finally(() => {
        setIsCrawling(false);
      });
  };

  const handleDelete = (id: string) => {
    http.delete(`/toxicity/${id}`).catch(() => {}).finally(() => {
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
              <CardTitle>毒性数据明细</CardTitle>
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
                          <TableHead className="w-1/3">化合物名称</TableHead>
                          <TableHead>分子式</TableHead>
                          <TableHead>化合物类型</TableHead>
                          <TableHead>健康危害</TableHead>
                          <TableHead>操作</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {currentItems.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                              暂无数据，请选择筛选条件后点击查询
                            </TableCell>
                          </TableRow>
                        ) : (
                          currentItems.map(item => (
                            <TableRow key={item.id}>
                              <TableCell className="font-medium truncate" title={item.name}>
                                {item.name}
                              </TableCell>
                              <TableCell>{item.molecular_formula || '-'}</TableCell>
                              <TableCell className="truncate" title={item.compound_descriptor_zh}>
                                {item.compound_descriptor_zh || item.compound_descriptor || '-'}
                              </TableCell>
                              <TableCell className="truncate">
                                {item.health_hazards?.length > 0 
                                  ? item.health_hazards.slice(0, 2).join(', ') 
                                  : '-'}
                              </TableCell>
                              <TableCell>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleDelete(item.id)}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
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
