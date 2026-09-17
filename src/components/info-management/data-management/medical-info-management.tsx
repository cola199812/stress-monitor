"use client";

import React, { useState, useRef, forwardRef, useImperativeHandle } from "react";
import { Badge } from "@/components/ui/badge";
import { Calendar, ExternalLink, Stethoscope, Hospital } from "lucide-react";
import SharedDataTable, { TableConfig, SharedDataTableRef, DataItem } from "./shared-data-table";
import SharedDataEdit, { EditConfig } from "./shared-data-edit";
import http from "@/lib/http";
import { toast } from "sonner";

export interface MedicalInfoManagementRef {
  refresh: () => void;
  handleAdd: () => void;
  handleSearch: (query: string) => void;
}

const MedicalInfoManagement = forwardRef<MedicalInfoManagementRef>((props, ref) => {
  const tableRef = useRef<SharedDataTableRef>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<DataItem | null>(null);

  useImperativeHandle(ref, () => ({
    refresh: () => tableRef.current?.refresh(),
    handleAdd: handleAdd,
    handleSearch: (query: string) => tableRef.current?.handleSearch(query)
  }));

  const handleAdd = () => {
    setEditingItem(null);
    setEditDialogOpen(true);
  };

  const handleEdit = (item: DataItem) => {
    setEditingItem(item);
    setEditDialogOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这条医疗信息吗？')) {
      return;
    }
    try {
      await http.delete(`/medical-info/${id}`);
      toast.success('医疗信息删除成功');
      tableRef.current?.refresh();
    } catch (error) {
      console.error('删除医疗信息失败:', error);
      toast.error('删除医疗信息失败');
    }
  };

  const handleSaveSuccess = () => {
    tableRef.current?.refresh();
  };
  const tableConfig: TableConfig = {
    title: "医疗信息管理",
    apiEndpoint: "/medical-info",
    columns: [
      {
        key: "title",
        title: "标题",
        width: "w-[350px]",
        render: (value, item) => (
          <div className="font-medium">
            <div className="max-w-[350px]">
              <div className="truncate flex items-center gap-2" title={value}>
                <Stethoscope className="h-4 w-4 text-green-500 flex-shrink-0" />
                {value}
              </div>
              <div className="flex gap-2 mt-1 text-xs text-muted-foreground">
                <span>来源: {item.source || '未知'}</span>
                {item.medical_type && (
                  <span>类型: {item.medical_type}</span>
                )}
                {item.patient_info && (
                  <span>患者: {item.patient_info}</span>
                )}
              </div>
            </div>
          </div>
        )
      },
      {
        key: "entityRelations",
        title: "实体关系",
        width: "w-[200px]",
        render: (value, item) => {
          const relations = item.entityRelations;
          if (relations && Array.isArray(relations) && relations.length > 0) {
            const displayRelations = relations.slice(0, 2);
            const hasMore = relations.length > 2;
            const allRelations = relations.map((r: any) => r.relation).join('、');
            
            return (
              <div className="max-w-[200px]" title={hasMore ? allRelations : undefined}>
                <div className="flex flex-col gap-1">
                  {displayRelations.map((rel: any, index: number) => {
                    // 最后一个Badge和+N放在同一行
                    if (index === displayRelations.length - 1 && hasMore) {
                      return (
                        <div key={index} className="flex items-center gap-1">
                          <Badge 
                            variant="secondary" 
                            className="bg-blue-50 text-blue-700 border-blue-200 text-xs w-fit"
                          >
                            {rel.relation}
                          </Badge>
                          <Badge 
                            variant="secondary" 
                            className="bg-gray-100 text-gray-600 border-gray-200 text-xs cursor-help w-fit"
                          >
                            +{relations.length - 2}
                          </Badge>
                        </div>
                      );
                    }
                    return (
                      <Badge 
                        key={index} 
                        variant="secondary" 
                        className="bg-blue-50 text-blue-700 border-blue-200 text-xs w-fit"
                      >
                        {rel.relation}
                      </Badge>
                    );
                  })}
                </div>
              </div>
            );
          }
          return <span className="text-muted-foreground text-sm">未设置</span>;
        }
      },
      {
        key: "publishTime",
        title: "发布日期",
        width: "w-[120px]",
        render: (value) => (
          <span className="text-muted-foreground text-sm">
            {value ? new Date(value).toLocaleDateString('zh-CN') : '-'}
          </span>
        )
      },
      {
        key: "severity",
        title: "状态",
        width: "w-[100px]",
        render: (value) => {
          const severityMap = {
            'low': { label: '轻微', variant: 'default' as const },
            'medium': { label: '中等', variant: 'secondary' as const },
            'high': { label: '严重', variant: 'destructive' as const },
            'critical': { label: '危急', variant: 'destructive' as const }
          };
          const severity = severityMap[value as keyof typeof severityMap] || { label: '未知', variant: 'secondary' as const };
          return (
            <Badge variant={severity.variant}>
              {severity.label}
            </Badge>
          );
        }
      }
    ]
  };

  const editConfig: EditConfig = {
    title: "医疗信息",
    apiEndpoint: "/medical-info",
    editFields: [
      {
        key: "title",
        label: "标题",
        type: "text",
        required: true,
        placeholder: "请输入医疗信息标题"
      },
      {
        key: "source",
        label: "医疗机构",
        type: "text",
        required: true,
        placeholder: "请输入医疗机构名称"
      },
      {
        key: "medical_type",
        label: "信息类型",
        type: "select",
        required: true,
        options: [
          { value: "case_report", label: "病例报告" },
          { value: "clinical_study", label: "临床研究" },
          { value: "adverse_event", label: "不良事件" },
          { value: "safety_alert", label: "安全警告" },
          { value: "guideline", label: "指南建议" },
          { value: "other", label: "其他" }
        ]
      },
      {
        key: "patient_info",
        label: "患者信息",
        type: "text",
        required: false,
        placeholder: "请输入患者基本信息（年龄、性别等）"
      },
      {
        key: "abstract",
        label: "详细描述",
        type: "textarea",
        required: true,
        placeholder: "请输入医疗信息的详细描述"
      },
      {
        key: "symptoms",
        label: "相关症状",
        type: "text",
        required: false,
        placeholder: "请输入相关症状"
      },
      {
        key: "treatment",
        label: "治疗方案",
        type: "textarea",
        required: false,
        placeholder: "请输入治疗方案"
      },
      {
        key: "link",
        label: "相关链接",
        type: "text",
        required: false,
        placeholder: "请输入相关链接"
      },
      {
        key: "publishTime",
        label: "发布时间",
        type: "date",
        required: false
      },
      {
        key: "severity",
        label: "严重程度",
        type: "select",
        required: true,
        options: [
          { value: "low", label: "轻微" },
          { value: "medium", label: "中等" },
          { value: "high", label: "严重" },
          { value: "critical", label: "危急" }
        ]
      }
    ]
  };

  return (
    <>
      <SharedDataTable 
        ref={tableRef} 
        config={tableConfig}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />
      <SharedDataEdit
        config={editConfig}
        open={editDialogOpen}
        editingItem={editingItem}
        onClose={() => setEditDialogOpen(false)}
        onSave={handleSaveSuccess}
      />
    </>
  );
});

MedicalInfoManagement.displayName = "MedicalInfoManagement";

export default MedicalInfoManagement;
