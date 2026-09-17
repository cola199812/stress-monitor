"use client";

import React, { useState, useRef, forwardRef, useImperativeHandle } from "react";
import { Badge } from "@/components/ui/badge";
import { Calendar, ExternalLink, AlertTriangle } from "lucide-react";
import SharedDataTable, { TableConfig, SharedDataTableRef, DataItem } from "./shared-data-table";
import SharedDataEdit, { EditConfig } from "./shared-data-edit";
import http from "@/lib/http";
import { toast } from "sonner";

export interface RecallManagementRef {
  refresh: () => void;
  handleAdd: () => void;
  handleSearch: (query: string) => void;
}

const RecallManagement = forwardRef<RecallManagementRef>((props, ref) => {
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
    if (!confirm('确定要删除这条召回信息吗？')) {
      return;
    }
    try {
      await http.delete(`/recalls/${id}`);
      toast.success('召回信息删除成功');
      tableRef.current?.refresh();
    } catch (error) {
      console.error('删除召回信息失败:', error);
      toast.error('删除召回信息失败');
    }
  };

  const handleSaveSuccess = () => {
    tableRef.current?.refresh();
  };
  const tableConfig: TableConfig = {
    title: "召回管理",
    apiEndpoint: "/recalls",
    columns: [
      {
        key: "title",
        title: "标题",
        width: "w-[350px]",
        render: (value, item) => (
          <div className="font-medium">
            <div className="max-w-[350px]">
              <div className="truncate flex items-center gap-2" title={value}>
                <AlertTriangle className="h-4 w-4 text-orange-500 flex-shrink-0" />
                {value}
              </div>
              <div className="flex gap-2 mt-1 text-xs text-muted-foreground">
                <span>来源: {item.source || '未知'}</span>
                {item.product_name && (
                  <span>产品: {item.product_name}</span>
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
        key: "status",
        title: "状态",
        width: "w-[100px]",
        render: (value) => {
          const statusMap = {
            'active': { label: '进行中', variant: 'destructive' as const },
            'completed': { label: '已完成', variant: 'default' as const },
            'pending': { label: '待处理', variant: 'secondary' as const }
          };
          const status = statusMap[value as keyof typeof statusMap] || { label: '未知', variant: 'secondary' as const };
          return (
            <Badge variant={status.variant}>
              {status.label}
            </Badge>
          );
        }
      }
    ]
  };

  const editConfig: EditConfig = {
    title: "召回",
    apiEndpoint: "/recalls",
    editFields: [
      {
        key: "title",
        label: "召回标题",
        type: "text",
        required: true,
        placeholder: "请输入召回标题"
      },
      {
        key: "source",
        label: "发布机构",
        type: "text",
        required: true,
        placeholder: "请输入发布机构"
      },
      {
        key: "product_name",
        label: "产品名称",
        type: "text",
        required: true,
        placeholder: "请输入产品名称"
      },
      {
        key: "recall_reason",
        label: "召回原因",
        type: "textarea",
        required: true,
        placeholder: "请输入召回原因"
      },
      {
        key: "abstract",
        label: "详细描述",
        type: "textarea",
        required: false,
        placeholder: "请输入详细描述"
      },
      {
        key: "link",
        label: "链接",
        type: "text",
        required: false,
        placeholder: "请输入召回公告链接"
      },
      {
        key: "publishTime",
        label: "发布时间",
        type: "date",
        required: false
      },
      {
        key: "status",
        label: "状态",
        type: "select",
        required: true,
        options: [
          { value: "pending", label: "待处理" },
          { value: "active", label: "进行中" },
          { value: "completed", label: "已完成" }
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

RecallManagement.displayName = "RecallManagement";

export default RecallManagement;
