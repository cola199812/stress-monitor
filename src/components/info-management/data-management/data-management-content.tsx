"use client";

import React, { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, Plus, Filter } from "lucide-react";
import InfoManagementNav from "../info-management-nav";

// 导入各个数据管理组件
import NewsManagement from "./news-management";
import RecallManagement from "./recall-management";
import ComplaintManagement from "./complaint-management";
import MedicalInfoManagement from "./medical-info-management";
import LiteratureManagement from "./literature-management";

// 导入组件引用类型
import { NewsManagementRef } from "./news-management";
import { RecallManagementRef } from "./recall-management";
import { ComplaintManagementRef } from "./complaint-management";
import { MedicalInfoManagementRef } from "./medical-info-management";
import { LiteratureManagementRef } from "./literature-management";

export default function DataManagementContent() {
  const [activeTab, setActiveTab] = useState("news");
  const [searchQuery, setSearchQuery] = useState("");

  const getActiveTabLabel = () => {
    switch (activeTab) {
      case "news":
        return "新闻";
      case "recalls":
        return "召回";
      case "complaints":
        return "投诉";
      case "medical":
        return "医疗信息";
      case "literature":
        return "文献";
      default:
        return "";
    }
  };

  // 各个组件的引用
  const newsRef = useRef<NewsManagementRef>(null);
  const recallRef = useRef<RecallManagementRef>(null);
  const complaintRef = useRef<ComplaintManagementRef>(null);
  const medicalInfoRef = useRef<MedicalInfoManagementRef>(null);
  const literatureRef = useRef<LiteratureManagementRef>(null);

  // 搜索处理
  const handleSearch = () => {
    const currentRef = getCurrentRef();
    if (currentRef && currentRef.current) {
      currentRef.current.handleSearch(searchQuery);
    }
  };

  // 新建处理
  const handleAdd = () => {
    const currentRef = getCurrentRef();
    if (currentRef && currentRef.current) {
      currentRef.current.handleAdd();
    }
  };

  // 获取当前活跃标签页对应的组件引用
  const getCurrentRef = () => {
    switch (activeTab) {
      case "news":
        return newsRef;
      case "recalls":
        return recallRef;
      case "complaints":
        return complaintRef;
      case "medical":
        return medicalInfoRef;
      case "literature":
        return literatureRef;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <InfoManagementNav />
      
      <div className="container mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-sm">
          {/* 顶部工具栏 */}
          <div className="border-b p-6">
            <div className="flex items-center gap-4">
              {/* 下拉选择框 */}
              <Select value={activeTab} onValueChange={setActiveTab}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="选择数据类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="news">新闻</SelectItem>
                  <SelectItem value="recalls">召回</SelectItem>
                  <SelectItem value="complaints">投诉</SelectItem>
                  <SelectItem value="medical">医疗信息</SelectItem>
                  <SelectItem value="literature">文献管理</SelectItem>
                </SelectContent>
              </Select>

              {/* 搜索框 */}
              <div className="flex-1 flex items-center gap-2">
                <div className="relative flex-1 max-w-xs">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-2 text-gray-400" />
                  <Input
                    placeholder={`搜索${getActiveTabLabel()}...`}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    className="pl-10"
                  />
                </div>
              </div>
              
              <Button onClick={handleAdd} className="bg-blue-600 hover:bg-blue-700">
                <Plus className="h-4 w-4 mr-2" />
                新建{getActiveTabLabel()}
              </Button>
            </div>
          </div>

          {/* 内容区域 */}
          <div className="p-6">
            {activeTab === "news" && <NewsManagement ref={newsRef} />}
            {activeTab === "recalls" && <RecallManagement ref={recallRef} />}
            {activeTab === "complaints" && <ComplaintManagement ref={complaintRef} />}
            {activeTab === "medical" && <MedicalInfoManagement ref={medicalInfoRef} />}
            {activeTab === "literature" && <LiteratureManagement ref={literatureRef} />}
          </div>
        </div>
      </div>
    </div>
  );
}
