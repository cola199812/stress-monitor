"use client";

import React, { useState, forwardRef, useImperativeHandle } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Plus, Trash2 } from "lucide-react";
import http from "@/lib/http";
import { toast } from "sonner";

// 通用数据项接口
export interface DataItem {
  id: number;
  title: string;
  source?: string;
  abstract?: string;
  link?: string;
  publishTime?: string;
  created_at?: string;
  updated_at?: string;
  [key: string]: any; // 允许额外字段
}

// 编辑配置接口
export interface EditConfig {
  title: string;
  apiEndpoint: string;
  editFields: EditFieldConfig[];
  enableRelations?: boolean; // 是否启用实体关系管理
  relationType?: 'product-symptom'; // 关系类型
}

export interface EditFieldConfig {
  key: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'date';
  required?: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
  width?: 'full' | 'half'; // 字段宽度：full=整行，half=半行
}

interface SharedDataEditProps {
  config: EditConfig;
  open: boolean;
  editingItem: DataItem | null;
  onClose: () => void;
  onSave?: () => void;
}

export interface SharedDataEditRef {
  // 预留接口，暂时为空
}

// 实体关系接口
interface EntityRelation {
  id?: number;
  product_id: number;
  product_name?: string;
  symptom_id: number;
  symptom_name?: string;
  relation?: string;
  isNew?: boolean;
}

// 已存在的产品-症状关系接口
interface ExistingRelation {
  product_id: number;
  symptom_id: number;
}

