"use client";

import React, { useState, useEffect, forwardRef, useImperativeHandle } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Edit2, Trash2 } from "lucide-react";
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

// 表格配置接口
export interface TableConfig {
  title: string;
  apiEndpoint: string;
  columns: ColumnConfig[];
  customSort?: (items: DataItem[]) => DataItem[];
}

export interface ColumnConfig {
  key: string;
  title: string;
  width?: string;
  render?: (value: any, item: DataItem) => React.ReactNode;
}

interface SharedDataTableProps {
  config: TableConfig;
  onEdit?: (item: DataItem) => void;
  onDelete?: (id: number) => void;
}

export interface SharedDataTableRef {
  refresh: () => void;
  handleSearch: (query: string) => void;
}

const SharedDataTable = forwardRef<SharedDataTableRef, SharedDataTableProps>(({ config, onEdit, onDelete }, ref) => {
  // 状态管理
  const [data, setData] = useState<DataItem[]>([]);
  const [allData, setAllData] = useState<DataItem[]>([]); // 保存全部原始数据
  const [filteredData, setFilteredData] = useState<DataItem[]>([]); // 保存过滤后的数据
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 10;

  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({
    refresh: fetchData,
    handleSearch: (query: string) => {
      setSearchTerm(query);
      setCurrentPage(1);
    }
  }));

  // 初始化数据
  useEffect(() => {
    fetchData();
  }, []);

  // searchTerm 变化时重置页码并过滤
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  // allData 或 searchTerm 变化时进行前端过滤
  useEffect(() => {
    if (!searchTerm.trim()) {
      // 没有搜索词，显示全部数据
      setFilteredData(allData);
    } else {
      // 有搜索词，进行前端过滤（支持 PMID 和标题搜索）
      const filtered = allData.filter(item => {
        const searchLower = searchTerm.toLowerCase().trim();
        const titleMatch = item.title?.toLowerCase().includes(searchLower);
        const pmidMatch = item.pmid?.toLowerCase().includes(searchLower);
        return titleMatch || pmidMatch;
      });
      setFilteredData(filtered);
    }
  }, [searchTerm, allData]);

  // 当过滤数据或当前页变化时，更新显示的数据
  useEffect(() => {
    const total = filteredData.length;
    const pages = Math.ceil(total / pageSize);
    setTotalCount(total);
    setTotalPages(pages);
    
    // 前端分页切片
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    setData(filteredData.slice(startIndex, endIndex));
  }, [filteredData, currentPage]);

  // 获取数据（获取全部数据，不传搜索参数）
  const fetchData = async () => {
    setLoading(true);
    try {
      // 不传分页和搜索参数，获取全部数据
      const response = await http.get(config.apiEndpoint);
      
      // 解析响应数据
      let items = [];
      let total = 0;
      let totalPages = 1;
      
      // 后端现在直接返回数组，不分页
      if (response && response.data && Array.isArray(response.data)) {
        items = response.data;
      } else if (Array.isArray(response)) {
        items = response;
      } else {
        items = [];
      }
      
      // 应用自定义排序（如果提供）
      if (config.customSort) {
        items = config.customSort(items);
      }
      
      total = items.length;
      totalPages = Math.ceil(total / pageSize);
      
      // 保存全部数据用于搜索和筛选
      setAllData(items);
      setTotalCount(total);
      setTotalPages(totalPages);
      
      // 前端分页：只显示当前页的数据
      const startIndex = (currentPage - 1) * pageSize;
      const endIndex = startIndex + pageSize;
      const currentPageItems = items.slice(startIndex, endIndex);
      
      setData(currentPageItems);
    } catch (error) {
      console.error(`获取${config.title}数据失败:`, error);
      toast.error(`获取${config.title}数据失败`);
      setData([]);
      setTotalCount(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  };

  // 编辑处理
  const handleEdit = (item: DataItem) => {
    if (onEdit) {
      onEdit(item);
    }
  };

  // 删除处理
  const handleDelete = (id: number) => {
    if (onDelete) {
      onDelete(id);
    }
  };

  return (
    <Card className="flex-1 flex flex-col border-none shadow-md">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>{config.title}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col">
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
                <TableHead className="w-[120px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={config.columns.length + 1} className="text-center py-8">
                    加载中...
                  </TableCell>
                </TableRow>
              ) : data.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={config.columns.length + 1} className="text-center py-8 text-muted-foreground">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                data.map((item) => (
                  <TableRow 
                    key={item.id} 
                    className="cursor-pointer hover:bg-muted/50"
                  >
                    {config.columns.map((column) => (
                      <TableCell key={column.key}>
                        {column.render 
                          ? column.render(item[column.key], item)
                          : item[column.key] || '-'
                        }
                      </TableCell>
                    ))}
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleEdit(item);
                          }}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(item.id);
                          }}
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
          <div className="flex items-center justify-between mt-6">
            <div className="text-sm text-muted-foreground">
              共 {totalCount} 条记录，第 {currentPage} / {totalPages} 页
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage <= 1}
              >
                上一页
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
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
});

SharedDataTable.displayName = "SharedDataTable";

export default SharedDataTable;
