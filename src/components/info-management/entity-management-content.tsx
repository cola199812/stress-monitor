"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Plus, Edit, Trash2, Save, X, ChevronRight, ChevronDown, Search, ChevronLeft } from "lucide-react";
import http from "@/lib/http";
import InfoManagementNav from "./info-management-nav";

interface Product {
  id: number;
  name: string;
  category_id?: number;
  created_at?: string;
  updated_at?: string;
}

interface Allergen {
  id: number;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

interface Symptom {
  id: number;
  symptom_name?: string;
  name?: string;
  major_id?: number;
  sub_id?: number;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

type EntityType = "product" | "allergen" | "symptom";

export default function EntityManagementContent() {
  const [entityType, setEntityType] = useState<EntityType>("product");
  const [loading, setLoading] = useState(false);
  
  // 产品相关状态
  const [products1, setProducts1] = useState<Product[]>([]);
  const [products2, setProducts2] = useState<Product[]>([]);
  const [products3, setProducts3] = useState<Product[]>([]);
  const [selectedProduct1, setSelectedProduct1] = useState<string>("");
  const [selectedProduct2, setSelectedProduct2] = useState<string>("");
  
  // 过敏原状态
  const [allergens, setAllergens] = useState<Allergen[]>([]);
  
  // 症状相关状态
  const [symptoms1, setSymptoms1] = useState<Symptom[]>([]);
  const [symptoms2, setSymptoms2] = useState<Symptom[]>([]);
  const [symptoms3, setSymptoms3] = useState<Symptom[]>([]);
  const [selectedSymptom1, setSelectedSymptom1] = useState<string>("");
  const [selectedSymptom2, setSelectedSymptom2] = useState<string>("");
  
  // 编辑对话框状态
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<any>(null);
  const [formData, setFormData] = useState({ name: "", description: "" });
  const [addingLevel, setAddingLevel] = useState<number>(1); // 要新增的层级
  const [addingParent, setAddingParent] = useState<any>(null); // 新增项的父级
  
  // 搜索和展开状态
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);

  // 获取一级产品
  const fetchProducts1 = async () => {
    setLoading(true);
    try {
      console.log('正在获取一级产品...');
      const response = await http.get('/entity/products/level1');
      console.log('一级产品响应:', response);
      const data = Array.isArray(response) ? response : [];
      console.log('设置一级产品数据:', data);
      setProducts1(data);
    } catch (error) {
      console.error("获取一级产品失败:", error);
      setProducts1([]);
    } finally {
      setLoading(false);
    }
  };

