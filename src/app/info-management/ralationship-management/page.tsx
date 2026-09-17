"use client";

import React, { useState, useEffect, useRef } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Plus } from "lucide-react";
import { useProductStore } from "@/store/useProductStore";
import InfoManagementNav from "@/components/info-management/info-management-nav";
import AllergenSymptomManagement from "@/components/info-management/relation-management/allergen-symptom-management";
import ProductAllergenManagementComponent from "@/components/info-management/relation-management/product-allergen-relationship";
import ProductAdverseReactionManagementComponent from "@/components/info-management/relation-management/product-symptom-management";

export default function RelationshipManagementPage() {
  const { setFeatureName } = useProductStore();
  const [activeTab, setActiveTab] = useState<"allergen-symptom" | "product-allergen" | "product-adverse-reaction">("allergen-symptom");
  const [searchQuery, setSearchQuery] = useState("");
  
  // 组件引用，用于调用子组件的方法
  const allergenSymptomRef = useRef<any>(null);
  const productAllergenRef = useRef<any>(null);
  const productAdverseReactionRef = useRef<any>(null);

  // 设置功能名称
  useEffect(() => {
    setFeatureName("关系管理");
  }, [setFeatureName]);

  // 处理搜索
  const handleSearch = () => {
    if (activeTab === "allergen-symptom" && allergenSymptomRef.current) {
      allergenSymptomRef.current.handleSearch(searchQuery);
    } else if (activeTab === "product-allergen" && productAllergenRef.current) {
      productAllergenRef.current.handleSearch(searchQuery);
    } else if (activeTab === "product-adverse-reaction" && productAdverseReactionRef.current) {
      productAdverseReactionRef.current.handleSearch(searchQuery);
    }
  };

  // 处理新建关联
  const handleAddRelation = () => {
    if (activeTab === "allergen-symptom" && allergenSymptomRef.current) {
      allergenSymptomRef.current.handleAddRelation();
    } else if (activeTab === "product-allergen" && productAllergenRef.current) {
      productAllergenRef.current.handleAddRelation();
    } else if (activeTab === "product-adverse-reaction" && productAdverseReactionRef.current) {
      productAdverseReactionRef.current.handleAddRelation();
    }
  };

  // Tab切换时清空搜索
  const handleTabChange = (value: string) => {
    setActiveTab(value as "allergen-symptom" | "product-allergen" | "product-adverse-reaction");
    setSearchQuery("");
  };

  return (
    <div className="container mx-auto px-4 pt-4 pb-8 space-y-6 h-full overflow-hidden flex flex-col">
      {/* 导航栏 */}
      <InfoManagementNav />
      
      {/* 主内容区域 */}
      <div className="flex-1 p-6 space-y-6">
        <Tabs value={activeTab} onValueChange={handleTabChange}>
          {/* Tab切换、搜索框、新建按钮在一行显示 */}
          <div className="flex items-center justify-between mb-6">
            <TabsList className="grid grid-cols-3 w-[600px]">
              <TabsTrigger value="allergen-symptom">化学应急源-不良反应关联</TabsTrigger>
              <TabsTrigger value="product-allergen">产品-化学应急源关联</TabsTrigger>
              <TabsTrigger value="product-adverse-reaction">产品-不良反应关联</TabsTrigger>
            </TabsList>

            <div className="flex items-center space-x-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder={
                    activeTab === "allergen-symptom" 
                      ? "搜索化学应急源或症状..." 
                      : activeTab === "product-allergen"
                      ? "搜索产品或化学应急源..."
                      : "搜索产品或不良反应..."
                  }
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="pl-10 w-80"
                />
              </div>
              <Button onClick={handleAddRelation}>
                <Plus className="h-4 w-4 mr-2" />
                新建关联
              </Button>
            </div>
          </div>

          <TabsContent value="allergen-symptom" className="mt-0">
            <AllergenSymptomManagement ref={allergenSymptomRef} />
          </TabsContent>

          <TabsContent value="product-allergen" className="mt-0">
            <ProductAllergenManagementComponent ref={productAllergenRef} />
          </TabsContent>

          <TabsContent value="product-adverse-reaction" className="mt-0">
            <ProductAdverseReactionManagementComponent ref={productAdverseReactionRef} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
