"use client";

import React, { useState, useEffect, forwardRef, useImperativeHandle } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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

interface AdverseReaction {
  id: number;
  name: string;
  symptom_name?: string;
  category?: string;
}

interface News {
  id: string;
  title: string;
  source: string;
  publishTime: string | null;
  abstract: string | null;
  link: string | null;
}

interface Complaint {
  id: number;
  title: string;
  source: string | null;
  publish_time: string | null;
  content: string | null;
  abstract: string | null;
  product_name: string | null;
  severity: string | null;
}

interface ProductAdverseReactionRelationship {
  id: number;
  product_id: number;
  product_name: string;
  symptom_id: number;
  symptom_name: string;
  confidence: number;
  evidence_count: number;
  created_at: string | null;
  updated_at: string | null;
}

interface ProductSymptomSource {
  id: number;
  product_symptom_id: number;
  news_id: number | null;
  medical_id: number | null;
  complaint_id: number | null;
  evidence_strength: number | null;
  note: string | null;
  created_at: string | null;
  updated_at: string | null;
  news_info?: {
    title: string;
    source: string;
    publishTime: string | null;
  };
  complaint_info?: {
    id: number;
    title: string;
    source: string | null;
    publish_time: string | null;
    content: string | null;
    abstract: string | null;
    severity: string | null;
  };
}

