"use client";

import { useProductStore } from "@/store/useProductStore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import React, { useEffect, useState } from "react";
import http from "@/lib/http";
import { Item } from "@/types";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button as UIButton } from "@/components/ui/button";
import { Trash2, Search, FileUp } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import CollectionSidebar from "./collection-sidebar";

/**
 * 文献采集增强组件
 * 
 * 功能说明：
 * 1. 支持双输入框模式：化学应急源 + 不良反应
 * 2. 支持研究类型筛选：流行病学研究、体内研究、体外研究
 * 3. 支持多维度数据筛选：产品类别、产品、过敏原
 * 4. 集成增强的PubMed爬虫和百度翻译服务
 * 5. 显示文献类型和发表日期
 * 
 * @returns {JSX.Element} 文献采集页面组件
 */
export default function LiteratureCollectionEnhanced() {
  // 从全局状态获取产品相关数据
  const { setFeatureName, header, categories, products, types } = useProductStore();
  
  // 设置功能名称，确保页面标题正确显示
  useEffect(() => {
    if (header && header.featureName !== '文献采集') {
      setFeatureName('文献采集');
    }
  }, [setFeatureName, header]);

  // ========== 状态管理 ==========
  
  // 文献列表相关状态
  const [items, setItems] = useState<Item[]>([]); // 文献数据列表
  const [loadingItems, setLoadingItems] = useState(false); // 数据加载状态
  const [currentPage, setCurrentPage] = useState(1); // 当前页码
  const [isCrawling, setIsCrawling] = useState(false); // 爬虫运行状态
  
  // 搜索输入框状态（双输入框模式）
  const [chemicalSource, setChemicalSource] = useState(""); // 化学应急源输入
  const [adverseReaction, setAdverseReaction] = useState(""); // 不良反应输入
  
  // 研究类型筛选状态
  const [studyType, setStudyType] = useState<string>("all"); // 研究类型：流行病学/体内/体外
  
  // 数据筛选相关状态
  const [selectedCategory, setSelectedCategory] = useState<string>("__all__"); // 选中的产品类别
  const [selectedProduct, setSelectedProduct] = useState<string>("__all__"); // 选中的产品
  const [selectedAllergen, setSelectedAllergen] = useState<string>("__all__"); // 选中的过敏原
  const [allergens, setAllergens] = useState<any[]>([]); // 过敏原列表
  
  // 分页配置
  const itemsPerPage = 10;
  
  // ========== 计算属性 ==========
  
  /**
   * 根据选中的类别过滤产品列表
   * 逻辑：通过类别ID找到对应的类型，再通过类型ID筛选产品
   */
  const filteredProducts = selectedCategory && selectedCategory !== "__all__"
    ? (() => {
        const categoryTypes = types?.filter(t => t.categoryId === selectedCategory) || [];
        const typeIds = categoryTypes.map(t => t.id);
        return products?.filter(p => typeIds.includes(p.categoryId)) || [];
      })()
    : (products || []);

  /**
   * 输入验证：两个输入框都有内容时才启用搜索
   * 确保用户同时输入化学应急源和不良反应
   */
  const isSearchEnabled = chemicalSource.trim() !== "" && adverseReaction.trim() !== "";

  // ========== 事件处理函数 ==========
  
  /**
   * 删除文献筛选记录
   * @param {string} id - 文献筛选记录ID
   */
  const handleDelete = (id: string) => {
    http.delete(`/literature/filter/${id}`).catch(() => {}).finally(() => {
      setItems(prev => prev.filter(x => x.id !== id));
    });
  };

  /**
   * 加载过敏原列表
   * @param {Object} params - 查询参数
   * @param {string} params.categoryId - 产品类别ID（可选）
   * @param {string} params.productId - 产品ID（可选）
   */
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

  // 当类别或产品变化时，自动加载对应的过敏原列表
  useEffect(() => {
    if (selectedProduct && selectedProduct !== "__all__") {
      // 优先按产品加载过敏原
      loadAllergens({ productId: selectedProduct });
    } else if (selectedCategory && selectedCategory !== "__all__") {
      // 其次按类别加载过敏原
      loadAllergens({ categoryId: selectedCategory });
    } else {
      // 清空过敏原列表
      setAllergens([]);
    }
  }, [selectedCategory, selectedProduct]);

  /**
   * 加载筛选后的文献数据
   * 根据选中的类别、产品或过敏原加载对应的文献列表
   */
  const loadFilteredData = () => {
    setLoadingItems(true);
    
    const params: any = { page: 1, pageSize: 100 };
    
    // 构建查询参数，优先级：过敏原 > 产品 > 类别
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
    
    console.log('[Literature] 加载数据，筛选条件:', {
      selectedCategory,
      selectedProduct,
      selectedAllergen,
      params
    });
    
    // 调用API获取文献数据
    http.get('/literature/filter', { params })
      .then((res: any) => {
        const list = res?.items || [];
        console.log('[Literature] 获取到数据:', list.length, '条');
        
        // 数据映射和格式化
        const mapped: any[] = list.map((x: any) => {
          // 解析可能是JSON字符串的作者字段
          const parseMaybeJson = (v: any) => {
            if (typeof v === 'string' && v.trim().startsWith('[')) {
              try { return JSON.parse(v); } catch { return v; }
            }
            return v;
          };
          
          return {
            id: x.id,
            title: x.title,
            source: x.source,
            authors: parseMaybeJson(x.authors) || null,
            searchKeyword: x.searchKeyword || '',
            publishedAt: x.publishDate, // 发表日期
            url: x.link,
            literatureType: x.literatureType || x.literature_type || 'Unknown', // 文献类型
          };
        });
        
        setItems(mapped);
        setCurrentPage(1); // 重置到第一页
      })
      .catch((error) => {
        console.error('[Literature] 加载失败:', error);
      })
      .finally(() => setLoadingItems(false));
  };

  /**
   * 处理文献采集（爬取）操作
   * 调用增强的PubMed爬虫API，支持双输入框和研究类型筛选
   */
  const handleCrawl = () => {
    // 验证输入
    if (!isSearchEnabled) {
      alert('请输入化学应急源和不良反应');
      return;
    }
    
    console.log('[Literature Crawl] 开始爬取，化学应急源:', chemicalSource, '不良反应:', adverseReaction, '研究类型:', studyType);
    setIsCrawling(true);
    
    // 调用增强的爬虫API
    http.post('/literature/enhanced-crawl', { 
      chemicalSource: chemicalSource.trim(),
      adverseReaction: adverseReaction.trim(),
      studyType: (studyType && studyType !== 'all') ? studyType : undefined // 研究类型可选，'all'视为未选择
    }, { timeout: 120000 }) // 2分钟超时
      .then((res: any) => {
        console.log('[Literature Crawl] 爬取完成，返回结果:', res);
        // 爬取完成后重新加载数据
        loadFilteredData();
      })
      .catch((error) => {
        console.error('[Literature Crawl] 爬取失败:', error);
        alert('文献爬取失败: ' + (error.message || '未知错误'));
      })
      .finally(() => {
        setIsCrawling(false);
      });
  };

  // ========== 分页计算 ==========
  
  // 前端分页切片
  const total = items.length;
  const indexOfLast = currentPage * itemsPerPage;
  const indexOfFirst = indexOfLast - itemsPerPage;
  const currentItems = items.slice(indexOfFirst, indexOfLast);

  return (
    <div className="container mx-auto px-4 pt-4 pb-8 h-full flex flex-col overflow-hidden">
      {/* 顶部搜索栏 */}
      <div className="flex items-center gap-3 mb-4 flex-shrink-0">
        {/* 采集类型下拉选择框 - 左上角 */}
        <CollectionSidebar />
        
        {/* 化学应急源输入框 */}
        <Input
          placeholder="请输入化学应急源"
          value={chemicalSource}
          onChange={(e) => setChemicalSource(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && isSearchEnabled) {
              handleCrawl();
            }
          }}
          className="w-[150px] ml-[15px]"
        />

        {/* 不良反应输入框 */}
        <Input
          placeholder="请输入不良反应"
          value={adverseReaction}
          onChange={(e) => setAdverseReaction(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && isSearchEnabled) {
              handleCrawl();
            }
          }}
          className="w-[150px]"
        />

        {/* 研究类型下拉选择框 */}
        <Select value={studyType} onValueChange={setStudyType}>
          <SelectTrigger className="w-[120px]">
            <SelectValue placeholder="研究类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="epidemiological">流行病学研究</SelectItem>
            <SelectItem value="in_vivo">体内研究</SelectItem>
            <SelectItem value="in_vitro">体外研究</SelectItem>
          </SelectContent>
        </Select>

        {/* 采集按钮 */}
        <Button 
          onClick={handleCrawl}
          disabled={!isSearchEnabled || isCrawling}
          className="whitespace-nowrap"
        >
          {isCrawling ? '爬取中...' : '采集'}
        </Button>

        {/* 右侧功能按钮 */}
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

      {/* 主内容区：左右布局 */}
      <div className="flex gap-6 flex-1 overflow-hidden">
        {/* 左侧：数据筛选 */}
        <div className="w-50 flex-shrink-0 space-y-4 bg-card border rounded-lg p-4 overflow-y-auto">
          <h3 className="text-lg font-semibold">数据筛选</h3>
          
          {/* 产品类别 */}
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
                {categories && categories.length > 0 ? (
                  categories.map((cat) => (
                    <SelectItem key={cat.id} value={cat.id}>{cat.name}</SelectItem>
                  ))
                ) : null}
              </SelectContent>
            </Select>
          </div>

          {/* 产品 */}
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
                {filteredProducts && filteredProducts.length > 0 ? (
                  filteredProducts.map((product) => (
                    <SelectItem key={product.id} value={product.id}>{product.name}</SelectItem>
                  ))
                ) : null}
              </SelectContent>
            </Select>
          </div>

          {/* 过敏原 */}
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
                {allergens && allergens.length > 0 ? (
                  allergens.map((allergen) => (
                    <SelectItem key={allergen.id} value={allergen.id}>{allergen.name}</SelectItem>
                  ))
                ) : null}
              </SelectContent>
            </Select>
          </div>

          {/* 发表时间 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">发表时间</label>
            <div className="space-y-2">
              <Input type="date" placeholder="开始日期" />
              <Input type="date" placeholder="结束日期" />
            </div>
          </div>

          {/* 查询按钮 */}
          <Button className="w-full" onClick={loadFilteredData}>
            查询
          </Button>
        </div>

        {/* 右侧：文献明细数据表格 */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <Card className="flex-1 flex flex-col overflow-hidden">
            <CardHeader className="flex-shrink-0">
              <CardTitle>文献明细数据</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto">
              {loadingItems ? (
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
                </div>
              ) : (
                <Table className="table-fixed">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[300px]">标题</TableHead>
                      <TableHead className="w-[150px]">作者</TableHead>
                      <TableHead className="w-[140px]">查询关键字</TableHead>
                      <TableHead className="w-[120px]">发表日期</TableHead>
                      <TableHead className="w-[120px]">文献类型</TableHead>
                      <TableHead className="w-[160px]">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(!selectedCategory || selectedCategory === "__all__") && 
                     (!selectedProduct || selectedProduct === "__all__") && 
                     (!selectedAllergen || selectedAllergen === "__all__") ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                          请在左侧选择产品类别、产品或过敏原以查看相关文献
                        </TableCell>
                      </TableRow>
                    ) : currentItems.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                          暂无数据，请选择筛选条件后点击查询
                        </TableCell>
                      </TableRow>
                    ) : (
                      currentItems.map(item => (
                        <TableRow key={item.id}>
                          <TableCell className="font-medium w-[300px] truncate" title={item.title}>
                            {item.title}
                          </TableCell>
                          <TableCell className="w-[150px] truncate" title={(item as any).authors?.join ? (item as any).authors.join('、') : (item as any).authors}>
                            {(item as any).authors?.join ? (item as any).authors.join('、') : (item as any).authors || '-'}
                          </TableCell>
                          <TableCell className="w-[140px] truncate" title={(item as any).searchKeyword}>
                            {(item as any).searchKeyword || '-'}
                          </TableCell>
                          <TableCell className="whitespace-nowrap w-[120px]">
                            {(item as any).publishedAt || '-'}
                          </TableCell>
                          <TableCell className="whitespace-nowrap w-[120px]">
                            {(item as any).literatureType || '-'}
                          </TableCell>
                          <TableCell className="whitespace-nowrap w-[160px]">
                            <a href={(item as any).url} target="_blank" rel="noopener noreferrer">
                              <UIButton variant="link">查看原文</UIButton>
                            </a>
                            <UIButton
                              variant="secondary"
                              size="sm"
                              className="ml-2"
                              onClick={() => {
                                http.post(`/literature/filter/promote/${item.id}`).then(() => {
                                  setItems(prev => prev.filter(x => x.id !== item.id));
                                })
                              }}
                              title="将此文献入库"
                            >
                              入库
                            </UIButton>
                            <UIButton
                              variant="destructive"
                              size="sm"
                              className="ml-2"
                              onClick={() => handleDelete(item.id)}
                              title="删除此文献"
                            >
                              <Trash2 className="h-4 w-4" />
                            </UIButton>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
            {!loadingItems && total > 0 && (
              <div className="flex justify-between items-center px-6 pb-6">
                <p className="text-sm text-muted-foreground">共 {total} 条，每页 {itemsPerPage} 条</p>
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
          </Card>
        </div>
      </div>
    </div>
  );
}
