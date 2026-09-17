"use client";

import { useProductStore } from "@/store/useProductStore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import React, { useEffect, useState, useRef } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Upload, Download, FileText, Info } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useRouter } from "next/navigation";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface ProductUsageItem {
  id: string;
  product: string;
  educationStage: string;
  gender: string;
  totalCount: number;
  usageDuration: string;
  contactPart: string;
  contactCount: number;
  created_at?: string;
}

// 模拟数据
const mockProductUsageData: ProductUsageItem[] = [
  {
    id: "1",
    product: "儿童地垫",
    educationStage: "幼儿园",
    gender: "男",
    totalCount: 68,
    usageDuration: "1-4小时",
    contactPart: "手部",
    contactCount: 45,
    created_at: "2024-01-15T10:30:00Z"
  },
  {
    id: "2",
    product: "儿童地垫",
    educationStage: "幼儿园",
    gender: "女",
    totalCount: 77,
    usageDuration: "1-4小时",
    contactPart: "手部",
    contactCount: 52,
    created_at: "2024-01-16T14:20:00Z"
  },
  {
    id: "3",
    product: "儿童地垫",
    educationStage: "幼儿园",
    gender: "男",
    totalCount: 68,
    usageDuration: "<1小时",
    contactPart: "面部",
    contactCount: 12,
    created_at: "2024-01-17T09:15:00Z"
  },
  {
    id: "4",
    product: "儿童地垫",
    educationStage: "幼儿园",
    gender: "女",
    totalCount: 77,
    usageDuration: "<1小时",
    contactPart: "面部",
    contactCount: 18,
    created_at: "2024-01-18T16:45:00Z"
  },
  {
    id: "5",
    product: "儿童地垫",
    educationStage: "幼儿园",
    gender: "男",
    totalCount: 68,
    usageDuration: "4-8小时",
    contactPart: "全身",
    contactCount: 8,
    created_at: "2024-01-19T11:30:00Z"
  }
];

