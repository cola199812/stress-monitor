"use client";

import React, { useState, useEffect, forwardRef, useImperativeHandle } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Checkbox } from "@/components/ui/checkbox";
import { Search, Plus, Edit, Trash2, FileText, Link2, ArrowRight, Star, TrendingUp, Activity, Shield } from "lucide-react";
import http from "@/lib/http";
import { toast } from "sonner";

// 类型定义
interface Allergen {
  id: number;
  name: string;
  category?: string;
}

interface Symptom {
  id: number;
  name: string;
  symptom_name?: string;
  category?: string;
}

interface Evidence {
  id: number;
  title: string;
  source: string;
  pmid?: string;
  authors?: string;
  literature_type?: string;
  abstract?: string;
}

interface LiteratureData {
  id: number;
  title: string;
  source: string;
  pmid?: string;
  authors?: string;
  literature_type: string;
  abstract?: string;
  keywords?: string;
  link?: string;
  publish_date?: string;
  scoring?: {
    type_display: string;
    reliability_score: number;
    correlation_score: number;
    concentration_weight: number;
    risk_intensity_score: number;
  };
}

interface AllergenSymptomRelationship {
  id: number;
  subject_id: number;
  subject_name: string;
  object_id: number;
  object_name: string;
  relation_type: string;
  evidence_count: number;
  literature_count: number;
  traec_score: number;
  created_at: string | null;
  updated_at: string | null;
}

interface AllergenSymptomManagementRef {
  handleSearch: (query: string) => void;
  handleAddRelation: () => void;
}

