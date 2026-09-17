"use client";

import React, { useState, useEffect, forwardRef, useImperativeHandle } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Trash2, Upload } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

// 通用采集数据项接口
export interface CollectionItem {
  id: string | number;
  [key: string]: any;
}

// 列配置接口
export interface CollectionColumnConfig {
  key: string;
  title: string;
  width?: string;
  render?: (value: any, item: CollectionItem) => React.ReactNode;
}

// 表格配置接口
export interface CollectionTableConfig {
  title: string;
  columns: CollectionColumnConfig[];
}

interface SharedCollectionTableProps {
  config: CollectionTableConfig;
  data: CollectionItem[];
  loading?: boolean;
  onDelete?: (id: string | number) => void;
  onPromote?: (id: string | number) => void;
}

export interface SharedCollectionTableRef {
  resetPage: () => void;
}

const SharedCollectionTable = forwardRef<SharedCollectionTableRef, SharedCollectionTableProps>(
  ({ config, data, loading = false, onDelete, onPromote }, ref) => {
    const [currentPage, setCurrentPage] = useState(1);
    const pageSize = 10;

    // 数据变化时重置到第一页
    useEffect(() => {
      setCurrentPage(1);
    }, [data]);

    // 暴露给父组件的方法
    useImperativeHandle(ref, () => ({
      resetPage: () => setCurrentPage(1),
    }));

    const total = data.length;
    const totalPages = Math.ceil(total / pageSize);
    const startIndex = (currentPage - 1) * pageSize;
    const currentItems = data.slice(startIndex, startIndex + pageSize);

    return (
      <Card className="flex-1 flex flex-col overflow-hidden">
        <CardHeader className="flex-shrink-0">
          <CardTitle>{config.title}</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col overflow-hidden">
          {/* 数据表格 */}
          <div className="rounded-md border flex-1 overflow-auto">
            <Table>
              <TableHeader className="bg-muted/50 sticky top-0 z-10">
                <TableRow>
                  {config.columns.map((column) => (
                    <TableHead key={column.key} className={column.width}>
                      {column.title}
                    </TableHead>
                  ))}
                  <TableHead className="w-[100px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  [...Array(5)].map((_, i) => (
                    <TableRow key={i}>
                      {config.columns.map((col) => (
                        <TableCell key={col.key}>
                          <Skeleton className="h-4 w-full" />
                        </TableCell>
                      ))}
                      <TableCell>
                        <Skeleton className="h-4 w-16" />
                      </TableCell>
                    </TableRow>
                  ))
                ) : currentItems.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={config.columns.length + 1}
                      className="text-center py-8 text-muted-foreground"
                    >
                      暂无数据，请选择筛选条件后点击查询
                    </TableCell>
                  </TableRow>
                ) : (
                  currentItems.map((item) => (
                    <TableRow key={item.id} className="hover:bg-muted/50">
                      {config.columns.map((column) => (
                        <TableCell key={column.key}>
                          {column.render
                            ? column.render(item[column.key], item)
                            : item[column.key] || "-"}
                        </TableCell>
                      ))}
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-green-600 hover:text-green-700 hover:bg-green-50"
                            onClick={() => onPromote?.(item.id)}
                          >
                            <Upload className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => onDelete?.(item.id)}
                          >
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
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 flex-shrink-0">
              <div className="text-sm text-muted-foreground">
                共 {total} 条记录，第 {currentPage} / {totalPages} 页
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                  disabled={currentPage <= 1}
                >
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                  disabled={currentPage >= totalPages}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }
);

SharedCollectionTable.displayName = "SharedCollectionTable";

export default SharedCollectionTable;
