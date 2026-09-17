"use client";

import React, { useState, useRef, forwardRef, useImperativeHandle } from "react";
import { Badge } from "@/components/ui/badge";
import { Calendar, ExternalLink } from "lucide-react";
import SharedDataTable, { TableConfig, SharedDataTableRef, DataItem } from "./shared-data-table";
import SharedDataEdit, { EditConfig } from "./shared-data-edit";
import http from "@/lib/http";
import { toast } from "sonner";

export interface NewsManagementRef {
  refresh: () => void;
  handleAdd: () => void;
  handleSearch: (query: string) => void;
}

const NewsManagement = forwardRef<NewsManagementRef>((props, ref) => {
  const tableRef = useRef<SharedDataTableRef>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<DataItem | null>(null);

  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({
    refresh: () => tableRef.current?.refresh(),
    handleAdd: handleAdd,
    handleSearch: (query: string) => tableRef.current?.handleSearch(query)
  }));

  // 打开新建对话框
  const handleAdd = () => {
    setEditingItem(null);
    setEditDialogOpen(true);
  };

  // 打开编辑对话框
  const handleEdit = (item: DataItem) => {
    setEditingItem(item);
    setEditDialogOpen(true);
  };

  // 删除处理
  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这条新闻吗？')) {
      return;
    }

    try {
      await http.delete(`/news/${id}`);
      toast.success('新闻删除成功');
      tableRef.current?.refresh();
    } catch (error) {
      console.error('删除新闻失败:', error);
      toast.error('删除新闻失败');
    }
  };

  // 保存成功后的回调
  const handleSaveSuccess = () => {
    tableRef.current?.refresh();
  };

  const tableConfig: TableConfig = {
    title: "新闻管理",
    apiEndpoint: "/news",
    columns: [
      {
        key: "title",
        title: "标题",
        width: "w-[350px]",
        render: (value, item) => (
          <div className="font-medium">
            <div className="max-w-[350px]">
              <div className="truncate" title={value}>
                {value}
              </div>
              <div className="flex gap-2 mt-1 text-xs text-muted-foreground">
                {item.source_wz && <span>日报: {item.source_wz}</span>}
                {item.source && (
                  <span>网站: {item.source}</span>
                )}
                {item.link && (
                  <a 
                    href={item.link} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline flex items-center gap-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="h-3 w-3" />
                    查看原文
                  </a>
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
        key: "state",
        title: "状态",
        width: "w-[100px]",
        render: (value) => (
          <Badge variant={value ? "default" : "secondary"}>
            {value ? "已处理" : "待处理"}
          </Badge>
        )
      }
    ]
  };

  const editConfig: EditConfig = {
    title: "新闻",
    apiEndpoint: "/news",
    enableRelations: true,
    relationType: 'product-symptom',
    editFields: [
      { key: "title", label: "标题", type: "text", required: true, placeholder: "请输入新闻标题", width: "half" },
      { key: "publishTime", label: "发布日期", required: true, type: "date", width: "half" },
      { key: "source", label: "来源网站", type: "text", placeholder: "请输入来源网站", width: "half" },
      { key: "source_wz", label: "来源日报", type: "text", placeholder: "请输入来源日报", width: "half" },
      { key: "state", label: "状态", type: "select", width: "half",
        options: [
          { value: "0", label: "待处理" },
          { value: "1", label: "已处理" }
        ]
      },
      { key: "link", label: "链接", type: "text", required: true, placeholder: "请输入新闻链接", width: "half" },
      { key: "abstract", label: "摘要", type: "textarea", placeholder: "请输入新闻摘要", width: "full" }
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

NewsManagement.displayName = "NewsManagement";

export default NewsManagement;