const AllergenSymptomManagement = forwardRef<AllergenSymptomManagementRef>((props, ref) => {
  // 状态管理
  const [relationships, setRelationships] = useState<AllergenSymptomRelationship[]>([]);
  const [loading, setLoading] = useState(false);
  
  // 实体数据
  const [allergens, setAllergens] = useState<Allergen[]>([]);
  const [symptoms, setSymptoms] = useState<Symptom[]>([]);
  
  // 搜索
  const [searchQuery, setSearchQuery] = useState("");

  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({
    handleSearch: (query: string) => {
      setSearchQuery(query);
      // 这里可以添加搜索逻辑
      fetchRelationships();
    },
    handleAddRelation: () => {
      // 调用内部的新建关系函数
      setEditingRelation(null);
      setSelectedSubject("");
      setSelectedObject("");
      setSelectedEvidences([]);
      fetchAvailableEvidences();
      setDialogOpen(true);
    }
  }));
  
  // 分页
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 10;
  
  // 新建/编辑关系对话框
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRelation, setEditingRelation] = useState<AllergenSymptomRelationship | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<string>("");
  const [selectedObject, setSelectedObject] = useState<string>("");
  const [selectedEvidences, setSelectedEvidences] = useState<number[]>([]);
  
  // 证据抽屉
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState(false);
  const [currentRelationEvidences, setCurrentRelationEvidences] = useState<Evidence[]>([]);
  
  // 文献数据抽屉
  const [literatureDrawerOpen, setLiteratureDrawerOpen] = useState(false);
  const [currentRelationLiteratures, setCurrentRelationLiteratures] = useState<LiteratureData[]>([]);
  const [currentRelationInfo, setCurrentRelationInfo] = useState<{allergen_name: string, symptom_name: string, relation_type: string} | null>(null);
  
  // 可用证据列表
  const [availableEvidences, setAvailableEvidences] = useState<Evidence[]>([]);

  // 批量选择
  const [selectedRows, setSelectedRows] = useState<number[]>([]);
  const [batchDeleting, setBatchDeleting] = useState(false);

  // 已存在的关联关系（用于高亮显示）
  const [existingRelations, setExistingRelations] = useState<{[key: string]: number[]}>({});

  // 根据选中的化学物质对症状进行排序和分类
  const getSortedSymptoms = () => {
    if (!selectedSubject || !symptoms.length) {
      return symptoms;
    }
    
    const relatedSymptomIds = existingRelations[selectedSubject] || [];
    const relatedSymptoms = symptoms.filter(symptom => relatedSymptomIds.includes(symptom.id));
    const unrelatedSymptoms = symptoms.filter(symptom => !relatedSymptomIds.includes(symptom.id));
    
    // 已关联的症状排在前面
    return [...relatedSymptoms, ...unrelatedSymptoms];
  };

  // 检查症状是否已与当前选中的化学物质关联
  const isSymptomRelated = (symptomId: number) => {
    if (!selectedSubject) return false;
    const relatedSymptomIds = existingRelations[selectedSubject] || [];
    return relatedSymptomIds.includes(symptomId);
  };

  // 文献类型转换为中文显示
  const getLiteratureTypeLabel = (type: string) => {
    switch (type) {
      case 'epidemiology': return '流行病学研究';
      case 'in-vivo': return '体内实验';
      case 'in-vitro': return '体外实验';
      default: return '流行病学研究';
    }
  };

  // 初始化数据
  useEffect(() => {
    fetchAllergens();
    fetchSymptoms();
    fetchAvailableEvidences();
    fetchRelationships();
    fetchExistingRelations();
  }, []);

  // 分页变化时重新加载数据
  useEffect(() => {
    fetchRelationships();
  }, [currentPage]);

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

  // 获取不良反应数据
  const fetchSymptoms = async () => {
    try {
      const response = await http.get('/entity/symptoms/level2');
      setSymptoms(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error("获取不良反应失败:", error);
      setSymptoms([]);
    }
  };

  // 获取已存在的关联关系（用于高亮显示）
  const fetchExistingRelations = async () => {
    try {
      const response = await http.get('/relationship/allergen-symptom/list', {
        params: {
          page_size: 1000 // 获取所有关系
        }
      });
      const data = response.data || response;
      const relations = data.items || [];
      
      // 构建关联关系映射：allergen_id -> [symptom_id1, symptom_id2, ...]
      const relationMap: {[key: string]: number[]} = {};
      relations.forEach((rel: any) => {
        const allergenId = rel.allergen_id.toString();
        if (!relationMap[allergenId]) {
          relationMap[allergenId] = [];
        }
        relationMap[allergenId].push(rel.symptom_id);
      });
      
      setExistingRelations(relationMap);
    } catch (error) {
      console.error("获取已存在关联关系失败:", error);
      setExistingRelations({});
    }
  };

  // 获取可用证据（文献）
  const fetchAvailableEvidences = async () => {
    try {
      const response = await http.get('/relationship/available-literature', {
        params: {
          page_size: 100
        }
      });
      const data = response.data || response;
      const evidences = (data.items || []).map((item: any) => ({
        id: item.id,
        title: item.title || '未命名文献',
        source: item.source || '文献来源',
        pmid: item.pmid,
        authors: item.authors,
        literature_type: item.literature_type,
        abstract: item.abstract
      }));
      setAvailableEvidences(evidences);
    } catch (error) {
      console.error('获取证据数据失败:', error);
      setAvailableEvidences([]);
    }
  };

  // 获取关系数据
  const fetchRelationships = async () => {
    setLoading(true);
    try {
      const response = await http.get('/relationship/allergen-symptom/list', {
        params: {
          page: currentPage,
          page_size: pageSize
        }
      });
      const data = response.data || response;
      
      if (data && data.items) {
        const formattedData: AllergenSymptomRelationship[] = data.items.map((item: any) => ({
          id: item.id,
          subject_id: item.allergen_id,
          subject_name: item.allergen_name,
          object_id: item.symptom_id,
          object_name: item.symptom_name,
          relation_type: item.relation || "引起",
          evidence_count: item.literature_count || 0,
          literature_count: item.literature_count || 0,
          traec_score: item.traec_score || 0,
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
    fetchAvailableEvidences();
    setDialogOpen(true);
  };

  // 打开编辑关系对话框
  const handleEditRelation = async (relation: AllergenSymptomRelationship) => {
    setEditingRelation(relation);
    setSelectedSubject(relation.subject_id.toString());
    setSelectedObject(relation.object_id.toString());
    setSelectedEvidences([]);
    
    // 获取已关联的文献
    try {
      const response = await http.get(`/relationship/allergen-symptom/${relation.id}/literature`);
      const data = response.data || response;
      if (data && data.literatures) {
        setCurrentRelationLiteratures(data.literatures);
        setSelectedEvidences(data.literatures.map((lit: LiteratureData) => lit.id));
      }
    } catch (error) {
      console.error('获取已关联文献失败:', error);
    }
    
    fetchAvailableEvidences();
    setDialogOpen(true);
  };

  // 保存关系
  const handleSaveRelation = async () => {
    if (!selectedSubject || !selectedObject) {
      toast.error("请选择化学应急源和不良反应");
      return;
    }

    try {
      if (editingRelation) {
        // 编辑模式
        const payload = {
          allergen_id: parseInt(selectedSubject),
          symptom_id: parseInt(selectedObject),
          literature_ids: selectedEvidences
        };
        
        await http.put(`/relationship/allergen-symptom/${editingRelation.id}`, payload);
        toast.success("关联关系更新成功");
      } else {
        // 新建模式
        const payload = {
          allergen_id: parseInt(selectedSubject),
          symptom_id: parseInt(selectedObject),
          literature_ids: selectedEvidences
        };
        
        await http.post('/relationship/allergen-symptom', payload);
        toast.success("关联关系创建成功");
      }
      
      setDialogOpen(false);
      fetchRelationships();
      fetchExistingRelations(); // 更新已存在的关联关系
    } catch (error) {
      console.error("保存关联关系失败:", error);
      toast.error("保存失败");
    }
  };

  // 删除关系
  const handleDeleteRelation = async (relationId: number) => {
    if (!confirm("确定要删除这个关联关系吗？")) {
      return;
    }

    try {
      await http.delete(`/relationship/allergen-symptom/${relationId}`);
      toast.success("关联关系删除成功");
      fetchRelationships();
      fetchExistingRelations(); // 更新已存在的关联关系
    } catch (error) {
      console.error("删除关联关系失败:", error);
      toast.error("删除失败");
    }
  };

  // 查看文献详情
  const handleViewLiteratures = async (relation: AllergenSymptomRelationship) => {
    try {
      const response = await http.get(`/relationship/allergen-symptom/${relation.id}/literature`);
      const data = response.data || response;
      if (data && data.literatures) {
        setCurrentRelationLiteratures(data.literatures);
        setCurrentRelationInfo({
          allergen_name: relation.subject_name,
          symptom_name: relation.object_name,
          relation_type: relation.relation_type
        });
        setLiteratureDrawerOpen(true);
      }
    } catch (error) {
      console.error('获取文献详情失败:', error);
      toast.error('获取文献详情失败');
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedRows.length === 0) return;
    if (!confirm(`确定要删除选中的 ${selectedRows.length} 条关联关系吗？`)) return;

    setBatchDeleting(true);
    try {
      const response = await http.delete('/relationship/allergen-symptom/batch-delete', {
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

  // 分页控制
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const renderPagination = () => {
    if (totalPages <= 1) return null;

    return (
      <div className="flex items-center justify-between mt-6 px-0">
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
          <span>化学应急源-不良反应关联管理</span>
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
                  <TableHead>化学应急源</TableHead>
                  <TableHead>不良反应</TableHead>
                  <TableHead>CSAR评分</TableHead>
                  <TableHead>佐证文献</TableHead>
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
                  relationships.map((rel) => (
                    <TableRow key={rel.id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedRows.includes(rel.id)}
                          onCheckedChange={(checked) => handleSelectRow(rel.id, !!checked)}
                        />
                      </TableCell>
                      <TableCell className="font-medium">{rel.subject_name}</TableCell>
                      <TableCell>{rel.object_name}</TableCell>
                      <TableCell>
                        <Badge 
                          variant="default" 
                          className={
                            (rel.literature_count || 0) > 0 
                              ? "bg-blue-500 hover:bg-blue-600" 
                              : "bg-gray-300 text-gray-600"
                          }
                        >
                          {rel.traec_score || 0}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge 
                          variant="default" 
                          className={
                            (rel.literature_count || 0) > 0 
                              ? "bg-blue-500 hover:bg-blue-600 cursor-pointer" 
                              : "bg-gray-300 text-gray-600 cursor-default"
                          }
                          onClick={(rel.literature_count || 0) > 0 ? () => handleViewLiteratures(rel) : undefined}
                        >
                          {rel.literature_count || 0} 条文献
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {rel.updated_at ? new Date(rel.updated_at).toLocaleString('zh-CN') : '-'}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm" onClick={() => handleEditRelation(rel)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="destructive" size="sm" onClick={() => handleDeleteRelation(rel.id)}>
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
          
          <div className="space-y-6 py-4">
            {/* 选择实体 */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>化学应急源</Label>
                <Select value={selectedSubject} onValueChange={setSelectedSubject}>
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
              
              <div className="space-y-2">
                <Label>不良反应</Label>
                <Select value={selectedObject} onValueChange={setSelectedObject}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择不良反应" />
                  </SelectTrigger>
                  <SelectContent>
                    {getSortedSymptoms().map((item) => (
                      <SelectItem 
                        key={item.id} 
                        value={item.id.toString()}
                        className={isSymptomRelated(item.id) ? "bg-blue-50 border-l-4 border-l-blue-500 font-medium text-blue-700" : ""}
                      >
                        <div className="flex items-center justify-between w-full">
                          <span>{item.name || item.symptom_name}</span>
                          {isSymptomRelated(item.id) && (
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

            {/* 选择文献 */}
            <div className="space-y-3">
              <Label>佐证数据 - 相关文献</Label>
              
              {/* 如果是编辑模式，显示已关联文献的详细信息 */}
              {editingRelation && 
               currentRelationLiteratures.filter(lit => selectedEvidences.includes(lit.id)).length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                    <FileText className="h-4 w-4 text-blue-500" />
                    已关联文献详情
                  </h4>
                  <div className="border rounded-md p-3 max-h-[200px] overflow-y-auto space-y-3">
                    {currentRelationLiteratures
                      .filter(literature => selectedEvidences.includes(literature.id))
                      .map((literature) => (
                      <div key={literature.id} className="bg-muted/30 p-3 rounded border-l-4 border-l-blue-500">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <h5 className="font-medium text-sm">{literature.title}</h5>
                            <div className="flex gap-2 mt-1 text-xs text-muted-foreground">
                              <span>来源: {literature.source}</span>
                              {literature.pmid && (
                                <span>PMID: {literature.pmid}</span>
                              )}
                              <span>类型: {getLiteratureTypeLabel(literature.literature_type)}</span>
                            </div>
                            <div className="flex items-center gap-2 mt-1">
                              {literature.scoring && (
                                <Badge variant="outline" className="text-xs">
                                  {literature.scoring.type_display}
                                </Badge>
                              )}
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleEvidence(literature.id)}
                            className="h-auto p-1 text-red-600 hover:text-red-700 hover:bg-red-50"
                            title="取消关联"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                        
                        {/* 评分信息 */}
                        {literature.scoring && (
                          <div className="grid grid-cols-2 gap-2 text-xs mt-2">
                            <div className="flex items-center gap-1">
                              <Shield className="h-3 w-3 text-green-600" />
                              <span>可靠性：{literature.scoring.reliability_score.toFixed(1)}/10</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <TrendingUp className="h-3 w-3 text-blue-600" />
                              <span>相关性：{literature.scoring.correlation_score}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <Activity className="h-3 w-3 text-purple-600" />
                              <span>浓度权重：{literature.scoring.concentration_weight.toFixed(2)}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <ArrowRight className="h-3 w-3 text-red-600" />
                              <span>风险强度：{literature.scoring.risk_intensity_score}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* 可选择的文献列表 */}
              <div className="border rounded-md p-3 max-h-[300px] overflow-y-auto">
                <h4 className="text-sm font-medium mb-2">可选择的文献</h4>
                {(() => {
                  // 过滤掉已关联且仍然选中的文献
                  // 如果已关联的文献被用户点击删除按钮（从selectedEvidences中移除），则应该显示在可选列表中
                  const stillLinkedIds = currentRelationLiteratures
                    .filter(lit => selectedEvidences.includes(lit.id))
                    .map(lit => lit.id);
                  const availableUnlinkedEvidences = availableEvidences.filter(evidence => 
                    !stillLinkedIds.includes(evidence.id)
                  );
                  
                  return availableUnlinkedEvidences.length === 0 ? (
                    <div className="text-center text-gray-500 py-4">
                      {availableEvidences.length === 0 ? "暂无文献数据" : "所有可用文献都已关联"}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {availableUnlinkedEvidences.map((evidence) => (
                        <div key={evidence.id} className="flex items-start space-x-3 p-2 hover:bg-muted/50 rounded">
                          <Checkbox
                            checked={selectedEvidences.includes(evidence.id)}
                            onCheckedChange={() => toggleEvidence(evidence.id)}
                          />
                          <div className="flex-1">
                            <div className="font-medium text-sm">{evidence.title}</div>
                            <div className="text-xs text-gray-600 mt-1">
                              来源: {evidence.source}
                              {evidence.pmid && ` | PMID: ${evidence.pmid}`}
                              {evidence.literature_type && ` | 类型: ${getLiteratureTypeLabel(evidence.literature_type)}`}
                            </div>
                            {evidence.abstract && (
                              <div className="text-xs text-gray-500 mt-1 line-clamp-2">
                                {evidence.abstract}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>
              <p className="text-xs text-muted-foreground">
                {editingRelation ? (
                  <>已关联 {currentRelationLiteratures.filter(lit => selectedEvidences.includes(lit.id)).length} 条文献，新选择 {selectedEvidences.filter(id => !currentRelationLiteratures.map(lit => lit.id).includes(id)).length} 条文献</>
                ) : (
                  <>已选择 {selectedEvidences.length} 条文献</>
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

      {/* 文献数据抽屉 */}
      <Sheet open={literatureDrawerOpen} onOpenChange={setLiteratureDrawerOpen}>
        <SheetContent className="w-[800px] sm:max-w-[800px]">
          <SheetHeader>
            <SheetTitle>文献数据详情</SheetTitle>
            <SheetDescription>
              {currentRelationInfo && (
                <span>
                  {currentRelationInfo.allergen_name} {currentRelationInfo.relation_type} {currentRelationInfo.symptom_name} 的文献支撑数据
                </span>
              )}
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6 space-y-4 max-h-[calc(100vh-200px)] overflow-y-auto">
            {currentRelationLiteratures.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                暂无文献数据
              </p>
            ) : (
              currentRelationLiteratures.map((literature, index) => (
                <Card key={literature.id} className="border-l-4 border-l-blue-500">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="outline">文献 {index + 1}</Badge>
                          <Badge variant="secondary" className="text-xs">
                            {literature.source}
                          </Badge>
                          {literature.pmid && (
                            <Badge variant="default" className="text-xs">
                              PMID: {literature.pmid}
                            </Badge>
                          )}
                          <Badge variant="outline" className="text-xs">
                            {getLiteratureTypeLabel(literature.literature_type)}
                          </Badge>
                        </div>
                        <h4 className="font-medium text-base mb-2">{literature.title}</h4>
                        {literature.authors && (
                          <p className="text-sm text-muted-foreground mb-1">
                            <span className="font-medium">作者：</span>{literature.authors}
                          </p>
                        )}
                        {literature.publish_date && (
                          <p className="text-sm text-muted-foreground mb-2">
                            <span className="font-medium">发布日期：</span>{new Date(literature.publish_date).toLocaleDateString('zh-CN')}
                          </p>
                        )}
                        
                        {/* 评分信息 */}
                        {literature.scoring && (
                          <div className="mt-3 p-3 bg-muted/50 rounded-lg">
                            <h5 className="font-medium text-sm mb-2 flex items-center gap-2">
                              <Star className="h-4 w-4" />
                              评分信息
                            </h5>
                            <div className="grid grid-cols-2 gap-3 text-sm">
                              <div className="flex items-center gap-2">
                                <Shield className="h-4 w-4 text-green-600" />
                                <span className="font-medium">可靠性得分：</span>
                                <Badge variant="outline">{literature.scoring.reliability_score.toFixed(1)}/10</Badge>
                              </div>
                              <div className="flex items-center gap-2">
                                <TrendingUp className="h-4 w-4 text-blue-600" />
                                <span className="font-medium">相关性得分：</span>
                                <Badge variant="outline">{literature.scoring.correlation_score}</Badge>
                              </div>
                              <div className="flex items-center gap-2">
                                <Activity className="h-4 w-4 text-purple-600" />
                                <span className="font-medium">浓度权重：</span>
                                <Badge variant="outline">{literature.scoring.concentration_weight.toFixed(2)}</Badge>
                              </div>
                              <div className="flex items-center gap-2">
                                <ArrowRight className="h-4 w-4 text-red-600" />
                                <span className="font-medium">风险强度：</span>
                                <Badge variant="outline">{literature.scoring.risk_intensity_score}</Badge>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  {literature.abstract && (
                    <CardContent className="pt-0">
                      <div className="space-y-2">
                        <p className="text-sm font-medium">摘要：</p>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {literature.abstract}
                        </p>
                      </div>
                      {literature.keywords && (
                        <div className="mt-3">
                          <p className="text-sm font-medium mb-1">关键词：</p>
                          <p className="text-sm text-muted-foreground">{literature.keywords}</p>
                        </div>
                      )}
                      {literature.link && (
                        <div className="mt-3">
                          <a 
                            href={literature.link} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-sm text-blue-600 hover:underline flex items-center gap-1"
                          >
                            <Link2 className="h-3 w-3" />
                            查看原文
                          </a>
                        </div>
                      )}
                    </CardContent>
                  )}
                </Card>
              ))
            )}
          </div>
        </SheetContent>
      </Sheet>
    </Card>
  );
});

AllergenSymptomManagement.displayName = "AllergenSymptomManagement";

export default AllergenSymptomManagement;