const ProductAdverseReactionManagementComponent = forwardRef<any, any>((props, ref) => {
  // 状态管理
  const [relationships, setRelationships] = useState<ProductAdverseReactionRelationship[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [adverseReactions, setAdverseReactions] = useState<AdverseReaction[]>([]);
  const [news, setNews] = useState<News[]>([]);
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  
  // 批量选择
  const [selectedRows, setSelectedRows] = useState<number[]>([]);
  const [batchDeleting, setBatchDeleting] = useState(false);
  const [recalculating, setRecalculating] = useState(false);

  // 已存在的关联关系（用于高亮显示）
  const [existingRelations, setExistingRelations] = useState<{[key: string]: number[]}>({});

  // 对话框状态
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRelation, setEditingRelation] = useState<ProductAdverseReactionRelationship | null>(null);
  const [selectedSubject, setSelectedSubject] = useState("");
  const [selectedObject, setSelectedObject] = useState("");
  
  // 证据来源相关状态
  const [sourcesDialogOpen, setSourcesDialogOpen] = useState(false);
  const [currentRelationSources, setCurrentRelationSources] = useState<ProductSymptomSource[]>([]);
  const [currentRelationId, setCurrentRelationId] = useState<number | null>(null);
  const [selectedNewsForSource, setSelectedNewsForSource] = useState<string>("");
  const [selectedComplaintForSource, setSelectedComplaintForSource] = useState<string>("");
  const [selectedNewsIds, setSelectedNewsIds] = useState<string[]>([]);
  const [selectedComplaintIds, setSelectedComplaintIds] = useState<string[]>([]);

  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({
    refresh: fetchRelationships,
    handleAddRelation: handleAddRelation,
    handleSearch: (searchQuery: string) => setSearchTerm(searchQuery)
  }));

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 10;

  // 获取关系列表
  const fetchRelationships = async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        page_size: pageSize,
        ...(searchTerm && { search: searchTerm })
      };
      
      const response = await http.get('/relationship/product-symptom/list', { params });
      
      // 根据后端API结构解析数据
      let items = [];
      let total = 0;
      let totalPages = 1;
      
      if (response && response.data && response.data.data) {
        const data = response.data.data;
        items = data.items || [];
        total = data.total || 0;
        totalPages = data.total_pages || 1;
      } else if (response && response.data) {
        items = response.data.items || [];
        total = response.data.total || 0;
        totalPages = response.data.total_pages || 1;
      } else if (Array.isArray(response)) {
        items = response;
        total = response.length;
        totalPages = 1;
      }
      
      setRelationships(items);
      setTotalCount(total);
      setTotalPages(totalPages);
    } catch (error) {
      console.error('获取产品-不良反应关系失败:', error);
      toast.error("获取关系列表失败");
      setRelationships([]);
      setTotalCount(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  };

  // 获取产品列表
  const fetchProducts = async () => {
    try {
      const response = await http.get('/entity/products/level3');
      setProducts(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error('获取产品列表失败:', error);
      setProducts([]);
    }
  };

  // 获取不良反应列表
  const fetchAdverseReactions = async () => {
    try {
      const response = await http.get('/entity/symptoms/level2');
      setAdverseReactions(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error('获取不良反应列表失败:', error);
      setAdverseReactions([]);
    }
  };

  // 获取已存在的关联关系（用于高亮显示）
  const fetchExistingRelations = async () => {
    try {
      const response = await http.get('/relationship/product-symptom/list', {
        params: {
          page_size: 1000 // 获取所有关系
        }
      });
      const data = response.data || response;
      const relations = data.items || [];
      
      // 构建关联关系映射：product_id -> [symptom_id1, symptom_id2, ...]
      const relationMap: {[key: string]: number[]} = {};
      relations.forEach((rel: any) => {
        const productId = rel.product_id.toString();
        if (!relationMap[productId]) {
          relationMap[productId] = [];
        }
        relationMap[productId].push(rel.symptom_id);
      });
      
      setExistingRelations(relationMap);
    } catch (error) {
      console.error("获取已存在关联关系失败:", error);
      setExistingRelations({});
    }
  };

  // 根据选中的产品对不良反应进行排序和分类
  const getSortedAdverseReactions = () => {
    if (!selectedSubject || !adverseReactions.length) {
      return adverseReactions;
    }
    
    const relatedSymptomIds = existingRelations[selectedSubject] || [];
    const relatedReactions = adverseReactions.filter(reaction => relatedSymptomIds.includes(reaction.id));
    const unrelatedReactions = adverseReactions.filter(reaction => !relatedSymptomIds.includes(reaction.id));
    
    // 已关联的不良反应排在前面
    return [...relatedReactions, ...unrelatedReactions];
  };

  // 检查不良反应是否已与当前选中的产品关联
  const isReactionRelated = (reactionId: number) => {
    if (!selectedSubject) return false;
    const relatedSymptomIds = existingRelations[selectedSubject] || [];
    return relatedSymptomIds.includes(reactionId);
  };

  // 获取新闻列表
  const fetchNews = async () => {
    try {
      const response = await http.get('/news');
      const data = response.data || response;
      const evidences = (data.items || data || []).map((item: any) => ({
        id: item.id,
        title: item.title || '未命名新闻',
        source: item.source || '新闻来源',
        publishTime: item.publishTime,
        abstract: item.abstract,
        link: item.link
      }));
      setNews(evidences);
    } catch (error) {
      console.error('获取新闻列表失败:', error);
      setNews([]);
    }
  };

  // 获取投诉列表
  const fetchComplaints = async () => {
    try {
      const response = await http.get('/complaints');
      const data = response.data || response;
      const complaintsData = (data.items || data || []).map((item: any) => ({
        id: item.id,
        title: item.title || item.content?.substring(0, 50) + '...' || '未命名投诉',
        source: item.source,
        publish_time: item.publish_time,
        content: item.content,
        abstract: item.abstract,
        product_name: item.product_name,
        severity: item.severity
      }));
      setComplaints(complaintsData);
    } catch (error) {
      console.error('获取投诉列表失败:', error);
      setComplaints([]);
    }
  };

  // 获取证据来源列表
  const fetchRelationSources = async (relationId: number) => {
    try {
      const response = await http.get(`/relationship/product-symptom/${relationId}/sources`);
      const data = response.data || response;
      if (data && Array.isArray(data.items)) {
        setCurrentRelationSources(data.items);
      } else {
        setCurrentRelationSources([]);
      }
    } catch (error) {
      console.error('获取证据来源失败:', error);
      setCurrentRelationSources([]);
    }
  };

  // 添加新闻证据来源
  const handleAddNewsSource = async () => {
    if (!currentRelationId || !selectedNewsForSource) {
      toast.error("请选择新闻作为证据来源");
      return;
    }

    try {
      await http.post(`/relationship/product-symptom/${currentRelationId}/sources`, {
        news_id: parseInt(selectedNewsForSource),
        evidence_strength: 1.0,
        note: '通过界面添加'
      });
      
      toast.success("新闻证据来源添加成功");
      await fetchRelationSources(currentRelationId);
      setSelectedNewsForSource("");
    } catch (error) {
      console.error('添加新闻证据来源失败:', error);
      toast.error("添加新闻证据来源失败");
    }
  };

  // 添加投诉证据来源
  const handleAddComplaintSource = async () => {
    if (!currentRelationId || !selectedComplaintForSource) {
      toast.error("请选择投诉作为证据来源");
      return;
    }

    try {
      await http.post(`/relationship/product-symptom/${currentRelationId}/sources`, {
        complaint_id: parseInt(selectedComplaintForSource),
        evidence_strength: 1.0,
        note: '通过界面添加'
      });
      
      toast.success("投诉证据来源添加成功");
      await fetchRelationSources(currentRelationId);
      setSelectedComplaintForSource("");
    } catch (error) {
      console.error('添加投诉证据来源失败:', error);
      toast.error("添加投诉证据来源失败");
    }
  };

  // 查看证据来源
  const handleViewSources = async (relation: ProductAdverseReactionRelationship) => {
    setCurrentRelationId(relation.id);
    await fetchRelationSources(relation.id);
    setSourcesDialogOpen(true);
  };

  // 初始化数据
  useEffect(() => {
    fetchRelationships();
    fetchProducts();
    fetchAdverseReactions();
    fetchNews();
    fetchComplaints();
    fetchExistingRelations();
  }, []);

  // 分页变化时重新加载数据
  useEffect(() => {
    fetchRelationships();
  }, [currentPage, searchTerm]);

  // 由于后端已实现分页和搜索，这里直接使用relationships数据
  const filteredRelationships = relationships;

  // 切换新闻选择
  const toggleNewsSelection = (newsId: string) => {
    setSelectedNewsIds(prev => 
      prev.includes(newsId) 
        ? prev.filter(id => id !== newsId)
        : [...prev, newsId]
    );
  };

  const toggleComplaintSelection = (complaintId: string) => {
    setSelectedComplaintIds(prev => 
      prev.includes(complaintId) 
        ? prev.filter(id => id !== complaintId)
        : [...prev, complaintId]
    );
  };

  // 打开新建对话框
  const handleAddRelation = () => {
    setEditingRelation(null);
    setSelectedSubject("");
    setSelectedObject("");
    setSelectedNewsIds([]);
    setSelectedComplaintIds([]);
    setDialogOpen(true);
  };

  // 打开编辑对话框
  const handleEditRelation = async (relation: ProductAdverseReactionRelationship) => {
    setEditingRelation(relation);
    setSelectedSubject(relation.product_id.toString());
    setSelectedObject(relation.symptom_id.toString());
    
    // 加载该关联的证据来源数据
    await fetchRelationSources(relation.id);
    setSelectedNewsIds([]);
    setSelectedComplaintIds([]);
    setDialogOpen(true);
  };

  // 保存关系
  const handleSaveRelation = async () => {
    if (!selectedSubject || !selectedObject) {
      toast.error("请选择产品和症状");
      return;
    }

    try {
      let relationId: number;
      
      if (editingRelation) {
        // 编辑模式
        const payload = {
          product_id: parseInt(selectedSubject),
          symptom_id: parseInt(selectedObject)
        };
        
        await http.put(`/relationship/product-symptom/${editingRelation.id}`, payload);
        relationId = editingRelation.id;
        toast.success("关联关系更新成功");
      } else {
        // 新建模式
        const payload = {
          product_id: parseInt(selectedSubject),
          symptom_id: parseInt(selectedObject)
        };
        
        const response = await http.post('/relationship/product-symptom', payload);
        relationId = response.data?.id || response.data?.data?.id;
        toast.success("关联关系创建成功");
      }
      
      // 保存选择的新闻证据来源
      if (selectedNewsIds.length > 0) {
        for (const newsId of selectedNewsIds) {
          try {
            await http.post(`/relationship/product-symptom/${relationId}/sources`, {
              news_id: parseInt(newsId),
              evidence_strength: 1.0,
              note: '通过界面添加'
            });
          } catch (error) {
            console.error(`添加新闻证据 ${newsId} 失败:`, error);
          }
        }
        if (selectedNewsIds.length > 0) {
          toast.success(`成功添加 ${selectedNewsIds.length} 条新闻证据`);
        }
      }
      
      // 保存选择的投诉证据来源
      if (selectedComplaintIds.length > 0) {
        for (const complaintId of selectedComplaintIds) {
          try {
            await http.post(`/relationship/product-symptom/${relationId}/sources`, {
              complaint_id: parseInt(complaintId),
              evidence_strength: 1.0,
              note: '通过界面添加'
            });
          } catch (error) {
            console.error(`添加投诉证据 ${complaintId} 失败:`, error);
          }
        }
        if (selectedComplaintIds.length > 0) {
          toast.success(`成功添加 ${selectedComplaintIds.length} 条投诉证据`);
        }
      }
      
      setDialogOpen(false);
      fetchRelationships();
      fetchExistingRelations(); // 更新已存在的关联关系
    } catch (error) {
      console.error("保存关联关系失败:", error);
      toast.error("保存失败");
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedRows.length === 0) return;
    if (!confirm(`确定要删除选中的 ${selectedRows.length} 条关联关系吗？`)) return;

    setBatchDeleting(true);
    try {
      const response = await http.delete('/relationship/product-symptom/batch-delete', {
        data: { ids: selectedRows }
      });

      if (response.data?.code === 200) {
        toast.success(`成功删除 ${selectedRows.length} 条关联关系`);
        setSelectedRows([]);
        await fetchRelationships();
      } else {
        throw new Error(response.data?.message || '删除失败');
      }
    } catch (error: any) {
      console.error('批量删除失败:', error);
      toast.error(`批量删除失败: ${error.message || '未知错误'}`);
    } finally {
      setBatchDeleting(false);
    }
  };

  // 重新计算所有置信度分数
  const handleRecalculateScores = async () => {
    if (!confirm('确定要重新计算所有产品-不良反应关系的置信度分数吗？这可能需要一些时间。')) return;

    setRecalculating(true);
    try {
      const response = await http.post('/relationship/product-symptom/recalculate-all-scores');
      
      if (response.data?.updated_count !== undefined) {
        toast.success(`成功重新计算了 ${response.data.updated_count} 个关系的置信度分数`);
        await fetchRelationships(); // 刷新列表以显示更新后的分数
      } else {
        toast.success('置信度分数重新计算完成');
        await fetchRelationships();
      }
    } catch (error: any) {
      console.error('重新计算置信度分数失败:', error);
      toast.error(`重新计算失败: ${error.response?.data?.message || error.message || '未知错误'}`);
    } finally {
      setRecalculating(false);
    }
  };

  const handleSelectAll = (checked: boolean) => {
    setSelectedRows(checked ? relationships.map(r => r.id) : []);
  };

  const handleSelectRow = (id: number, checked: boolean) => {
    setSelectedRows(prev => checked ? [...prev, id] : prev.filter(i => i !== id));
  };

  // 删除关系
  const handleDeleteRelation = async (relationId: number) => {
    if (!confirm("确定要删除这个关联关系吗？")) {
      return;
    }

    try {
      await http.delete(`/relationship/product-symptom/${relationId}`);
      toast.success("关联关系删除成功");
      fetchRelationships();
      fetchExistingRelations(); // 更新已存在的关联关系
    } catch (error) {
      console.error('删除关联关系失败:', error);
      toast.error("删除失败");
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>产品-不良反应关联管理</span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRecalculateScores}
              disabled={recalculating}
            >
              {recalculating ? '计算中...' : '重新计算置信度'}
            </Button>
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
          </div>
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
                <TableHead>不良反应</TableHead>
                <TableHead>证据支持分数</TableHead>
                <TableHead>佐证数据</TableHead>
                <TableHead>更新时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    加载中...
                  </TableCell>
                </TableRow>
              ) : filteredRelationships.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                filteredRelationships.map((relation) => (
                  <TableRow key={relation.id}>
                    <TableCell>
                      <Checkbox
                        checked={selectedRows.includes(relation.id)}
                        onCheckedChange={(checked) => handleSelectRow(relation.id, !!checked)}
                      />
                    </TableCell>
                    <TableCell className="font-medium">
                      {relation.product_name}
                    </TableCell>
                    <TableCell>
                      {relation.symptom_name}
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant="default" 
                        className={
                          (relation.confidence || 0) > 0 
                            ? "bg-blue-500 hover:bg-blue-600" 
                            : "bg-gray-300 text-gray-600"
                        }
                      >
                        {relation.confidence || 0.0}
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
                        onClick={(relation.evidence_count || 0) > 0 ? () => handleViewSources(relation) : undefined}
                      >
                        {relation.evidence_count || 0} 条证据
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {relation.updated_at ? new Date(relation.updated_at).toLocaleString('zh-CN') : '未知'}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEditRelation(relation)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteRelation(relation.id)}
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
        </div>
        
        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-6 px-0">
            <div className="text-sm text-muted-foreground">
              共 {totalCount} 条记录，第 {currentPage} / {totalPages} 页
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage <= 1}
              >
                上一页
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage >= totalPages}
              >
                下一页
              </Button>
            </div>
          </div>
        )}
      </CardContent>

      {/* 编辑/新建对话框 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingRelation ? '编辑关联关系' : '新建关联关系'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {/* 产品选择 */}
                <div className="space-y-2">
                  <Label>产品</Label>
                  <Select value={selectedSubject} onValueChange={setSelectedSubject}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择产品" />
                    </SelectTrigger>
                    <SelectContent>
                      {products.map((product) => (
                        <SelectItem key={product.id} value={product.id.toString()}>
                          {product.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* 不良反应选择 */}
                <div className="space-y-2">
                  <Label>症状</Label>
                  <Select value={selectedObject} onValueChange={setSelectedObject}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择症状" />
                    </SelectTrigger>
                    <SelectContent>
                      {getSortedAdverseReactions().map((reaction) => (
                        <SelectItem 
                          key={reaction.id} 
                          value={reaction.id.toString()}
                          className={isReactionRelated(reaction.id) ? "bg-blue-50 border-l-4 border-l-blue-500 font-medium text-blue-700" : ""}
                        >
                          <div className="flex items-center justify-between w-full">
                            <span>{reaction.name || reaction.symptom_name}</span>
                            {isReactionRelated(reaction.id) && (
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
              </div>


              {/* 选择新闻 */}
              <div className="space-y-3">
                <Label>佐证数据 - 相关新闻与投诉</Label>
                
                {/* 如果是编辑模式，显示已关联新闻的详细信息 */}
                {editingRelation && currentRelationSources.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <FileText className="h-4 w-4 text-blue-500" />
                      已关联证据详情
                    </h4>
                    <div className="border rounded-md p-3 max-h-[200px] overflow-y-auto space-y-3">
                      {currentRelationSources.map((source) => (
                        <div key={source.id} className={`bg-muted/30 p-3 rounded border-l-4 ${
                          source.news_id ? 'border-l-blue-500' : 
                          source.complaint_id ? 'border-l-orange-500' : 
                          'border-l-gray-500'
                        }`}>
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <Badge variant="secondary" className="text-xs">
                                  {source.news_id ? '新闻' : source.complaint_id ? '投诉' : '其他'}
                                </Badge>
                              </div>
                              <h5 className="font-medium text-sm">
                                {source.news_info?.title || source.complaint_info?.title || '无标题'}
                              </h5>
                              <div className="flex gap-2 mt-1 text-xs text-muted-foreground">
                                <span>来源: {
                                  source.news_info?.source || 
                                  (source.complaint_info ? (source.complaint_info.source || '投诉来源') : '未知来源')
                                }</span>
                                <span>时间: {
                                  source.news_info?.publishTime ? 
                                    new Date(source.news_info.publishTime).toLocaleDateString('zh-CN') : 
                                    source.complaint_info?.publish_time ?
                                    new Date(source.complaint_info.publish_time).toLocaleDateString('zh-CN') :
                                    '未知'
                                }</span>
                              </div>
                              {source.complaint_info?.severity && (
                                <div className="flex gap-2 mt-1 text-xs text-muted-foreground">
                                  <span>严重程度: {source.complaint_info.severity}</span>
                                </div>
                              )}
                              <div className="flex items-center gap-2 mt-1">
                                <Badge variant="outline" className="text-xs">
                                  证据强度: {source.evidence_strength || 1.0}
                                </Badge>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 可选择的新闻列表 */}
                <div className="border rounded-md p-3 max-h-[300px] overflow-y-auto">
                  <h4 className="text-sm font-medium mb-2">可选择的新闻</h4>
                  {news.length === 0 ? (
                    <div className="text-center text-gray-500 py-4">
                      暂无新闻数据
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {news.slice(0, 10).map((item) => (
                        <div key={item.id} className="flex items-start space-x-3 p-2 hover:bg-muted/50 rounded">
                          <Checkbox
                            checked={selectedNewsIds.includes(item.id)}
                            onCheckedChange={() => toggleNewsSelection(item.id)}
                          />
                          <div className="flex-1">
                            <div className="font-medium text-sm">{item.title}</div>
                            <div className="text-xs text-gray-600 mt-1">
                              来源: {item.source} | 发布时间: {item.publishTime ? new Date(item.publishTime).toLocaleDateString('zh-CN') : '未知'}
                            </div>
                            {item.abstract && (
                              <div className="text-xs text-gray-500 mt-1 line-clamp-2">
                                {item.abstract}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                      {news.length > 10 && (
                        <div className="text-xs text-gray-500 text-center pt-2">
                          还有 {news.length - 10} 条新闻...
                        </div>
                      )}
                    </div>
                  )}
                </div>
                {/* 可选择的投诉列表 */}
                <div className="border rounded-md p-3 max-h-[300px] overflow-y-auto mt-4">
                  <h4 className="text-sm font-medium mb-2">可选择的投诉</h4>
                  {complaints.length === 0 ? (
                    <div className="text-center text-gray-500 py-4">
                      暂无投诉数据
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {complaints.slice(0, 10).map((item) => (
                        <div key={item.id} className="flex items-start space-x-3 p-2 hover:bg-muted/50 rounded">
                          <Checkbox
                            checked={selectedComplaintIds.includes(item.id.toString())}
                            onCheckedChange={() => toggleComplaintSelection(item.id.toString())}
                          />
                          <div className="flex-1">
                            <div className="font-medium text-sm">{item.title}</div>
                            <div className="text-xs text-gray-600 mt-1">
                              来源: {item.source || '未知来源'} | 投诉时间: {item.publish_time ? new Date(item.publish_time).toLocaleDateString('zh-CN') : '未知'}
                            </div>
                            {item.severity && (
                              <div className="text-xs text-orange-600 mt-1">
                                严重程度: {item.severity}
                              </div>
                            )}
                            {item.abstract && (
                              <div className="text-xs text-gray-500 mt-1 line-clamp-2">
                                {item.abstract}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                      {complaints.length > 10 && (
                        <div className="text-xs text-gray-500 text-center pt-2">
                          还有 {complaints.length - 10} 条投诉...
                        </div>
                      )}
                    </div>
                  )}
                </div>
                
                <p className="text-xs text-muted-foreground">
                  {editingRelation ? (
                    <>已关联 {currentRelationSources.filter(s => s.news_id).length} 条新闻、{currentRelationSources.filter(s => s.complaint_id).length} 条投诉，新选择 {selectedNewsIds.length} 条新闻、{selectedComplaintIds.length} 条投诉</>
                  ) : (
                    <>已选择 {selectedNewsIds.length} 条新闻、{selectedComplaintIds.length} 条投诉</>
                  )}
                </p>
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
        </DialogContent>
      </Dialog>

      {/* 证据来源管理对话框 */}
      <Dialog open={sourcesDialogOpen} onOpenChange={setSourcesDialogOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>证据来源管理</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* 添加新证据来源 */}
            <div className="border rounded-lg p-4 bg-gray-50">
              <h3 className="font-medium mb-3">添加新证据来源</h3>
              
              {/* 添加新闻证据来源 */}
              <div className="flex gap-2 mb-3">
                <Select value={selectedNewsForSource} onValueChange={setSelectedNewsForSource}>
                  <SelectTrigger className="flex-1">
                    <SelectValue placeholder="选择新闻作为证据来源" />
                  </SelectTrigger>
                  <SelectContent>
                    {news.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button onClick={handleAddNewsSource} disabled={!selectedNewsForSource}>
                  添加新闻证据
                </Button>
              </div>

              {/* 添加投诉证据来源 */}
              <div className="flex gap-2">
                <Select value={selectedComplaintForSource} onValueChange={setSelectedComplaintForSource}>
                  <SelectTrigger className="flex-1">
                    <SelectValue placeholder="选择投诉作为证据来源" />
                  </SelectTrigger>
                  <SelectContent>
                    {complaints.map((item) => (
                      <SelectItem key={item.id.toString()} value={item.id.toString()}>
                        {item.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button onClick={handleAddComplaintSource} disabled={!selectedComplaintForSource}>
                  添加投诉证据
                </Button>
              </div>
            </div>

            {/* 现有证据来源列表 */}
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>证据类型</TableHead>
                    <TableHead>标题</TableHead>
                    <TableHead>来源</TableHead>
                    <TableHead>发布时间</TableHead>
                    <TableHead>证据强度</TableHead>
                    <TableHead>备注</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentRelationSources.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                        暂无证据来源
                      </TableCell>
                    </TableRow>
                  ) : (
                    currentRelationSources.map((source) => (
                      <TableRow key={source.id}>
                        <TableCell>
                          <Badge variant="secondary">
                            {source.news_id ? '新闻' : source.medical_id ? '医疗' : source.complaint_id ? '投诉' : '其他'}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-xs">
                          <div className="truncate" title={
                            source.news_info?.title || 
                            source.complaint_info?.title || 
                            '无标题'
                          }>
                            {source.news_info?.title || 
                             source.complaint_info?.title || 
                             '无标题'}
                          </div>
                        </TableCell>
                        <TableCell>
                          {source.news_info?.source || 
                           (source.complaint_info ? (source.complaint_info.source || '投诉来源') : '未知来源')}
                        </TableCell>
                        <TableCell>
                          {source.news_info?.publishTime ? 
                            new Date(source.news_info.publishTime).toLocaleDateString('zh-CN') : 
                            source.complaint_info?.publish_time ?
                            new Date(source.complaint_info.publish_time).toLocaleDateString('zh-CN') :
                            '未知时间'
                          }
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {source.evidence_strength || 1.0}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-xs">
                          <div className="truncate" title={source.note || ''}>
                            {source.note || '无备注'}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSourcesDialogOpen(false)}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
});

ProductAdverseReactionManagementComponent.displayName = "ProductAdverseReactionManagementComponent";

export default ProductAdverseReactionManagementComponent;
