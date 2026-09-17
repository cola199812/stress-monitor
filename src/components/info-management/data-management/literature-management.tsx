"use client";

import React, { useRef, forwardRef, useImperativeHandle } from "react";
import SharedDataTable, { SharedDataTableRef } from "./shared-data-table";
import LiteratureEdit, { LiteratureEditRef } from "./literature-management-edit";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import http from "@/lib/http";

export interface LiteratureManagementRef {
  handleAdd: () => void;
  handleSearch: (query: string) => void;
  refresh: () => void;
}

const LiteratureManagement = forwardRef<LiteratureManagementRef, {}>((props, ref) => {
  const tableRef = useRef<SharedDataTableRef>(null);
  const editRef = useRef<LiteratureEditRef>(null);

  // 暴露方法给父组件
  useImperativeHandle(ref, () => ({
    handleAdd: () => {
      editRef.current?.open();
    },
    handleSearch: (query: string) => {
      tableRef.current?.handleSearch(query);
    },
    refresh: () => {
      tableRef.current?.refresh();
    }
  }));

  // 删除处理
  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这篇文献吗？')) {
      return;
    }

    try {
      await http.delete(`/literature/${id}`);
      toast.success('文献删除成功');
      tableRef.current?.refresh();
    } catch (error) {
      console.error('删除文献失败:', error);
      toast.error('删除文献失败');
    }
  };

  // 编辑处理
  const handleEdit = (item: any) => {
    editRef.current?.open(item);
  };

  // 保存成功后的回调
  const handleSaveSuccess = () => {
    tableRef.current?.refresh();
  };

  // 获取文献类型标签
  const getLiteratureTypeLabel = (type: string) => {
    switch (type) {
      case 'epidemiology':
        return '流行病学';
      case 'in-vivo':
        return '体内实验';
      case 'in-vitro':
        return '体外实验';
      default:
        return '未知';
    }
  };

  // 获取文献类型颜色样式
  const getLiteratureTypeColor = (type: string) => {
    switch (type) {
      case 'epidemiology':
        return 'text-blue-600'; // 流行病学使用蓝色
      case 'in-vivo':
        return 'text-green-600'; // 体内实验使用绿色
      case 'in-vitro':
        return 'text-orange-600'; // 体外实验使用橙色
      default:
        return 'text-gray-600'; // 未知类型使用灰色
    }
  };

  // 获取文献类型排序优先级
  const getLiteratureTypePriority = (type: string) => {
    switch (type) {
      case 'epidemiology':
        return 1; // 流行病学优先级最高
      case 'in-vivo':
        return 2; // 体内实验次之
      case 'in-vitro':
        return 3; // 体外实验再次
      default:
        return 4; // 未知类型优先级最低
    }
  };

  // 表格配置
  const tableConfig = {
    title: '文献',
    apiEndpoint: '/literature',
    customSort: (items: any[]) => {
      return [...items].sort((a, b) => {
        const aPriority = getLiteratureTypePriority(a.literatureType || '');
        const bPriority = getLiteratureTypePriority(b.literatureType || '');
        return aPriority - bPriority;
      });
    },
    columns: [
      {
        key: 'title',
        title: '标题',
        width: 'w-[350px]',
        render: (value: any, item: any) => (
          <div className="max-w-[350px]">
            <div className="truncate font-medium" title={item.title}>
              {item.title}
            </div>
            <div className="flex gap-2 mt-1 text-xs text-muted-foreground">
              <span>来源: {item.source}</span>
              {item.pmid && <span>PMID: {item.pmid}</span>}
              {item.literatureType && (
                <span className={getLiteratureTypeColor(item.literatureType)}>
                  类型: {getLiteratureTypeLabel(item.literatureType)}
                </span>
              )}
            </div>
          </div>
        )
      },
      {
        key: 'entityRelations',
        title: '实体关系',
        width: 'w-[200px]',
        render: (value: any, item: any) => {
          const relations = value || [];
          const maxDisplay = 2;

          if (relations.length === 0) {
            return <span className="text-muted-foreground text-sm">未设置</span>;
          }

          const displayRelations = relations.slice(0, maxDisplay);
          const remainingCount = relations.length - maxDisplay;

          return (
            <div className="flex flex-col gap-1">
              {displayRelations.map((rel: any, idx: number) => (
                <Badge
                  key={idx}
                  variant="secondary"
                  className="bg-blue-50 text-blue-700 border-blue-200 text-xs w-fit"
                >
                  {rel.relation}
                </Badge>
              ))}
              {remainingCount > 0 && (
                <Badge variant="outline" className="text-xs w-fit">
                  +{remainingCount}
                </Badge>
              )}
            </div>
          );
        }
      },
      {
        key: 'publishDate',
        title: '发布日期',
        width: 'w-[120px]',
        render: (value: any, item: any) => (
          <span className="text-muted-foreground text-sm">
            {value || '-'}
          </span>
        )
      },
      {
        key: 'state',
        title: '状态',
        width: 'w-[100px]',
        render: (value: any, item: any) => (
          <Badge variant={value ? "default" : "secondary"}>
            {value ? "已处理" : "待处理"}
          </Badge>
        )
      }
    ]
  };

  // 编辑配置
  const editConfig = {
    title: '文献',
    apiEndpoint: '/literature',
    enableRelations: true
  };

  return (
    <>
      <SharedDataTable
        ref={tableRef}
        config={tableConfig}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />

      <LiteratureEdit
        ref={editRef}
        config={editConfig}
        onSave={handleSaveSuccess}
      />
    </>
  );
});

LiteratureManagement.displayName = 'LiteratureManagement';

export default LiteratureManagement;
