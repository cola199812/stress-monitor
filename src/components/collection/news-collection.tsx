"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, FileUp, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import http from "@/lib/http";
import { formatDateYMD } from "@/lib/utils";
import CollectionSidebar from "./collection-sidebar";
import SharedCollectionTable, { CollectionTableConfig } from "./shared-table";

interface NewsItem {
  id: string;
  title: string;
  source: string;
  source_wz: string | null;
  searchKeyword: string;
  publishedAt: string | null;
  abstract: string;
  url: string;
  ai_category: string;
  category_reason: string;
}

interface NewsCollectionProps {
  categories: any[];
  products: any[];
  types: any[];
}

export default function NewsCollection({ categories, products, types }: NewsCollectionProps) {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [isCrawling, setIsCrawling] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("__all__");
  const [selectedProduct, setSelectedProduct] = useState<string>("__all__");
  const [selectedAllergen, setSelectedAllergen] = useState<string>("__all__");
  const [allergens, setAllergens] = useState<any[]>([]);

  // 过滤当前选中类别下的产品
  const filteredProducts = selectedCategory && selectedCategory !== "__all__"
    ? (() => {
        const categoryTypes = types?.filter(t => t.categoryId === selectedCategory) || [];
        const typeIds = categoryTypes.map(t => t.id);
        return products?.filter(p => typeIds.includes(p.categoryId)) || [];
      })()
    : (products || []);

  // 加载过敏原列表
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

  // 当类别或产品变化时，加载对应的过敏原列表
  useEffect(() => {
    if (selectedProduct && selectedProduct !== "__all__") {
      loadAllergens({ productId: selectedProduct });
    } else if (selectedCategory && selectedCategory !== "__all__") {
      loadAllergens({ categoryId: selectedCategory });
    } else {
      setAllergens([]);
    }
  }, [selectedCategory, selectedProduct]);

  // 加载数据
  const loadFilteredData = () => {
    setLoadingItems(true);
    const params: any = {};
    
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
    
    http.get('/news/filter', { params })
      .then((res: any) => {
        const list = Array.isArray(res) ? res : [];
        const mapped: NewsItem[] = list.map((x: any) => ({
          id: x.id,
          title: x.title,
          source: x.source,
          source_wz: x.source_wz || null,
          searchKeyword: x.searchKeyword || '',
          publishedAt: formatDateYMD(x.publishTime) ||
            formatDateYMD(x.publishDate) ||
            x.publishTime || x.publishDate || null,
          abstract: x.abstract || '',
          url: x.link,
          ai_category: x.ai_relevance || '',
          category_reason: x.ai_reason || '',
        }));
        setItems(mapped);
      })
      .catch((error) => {
        console.error('[News] 加载失败:', error);
      })
      .finally(() => setLoadingItems(false));
  };

  // 爬取数据
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
    
    http.post('/news/crawl', { 
      keywordsOverride: crawlKeywords 
    }, { timeout: 120000 })
      .then((res: any) => {
        console.log('[News Crawl] 爬取完成，返回结果:', res);
        loadFilteredData();
      })
      
      .catch((error) => {
        console.error('[News Crawl] 爬取失败:', error);
        alert('新闻爬取失败: ' + (error.message || '未知错误'));
      })
      .finally(() => {
        setIsCrawling(false);
      });
  };

  const handleDelete = (id: string | number) => {
    http.delete(`/news/filter/${id}`).catch(() => {}).finally(() => {
      setItems(prev => prev.filter(x => x.id !== id));
    });
  };

  const handlePromote = async (id: string | number) => {
    if (!confirm('确定要将这条新闻入库吗？')) {
      return;
    }

    try {
      await http.post(`/news/filter/promote/${id}`);
      toast.success('新闻入库成功');
      setItems(prev => prev.filter(x => x.id !== id));
    } catch (error) {
      console.error('入库失败:', error);
      toast.error('入库失败，请重试');
    }
  };

  const tableConfig: CollectionTableConfig = {
    title: "新闻明细数据",
    columns: [
      {
        key: "title",
        title: "标题",
        width: "w-[350px]",
        render: (value, item) => (
          <div className="font-medium">
            <div className="max-w-[320px]">
              <div className="truncate font-bold" title={value}>
                {value}
              </div>
              <div className="flex flex-wrap gap-2 mt-1 text-xs text-muted-foreground">
                {item.source && <span>来源网站: {item.source}</span>}
                {item.source_wz && <span>来源日报: {item.source_wz}</span>}
                {item.url && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline flex items-center gap-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="h-3 w-3" />
                    查看原文
                  </a>
                )}
              </div>
            </div>
          </div>
        ),
      },
      {
        key: "ai_category",
        title: "AI分类",
        width: "w-[120px]",
        render: (value) =>
          value ? (
            <Badge 
              variant="secondary" 
              className={
                value === 'medium' 
                  ? "bg-yellow-50 text-yellow-700 border-yellow-200"
                  : value === 'high'
                  ? "bg-red-50 text-red-700 border-red-200"
                  : "bg-purple-50 text-purple-700 border-purple-200"
              }
            >
              {value}
            </Badge>
          ) : (
            <span className="text-muted-foreground text-sm">未分类</span>
          ),
      },
      {
        key: "category_reason",
        title: "分类原因",
        width: "w-[200px]",
        render: (value) => (
          <div className="max-w-[200px] text-sm text-muted-foreground truncate" title={value || '-'}>
            {value || '-'}
          </div>
        ),
      },
      {
        key: "publishedAt",
        title: "发布时间",
        width: "w-[130px]",
        render: (value) => (
          <div className="max-w-[130px] text-sm text-muted-foreground truncate" title={value || '-'}>
            {value || '-'}
          </div>
        ),
      },
      {
        key: "searchKeyword",
        title: "搜索关键字",
        width: "w-[130px]",
        render: (value) => (
          <div className="max-w-[130px] text-sm text-muted-foreground truncate" title={value || '-'}>
            {value || '-'}
          </div>
        ),
      },
    ],
  };

  return (
    <div className="container mx-auto px-4 pt-4 pb-8 h-full flex flex-col overflow-hidden">
      {/* 顶部搜索栏 */}
      <div className="flex items-center gap-3 mb-4 flex-shrink-0">
        {/* 采集类型下拉选择框 */}
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

          {/* 爬取状态提示 */}
      {isCrawling && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground bg-blue-50 dark:bg-blue-950 p-3 rounded-md mb-4 flex-shrink-0">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
          <span>正在爬取数据，请稍候...</span>
        </div>
      )}

      {/* 主内容区 */}
      <div className="flex gap-6 flex-1 overflow-hidden">
        {/* 左侧筛选 */}
        <div className="w-50 flex-shrink-0 space-y-4 bg-card border rounded-lg p-4 overflow-y-auto">
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

        {/* 右侧表格 */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <SharedCollectionTable
            config={tableConfig}
            data={items}
            loading={loadingItems}
            onDelete={handleDelete}
            onPromote={handlePromote}
          />
        </div>
      </div>
    </div>
  );
}