  // 获取二级产品
  const fetchProducts2 = async (categoryId: string) => {
    setLoading(true);
    try {
      const response = await http.get(`/entity/products/level2/${categoryId}`);
      setProducts2(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error("获取二级产品失败:", error);
      setProducts2([]);
    } finally {
      setLoading(false);
    }
  };

  // 获取三级产品
  const fetchProducts3 = async (categoryId: string) => {
    setLoading(true);
    try {
      const response = await http.get(`/entity/products/level3/${categoryId}`);
      setProducts3(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error("获取三级产品失败:", error);
      setProducts3([]);
    } finally {
      setLoading(false);
    }
  };

  // 获取过敏原
  const fetchAllergens = async () => {
    setLoading(true);
    try {
      const response = await http.get('/entity/allergens');
      setAllergens(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error("获取过敏原失败:", error);
      setAllergens([]);
    } finally {
      setLoading(false);
    }
  };

  // 获取一级症状
  const fetchSymptoms1 = async () => {
    setLoading(true);
    try {
      const response = await http.get('/entity/symptoms/level1');
      setSymptoms1(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error("获取一级症状失败:", error);
      setSymptoms1([]);
    } finally {
      setLoading(false);
    }
  };

  // 获取二级症状
  const fetchSymptoms2 = async (majorId: string) => {
    setLoading(true);
    try {
      const response = await http.get(`/entity/symptoms/level2/${majorId}`);
      setSymptoms2(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error("获取二级症状失败:", error);
      setSymptoms2([]);
    } finally {
      setLoading(false);
    }
  };

  // 获取三级症状
  const fetchSymptoms3 = async (subId: string) => {
    setLoading(true);
    try {
      const response = await http.get(`/entity/symptoms/level3/${subId}`);
      setSymptoms3(Array.isArray(response) ? response : []);
    } catch (error) {
      console.error("获取三级症状失败:", error);
      setSymptoms3([]);
    } finally {
      setLoading(false);
    }
  };

  // 初始化数据
  useEffect(() => {
    // 切换实体类型时重置页面
    setCurrentPage(1);
    
    if (entityType === "product") {
      fetchProducts1();
      setSelectedProduct1("");
      setSelectedProduct2("");
      setProducts2([]);
      setProducts3([]);
    } else if (entityType === "allergen") {
      fetchAllergens();
    } else if (entityType === "symptom") {
      fetchSymptoms1();
      setSelectedSymptom1("");
      setSelectedSymptom2("");
      setSymptoms2([]);
      setSymptoms3([]);
    }
  }, [entityType]);

  // 搜索时重置页面
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  // 当选择一级产品时，获取二级产品
  useEffect(() => {
    if (selectedProduct1) {
      fetchProducts2(selectedProduct1);
      setSelectedProduct2("");
      setProducts3([]);
    } else {
      setProducts2([]);
      setProducts3([]);
    }
  }, [selectedProduct1]);

  // 当选择二级产品时，获取三级产品
  useEffect(() => {
    if (selectedProduct2) {
      fetchProducts3(selectedProduct2);
    } else {
      setProducts3([]);
    }
  }, [selectedProduct2]);

  // 当选择一级症状时，获取二级症状
  useEffect(() => {
    if (selectedSymptom1) {
      fetchSymptoms2(selectedSymptom1);
      setSelectedSymptom2("");
      setSymptoms3([]);
    } else {
      setSymptoms2([]);
      setSymptoms3([]);
    }
  }, [selectedSymptom1]);

  // 当选择二级症状时，获取三级症状
  useEffect(() => {
    if (selectedSymptom2) {
      fetchSymptoms3(selectedSymptom2);
    } else {
      setSymptoms3([]);
    }
  }, [selectedSymptom2]);

  // 打开新增对话框 - 支持指定层级和父级
  const handleAdd = (level: number = 1, parent: any = null) => {
    setEditingItem(null);
    setAddingLevel(level);
    setAddingParent(parent);
    setFormData({ name: "", description: "", cas_number: "" } as any);
    setDialogOpen(true);
  };

  // 打开编辑对话框
  const handleEdit = (item: any) => {
    setEditingItem(item);
    setFormData({ 
      name: item.name || item.symptom_name || "", 
      description: item.description || "",
      cas_number: item.cas_number || ""
    } as any);
    setDialogOpen(true);
  };

  // 保存实体
  const handleSave = async () => {
    if (loading) return; // 防止重复点击
    
    setLoading(true);
    try {
      console.log('开始保存...', { entityType, editingItem, formData });
      
      if (entityType === "product") {
        if (editingItem) {
          // 编辑现有产品
          // 判断产品层级：有category_id的是三级产品，否则根据products1/products2判断
          let level = 1;
          if (editingItem.category_id) {
            // 有category_id，可能是二级或三级
            // 检查是否在products3中
            const isLevel3 = products3.some(p => p.id === editingItem.id);
            level = isLevel3 ? 3 : 2;
          }
          
          console.log('更新产品:', editingItem.id, '新名称:', formData.name, '层级:', level);
          const response = await http.put(`/entity/products/${editingItem.id}`, { 
            name: formData.name,
            level: level
          });
          console.log('更新响应:', response);
          
          // 刷新数据 - 根据编辑的产品层级刷新对应列表
          console.log('开始刷新数据...', { selectedProduct1, selectedProduct2, editingItem });
          
          // 总是刷新一级产品
          await fetchProducts1();
          
          // 如果编辑的是三级产品，需要刷新其所属的二级和三级列表
          if (editingItem.category_id) {
            // 三级产品的category_id是二级产品的id
            console.log('刷新三级产品所属的二级和三级列表...');
            // 需要找到二级产品所属的一级产品
            const type = products2.find(p => p.id === editingItem.category_id);
            if (type && type.category_id) {
              await fetchProducts2(type.category_id.toString());
              await fetchProducts3(editingItem.category_id.toString());
            } else if (selectedProduct1) {
              await fetchProducts2(selectedProduct1);
              if (selectedProduct2) {
                await fetchProducts3(selectedProduct2);
              }
            }
          } else {
            // 一级或二级产品
            if (selectedProduct1) {
              await fetchProducts2(selectedProduct1);
            }
            if (selectedProduct2) {
              await fetchProducts3(selectedProduct2);
            }
          }
          console.log('数据刷新完成');
        } else {
          // 新增产品
          const categoryId = addingParent ? addingParent.id : undefined;
          await http.post('/entity/products', { 
            name: formData.name, 
            level: addingLevel, 
            category_id: categoryId 
          });
          
          // 刷新对应层级的数据
          await fetchProducts1();
          if (addingParent && addingLevel === 2) {
            await fetchProducts2(addingParent.id.toString());
          } else if (addingParent && addingLevel === 3) {
            // 需要找到二级父级来刷新
            const parent2 = products2.find(p => p.id === addingParent.id);
            if (parent2) await fetchProducts3(parent2.id.toString());
          }
        }
        
      } else if (entityType === "allergen") {
        if (editingItem) {
          await http.put(`/entity/allergens/${editingItem.id}`, formData);
        } else {
          await http.post('/entity/allergens', formData);
        }
        await fetchAllergens();
        
      } else if (entityType === "symptom") {
        if (editingItem) {
          // 判断症状层级
          let level = 1;
          if (editingItem.major_id) {
            level = 2;
          } else if (editingItem.sub_id) {
            level = 3;
          }
          
          await http.put(`/entity/symptoms/${editingItem.id}`, { 
            symptom_name: formData.name,
            name: formData.name,
            description: formData.description,
            level: level
          });
          
          // 刷新数据 - 根据编辑的症状层级刷新对应列表
          await fetchSymptoms1();
          if (selectedSymptom1) {
            await fetchSymptoms2(selectedSymptom1);
          }
          if (selectedSymptom2) {
            await fetchSymptoms3(selectedSymptom2);
          }
        } else {
          const majorId = addingLevel === 2 && addingParent ? addingParent.id : undefined;
          const subId = addingLevel === 3 && addingParent ? addingParent.id : undefined;
          
          await http.post('/entity/symptoms', { 
            symptom_name: formData.name,
            name: formData.name,
            description: formData.description,
            level: addingLevel,
            major_id: majorId,
            sub_id: subId
          });
          
          // 刷新对应层级的数据
          await fetchSymptoms1();
          if (addingParent && addingLevel === 2) {
            await fetchSymptoms2(addingParent.id.toString());
          } else if (addingParent && addingLevel === 3) {
            const parent2 = symptoms2.find(s => s.id === addingParent.id);
            if (parent2) await fetchSymptoms3(parent2.id.toString());
          }
        }
      }
      
      setDialogOpen(false);
      console.log('保存完成，显示成功提示');
      alert(editingItem ? "修改成功" : "添加成功");
    } catch (error: any) {
      console.error("保存失败:", error);
      const errorMsg = error.response?.data?.error || error.response?.data?.message || error.message || "保存失败，请重试";
      alert(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // 删除实体
  const handleDelete = async (item: any, level: number) => {
    const itemName = item.name || item.symptom_name;
    
    // 检查是否为一级产品/症状（不可删除）
    if (entityType === "product" && level === 1) {
      alert("一级产品不可删除！");
      return;
    }
    if (entityType === "symptom" && level === 1) {
      alert("一级症状不可删除！");
      return;
    }
    
    // 检查是否有子项
    if (entityType === "product") {
      if (level === 1) {
        const hasChildren = products2.some(p => p.category_id === item.id);
        if (hasChildren) {
          alert("该一级产品下还有二级产品，请先删除所有二级产品！");
          return;
        }
      } else if (level === 2) {
        const hasChildren = products3.some(p => p.category_id === item.id);
        if (hasChildren) {
          alert("该二级产品下还有三级产品，请先删除所有三级产品！");
          return;
        }
      }
    } else if (entityType === "symptom") {
      if (level === 1) {
        const hasChildren = symptoms2.some(s => s.major_id === item.id);
        if (hasChildren) {
          alert("该一级症状下还有二级症状，请先删除所有二级症状！");
          return;
        }
      } else if (level === 2) {
        const hasChildren = symptoms3.some(s => s.sub_id === item.id);
        if (hasChildren) {
          alert("该二级症状下还有三级症状，请先删除所有三级症状！");
          return;
        }
      }
    }
    
    if (!confirm(`确定要删除 "${itemName}" 吗？`)) return;
    
    try {
      if (entityType === "product") {
        await http.delete(`/entity/products/${item.id}?level=${level}`);
        // 刷新数据
        fetchProducts1();
        if (level >= 2) {
          const parent1 = products1.find(p => products2.some(p2 => p2.id === item.category_id && p2.category_id === p.id));
          if (parent1) fetchProducts2(parent1.id.toString());
        }
        if (level === 3 && item.category_id) {
          fetchProducts3(item.category_id.toString());
        }
      } else if (entityType === "allergen") {
        await http.delete(`/entity/allergens/${item.id}`);
        fetchAllergens();
      } else if (entityType === "symptom") {
        await http.delete(`/entity/symptoms/${item.id}?level=${level}`);
        // 刷新数据
        fetchSymptoms1();
        if (level >= 2) {
          const parent1 = symptoms1.find(s => symptoms2.some(s2 => s2.id === item.major_id && s2.major_id === s.id));
          if (parent1) fetchSymptoms2(parent1.id.toString());
        }
        if (level === 3 && item.sub_id) {
          fetchSymptoms3(item.sub_id.toString());
        }
      }
      alert("删除成功");
    } catch (error: any) {
      console.error("删除失败:", error);
      const errorMsg = error.response?.data?.error || error.message || "删除失败";
      
      // 检查是否为外键约束错误
      if (errorMsg.includes("foreign key") || errorMsg.includes("外键") || errorMsg.includes("FOREIGN KEY")) {
        alert("删除失败：该项存在关联数据，请先删除相关联的数据！\n\n详细信息：" + errorMsg);
      } else {
        alert("删除失败：" + errorMsg);
      }
    }
  };

  // 切换展开/折叠
  const toggleExpand = (key: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedItems(newExpanded);
  };

  // 渲染树形产品行
  const renderProductTreeRows = () => {
    const rows: React.ReactElement[] = [];
    const query = searchQuery.toLowerCase();
    
    // 如果有搜索词，检查所有层级是否匹配
    const matchesSearch = (p1: any, p2?: any, p3?: any) => {
      if (!query) return true;
      if (p1.name.toLowerCase().includes(query)) return true;
      if (p2 && p2.name.toLowerCase().includes(query)) return true;
      if (p3 && p3.name.toLowerCase().includes(query)) return true;
      return false;
    };

    products1.forEach(p1 => {
      const key1 = `product-1-${p1.id}`;
      const isExpanded1 = expandedItems.has(key1);
      const children2 = products2.filter(p => p.category_id === p1.id);
      
      // 检查是否有匹配的子项
      let hasMatchingChildren = false;
      if (query) {
        hasMatchingChildren = children2.some(p2 => {
          if (p2.name.toLowerCase().includes(query)) return true;
          const children3 = products3.filter(p => p.category_id === p2.id);
          return children3.some(p3 => p3.name.toLowerCase().includes(query));
        });
      }
      
      // 如果有搜索词，只显示匹配的项
      const shouldShowP1 = !query || p1.name.toLowerCase().includes(query) || hasMatchingChildren;
      if (!shouldShowP1) return;
      
      // 一级产品行
      rows.push(
        <TableRow key={key1} className="hover:bg-muted/50">
          <TableCell>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => {
                toggleExpand(key1);
                if (!isExpanded1) {
                  fetchProducts2(p1.id.toString());
                }
              }}
            >
              {isExpanded1 ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </Button>
          </TableCell>
          <TableCell className="font-semibold text-base text-blue-700">{p1.name}</TableCell>
          <TableCell className="text-blue-700 text-sm">-</TableCell>
          <TableCell className="text-sm">{p1.created_at ? new Date(p1.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
          <TableCell>
            <div className="flex gap-2">
              <Button variant="default" size="sm" className="bg-green-600 hover:bg-green-700" onClick={() => handleAdd(2, p1)}>
                <Plus className="h-4 w-4 mr-1" />
                类型
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleEdit(p1)}>
                <Edit className="h-4 w-4" />
              </Button>
            </div>
          </TableCell>
        </TableRow>
      );

      // 如果展开或有搜索，显示二级产品
      if (isExpanded1 || query) {
        children2.forEach(p2 => {
          const key2 = `product-2-${p2.id}`;
          const isExpanded2 = expandedItems.has(key2);
          const children3 = products3.filter(p => p.category_id === p2.id);
          
          // 检查是否有匹配的三级产品
          const hasMatchingP3 = query && children3.some(p3 => p3.name.toLowerCase().includes(query));
          const shouldShowP2 = !query || p2.name.toLowerCase().includes(query) || hasMatchingP3;
          if (!shouldShowP2) return;
          
          rows.push(
            <TableRow key={key2} className="hover:bg-muted/50 bg-muted/20">
              <TableCell className="pl-8">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  onClick={() => {
                    toggleExpand(key2);
                    if (!isExpanded2) {
                      fetchProducts3(p2.id.toString());
                    }
                  }}
                >
                  {isExpanded2 ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </Button>
              </TableCell>
              <TableCell className="font-medium text-green-700">{p2.name}</TableCell>
              <TableCell className="text-blue-700 text-sm">{p1.name}</TableCell>
              <TableCell className="text-sm">{p2.created_at ? new Date(p2.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
              <TableCell>
                <div className="flex gap-2">
                  <Button variant="default" size="sm" className="bg-gray-600 hover:bg-gray-700" onClick={() => handleAdd(3, p2)}>
                    <Plus className="h-4 w-4 mr-1" />
                    产品
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleEdit(p2)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => handleDelete(p2, 2)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          );

          // 如果展开或有搜索，显示三级产品
          if (isExpanded2 || query) {
            children3.forEach(p3 => {
              const shouldShowP3 = !query || p3.name.toLowerCase().includes(query);
              if (!shouldShowP3) return;
              
              rows.push(
                <TableRow key={`product-3-${p3.id}`} className="hover:bg-muted/50 bg-muted/30">
                  <TableCell className="pl-16"></TableCell>
                  <TableCell className="text-sm text-gray-700">{p3.name}</TableCell>
                  <TableCell className="text-green-700 text-sm">{p2.name}</TableCell>
                  <TableCell className="text-sm">{p3.created_at ? new Date(p3.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <div className="w-[72px]"></div>
                      <Button variant="outline" size="sm" onClick={() => handleEdit(p3)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="destructive" size="sm" onClick={() => handleDelete(p3, 3)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            });
          }
        });
      }
    });

    return rows;
  };

  // 渲染症状树形行（类似产品）
  const renderSymptomTreeRows = () => {
    const rows: React.ReactElement[] = [];
    const query = searchQuery.toLowerCase();

    symptoms1.forEach(s1 => {
      const key1 = `symptom-1-${s1.id}`;
      const isExpanded1 = expandedItems.has(key1);
      const children2 = symptoms2.filter(s => s.major_id === s1.id);
      
      // 检查是否有匹配的子项
      let hasMatchingChildren = false;
      if (query) {
        hasMatchingChildren = children2.some(s2 => {
          if ((s2.symptom_name || s2.name || '').toLowerCase().includes(query)) return true;
          const children3 = symptoms3.filter(s => s.sub_id === s2.id);
          return children3.some(s3 => (s3.name || '').toLowerCase().includes(query));
        });
      }
      
      // 如果有搜索词，只显示匹配的项
      const s1Name = s1.symptom_name || s1.name || '';
      const shouldShowS1 = !query || s1Name.toLowerCase().includes(query) || hasMatchingChildren;
      if (!shouldShowS1) return;
      
      rows.push(
        <TableRow key={key1} className="hover:bg-muted/50">
          <TableCell>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => {
                toggleExpand(key1);
                if (!isExpanded1) {
                  fetchSymptoms2(s1.id.toString());
                }
              }}
            >
              {isExpanded1 ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </Button>
          </TableCell>
          <TableCell className="font-semibold text-base text-blue-700">{s1.symptom_name || s1.name}</TableCell>
          <TableCell className="text-blue-700 text-sm">-</TableCell>
          <TableCell className="text-sm">{s1.created_at ? new Date(s1.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
          <TableCell>
            <div className="flex gap-2">
              <Button variant="default" size="sm" className="bg-green-600 hover:bg-green-700" onClick={() => handleAdd(2, s1)}>
                <Plus className="h-4 w-4 mr-1" />
                二级症状
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleEdit(s1)}>
                <Edit className="h-4 w-4" />
              </Button>
            </div>
          </TableCell>
        </TableRow>
      );

      if (isExpanded1 || query) {
        children2.forEach(s2 => {
          const key2 = `symptom-2-${s2.id}`;
          const isExpanded2 = expandedItems.has(key2);
          const children3 = symptoms3.filter(s => s.sub_id === s2.id);
          
          // 检查是否有匹配的三级症状
          const hasMatchingS3 = query && children3.some(s3 => (s3.name || '').toLowerCase().includes(query));
          const s2Name = s2.symptom_name || s2.name || '';
          const shouldShowS2 = !query || s2Name.toLowerCase().includes(query) || hasMatchingS3;
          if (!shouldShowS2) return;
          
          rows.push(
            <TableRow key={key2} className="hover:bg-muted/50 bg-muted/20">
              <TableCell className="pl-8">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  onClick={() => {
                    toggleExpand(key2);
                    if (!isExpanded2) {
                      fetchSymptoms3(s2.id.toString());
                    }
                  }}
                >
                  {isExpanded2 ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </Button>
              </TableCell>
              <TableCell className="font-medium text-green-700">{s2.symptom_name || s2.name}</TableCell>
              <TableCell className="text-blue-700 text-sm">{s1.symptom_name || s1.name}</TableCell>
              <TableCell className="text-sm">{s2.created_at ? new Date(s2.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
              <TableCell>
                <div className="flex gap-2">
                  <Button variant="default" size="sm" className="bg-gray-600 hover:bg-gray-700" onClick={() => handleAdd(3, s2)}>
                    <Plus className="h-4 w-4 mr-1" />
                    三级症状
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleEdit(s2)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => handleDelete(s2, 2)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          );

          if (isExpanded2 || query) {
            children3.forEach(s3 => {
              const s3Name = s3.name || '';
              const shouldShowS3 = !query || s3Name.toLowerCase().includes(query);
              if (!shouldShowS3) return;
              
              rows.push(
                <TableRow key={`symptom-3-${s3.id}`} className="hover:bg-muted/50 bg-muted/30">
                  <TableCell className="pl-16"></TableCell>
                  <TableCell className="text-sm text-gray-700">{s3.name}</TableCell>
                  <TableCell className="text-green-700 text-sm">{s2.symptom_name || s2.name}</TableCell>
                  <TableCell className="text-sm">{s3.created_at ? new Date(s3.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <div className="w-[72px]"></div>
                      <Button variant="outline" size="sm" onClick={() => handleEdit(s3)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="destructive" size="sm" onClick={() => handleDelete(s3, 3)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            });
          }
        });
      }
    });

    return rows;
  };

  // 渲染主界面
  const renderMainContent = () => {
    const getTitle = () => {
      if (entityType === "product") return "产品管理";
      if (entityType === "allergen") return "化学应急源管理";
      return "症状管理";
    };

    const filteredAllergens = allergens.filter(a => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return a.name.toLowerCase().includes(query) || 
             (a.description && a.description.toLowerCase().includes(query)) ||
             ((a as any).cas_number && (a as any).cas_number.toLowerCase().includes(query));
    });

    // 分页计算
    const totalItems = filteredAllergens.length;
    const totalPages = Math.ceil(totalItems / pageSize);
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    const paginatedAllergens = filteredAllergens.slice(startIndex, endIndex);

    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            {/* 实体类型选择器 */}
            <div className="w-[100px]">
              <Select value={entityType} onValueChange={(v) => setEntityType(v as EntityType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="product">产品</SelectItem>
                  <SelectItem value="allergen">化学应急源</SelectItem>
                  <SelectItem value="symptom">症状</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {/* 搜索框 */}
            <div className="w-[300px] relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            
            {/* 新增按钮 - 靠右 */}
            <div className="ml-auto">
              {entityType === "product" && (
                <Button onClick={() => handleAdd(1, null)} className="bg-blue-600 hover:bg-blue-700">
                  <Plus className="h-4 w-4 mr-2" />
                  新增种类
                </Button>
              )}
              {entityType === "allergen" && (
                <Button onClick={() => handleAdd(1, null)} className="bg-blue-600 hover:bg-blue-700">
                  <Plus className="h-4 w-4 mr-2" />
                  新增化学应急源
                </Button>
              )}
              {entityType === "symptom" && (
                <Button onClick={() => handleAdd(1, null)} className="bg-blue-600 hover:bg-blue-700">
                  <Plus className="h-4 w-4 mr-2" />
                  新增一级症状
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">加载中...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  {entityType !== "allergen" && <TableHead className="w-[50px]"></TableHead>}
                  <TableHead>名称</TableHead>
                  {entityType !== "allergen" && <TableHead>所属分类</TableHead>}
                  {entityType === "allergen" && <TableHead>英文名</TableHead>}
                  {entityType === "allergen" && <TableHead>CAS号</TableHead>}
                  <TableHead>创建时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entityType === "product" && renderProductTreeRows()}
                {entityType === "symptom" && renderSymptomTreeRows()}
                {entityType === "allergen" && paginatedAllergens.map(item => (
                  <TableRow key={item.id}>
                    <TableCell>{item.name}</TableCell>
                    <TableCell>{item.description || '-'}</TableCell>
                    <TableCell>{(item as any).cas_number || '-'}</TableCell>
                    <TableCell>{item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => handleEdit(item)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button variant="destructive" size="sm" onClick={() => handleDelete(item, 1)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {((entityType === "product" && products1.length === 0) ||
                  (entityType === "allergen" && filteredAllergens.length === 0) ||
                  (entityType === "symptom" && symptoms1.length === 0)) && (
                  <TableRow>
                    <TableCell colSpan={entityType === "allergen" ? 4 : 5} className="text-center py-8 text-muted-foreground">
                      暂无数据
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
          
          {/* 分页控件 - 仅在化学应激源管理时显示 */}
          {entityType === "allergen" && filteredAllergens.length > 0 && (
            <div className="flex items-center justify-between px-4 py-3 border-t">
              <div className="text-sm text-muted-foreground">
                显示第 {startIndex + 1} - {Math.min(endIndex, totalItems)} 项，共 {totalItems} 项
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                >
                  下一页
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="container mx-auto px-4 pt-4 pb-8 space-y-6 h-full overflow-auto">
      <InfoManagementNav />
      {renderMainContent()}

      {/* 编辑对话框 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingItem ? "编辑" : "新增"}
              {!editingItem && entityType === "product" && `${addingLevel === 1 ? "种类" : addingLevel === 2 ? "类型" : "产品"}`}
              {!editingItem && entityType === "symptom" && `${addingLevel === 1 ? "一级" : addingLevel === 2 ? "二级" : "三级"}症状`}
              {!editingItem && entityType === "allergen" && " 化学应急源"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {!editingItem && addingParent && (
              <div className="p-3 bg-muted rounded-md text-sm">
                <span className="font-medium">所属分类：</span>
                {addingParent.name || addingParent.symptom_name}
              </div>
            )}
            <div className="space-y-2">
              <Label>名称</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="请输入名称"
              />
            </div>
            {entityType === "allergen" && (
              <>
                <div className="space-y-2">
                  <Label>英文名</Label>
                  <Input
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="请输入英文名（可选）"
                  />
                </div>
                <div className="space-y-2">
                  <Label>CAS号</Label>
                  <Input
                    value={(formData as any).cas_number || ''}
                    onChange={(e) => setFormData({ ...formData, cas_number: e.target.value } as any)}
                    placeholder="请输入CAS号（可选）"
                  />
                </div>
              </>
            )}
            {entityType === "symptom" && addingLevel === 3 && (
              <div className="space-y-2">
                <Label>描述</Label>
                <Input
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="请输入描述（可选）"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              <X className="h-4 w-4 mr-2" />
              取消
            </Button>
            <Button onClick={handleSave}>
              <Save className="h-4 w-4 mr-2" />
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
