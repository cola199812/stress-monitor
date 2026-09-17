"use client";

import React, { useState, useEffect, forwardRef, useImperativeHandle } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Trash2, Plus, ChevronDown, ChevronUp } from "lucide-react";
import { toast } from "sonner";
import http from "@/lib/http";

// 类型定义
interface LiteratureEditConfig {
  title: string;
  apiEndpoint: string;
  enableRelations: boolean;
}

interface DataItem {
  id?: number;
  [key: string]: any;
}

interface Allergen {
  id: number;
  name: string;
}

interface Symptom {
  id: number;
  name?: string;
  symptom_name: string;
}

interface ScoringData {
  concentrationWeight?: any;
  reliabilityScores?: Record<string, { score: string; comment: string }>;
  correlation?: string;
  riskIntensity?: string;
}

interface EntityRelation {
  id?: number;
  allergen_id: number;
  allergen_name?: string;
  symptom_id: number;
  symptom_name?: string;
  relation?: string;
  literatureType: 'epidemiology' | 'in-vivo' | 'in-vitro';
  scoringData: ScoringData;
}

interface ExistingRelation {
  allergen_id: number;
  symptom_id: number;
}

interface LiteratureEditProps {
  config: LiteratureEditConfig;
  onSave?: () => void;
}

export interface LiteratureEditRef {
  open: (item?: DataItem) => void;
}

