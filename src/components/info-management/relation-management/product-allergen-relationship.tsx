"use client";

import React, { useState, useEffect, forwardRef, useImperativeHandle } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { Search, Plus, Edit, Trash2, FileText } from "lucide-react";
import http from "@/lib/http";
import { toast } from "sonner";

// 类型定义
interface Product {
  id: number;
  name: string;
  category?: string;
}

interface Allergen {
  id: number;
  name: string;
  category?: string;
}

interface Evidence {
  id: number;
  title: string;
  source: string;
}

interface ProductAllergenRelationship {
  id: number;
  subject_id: number;
  subject_name: string;
  object_id: number;
  object_name: string;
  relation_type: string;
  evidence_count: number;
  exposure_score: number | null;
  exposure_details: Record<string, string>;
  created_at: string | null;
  updated_at: string | null;
}

const ProductAllergenManagementComponent = forwardRef((props, ref) => {
  // 维度配置数据
  const dimensionsConfig = [
    {
      key: 'age',
      name: '年龄',
      options: ['8-13', '7-9', '4-6', '0-3']
    },
    {
      key: 'product_form',
      name: '产品形态',
      options: ['固体', '液体', '非固体液体', '接近泉液体(粉末)']
    },
    {
      key: 'content',
      name: '含量',
      options: ['<0.1%', '0.1%-1%', '1-10%', '>10%']
    },
    {
      key: 'frequency',
      name: '使用频率',
      options: ['每月一次', '每月几次', '每周几次', '每天']
    },
    {
      key: 'duration',
      name: '使用时间',
      options: ['<1 min', '1-60 min', '1-8 h', '9-24 h']
    }
  ];

  // 状态管理
  const [relationships, setRelationships] = useState<ProductAllergenRelationship[]>([]);
  const [loading, setLoading] = useState(false);
  
  // 实体数据
  const [products, setProducts] = useState<Product[]>([]);
  const [allergens, setAllergens] = useState<Allergen[]>([]);
  
  // 搜索
  const [searchQuery, setSearchQuery] = useState("");

  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({
    handleSearch: (query: string) => {
      setSearchQuery(query);
      setCurrentPage(1);
      fetchRelationships();
    },
    handleAddRelation: () => {
      handleAddRelation();
    }
  }));
  
  // 分页
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 10;
  
  // 新建/编辑关系对话框
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRelation, setEditingRelation] = useState<ProductAllergenRelationship | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<string>("");
  const [selectedObject, setSelectedObject] = useState<string>("");
  const [selectedEvidences, setSelectedEvidences] = useState<number[]>([]);
  
  // 可用证据列表
  const [availableEvidences, setAvailableEvidences] = useState<Evidence[]>([]);
  
  // 暴露潜力评分相关状态
  const [scoringDetails, setScoringDetails] = useState<Record<string, string>>({});
  const [calculatedScore, setCalculatedScore] = useState(0);
  const [savingScore, setSavingScore] = useState(false);

  // 批量选择
  const [selectedRows, setSelectedRows] = useState<number[]>([]);
  const [batchDeleting, setBatchDeleting] = useState(false);

  // 已存在的关联关系（用于高亮显示）
  const [existingRelations, setExistingRelations] = useState<{[key: string]: number[]}>({});

  // 初始化数据
  useEffect(() => {
    fetchProducts();
    fetchAllergens();
    fetchAvailableEvidences();
    fetchRelationships();
    fetchExistingRelations();
  }, []);

  // 分页变化时重新加载数据
  useEffect(() => {
    fetchRelationships();
  }, [currentPage]);

  // 获取产品数据
  const fetchProducts = async () => {
    try {
      const response = await http.get('/entity/products/level3');
      setProducts(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error("获取产品失败:", error);
      setProducts([]);
    }
  };

  // 获取化学应急源数据
  const fetchAllergens = async () => {
    try {
      const response = await http.get('/entity/allergens');
      setAllergens(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error("获取化学应急源失败:", error);
      setAllergens([]);
    }
  };

  // 获取可用证据（新闻）
  const fetchAvailableEvidences = async () => {
    try {
      const response = await http.get('/news');
      const data = response.data || response;
      const evidences = (data.items || data || []).map((item: any) => ({
        id: item.id,
        title: item.title || '未命名新闻',
        source: item.source || '新闻来源'
      }));
      setAvailableEvidences(evidences);
    } catch (error) {
      console.error('获取证据数据失败:', error);
      setAvailableEvidences([]);
    }
  };

  // 获取已存在的关联关系（用于高亮显示）
  const fetchExistingRelations = async () => {
    try {
      const response = await http.get('/relationship/allergen-product/list', {
        params: {
          page_size: 1000 // 获取所有关系
        }
      });
      const data = response.data || response;
      const relations = data.items || [];
      
      // 构建关联关系映射：allergen_id -> [product_id1, product_id2, ...]
      const relationMap: {[key: string]: number[]} = {};
      relations.forEach((rel: any) => {
        const allergenId = rel.subject_id.toString();
        if (!relationMap[allergenId]) {
          relationMap[allergenId] = [];
        }
        relationMap[allergenId].push(rel.object_id);
      });
      
      setExistingRelations(relationMap);
    } catch (error) {
      console.error("获取已存在关联关系失败:", error);
      setExistingRelations({});
    }
  };

  // 根据选中的化学物质对产品进行排序和分类
  const getSortedProducts = () => {
    if (!selectedObject || !products.length) {
      return products;
    }
    
    const relatedProductIds = existingRelations[selectedObject] || [];
    const relatedProducts = products.filter(product => relatedProductIds.includes(product.id));
    const unrelatedProducts = products.filter(product => !relatedProductIds.includes(product.id));
    
    // 已关联的产品排在前面
    return [...relatedProducts, ...unrelatedProducts];
  };

  // 检查产品是否已与当前选中的化学物质关联
  const isProductRelated = (productId: number) => {
    if (!selectedObject) return false;
    const relatedProductIds = existingRelations[selectedObject] || [];
    return relatedProductIds.includes(productId);
  };

  // 计算总分
  const calculateTotalScore = (details: Record<string, string>) => {
    const dimensions = ['age', 'product_form', 'content', 'frequency', 'duration'];
    return dimensions.reduce((sum, dimension) => {
      const score = details[dimension] ? parseInt(details[dimension]) : 0;
      return sum + score;
    }, 0);
  };

  // 处理暴露潜力评分选择
  const handleScoringSelection = (dimension: string, level: string) => {
    const newDetails = { ...scoringDetails, [dimension]: level };
    setScoringDetails(newDetails);
    setCalculatedScore(calculateTotalScore(newDetails));
  };

  // 保存暴露潜力评分
  const saveExposureScoring = async () => {
    if (!editingRelation) return;
    
    setSavingScore(true);
    try {
      const payload = {
        scoring_details: scoringDetails,
        exposure_score: calculatedScore,
        note: `暴露潜力评分更新 - ${new Date().toLocaleString('zh-CN')}`
      };
      
      const response = await http.put(
        `/relationship/allergen-product/${editingRelation.id}/exposure-scoring`,
        payload
      );
      
      console.log('保存评分响应:', response); // 调试完整响应
      
      // 检查响应是否存在且有效
      if (!response) {
        throw new Error('未收到服务器响应');
      }
      
      // 兼容不同的HTTP客户端响应格式
      const status = response.status || (response.data ? 200 : 500);
      const responseData = response.data || response;
      
      console.log('解析后的状态:', status);
      console.log('解析后的数据:', responseData);
      
      // 检查是否成功
      const isSuccess = status === 200 || status === 201 || 
                       (responseData && responseData.code === 200) ||
                       (status >= 200 && status < 300);
      
      if (isSuccess) {
        toast.success('暴露潜力评分保存成功');
        
        // 更新本地数据
        setRelationships(prev => prev.map(rel => 
          rel.id === editingRelation.id 
            ? { ...rel, exposure_score: calculatedScore, exposure_details: scoringDetails }
            : rel
        ));
        setDialogOpen(false);
        fetchRelationships(); // 重新加载数据
      } else {
        const errorMessage = responseData?.message || responseData?.error || `HTTP ${status} 错误`;
        console.error('保存失败，状态:', status, '消息:', errorMessage);
        throw new Error(errorMessage);
      }
    } catch (error: any) {
      console.error('保存暴露潜力评分失败:', error);
      console.error('错误详情:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        message: error.message
      });
      const errorMessage = error.response?.data?.message || error.message || '保存失败';
      toast.error(`保存失败: ${errorMessage}`);
    } finally {
      setSavingScore(false);
    }
  };

  // 获取关系数据
  const fetchRelationships = async () => {
    setLoading(true);
    try {
      const params: any = {
        page: currentPage,
        page_size: pageSize
      };
      
      // 添加搜索参数（如果有搜索关键词）
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }

      const response = await http.get('/relationship/allergen-product/list', { params });
      const data = response.data || response;
      
      if (data && data.items) {
        const formattedData: ProductAllergenRelationship[] = data.items.map((item: any) => ({
          id: item.id,
          subject_id: item.product_id,
          subject_name: item.product_name,
          object_id: item.allergen_id,
          object_name: item.allergen_name,
          relation_type: item.note || "包含",
          evidence_count: 0, // 产品-化学应急源关联暂时没有证据计数
          exposure_score: item.exposure_score || null,
          exposure_details: item.exposure_details || {},
          created_at: item.created_at,
          updated_at: item.updated_at,
        }));
        setRelationships(formattedData);
        setTotalCount(data.total || 0);
        setTotalPages(data.total_pages || 1);
      } else {
        setRelationships([]);
        setTotalCount(0);
        setTotalPages(1);
      }
    } catch (error) {
      console.error("获取关系数据失败:", error);
      setRelationships([]);
      setTotalCount(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  };

  // 切换证据选择
  const toggleEvidence = (evidenceId: number) => {
    setSelectedEvidences(prev => 
      prev.includes(evidenceId) 
        ? prev.filter(id => id !== evidenceId)
        : [...prev, evidenceId]
    );
  };

  // 打开新建关系对话框
  const handleAddRelation = () => {
    setEditingRelation(null);
    setSelectedSubject("");
    setSelectedObject("");
    setSelectedEvidences([]);
    setScoringDetails({});
    setCalculatedScore(0);
    fetchAvailableEvidences();
    setDialogOpen(true);
  };

  // 打开编辑关系对话框
  const handleEditRelation = async (relation: ProductAllergenRelationship) => {
    setEditingRelation(relation);
    setSelectedSubject(relation.subject_id.toString());
    setSelectedObject(relation.object_id.toString());
    
    // 从数据库加载已保存的暴露潜力评分细节
    try {
      console.log('正在加载评分细节，关系ID:', relation.id);
      const response = await http.get(`/relationship/allergen-product/${relation.id}/exposure-scoring`);
      console.log('评分细节响应:', response);
      
      // 兼容不同的响应格式
      const responseData = response.data || response;
      const status = response.status || (responseData ? 200 : 500);
      
      if (status === 200 || (responseData && responseData.code === 200)) {
        const data = responseData.data || responseData;
        const scoring_details = data.scoring_details || {};
        const total_score = data.total_score || 0;
        
        console.log('加载的评分细节:', scoring_details);
        console.log('加载的总分:', total_score);
        
        setScoringDetails(scoring_details);
        setCalculatedScore(total_score);
      } else {
        console.log('没有评分细节数据，使用默认值');
        setScoringDetails({});
        setCalculatedScore(0);
      }
    } catch (error: any) {
      console.error('加载暴露潜力评分细节失败:', error);
      console.error('错误详情:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message
      });
      // 使用默认值
      setScoringDetails({});
      setCalculatedScore(0);
    }
    
    fetchAvailableEvidences();
    setDialogOpen(true);
  };

  // 保存关系
  const handleSaveRelation = async () => {
    if (!selectedSubject || !selectedObject) {
      toast.error("请选择产品和化学应急源");
      return;
    }

    setLoading(true);
    try {
      if (editingRelation) {
        // 编辑模式 - 更新现有关联关系
        const payload = {
          product_id: parseInt(selectedSubject),
          allergen_id: parseInt(selectedObject),
        };
        
        const response = await http.put(`/relationship/allergen-product/${editingRelation.id}`, payload);
        
        console.log('保存关联响应:', response);
        
        // 检查响应是否存在且有效
        if (!response) {
          throw new Error('未收到服务器响应');
        }
        
        // 兼容不同的HTTP客户端响应格式
        const status = response.status || (response.data ? 200 : 500);
        const responseData = response.data || response;
        
        // 检查是否成功
        const isSuccess = status === 200 || status === 201 || 
                         (responseData && responseData.code === 200) ||
                         (status >= 200 && status < 300);
        
        if (isSuccess) {
          toast.success("关联关系更新成功");
        } else {
          const errorMessage = responseData?.message || responseData?.error || `HTTP ${status} 错误`;
          throw new Error(errorMessage);
        }
      } else {
        // 新建模式
        const payload = {
          product_id: parseInt(selectedSubject),
          allergen_id: parseInt(selectedObject),
        };
        
        const response = await http.post('/relationship/allergen-product/create', payload);
        
        console.log('创建关联响应:', response);
        
        // 检查响应是否存在且有效
        if (!response) {
          throw new Error('未收到服务器响应');
        }
        
        // 兼容不同的HTTP客户端响应格式
        const status = response.status || (response.data ? 200 : 500);
        const responseData = response.data || response;
        
        // 检查是否成功
        const isSuccess = status === 200 || status === 201 || 
                         (responseData && responseData.code === 200) ||
                         (status >= 200 && status < 300);
        
        if (isSuccess) {
          toast.success("关联关系创建成功");
        } else {
          const errorMessage = responseData?.message || responseData?.error || `HTTP ${status} 错误`;
          throw new Error(errorMessage);
        }
      }
      
      setDialogOpen(false);
      fetchRelationships();
      fetchExistingRelations(); // 更新已存在的关联关系
      
      // 重置表单状态
      setSelectedSubject("");
      setSelectedObject("");
      setEditingRelation(null);
      
    } catch (error: any) {
      console.error("保存关联关系失败:", error);
      const errorMessage = error.response?.data?.message || error.message || "保存失败";
      toast.error(`保存失败: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  // 删除关系
  const handleDeleteRelation = async (relationId: number) => {
    if (!confirm("确定要删除这个关联关系吗？")) {
      return;
    }

    try {
      await http.delete(`/relationship/allergen-product/${relationId}`);
      toast.success("关联关系删除成功");
      fetchRelationships();
      fetchExistingRelations(); // 更新已存在的关联关系
    } catch (error) {
      console.error("删除关联关系失败:", error);
      toast.error("删除失败");
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedRows.length === 0) return;
    if (!confirm(`确定要删除选中的 ${selectedRows.length} 条关联关系吗？`)) return;

    setBatchDeleting(true);
    try {
      const response = await http.delete('/relationship/allergen-product/batch-delete', {
        data: { ids: selectedRows }
      });
      const result = response.data || response;
      toast.success(`成功删除 ${result.success_count ?? selectedRows.length} 条关联关系`);
      setSelectedRows([]);
      fetchRelationships();
    } catch (error) {
      console.error("批量删除失败:", error);
      toast.error("批量删除失败");
    } finally {
      setBatchDeleting(false);
    }
  };

  const handleSelectAll = (checked: boolean) => {
    setSelectedRows(checked ? relationships.map(r => r.id) : []);
  };

  const handleSelectRow = (id: number, checked: boolean) => {
    setSelectedRows(prev => checked ? [...prev, id] : prev.filter(i => i !== id));
  };

  // 搜索处理
  const handleSearch = () => {
    setCurrentPage(1);
    fetchRelationships();
  };

  // 分页控制
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const renderPagination = () => {
    if (totalPages <= 1) return null;

    return (
      <div className="flex items-center justify-between px-2">
        <div className="text-sm text-muted-foreground">
          共 {totalCount} 条记录，第 {currentPage} / {totalPages} 页
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage <= 1}
          >
            上一页
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage >= totalPages}
          >
            下一页
          </Button>
        </div>
      </div>
    );
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>产品-化学应急源关联管理</span>
          {selectedRows.length > 0 && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleBatchDelete}
              disabled={batchDeleting}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              {batchDeleting ? '删除中...' : `删除选中 (${selectedRows.length})`}
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* 关系列表 */}
        <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40px]">
                    <Checkbox
                      checked={relationships.length > 0 && selectedRows.length === relationships.length}
                      onCheckedChange={(checked) => handleSelectAll(!!checked)}
                    />
                  </TableHead>
                  <TableHead>产品</TableHead>
                  <TableHead>化学应急源</TableHead>
                  <TableHead>暴露潜力分数</TableHead>
                  <TableHead>佐证数据</TableHead>
                  <TableHead>更新时间</TableHead>
                  <TableHead className="w-[150px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      加载中...
                    </TableCell>
                  </TableRow>
                ) : relationships.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      暂无关联数据
                    </TableCell>
                  </TableRow>
                ) : (
                  relationships.map((relation) => (
                    <TableRow key={relation.id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedRows.includes(relation.id)}
                          onCheckedChange={(checked) => handleSelectRow(relation.id, !!checked)}
                        />
                      </TableCell>
                      <TableCell className="font-medium">{relation.subject_name}</TableCell>
                      <TableCell>{relation.object_name}</TableCell>
                      <TableCell>
                        <Badge 
                          variant="default" 
                          className={
                            (relation.exposure_score || 0) > 0 
                              ? "bg-blue-500 hover:bg-blue-600" 
                              : "bg-gray-300 text-gray-600"
                          }
                        >
                          {relation.exposure_score || 0} 分
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge 
                          variant="default" 
                          className={
                            (relation.evidence_count || 0) > 0 
                              ? "bg-blue-500 hover:bg-blue-600 cursor-pointer" 
                              : "bg-gray-300 text-gray-600 cursor-default"
                          }
                          onClick={(relation.evidence_count || 0) > 0 ? () => {
                            // TODO: 实现查看证据详情功能
                            toast.info("查看证据详情功能待实现");
                          } : undefined}
                        >
                          {relation.evidence_count || 0} 条证据
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {relation.updated_at ? new Date(relation.updated_at).toLocaleString('zh-CN') : '-'}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm" onClick={() => handleEditRelation(relation)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="destructive" size="sm" onClick={() => handleDeleteRelation(relation.id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
        </div>
        
        {/* 分页 */}
        {renderPagination()}
      </CardContent>

      {/* 新建/编辑关系对话框 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingRelation ? "编辑关联" : "新建关联"}</DialogTitle>
          </DialogHeader>
          
          {/* 如果是编辑模式，显示Tab切换 */}
          {editingRelation ? (
            <Tabs defaultValue="basic" className="space-y-4">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="basic">基本关系</TabsTrigger>
                <TabsTrigger value="scoring">暴露潜力选择</TabsTrigger>
              </TabsList>

              {/* 基本关系 Tab */}
              <TabsContent value="basic" className="space-y-4">
                <div className="space-y-6 py-4">
                  {/* 选择产品和化学应急源 */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>产品</Label>
                      <Select value={selectedSubject} onValueChange={setSelectedSubject}>
                        <SelectTrigger>
                          <SelectValue placeholder="选择产品" />
                        </SelectTrigger>
                        <SelectContent>
                          {getSortedProducts().map((item) => (
                            <SelectItem 
                              key={item.id} 
                              value={item.id.toString()}
                              className={isProductRelated(item.id) ? "bg-blue-50 border-l-4 border-l-blue-500 font-medium text-blue-700" : ""}
                            >
                              <div className="flex items-center justify-between w-full">
                                <span>{item.name}</span>
                                {isProductRelated(item.id) && (
                                  <Badge variant="secondary" className="ml-2 bg-blue-100 text-blue-700 text-xs">
                                    已关联
                                  </Badge>
                                )}
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>化学应急源</Label>
                      <Select value={selectedObject} onValueChange={setSelectedObject}>
                        <SelectTrigger>
                          <SelectValue placeholder="选择化学应急源" />
                        </SelectTrigger>
                        <SelectContent>
                          {allergens.map((item) => (
                            <SelectItem key={item.id} value={item.id.toString()}>
                              {item.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  
                  {/* 佐证数据 */}
                  <div className="space-y-2">
                    <Label>佐证数据</Label>
                    <div className="p-3 border rounded-lg bg-muted">
                      <Badge variant="outline">{editingRelation?.evidence_count || 0} 条证据</Badge>
                    </div>
                  </div>

                  {/* 保存关联按钮 */}
                  <div className="flex justify-end gap-2 pt-4">
                    <Button variant="outline" onClick={() => setDialogOpen(false)}>
                      取消
                    </Button>
                    <Button onClick={handleSaveRelation} disabled={loading}>
                      {loading ? '保存中...' : '保存关联'}
                    </Button>
                  </div>
                </div>
              </TabsContent>

              {/* 暴露潜力选择 Tab */}
              <TabsContent value="scoring" className="space-y-4">
                <div className="space-y-6">
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold">产品-化学应急源暴露潜力评分</h3>
                    <div className="text-right">
                      <div className="text-sm text-muted-foreground">当前总分</div>
                      <Badge variant="secondary" className="text-lg">
                        {calculatedScore} 分
                      </Badge>
                    </div>
                  </div>

                  {/* 评分表格 */}
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-muted/50">
                          <TableHead className="w-32">暴露维度</TableHead>
                          <TableHead className="text-center">1分</TableHead>
                          <TableHead className="text-center">2分</TableHead>
                          <TableHead className="text-center">3分</TableHead>
                          <TableHead className="text-center">4分</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {dimensionsConfig.map((dimension) => (
                          <TableRow key={dimension.key}>
                            <TableCell className="font-medium bg-muted/30">
                              {dimension.name}
                            </TableCell>
                            {dimension.options.map((option, index) => (
                              <TableCell key={index} className="text-center">
                                <Button
                                  variant={scoringDetails[dimension.key] === String(index + 1) ? "default" : "outline"}
                                  size="sm"
                                  onClick={() => handleScoringSelection(dimension.key, String(index + 1))}
                                  className="w-full"
                                >
                                  {option}
                                </Button>
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {/* 保存按钮 */}
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setDialogOpen(false)}>
                      取消
                    </Button>
                    <Button 
                      onClick={saveExposureScoring}
                      disabled={savingScore || Object.keys(scoringDetails).length !== 5}
                    >
                      {savingScore ? '保存中...' : '保存评分'}
                    </Button>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          ) : (
            <div className="space-y-6 py-4">
              {/* 新建关系表单 */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>产品</Label>
                  <Select value={selectedSubject} onValueChange={setSelectedSubject}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择产品" />
                    </SelectTrigger>
                    <SelectContent>
                      {products.map((item) => (
                        <SelectItem key={item.id} value={item.id.toString()}>
                          {item.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label>化学应急源</Label>
                  <Select value={selectedObject} onValueChange={setSelectedObject}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择化学应急源" />
                    </SelectTrigger>
                    <SelectContent>
                      {allergens.map((item) => (
                        <SelectItem key={item.id} value={item.id.toString()}>
                          {item.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* 保存关联按钮 */}
              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={() => setDialogOpen(false)}>
                  取消
                </Button>
                <Button onClick={handleSaveRelation} disabled={loading}>
                  {loading ? '保存中...' : '保存关联'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
});

ProductAllergenManagementComponent.displayName = "ProductAllergenManagementComponent";

export default ProductAllergenManagementComponent;