const SharedDataEdit = forwardRef<SharedDataEditRef, SharedDataEditProps>(({ config, open, editingItem, onClose, onSave }, ref) => {
  // 状态管理
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState('basic');
  const [entityRelations, setEntityRelations] = useState<EntityRelation[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [symptoms, setSymptoms] = useState<any[]>([]);
  const [existingRelations, setExistingRelations] = useState<ExistingRelation[]>([]);

  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({}));

  // 当对话框打开或编辑项改变时，初始化表单数据
  React.useEffect(() => {
    if (open) {
      const initialData: Record<string, any> = {};
      config.editFields.forEach(field => {
        let value = editingItem ? (editingItem[field.key] || '') : '';
        
        // 对日期类型字段进行格式转换
        if (field.type === 'date' && value) {
          try {
            // 将 ISO 格式或其他日期格式转换为 YYYY-MM-DD
            const date = new Date(value);
            if (!isNaN(date.getTime())) {
              value = date.toISOString().split('T')[0];
            }
          } catch (e) {
            console.warn(`日期字段 ${field.key} 格式转换失败:`, e);
          }
        }
        
        initialData[field.key] = value;
      });
      setFormData(initialData);
      setActiveTab('basic');
      
      // 加载实体关系
      if (config.enableRelations && editingItem) {
        loadEntityRelations();
      } else {
        setEntityRelations([]);
      }
      
      // 加载产品和症状列表
      if (config.enableRelations) {
        loadProducts();
        loadSymptoms();
        loadExistingRelations();
      }
    }
  }, [open, editingItem, config.editFields]);

  // 加载所有已存在的产品-症状关系
  const loadExistingRelations = async () => {
    try {
      const response = await http.get('/relationship/product-symptom/list', {
        params: { page_size: 10000 }  // 获取所有关系数据用于排序
      });
      const relations = response.data?.data?.items || response.data?.items || [];
      const relationMap = relations.map((rel: any) => ({
        product_id: rel.product_id,
        symptom_id: rel.symptom_id
      }));
      setExistingRelations(relationMap);
    } catch (error) {
      console.error('加载已存在关系失败:', error);
      setExistingRelations([]);
    }
  };

  // 加载实体关系
  const loadEntityRelations = async () => {
    if (!editingItem?.entityRelations) return;
    
    try {
      const relations = editingItem.entityRelations.map((rel: any) => ({
        id: rel.id,
        product_id: rel.product_id,
        product_name: rel.product_name,
        symptom_id: rel.symptom_id,
        symptom_name: rel.symptom_name,
        relation: rel.relation
      }));
      setEntityRelations(relations);
    } catch (error) {
      console.error('加载实体关系失败:', error);
    }
  };

  // 加载产品列表
  const loadProducts = async () => {
    try {
      const response = await http.get('/entity/products/level3');
      const productList = response.data?.data || response.data || response || [];
      setProducts(Array.isArray(productList) ? productList : []);
    } catch (error) {
      console.error('加载产品列表失败:', error);
      setProducts([]);
    }
  };

  // 加载症状列表
  const loadSymptoms = async () => {
    try {
      const response = await http.get('/entity/symptoms/level2');
      const symptomList = response.data?.data || response.data || response || [];
      setSymptoms(Array.isArray(symptomList) ? symptomList : []);
    } catch (error) {
      console.error('加载症状列表失败:', error);
      setSymptoms([]);
    }
  };

  // 添加新的实体关系
  const handleAddRelation = () => {
    setEntityRelations(prev => [
      ...prev,
      {
        product_id: 0,
        symptom_id: 0,
        isNew: true
      }
    ]);
  };

  // 删除实体关系
  const handleDeleteRelation = (index: number) => {
    setEntityRelations(prev => prev.filter((_, i) => i !== index));
  };

  // 更新实体关系
  const handleUpdateRelation = (index: number, field: string, value: any) => {
    setEntityRelations(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      
      // 更新显示名称
      if (field === 'product_id') {
        const product = products.find(p => p.id === parseInt(value));
        updated[index].product_name = product?.name || '';
      } else if (field === 'symptom_id') {
        const symptom = symptoms.find(s => s.id === parseInt(value));
        updated[index].symptom_name = symptom?.name || '';
      }
      
      return updated;
    });
  };

  // 检查产品-症状关系是否已存在
  const isRelationExists = (productId: number, symptomId: number): boolean => {
    return existingRelations.some(
      rel => rel.product_id === productId && rel.symptom_id === symptomId
    );
  };

  // 获取已选产品对应的已存在症状列表
  const getRelatedSymptoms = (productId: number): number[] => {
    if (!productId) return [];
    return existingRelations
      .filter(rel => rel.product_id === productId)
      .map(rel => rel.symptom_id);
  };

  // 获取已选症状对应的已存在产品列表
  const getRelatedProducts = (symptomId: number): number[] => {
    if (!symptomId) return [];
    return existingRelations
      .filter(rel => rel.symptom_id === symptomId)
      .map(rel => rel.product_id);
  };

  // 对产品列表排序：已存在关系的优先
  const getSortedProducts = (currentSymptomId: number) => {
    if (!currentSymptomId) return products;
    const relatedProductIds = getRelatedProducts(currentSymptomId);
    const related = products.filter(p => relatedProductIds.includes(p.id));
    const unrelated = products.filter(p => !relatedProductIds.includes(p.id));
    return [...related, ...unrelated];
  };

  // 对症状列表排序：已存在关系的优先
  const getSortedSymptoms = (currentProductId: number) => {
    if (!currentProductId) return symptoms;
    const relatedSymptomIds = getRelatedSymptoms(currentProductId);
    const related = symptoms.filter(s => relatedSymptomIds.includes(s.id));
    const unrelated = symptoms.filter(s => !relatedSymptomIds.includes(s.id));
    return [...related, ...unrelated];
  };

  // 保存数据
  const handleSave = async () => {
    // 验证必填字段
    const missingFields = config.editFields
      .filter(field => field.required && !formData[field.key])
      .map(field => field.label);
    
    if (missingFields.length > 0) {
      toast.error(`请填写必填字段: ${missingFields.join(', ')}`);
      return;
    }

    // 验证实体关系
    if (config.enableRelations && entityRelations.length > 0) {
      const invalidRelations = entityRelations.filter(
        rel => !rel.product_id || !rel.symptom_id
      );
      if (invalidRelations.length > 0) {
        toast.error('请完善所有实体关系的产品和症状信息');
        return;
      }
    }

    setLoading(true);
    try {
      if (config.enableRelations) {
        // 使用嵌套格式（适配后端 API）
        const requestData = {
          basicInfo: formData,
          entityRelations: entityRelations.map(rel => ({
            productId: rel.product_id,
            symptomId: rel.symptom_id
          }))
        };
        
        if (editingItem) {
          // 编辑模式
          await http.put(`${config.apiEndpoint}/${editingItem.id}`, requestData);
        } else {
          // 新建模式 - 使用 /create 端点
          await http.post(`${config.apiEndpoint}/create`, requestData);
        }
      } else {
        // 不启用实体关系时，使用扁平格式
        if (editingItem) {
          await http.put(`${config.apiEndpoint}/${editingItem.id}`, formData);
        } else {
          await http.post(config.apiEndpoint, formData);
        }
      }
      
      toast.success(`${config.title}${editingItem ? '更新' : '创建'}成功`);
      onClose();
      onSave?.();
    } catch (error) {
      console.error(`保存${config.title}失败:`, error);
      toast.error(`保存${config.title}失败`);
    } finally {
      setLoading(false);
    }
  };



  // 渲染表单字段组（支持行布局）
  const renderFormFields = () => {
    const rows: React.ReactElement[] = [];
    let currentRow: EditFieldConfig[] = [];
    
    config.editFields.forEach((field, index) => {
      const width = field.width || 'full';
      
      if (width === 'full') {
        // 如果当前行有字段，先渲染当前行
        if (currentRow.length > 0) {
          rows.push(renderFieldRow(currentRow, rows.length));
          currentRow = [];
        }
        // 渲染整行字段
        rows.push(renderFieldRow([field], rows.length));
      } else if (width === 'half') {
        currentRow.push(field);
        // 如果当前行已有2个字段，渲染这一行
        if (currentRow.length === 2) {
          rows.push(renderFieldRow(currentRow, rows.length));
          currentRow = [];
        }
      }
    });
    
    // 渲染剩余的字段
    if (currentRow.length > 0) {
      rows.push(renderFieldRow(currentRow, rows.length));
    }
    
    return rows;
  };
  
  // 渲染一行字段
  const renderFieldRow = (fields: EditFieldConfig[], rowIndex: number) => {
    if (fields.length === 1) {
      const field = fields[0];
      return (
        <div key={`row-${rowIndex}`} className="space-y-2">
          <Label>
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </Label>
          {renderFormField(field)}
        </div>
      );
    } else {
      // 两个字段并排
      return (
        <div key={`row-${rowIndex}`} className="grid grid-cols-2 gap-4">
          {fields.map((field) => (
            <div key={field.key} className="space-y-2">
              <Label>
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </Label>
              {renderFormField(field)}
            </div>
          ))}
        </div>
      );
    }
  };

  // 渲染表单字段
  const renderFormField = (field: EditFieldConfig) => {
    const value = formData[field.key] || '';
    
    switch (field.type) {
      case 'textarea':
        return (
          <Textarea
            value={value}
            onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
            placeholder={field.placeholder}
            rows={4}
          />
        );
      
      case 'select':
        return (
          <Select 
            value={value} 
            onValueChange={(val) => setFormData(prev => ({ ...prev, [field.key]: val }))}
          >
            <SelectTrigger>
              <SelectValue placeholder={field.placeholder} />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      
      case 'date':
        return (
          <Input
            type="date"
            value={value}
            onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
          />
        );
      
      default:
        return (
          <Input
            value={value}
            onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
            placeholder={field.placeholder}
          />
        );
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingItem ? `编辑${config.title}` : `新建${config.title}`}
            </DialogTitle>
          </DialogHeader>
          
          {config.enableRelations ? (
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="basic">基础信息</TabsTrigger>
                <TabsTrigger value="relations">实体关系</TabsTrigger>
              </TabsList>
              
              <TabsContent value="basic" className="py-4">
                <div className="space-y-4">
                  {renderFormFields()}
                </div>
              </TabsContent>
              
              <TabsContent value="relations" className="space-y-4 py-4">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-sm font-medium">产品-不良反应关系</h3>
                  <Button onClick={handleAddRelation} size="sm">
                    <Plus className="h-4 w-4 mr-2" />
                    添加关系
                  </Button>
                </div>
                
                {entityRelations.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    暂无实体关系，点击"添加关系"按钮创建
                  </div>
                ) : (
                  <div className="border rounded-md">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[40%]">产品</TableHead>
                          <TableHead className="w-[40%]">症状</TableHead>
                          <TableHead className="w-[20%]">操作</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {entityRelations.map((relation, index) => (
                          <TableRow key={index}>
                            <TableCell>
                              <Select
                                value={relation.product_id?.toString() || ''}
                                onValueChange={(value) => handleUpdateRelation(index, 'product_id', parseInt(value))}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder="选择产品" />
                                </SelectTrigger>
                                <SelectContent>
                                  {getSortedProducts(relation.symptom_id).map((product) => {
                                    const hasRelation = relation.symptom_id && isRelationExists(product.id, relation.symptom_id);
                                    return (
                                      <SelectItem 
                                        key={product.id} 
                                        value={product.id.toString()}
                                        className={hasRelation ? 'text-blue-600 font-medium' : ''}
                                      >
                                        {product.name}
                                      </SelectItem>
                                    );
                                  })}
                                </SelectContent>
                              </Select>
                            </TableCell>
                            <TableCell>
                              <Select
                                value={relation.symptom_id?.toString() || ''}
                                onValueChange={(value) => handleUpdateRelation(index, 'symptom_id', parseInt(value))}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder="选择症状" />
                                </SelectTrigger>
                                <SelectContent>
                                  {getSortedSymptoms(relation.product_id).map((symptom) => {
                                    const hasRelation = relation.product_id && isRelationExists(relation.product_id, symptom.id);
                                    return (
                                      <SelectItem 
                                        key={symptom.id} 
                                        value={symptom.id.toString()}
                                        className={hasRelation ? 'text-blue-600 font-medium' : ''}
                                      >
                                        {symptom.name}
                                      </SelectItem>
                                    );
                                  })}
                                </SelectContent>
                              </Select>
                            </TableCell>
                            <TableCell>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteRelation(index)}
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          ) : (
            <div className="py-4">
              <div className="space-y-4">
                {renderFormFields()}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={onClose}>
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

SharedDataEdit.displayName = "SharedDataEdit";

export default SharedDataEdit;