const LiteratureEdit = forwardRef<LiteratureEditRef, LiteratureEditProps>(({ config, onSave }, ref) => {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [editingItem, setEditingItem] = useState<DataItem | null>(null);
  
  const [formData, setFormData] = useState({
    title: '',
    source: '',
    authors: '',
    publishDate: '',
    abstract: '',
    link: '',
    pmid: '',
    literatureType: 'epidemiology' as 'epidemiology' | 'in-vivo' | 'in-vitro'
  });

  const [entityRelations, setEntityRelations] = useState<EntityRelation[]>([]);
  const [allergens, setAllergens] = useState<Allergen[]>([]);
  const [symptoms, setSymptoms] = useState<Symptom[]>([]);
  const [existingRelations, setExistingRelations] = useState<ExistingRelation[]>([]);
  const [activeTab, setActiveTab] = useState("basic");
  const [expandedScoring, setExpandedScoring] = useState<{ [key: number]: boolean }>({});

  useImperativeHandle(ref, () => ({
    open: (item?: DataItem) => {
      setEditingItem(item || null);
      setIsOpen(true);
      if (item) {
        loadEditData(item);
      } else {
        resetForm();
      }
    }
  }));

  useEffect(() => {
    if (isOpen && config.enableRelations) {
      loadAllergens();
      loadSymptoms();
      loadExistingRelations();
    }
  }, [isOpen, config.enableRelations]);

  const loadAllergens = async () => {
    try {
      const response = await http.get('/entity/allergens');
      const data = response.data?.data || response.data || response;
      setAllergens(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('加载过敏原失败:', error);
      setAllergens([]);
    }
  };

  const loadSymptoms = async () => {
    try {
      const response = await http.get('/entity/symptoms/level2');
      const data = response.data?.data || response.data || response;
      setSymptoms(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('加载症状失败:', error);
      setSymptoms([]);
    }
  };

  const loadExistingRelations = async () => {
    try {
      const response = await http.get('/relationship/allergen-symptom/list?page_size=1000');
      console.log('[Literature Edit] 加载已存在关系响应:', response);
      
      // 正确解析后端返回的数据格式
      const data = response.data?.data?.items || response.data?.items || [];
      console.log('[Literature Edit] 解析后的关系数据:', data);
      
      setExistingRelations(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('加载已存在关系失败:', error);
      setExistingRelations([]);
    }
  };

  const loadEditData = (item: DataItem) => {
    console.log('[Literature Edit] 加载编辑数据:', item);
    
    setFormData({
      title: item.title || '',
      source: item.source || '',
      authors: item.authors || '',
      publishDate: item.publishDate || '',
      abstract: item.abstract || '',
      link: item.link || '',
      pmid: item.pmid || '',
      literatureType: item.literatureType || 'epidemiology'
    });

    if (item.entityRelations && Array.isArray(item.entityRelations)) {
      console.log('[Literature Edit] 原始实体关系数据:', item.entityRelations);
      
      const relations = item.entityRelations.map((rel: any) => ({
        allergen_id: rel.allergen_id || 0,
        allergen_name: rel.allergen_name || '',
        symptom_id: rel.symptom_id || 0,
        symptom_name: rel.symptom_name || '',
        relation: rel.relation || '',
        literatureType: rel.literatureType || 'epidemiology',
        scoringData: rel.scoringData || {}
      }));
      
      console.log('[Literature Edit] 转换后的关系数据:', relations);
      console.log('[Literature Edit] 第一个关系的评分数据:', relations[0]?.scoringData);
      
      setEntityRelations(relations);
    } else {
      setEntityRelations([]);
    }
  };

  const resetForm = () => {
    setFormData({
      title: '',
      source: '',
      authors: '',
      publishDate: '',
      abstract: '',
      link: '',
      pmid: '',
      literatureType: 'epidemiology'
    });
    setEntityRelations([]);
    setExpandedScoring({});
  };

  const handleAddRelation = () => {
    setEntityRelations([...entityRelations, {
      allergen_id: 0,
      symptom_id: 0,
      literatureType: formData.literatureType,
      scoringData: {}
    }]);
  };

  const handleRemoveRelation = (index: number) => {
    setEntityRelations(entityRelations.filter((_, i) => i !== index));
    const newExpanded = { ...expandedScoring };
    delete newExpanded[index];
    setExpandedScoring(newExpanded);
  };

  const handleRelationChange = (index: number, field: string, value: any) => {
    const newRelations = [...entityRelations];
    newRelations[index] = { ...newRelations[index], [field]: value };
    setEntityRelations(newRelations);
  };

  const handleScoringDataChange = (index: number, path: string[], value: any) => {
    const newRelations = [...entityRelations];
    let target: any = newRelations[index].scoringData;
    
    for (let i = 0; i < path.length - 1; i++) {
      if (!target[path[i]]) {
        target[path[i]] = {};
      }
      target = target[path[i]];
    }
    
    target[path[path.length - 1]] = value;
    setEntityRelations(newRelations);
  };

  const isRelationExists = (allergerId: number, symptomId: number): boolean => {
    return existingRelations.some(rel => rel.allergen_id === allergerId && rel.symptom_id === symptomId);
  };

  const getSortedAllergens = (selectedSymptomId?: number) => {
    if (!selectedSymptomId) return allergens;
    
    return [...allergens].sort((a, b) => {
      const aExists = isRelationExists(a.id, selectedSymptomId);
      const bExists = isRelationExists(b.id, selectedSymptomId);
      if (aExists && !bExists) return -1;
      if (!aExists && bExists) return 1;
      return 0;
    });
  };

  const getSortedSymptoms = (selectedAllergerId?: number) => {
    if (!selectedAllergerId) return symptoms;
    
    return [...symptoms].sort((a, b) => {
      const aExists = isRelationExists(selectedAllergerId, a.id);
      const bExists = isRelationExists(selectedAllergerId, b.id);
      if (aExists && !bExists) return -1;
      if (!aExists && bExists) return 1;
      return 0;
    });
  };

  const handleSave = async () => {
    if (!formData.title || !formData.source) {
      toast.error('请填写必填字段');
      return;
    }

    if (config.enableRelations && entityRelations.length > 0) {
      for (let i = 0; i < entityRelations.length; i++) {
        const rel = entityRelations[i];
        if (!rel.allergen_id || !rel.symptom_id) {
          toast.error(`请完善第 ${i + 1} 个实体关系的信息`);
          return;
        }
      }
    }

    setLoading(true);
    try {
      const requestData = {
        basicInfo: formData,
        entityRelations: entityRelations.map(rel => ({
          allergenId: rel.allergen_id,
          symptomId: rel.symptom_id,
          scoringData: rel.scoringData
        }))
      };

      if (editingItem) {
        await http.put(`${config.apiEndpoint}/${editingItem.id}`, requestData);
        toast.success(`${config.title}更新成功`);
      } else {
        await http.post(`${config.apiEndpoint}/create`, requestData);
        toast.success(`${config.title}创建成功`);
      }

      setIsOpen(false);
      onSave?.();
    } catch (error) {
      console.error(`保存${config.title}失败:`, error);
      toast.error(`保存${config.title}失败`);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    resetForm();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editingItem ? `编辑${config.title}` : `新建${config.title}`}</DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="basic">基础信息</TabsTrigger>
            <TabsTrigger value="relations">实体关系</TabsTrigger>
          </TabsList>

          <TabsContent value="basic" className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-1">
                <Label>标题 *</Label>
                <Input
                  value={formData.title || ''}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="请输入标题"
                />
              </div>
              <div className="col-span-1">
                <Label>发布日期</Label>
                <Input
                  type="date"
                  value={formData.publishDate || ''}
                  onChange={(e) => setFormData({ ...formData, publishDate: e.target.value })}
                />
              </div>
              <div className="col-span-1">
                <Label>来源 *</Label>
                <Input
                  value={formData.source || ''}
                  onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                  placeholder="请输入来源"
                />
              </div>
              <div className="col-span-1">
                <Label>PMID</Label>
                <Input
                  value={formData.pmid || ''}
                  onChange={(e) => setFormData({ ...formData, pmid: e.target.value })}
                  placeholder="请输入PMID"
                />
              </div>
              <div className="col-span-1">
                <Label>作者</Label>
                <Input
                  value={formData.authors || ''}
                  onChange={(e) => setFormData({ ...formData, authors: e.target.value })}
                  placeholder="请输入作者"
                />
              </div>
              <div className="col-span-1">
                <Label>文献类型 *</Label>
                <Select
                  value={formData.literatureType}
                  onValueChange={(value: any) => setFormData({ ...formData, literatureType: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="epidemiology">流行病学</SelectItem>
                    <SelectItem value="in-vivo">体内实验</SelectItem>
                    <SelectItem value="in-vitro">体外实验</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="col-span-2">
                <Label>链接</Label>
                <Input
                  value={formData.link || ''}
                  onChange={(e) => setFormData({ ...formData, link: e.target.value })}
                  placeholder="请输入链接"
                />
              </div>
              <div className="col-span-2">
                <Label>摘要</Label>
                <Textarea
                  value={formData.abstract || ''}
                  onChange={(e) => setFormData({ ...formData, abstract: e.target.value })}
                  placeholder="请输入摘要"
                  rows={4}
                />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="relations" className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">实体关系列表</h3>
              <Button size="sm" onClick={handleAddRelation}>
                <Plus className="h-4 w-4 mr-1" />
                新增关系
              </Button>
            </div>

            {entityRelations.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                暂无实体关系，点击"新增关系"添加
              </div>
            ) : (
              <div className="space-y-4">
                {entityRelations.map((relation, index) => (
                  <Card key={index} className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <Badge variant="outline">关系 {index + 1}</Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveRelation(index)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-sm">化学应激源</Label>
                        <Select
                          value={relation.allergen_id?.toString() || ''}
                          onValueChange={(value) => handleRelationChange(index, 'allergen_id', parseInt(value))}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="选择化学应激源" />
                          </SelectTrigger>
                          <SelectContent>
                            {getSortedAllergens(relation.symptom_id).map((allergen) => {
                              const hasRelation = relation.symptom_id && isRelationExists(allergen.id, relation.symptom_id);
                              return (
                                <SelectItem
                                  key={allergen.id}
                                  value={allergen.id.toString()}
                                  className={hasRelation ? 'text-blue-600 font-medium' : ''}
                                >
                                  {allergen.name}
                                </SelectItem>
                              );
                            })}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-sm">症状</Label>
                        <Select
                          value={relation.symptom_id?.toString() || ''}
                          onValueChange={(value) => handleRelationChange(index, 'symptom_id', parseInt(value))}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="选择症状" />
                          </SelectTrigger>
                          <SelectContent>
                            {getSortedSymptoms(relation.allergen_id).map((symptom) => {
                              const hasRelation = relation.allergen_id && isRelationExists(relation.allergen_id, symptom.id);
                              return (
                                <SelectItem
                                  key={symptom.id}
                                  value={symptom.id.toString()}
                                  className={hasRelation ? 'text-blue-600 font-medium' : ''}
                                >
                                  {symptom.name || symptom.symptom_name}
                                </SelectItem>
                              );
                            })}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {relation.allergen_id && relation.symptom_id && (
                      <div className="mt-3 border-t pt-3">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="w-full flex items-center justify-between"
                          onClick={() => setExpandedScoring(prev => ({ ...prev, [index]: !prev[index] }))}
                        >
                          <span className="font-medium text-sm">评分打分</span>
                          {expandedScoring[index] ? (
                            <ChevronUp className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                        </Button>
                        
                        {expandedScoring[index] && (
                          <div className="space-y-4 mt-4 p-4 border rounded-lg bg-gray-50">
                            {/* 流行病学评分 */}
                            {formData.literatureType === 'epidemiology' && (
                              <div className="space-y-4">
                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-blue-100 text-blue-600 text-xs font-bold flex items-center justify-center">I</div>
                                    浓度权重
                                  </h5>
                                  <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1">
                                      <Label className="text-xs">暴露模式</Label>
                                      <Select 
                                        value={relation.scoringData?.concentrationWeight?.modeOfExposure || ''}
                                        onValueChange={(value) => handleScoringDataChange(index, ['concentrationWeight', 'modeOfExposure'], value)}
                                      >
                                        <SelectTrigger className="h-9">
                                          <SelectValue placeholder="选择暴露模式" />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="oral">内暴露</SelectItem>
                                          <SelectItem value="dermal">外暴露</SelectItem>
                                          <SelectItem value="inhalation">其他</SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </div>
                                    <div className="space-y-1">
                                      <Label className="text-xs">生物样本类型</Label>
                                      <Select 
                                        value={relation.scoringData?.concentrationWeight?.typeOfBiosample || ''}
                                        onValueChange={(value) => handleScoringDataChange(index, ['concentrationWeight', 'typeOfBiosample'], value)}
                                      >
                                        <SelectTrigger className="h-9">
                                          <SelectValue placeholder="选择样本类型" />
                                        </SelectTrigger>
                                        <SelectContent>
                                          {relation.scoringData?.concentrationWeight?.modeOfExposure === 'oral' ? (
                                            <>
                                              <SelectItem value="serum">血清</SelectItem>
                                              <SelectItem value="whole_blood">全血</SelectItem>
                                              <SelectItem value="plasma">血浆</SelectItem>
                                              <SelectItem value="urine">尿液</SelectItem>
                                              <SelectItem value="feces">粪便</SelectItem>
                                              <SelectItem value="adipose">脂肪组织</SelectItem>
                                              <SelectItem value="other">其他</SelectItem>
                                            </>
                                          ) : relation.scoringData?.concentrationWeight?.modeOfExposure === 'dermal' ? (
                                            <>
                                              <SelectItem value="drinking_water">饮用水</SelectItem>
                                              <SelectItem value="dust">灰尘</SelectItem>
                                              <SelectItem value="food">食物</SelectItem>
                                              <SelectItem value="other">其他</SelectItem>
                                            </>
                                          ) : (
                                            <>
                                              <SelectItem value="serum">血清</SelectItem>
                                              <SelectItem value="whole_blood">全血</SelectItem>
                                              <SelectItem value="plasma">血浆</SelectItem>
                                              <SelectItem value="urine">尿液</SelectItem>
                                              <SelectItem value="feces">粪便</SelectItem>
                                              <SelectItem value="adipose">脂肪组织</SelectItem>
                                              <SelectItem value="drinking_water">饮用水</SelectItem>
                                              <SelectItem value="dust">灰尘</SelectItem>
                                              <SelectItem value="food">食物</SelectItem>
                                              <SelectItem value="other">其他</SelectItem>
                                            </>
                                          )}
                                        </SelectContent>
                                      </Select>
                                    </div>
                                    <div className="space-y-1">
                                      <Label className="text-xs">浓度</Label>
                                      <div className="flex gap-2">
                                        <Input 
                                          type="number" 
                                          placeholder="输入浓度值" 
                                          className="h-9 flex-1" 
                                          value={relation.scoringData?.concentrationWeight?.concentrations || ''}
                                          onChange={(e) => handleScoringDataChange(index, ['concentrationWeight', 'concentrations'], e.target.value)}
                                        />
                                        <Select 
                                          value={relation.scoringData?.concentrationWeight?.concentrationUnit || 'mg/L'}
                                          onValueChange={(value) => handleScoringDataChange(index, ['concentrationWeight', 'concentrationUnit'], value)}
                                        >
                                          <SelectTrigger className="h-9 w-24">
                                            <SelectValue />
                                          </SelectTrigger>
                                          <SelectContent>
                                            <SelectItem value="mg/L">mg/L</SelectItem>
                                            <SelectItem value="μg/L">μg/L</SelectItem>
                                            <SelectItem value="ng/g">ng/g</SelectItem>
                                            <SelectItem value="mg/g">mg/g</SelectItem>
                                            <SelectItem value="ppm">ppm</SelectItem>
                                          </SelectContent>
                                        </Select>
                                      </div>
                                    </div>
                                    <div className="space-y-1">
                                      <Label className="text-xs">转换因子</Label>
                                      <Input 
                                        type="number" 
                                        placeholder="可选" 
                                        className="h-9" 
                                        value={relation.scoringData?.concentrationWeight?.conversionFactor || ''}
                                        onChange={(e) => handleScoringDataChange(index, ['concentrationWeight', 'conversionFactor'], e.target.value)}
                                      />
                                    </div>
                                  </div>
                                </Card>

                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-green-100 text-green-600 text-xs font-bold flex items-center justify-center">II</div>
                                    可靠性得分 (0-10分)
                                  </h5>
                                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                                    {[
                                      "研究对象的基本信息是否充分，如年龄、性别和 BMI 等？",
                                      "研究样本量是否充分且合理？",
                                      "设计方案是否适合验证毒物的特点？例如选取的暴露人群、时间和模式。",
                                      "是否纳入对照组，如阳性对照、阴性对照、父亲对照或自身对照？",
                                      "暴露检测或评估的方法是否科学恰当？",
                                      "是否明确描述研究终点及其测定方法？",
                                      "是否适当且透明的提供与使用了数据分析的统计方法？",
                                      "是否清晰和完整的描述了研究结果？",
                                      "纳入/排除人群以及/或低暴露组的基线数据均衡可比，并控制相要混杂因素。",
                                      "描述实施过程中的质量控制措施，如现场监督、样品或问卷的质量控制措施等。"
                                    ].map((question, qIdx) => (
                                      <div key={qIdx} className="flex items-center gap-2 p-2 border rounded">
                                        <div className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-200 text-slate-700 text-xs font-bold shrink-0">
                                          {qIdx + 1}
                                        </div>
                                        <p className="text-xs flex-1">{question}</p>
                                        <Select 
                                          value={relation.scoringData?.reliabilityScores?.[`q${qIdx + 1}`]?.score || "1"}
                                          onValueChange={(value) => handleScoringDataChange(index, ['reliabilityScores', `q${qIdx + 1}`, 'score'], value)}
                                        >
                                          <SelectTrigger className="w-32 h-8">
                                            <SelectValue />
                                          </SelectTrigger>
                                          <SelectContent>
                                            <SelectItem value="1">满足 (1分)</SelectItem>
                                            <SelectItem value="0.5">部分满足 (0.5分)</SelectItem>
                                            <SelectItem value="0">不满足 (0分)</SelectItem>
                                          </SelectContent>
                                        </Select>
                                        <Input 
                                          placeholder="Comment" 
                                          className="w-40 h-8 text-xs" 
                                          value={relation.scoringData?.reliabilityScores?.[`q${qIdx + 1}`]?.comment || ''}
                                          onChange={(e) => handleScoringDataChange(index, ['reliabilityScores', `q${qIdx + 1}`, 'comment'], e.target.value)}
                                        />
                                      </div>
                                    ))}
                                  </div>
                                </Card>

                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-purple-100 text-purple-600 text-xs font-bold flex items-center justify-center">III</div>
                                    相关性
                                  </h5>
                                  <Select 
                                    value={relation.scoringData?.correlation || '1'}
                                    onValueChange={(value) => handleScoringDataChange(index, ['correlation'], value)}
                                  >
                                    <SelectTrigger className="h-9">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="1">正相关 (1分)</SelectItem>
                                      <SelectItem value="0">负相关 (0分)</SelectItem>
                                      <SelectItem value="-1">无相关 (-1分)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </Card>

                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 text-xs font-bold flex items-center justify-center">IV</div>
                                    风险强度
                                  </h5>
                                  <Select 
                                    value={relation.scoringData?.riskIntensity || '1'}
                                    onValueChange={(value) => handleScoringDataChange(index, ['riskIntensity'], value)}
                                  >
                                    <SelectTrigger className="h-9">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="1">高风险强度 (1分)</SelectItem>
                                      <SelectItem value="0.8">中等风险强度 (0.8分)</SelectItem>
                                      <SelectItem value="0.4">低风险强度 (0.4分)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </Card>
                              </div>
                            )}

                            {formData.literatureType === 'in-vivo' && (
                              <div className="space-y-4">
                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-blue-100 text-blue-600 text-xs font-bold flex items-center justify-center">I</div>
                                    浓度权重
                                  </h5>
                                  <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1">
                                      <Label className="text-xs">模型类型</Label>
                                      <Select 
                                        value={relation.scoringData?.concentrationWeight?.typeOfModel || ''}
                                        onValueChange={(value) => handleScoringDataChange(index, ['concentrationWeight', 'typeOfModel'], value)}
                                      >
                                        <SelectTrigger className="h-9">
                                          <SelectValue placeholder="选择模型类型" />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="mice">小鼠</SelectItem>
                                          <SelectItem value="rat">大鼠</SelectItem>
                                          <SelectItem value="cavy">豚鼠</SelectItem>
                                          <SelectItem value="rabbit">兔子</SelectItem>
                                          <SelectItem value="monkey">猕猴</SelectItem>
                                          <SelectItem value="dog">狗</SelectItem>
                                          <SelectItem value="zebrafish">斑马鱼</SelectItem>
                                          <SelectItem value="other">其他</SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </div>
                                    <div className="space-y-1">
                                      <Label className="text-xs">暴露模式</Label>
                                      <Select 
                                        value={relation.scoringData?.concentrationWeight?.modeOfExposure || ''}
                                        onValueChange={(value) => handleScoringDataChange(index, ['concentrationWeight', 'modeOfExposure'], value)}
                                      >
                                        <SelectTrigger className="h-9">
                                          <SelectValue placeholder="选择暴露模式" />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="inhalation">口服暴露</SelectItem>
                                          <SelectItem value="oral">吸入暴露</SelectItem>
                                          <SelectItem value="dermal">皮肤暴露</SelectItem>
                                          <SelectItem value="transplacental">胎盘接触</SelectItem>
                                          <SelectItem value="ocular ">眼部暴露</SelectItem>
                                          <SelectItem value="other">其他</SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </div>
                                    <div className="space-y-1">
                                      <Label className="text-xs">剂量</Label>
                                      <div className="flex gap-2">
                                        <Input 
                                          type="number" 
                                          placeholder="输入剂量" 
                                          className="h-9 flex-1" 
                                          value={relation.scoringData?.concentrationWeight?.dose || ''}
                                          onChange={(e) => handleScoringDataChange(index, ['concentrationWeight', 'dose'], e.target.value)}
                                        />
                                        <Select 
                                          value={relation.scoringData?.concentrationWeight?.doseUnit || 'mg/kg/d'}
                                          onValueChange={(value) => handleScoringDataChange(index, ['concentrationWeight', 'doseUnit'], value)}
                                        >
                                          <SelectTrigger className="h-9 w-28">
                                            <SelectValue />
                                          </SelectTrigger>
                                          <SelectContent>
                                            <SelectItem value="mg/kg/d">mg/kg/d</SelectItem>
                                            <SelectItem value="mg/L">mg/L</SelectItem>
                                          </SelectContent>
                                        </Select>
                                      </div>
                                    </div>
                                    <div className="space-y-1">
                                      <Label className="text-xs">NOAEL</Label>
                                      <Input 
                                        type="number" 
                                        placeholder="输入NOAEL" 
                                        className="h-9" 
                                        value={relation.scoringData?.concentrationWeight?.noael || ''}
                                        onChange={(e) => handleScoringDataChange(index, ['concentrationWeight', 'noael'], e.target.value)}
                                      />
                                    </div>
                                    <div className="col-span-2 space-y-1">
                                      <Label className="text-xs">转换因子</Label>
                                      <Input 
                                        type="number" 
                                        placeholder="可选" 
                                        className="h-9" 
                                        value={relation.scoringData?.concentrationWeight?.conversionFactors || ''}
                                        onChange={(e) => handleScoringDataChange(index, ['concentrationWeight', 'conversionFactors'], e.target.value)}
                                      />
                                    </div>
                                  </div>
                                </Card>

                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-green-100 text-green-600 text-xs font-bold flex items-center justify-center">II</div>
                                    可靠性得分 (0-10分)
                                  </h5>
                                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                                    {[
                                      "是否提供试验化学物的化学名称、来源以及纯度？",
                                      "是否使用合适的溶剂（载体）？其在试验浓度下不会干扰结果，并加入溶剂（载体）对照。",
                                      "用于研究试验化学物和选定终点的动物模型是否可靠和敏感？",
                                      "是否描述动物模型的物种、品系、年龄或生命阶段和性别？",
                                      "是否有合理的染毒模式？对染毒时间、剂量和途径均有明确解释。",
                                      "是否规定将动物分配到不同染毒组的方法和每个剂量组的动物总数？",
                                      "是否充分描述所使用的测试和分析方法，以评估结果的可靠性？",
                                      "是否报告关于试验终点的所有研究结果？对变化趋势的描述和具有统计意义的结果以表格和图表形式呈现。",
                                      "各研究组的实验条件是否相同？",
                                      "结果评估方法是否可靠？"
                                    ].map((question, qIdx) => (
                                      <div key={qIdx} className="flex items-center gap-2 p-2 border rounded">
                                        <div className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-200 text-slate-700 text-xs font-bold shrink-0">
                                          {qIdx + 1}
                                        </div>
                                        <p className="text-xs flex-1">{question}</p>
                                        <Select 
                                          value={relation.scoringData?.reliabilityScores?.[`q${qIdx + 1}`]?.score || "1"}
                                          onValueChange={(value) => handleScoringDataChange(index, ['reliabilityScores', `q${qIdx + 1}`, 'score'], value)}
                                        >
                                          <SelectTrigger className="w-32 h-8">
                                            <SelectValue />
                                          </SelectTrigger>
                                          <SelectContent>
                                            <SelectItem value="1">满足 (1分)</SelectItem>
                                            <SelectItem value="0.5">部分满足 (0.5分)</SelectItem>
                                            <SelectItem value="0">不满足 (0分)</SelectItem>
                                          </SelectContent>
                                        </Select>
                                        <Input 
                                          placeholder="Comment" 
                                          className="w-40 h-8 text-xs" 
                                          value={relation.scoringData?.reliabilityScores?.[`q${qIdx + 1}`]?.comment || ''}
                                          onChange={(e) => handleScoringDataChange(index, ['reliabilityScores', `q${qIdx + 1}`, 'comment'], e.target.value)}
                                        />
                                      </div>
                                    ))}
                                  </div>
                                </Card>

                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-purple-100 text-purple-600 text-xs font-bold flex items-center justify-center">III</div>
                                    相关性
                                  </h5>
                                  <Select 
                                    value={relation.scoringData?.correlation || '1'}
                                    onValueChange={(value) => handleScoringDataChange(index, ['correlation'], value)}
                                  >
                                    <SelectTrigger className="h-9">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="1">正相关 (1分)</SelectItem>
                                      <SelectItem value="0">负相关 (0分)</SelectItem>
                                      <SelectItem value="-1">无相关 (-1分)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </Card>

                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 text-xs font-bold flex items-center justify-center">IV</div>
                                    风险强度
                                  </h5>
                                  <Select 
                                    value={relation.scoringData?.riskIntensity || '1'}
                                    onValueChange={(value) => handleScoringDataChange(index, ['riskIntensity'], value)}
                                  >
                                    <SelectTrigger className="h-9">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="1">高风险强度 (1分)</SelectItem>
                                      <SelectItem value="0.8">中等风险强度 (0.8分)</SelectItem>
                                      <SelectItem value="0.4">低风险强度 (0.4分)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </Card>
                              </div>
                            )}

                            {/* 体外实验评分 */}
                            {formData.literatureType === 'in-vitro' && (
                              <div className="space-y-4">
                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-blue-100 text-blue-600 text-xs font-bold flex items-center justify-center">I</div>
                                    浓度权重
                                  </h5>
                                  <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1">
                                      <Label className="text-xs">剂量</Label>
                                      <div className="flex gap-2">
                                        <Input 
                                          type="number" 
                                          placeholder="输入剂量" 
                                          className="h-9 flex-1" 
                                          value={relation.scoringData?.concentrationWeight?.dose || ''}
                                          onChange={(e) => handleScoringDataChange(index, ['concentrationWeight', 'dose'], e.target.value)}
                                        />
                                        <Select 
                                          value={relation.scoringData?.concentrationWeight?.doseUnit || 'mM'}
                                          onValueChange={(value) => handleScoringDataChange(index, ['concentrationWeight', 'doseUnit'], value)}
                                        >
                                          <SelectTrigger className="h-9 w-24">
                                            <SelectValue />
                                          </SelectTrigger>
                                          <SelectContent>
                                            <SelectItem value="mM">mM</SelectItem>
                                            <SelectItem value="μM">μM</SelectItem>
                                            <SelectItem value="mg/L">mg/L</SelectItem>
                                          </SelectContent>
                                        </Select>
                                      </div>
                                    </div>
                                    <div className="space-y-1">
                                      <Label className="text-xs">分子量</Label>
                                      <Input 
                                        type="number" 
                                        placeholder="输入分子量" 
                                        className="h-9" 
                                        value={relation.scoringData?.concentrationWeight?.molecularWeight || ''}
                                        onChange={(e) => handleScoringDataChange(index, ['concentrationWeight', 'molecularWeight'], e.target.value)}
                                      />
                                    </div>
                                  </div>
                                </Card>

                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-green-100 text-green-600 text-xs font-bold flex items-center justify-center">II</div>
                                    可靠性得分 (0-10分)
                                  </h5>
                                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                                    {[
                                      "是否提供试验化学物的化学名称、来源以及纯度？",
                                      "是否使用合适的溶剂（载体）？其在试验浓度下不会干扰结果，并加入溶剂（载体）对照。",
                                      "在适用的情况下，是否有可靠和灵敏的具有代谢能力的测试系统（如细胞系/细胞/组织/器官/胚胎/亚细胞组分）用于研究试验化学物和终点？",
                                      "培养和维持细胞系/细胞/组织/器官/胚胎/亚细胞组分的条件是否合适？（包括温度、湿度、CO₂ 浓度、培养基配方、传代次数和避免污染）。",
                                      "染毒时间和浓度是否适合测试系统和研究终点？",
                                      "暴露于试验化学物期间和之后的条件是否合适？（例如使用的培养基、血清、细胞密度、培养温度、湿度和 CO₂ 浓度）。",
                                      "是否使用可靠和敏感的测试和分析方法来调查终点？",
                                      "是否描述清楚统计方法，没有不恰当、不寻常或不恰当的内容？",
                                      "各研究组的实验条件是否相同？",
                                      "结果评估方法是否可靠？"
                                    ].map((question, qIdx) => (
                                      <div key={qIdx} className="flex items-center gap-2 p-2 border rounded">
                                        <div className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-200 text-slate-700 text-xs font-bold shrink-0">
                                          {qIdx + 1}
                                        </div>
                                        <p className="text-xs flex-1">{question}</p>
                                        <Select 
                                          value={relation.scoringData?.reliabilityScores?.[`q${qIdx + 1}`]?.score || "1"}
                                          onValueChange={(value) => handleScoringDataChange(index, ['reliabilityScores', `q${qIdx + 1}`, 'score'], value)}
                                        >
                                          <SelectTrigger className="w-32 h-8">
                                            <SelectValue />
                                          </SelectTrigger>
                                          <SelectContent>
                                            <SelectItem value="1">满足 (1分)</SelectItem>
                                            <SelectItem value="0.5">部分满足 (0.5分)</SelectItem>
                                            <SelectItem value="0">不满足 (0分)</SelectItem>
                                          </SelectContent>
                                        </Select>
                                        <Input 
                                          placeholder="Comment" 
                                          className="w-40 h-8 text-xs" 
                                          value={relation.scoringData?.reliabilityScores?.[`q${qIdx + 1}`]?.comment || ''}
                                          onChange={(e) => handleScoringDataChange(index, ['reliabilityScores', `q${qIdx + 1}`, 'comment'], e.target.value)}
                                        />
                                      </div>
                                    ))}
                                  </div>
                                </Card>

                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-purple-100 text-purple-600 text-xs font-bold flex items-center justify-center">III</div>
                                    相关性
                                  </h5>
                                  <Select 
                                    value={relation.scoringData?.correlation || '1'}
                                    onValueChange={(value) => handleScoringDataChange(index, ['correlation'], value)}
                                  >
                                    <SelectTrigger className="h-9">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="1">正相关 (1分)</SelectItem>
                                      <SelectItem value="0">负相关 (0分)</SelectItem>
                                      <SelectItem value="-1">无相关 (-1分)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </Card>

                                <Card className="p-4 space-y-3">
                                  <h5 className="font-medium text-sm flex items-center gap-2">
                                    <div className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 text-xs font-bold flex items-center justify-center">IV</div>
                                    风险强度
                                  </h5>
                                  <Select 
                                    value={relation.scoringData?.riskIntensity || '1'}
                                    onValueChange={(value) => handleScoringDataChange(index, ['riskIntensity'], value)}
                                  >
                                    <SelectTrigger className="h-9">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="1">高风险强度 (1分)</SelectItem>
                                      <SelectItem value="0.8">中等风险强度 (0.8分)</SelectItem>
                                      <SelectItem value="0.4">低风险强度 (0.4分)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </Card>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={loading}>
            {loading ? '保存中...' : '保存'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
});

LiteratureEdit.displayName = 'LiteratureEdit';

export default LiteratureEdit;