export default function MedicalCollectionContent() {
  const router = useRouter();
  const { setFeatureName, header } = useProductStore();
  const hasSetFeatureName = useRef(false);
  
  useEffect(() => {
    if (!hasSetFeatureName.current) {
      setFeatureName('医疗信息采集');
      hasSetFeatureName.current = true;
    }
  }, [setFeatureName]);

  const [items, setItems] = useState<ProductUsageItem[]>(mockProductUsageData);
  const [loadingItems, setLoadingItems] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const itemsPerPage = 10;

  // 过滤数据
  const filteredItems = items.filter(item => {
    if (!searchInput.trim()) return true;
    const searchLower = searchInput.toLowerCase();
    return (
      item.product.toLowerCase().includes(searchLower) ||
      item.educationStage.toLowerCase().includes(searchLower) ||
      item.gender.toLowerCase().includes(searchLower) ||
      item.usageDuration.toLowerCase().includes(searchLower) ||
      item.contactPart.toLowerCase().includes(searchLower)
    );
  });

  // 处理文件上传（模拟）
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // 验证文件类型
    const allowedTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/json'];
    if (!allowedTypes.includes(file.type)) {
      alert('请选择CSV、Excel或JSON文件');
      return;
    }

    // 验证文件大小 (10MB限制)
    if (file.size > 10 * 1024 * 1024) {
      alert('文件大小不能超过10MB');
      return;
    }

    setIsUploading(true);

    // 模拟上传过程
    setTimeout(() => {
      setIsUploading(false);
      alert('文件上传成功！\n\n注意：这是演示版本，实际数据未保存到数据库。');
      // 清空文件输入
      event.target.value = '';
    }, 2000);
  };

  // 导出数据（模拟）
  const handleExport = () => {
    const headers = ['产品', '教育阶段', '性别', '总人数', '使用时长', '接触部分', '接触人数', '创建时间'];
    const csvContent = [
      headers.join(','),
      ...filteredItems.map((item) => [
        item.product,
        item.educationStage,
        item.gender,
        item.totalCount,
        item.usageDuration,
        item.contactPart,
        item.contactCount,
        item.created_at || ''
      ].join(','))
    ].join('\n');

    // 下载文件
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `产品使用数据_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 前端分页切片
  const total = filteredItems.length;
  const indexOfLast = currentPage * itemsPerPage;
  const indexOfFirst = indexOfLast - itemsPerPage;
  const currentItems = filteredItems.slice(indexOfFirst, indexOfLast);

  return (
    <div className="container mx-auto px-4 pt-4 pb-8 space-y-4 h-full overflow-auto">
      {/* 顶部操作栏 */}
      <div className="flex items-center gap-4">
        {/* 数据类型选择 */}
        <Select value="medical" onValueChange={(val) => {
          if (val === 'literature') router.push('/collect/literature');
          else if (val === 'news') router.push('/collect/news');
          else if (val === 'recall') router.push('/collect/recall');
          else if (val === 'toxicity') router.push('/collect/toxicity');
        }}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="literature">文献采集</SelectItem>
            <SelectItem value="news">新闻采集</SelectItem>
            <SelectItem value="recall">召回采集</SelectItem>
            <SelectItem value="toxicity">毒性数据库</SelectItem>
            <SelectItem value="medical">医疗数据采集</SelectItem>
          </SelectContent>
        </Select>

        {/* 搜索框 */}
        <div className="flex-1 flex items-center gap-2 max-w-[50%]">
          <Input
            placeholder="搜索产品、教育阶段、性别、使用时长或接触部分..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="flex-1"
          />
        </div>

        {/* 右侧功能按钮 */}
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleExport} disabled={filteredItems.length === 0}>
            <Download className="h-4 w-4 mr-2" />
            导出数据
          </Button>
          
          <Button variant="outline" onClick={() => {
            const link = document.createElement('a');
            link.href = '/product_usage_template.csv';
            link.download = '医疗数据采集模板.csv';
            link.click();
          }}>
            <FileText className="h-4 w-4 mr-2" />
            下载模板
          </Button>
          
          <div className="relative">
            <input
              type="file"
              accept=".csv,.xlsx,.xls,.json"
              onChange={handleFileUpload}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              disabled={isUploading}
            />
            <Button disabled={isUploading}>
              <Upload className="h-4 w-4 mr-2" />
              {isUploading ? '上传中...' : '导入文件'}
            </Button>
          </div>
        </div>
      </div>

      {/* 文件格式说明 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            文件格式说明
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground space-y-2">
            <p>支持的文件格式：CSV、Excel (.xlsx/.xls)、JSON</p>
            <p>必需字段：product（产品）、educationStage（教育阶段）、gender（性别）、totalCount（总人数）</p>
            <p>可选字段：usageDuration（使用时长）、contactPart（接触部分）、contactCount（接触人数）</p>
            <p>文件大小限制：10MB</p>
          </div>
        </CardContent>
      </Card>

      {/* 医疗数据采集表格 */}
      <Card>
        <CardHeader>
          <CardTitle>医疗数据</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingItems ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : (
            <Table className="table-fixed">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[140px] text-base font-semibold text-left">产品</TableHead>
                  <TableHead className="w-[120px] text-base font-semibold text-center">教育阶段</TableHead>
                  <TableHead className="w-[80px] text-base font-semibold text-center">性别</TableHead>
                  <TableHead className="w-[90px] text-base font-semibold text-center">总人数</TableHead>
                  <TableHead className="w-[120px] text-base font-semibold text-center">使用时长</TableHead>
                  <TableHead className="w-[120px] text-base font-semibold text-center">接触部分</TableHead>
                  <TableHead className="w-[90px] text-base font-semibold text-center">接触人数</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {currentItems.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8 text-base">
                      {searchInput ? '没有找到匹配的医疗数据' : '暂无医疗数据'}
                    </TableCell>
                  </TableRow>
                ) : (
                  currentItems.map(item => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium text-base text-left">{item.product}</TableCell>
                      <TableCell className="text-base text-center">{item.educationStage}</TableCell>
                      <TableCell className="text-base text-center">{item.gender}</TableCell>
                      <TableCell className="text-center text-base font-semibold">{item.totalCount}</TableCell>
                      <TableCell className="text-base text-center">{item.usageDuration}</TableCell>
                      <TableCell className="text-base text-center">{item.contactPart}</TableCell>
                      <TableCell className="text-center text-base font-semibold">{item.contactCount}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
        {!loadingItems && total > 0 && (
          <div className="flex justify-between items-center px-6 pb-6">
            <p className="text-sm text-muted-foreground">共 {total} 条，每页 {itemsPerPage} 条</p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >上一页</Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(p => (p * itemsPerPage < total ? p + 1 : p))}
                disabled={currentPage * itemsPerPage >= total}
              >下一页</Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}