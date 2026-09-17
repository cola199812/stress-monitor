"use client";

import React, { useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ArrowRight, Search, ShieldAlert, AlertTriangle, Loader2 } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { GraphData } from "@/types";
import http from "@/lib/http";

interface ProductOption {
  id: number;
  name: string;
}

interface ProductInfo {
  id: number;
  name: string;
}

interface SymptomOption {
  id: number;
  name: string;
  confidence: number | null;
}

interface HazardResult {
  allergen_id: number;
  allergen_name: string;
  cas_number: string | null;
  exposure_score: number;
  exposure_level: number;
  traec_score: number;
  traec_level: number;
  confidence: number;
  confidence_level: number;
  total_score: number;
  risk_label: string;
}

interface SourceTracingPanelProps {
  onGraphDataChange?: (data: GraphData | null) => void;
}

export default function SourceTracingPanel({ onGraphDataChange }: SourceTracingPanelProps) {
  const [productOptions, setProductOptions] = useState<ProductOption[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [productInfo, setProductInfo] = useState<ProductInfo | null>(null);
  const [symptomOptions, setSymptomOptions] = useState<SymptomOption[]>([]);
  const [selectedSymptomId, setSelectedSymptomId] = useState<string>("");
  const [results, setResults] = useState<HazardResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [productLoading, setProductLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [activeDetail, setActiveDetail] = useState<HazardResult | null>(null);
  const [confidenceInfo, setConfidenceInfo] = useState<{ overall: number; level: string } | null>(null);

  // 加载产品列表
  React.useEffect(() => {
    const loadProducts = async () => {
      try {
        const res: any = await http.get('/hazard-assessment/products');
        if (res.code === 200 && res.data) {
          setProductOptions(res.data.products || []);
        }
      } catch (err) {
        console.error('加载产品列表失败:', err);
      }
    };
    loadProducts();
  }, []);

  // 转换后端图谱数据为前端GraphData格式
  const convertGraphData = useCallback((graphData: { nodes: any[]; edges: any[] }): GraphData => {
    return {
      nodes: graphData.nodes.map((node: any) => ({
        id: String(node.id),
        label: node.label || '',
        name: node.data?.name || node.label || '',
        entityType: node.type === 'product' ? 'Product' :
                   node.type === 'allergen' ? 'Allergen' :
                   node.type === 'symptom' ? 'Symptom' : node.type,
        meta: node.data
      })),
      edges: graphData.edges.map((edge: any) => ({
        from: String(edge.source),
        to: String(edge.target),
        type: edge.label || edge.type || ''
      }))
    };
  }, []);

  // 选择产品后加载关联化学物质
  const handleProductChange = async (productId: string) => {
    setSelectedProductId(productId);
    
    if (!productId) {
      setProductInfo(null);
      setSymptomOptions([]);
      setSelectedSymptomId("");
      setResults([]);
      setHasSearched(false);
      if (onGraphDataChange) onGraphDataChange(null);
      return;
    }

    setProductLoading(true);
    setError(null);
    setSymptomOptions([]);
    setSelectedSymptomId("");
    setResults([]);
    setHasSearched(false);

    try {
      const res: any = await http.get(`/hazard-assessment/product-chemicals/${productId}`);

      if (res.code === 200 && res.data) {
        const product = res.data.product;
        setProductInfo(product);

        // 更新左侧知识图谱
        if (onGraphDataChange && res.data.graph_data) {
          onGraphDataChange(convertGraphData(res.data.graph_data));
        }

        // 加载产品关联的不良反应
        const symptomRes: any = await http.get('/hazard-assessment/product-symptoms', {
          params: { product_id: product.id }
        });
        if (symptomRes.code === 200 && symptomRes.data) {
          setSymptomOptions(symptomRes.data.symptoms || []);
        }
      } else {
        setError(res.message || '加载产品失败');
        if (onGraphDataChange) onGraphDataChange(null);
      }
    } catch (err) {
      setError('加载产品失败，请检查网络');
    } finally {
      setProductLoading(false);
    }
  };

  // 开始危害识别查询
  const handleIdentify = async () => {
    if (!productInfo || !selectedSymptomId) return;

    setLoading(true);
    setHasSearched(true);
    setError(null);

    try {
      const res: any = await http.post('/hazard-assessment/identify', {
        product_id: productInfo.id,
        symptom_id: parseInt(selectedSymptomId)
      });

      if (res.code === 200 && res.data) {
        setResults(res.data.combinations || []);
        setConfidenceInfo(res.data.confidence ? {
          overall: res.data.confidence.overall,
          level: res.data.confidence.level
        } : null);

        // 更新图谱
        if (onGraphDataChange && res.data.graph_data) {
          onGraphDataChange(convertGraphData(res.data.graph_data));
        }
      } else {
        setError(res.message || '查询失败');
        setResults([]);
      }
    } catch (err) {
      setError('危害识别失败，请检查网络');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (label: string) => {
    switch (label) {
      case '高风险': return { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', badge: 'destructive' as const };
      case '中风险': return { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-200', badge: 'secondary' as const };
      default: return { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', badge: 'outline' as const };
    }
  };

  const selectedSymptom = symptomOptions.find(s => String(s.id) === selectedSymptomId);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex flex-col gap-4 mb-4 flex-shrink-0">
        <div className="space-y-1">
          <h3 className="text-lg font-medium">危害识别</h3>
        </div>

        <div className="space-y-3 p-3 bg-muted/50 rounded-lg border">
          {/* 产品选择 */}
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">涉事产品</Label>
            <Select
              value={selectedProductId}
              onValueChange={handleProductChange}
              disabled={productLoading}
            >
              <SelectTrigger className="h-8 bg-background">
                <SelectValue placeholder="选择产品" />
              </SelectTrigger>
              <SelectContent>
                {productOptions.map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {productLoading && (
              <div className="flex items-center gap-1.5 mt-1 text-[10px] text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>加载中...</span>
              </div>
            )}
          </div>

          <div className="flex justify-center -my-1">
            <ArrowRight className="h-4 w-4 text-muted-foreground rotate-90" />
          </div>

          {/* 不良反应选择框 */}
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">不良反应</Label>
            <Select
              value={selectedSymptomId}
              onValueChange={setSelectedSymptomId}
              disabled={!productInfo || symptomOptions.length === 0}
            >
              <SelectTrigger className="h-8 bg-background">
                <SelectValue placeholder={
                  !productInfo ? "请先搜索产品" :
                  symptomOptions.length === 0 ? "该产品暂无关联不良反应" :
                  "选择不良反应"
                } />
              </SelectTrigger>
              <SelectContent>
                {symptomOptions.map((s) => (
                  <SelectItem key={s.id} value={String(s.id)}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button
            className="w-full mt-2"
            size="sm"
            onClick={handleIdentify}
            disabled={loading || !productInfo || !selectedSymptomId}
          >
            {loading ? "评估计算中..." : "开始查询"}
          </Button>
        </div>

        {error && (
          <div className="text-xs text-red-500 px-1">{error}</div>
        )}
      </div>

      {/* 结果展示区域 */}
      <div className="flex-1 overflow-y-auto min-h-0 space-y-4 pr-1">
        {hasSearched && !loading && (
          <div className="space-y-4">
            {/* 置信度信息 */}
            {confidenceInfo && (
              <div className="p-2.5 rounded-lg border bg-muted/30">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">产品-不良反应置信度</span>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{(confidenceInfo.overall * 100).toFixed(0)}%</span>
                    <Badge variant="outline" className="text-[10px] h-4 px-1">{confidenceInfo.level}</Badge>
                  </div>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium flex items-center">
                <ShieldAlert className="h-4 w-4 mr-2 text-orange-500" />
                风险化学物质
              </h4>
              <Badge variant="outline" className="text-xs font-normal">
                {results.length} 个交集物质
              </Badge>
            </div>

            <div className="space-y-3">
              {results.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground text-sm">
                  未找到产品与不良反应的共同关联化学物质
                </div>
              ) : (
                results.map((item) => {
                  const riskColor = getRiskColor(item.risk_label);
                  return (
                    <Card
                      key={item.allergen_id}
                      className={`overflow-hidden transition-all hover:shadow-sm cursor-pointer ${riskColor.border}`}
                      onClick={() => { setActiveDetail(item); setDetailOpen(true); }}
                    >
                      <CardContent className="p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{item.allergen_name}</div>
                            {item.cas_number && (
                              <div className="text-[10px] text-muted-foreground font-mono">CAS: {item.cas_number}</div>
                            )}
                          </div>
                          <Badge variant={riskColor.badge} className="text-[10px] h-5 px-1.5 ml-2 shrink-0">
                            {item.risk_label} ({item.total_score}分)
                          </Badge>
                        </div>

                        {/* 三维度评分条 */}
                        <div className="space-y-1.5 text-[10px]">
                          <div className="flex items-center gap-2">
                            <span className="w-16 text-muted-foreground shrink-0">暴露潜力</span>
                            <Progress value={item.exposure_level / 3 * 100} className="h-1.5 flex-1" />
                            <span className="w-12 text-right">{item.exposure_score} → {item.exposure_level}分</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="w-16 text-muted-foreground shrink-0">TRAEC</span>
                            <Progress value={item.traec_level / 3 * 100} className="h-1.5 flex-1" />
                            <span className="w-12 text-right">{item.traec_score.toFixed(1)} → {item.traec_level}分</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="w-16 text-muted-foreground shrink-0">置信度</span>
                            <Progress value={item.confidence_level / 3 * 100} className="h-1.5 flex-1" />
                            <span className="w-12 text-right">{(item.confidence * 100).toFixed(0)}% → {item.confidence_level}分</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })
              )}
            </div>
          </div>
        )}

        {loading && (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin mb-2" />
            <span className="text-sm">正在进行危害识别计算...</span>
          </div>
        )}
      </div>

      {/* 详情侧边栏 */}
      <Sheet open={detailOpen} onOpenChange={setDetailOpen}>
        <SheetContent className="w-[400px] sm:max-w-[540px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle>危害识别详情</SheetTitle>
            <SheetDescription>
              化学物质 "{activeDetail?.allergen_name}" 的风险评估详情
            </SheetDescription>
          </SheetHeader>

          {activeDetail && (
            <div className="mt-6 space-y-6">
              {/* 风险等级 */}
              <div className={`p-4 rounded-lg border ${getRiskColor(activeDetail.risk_label).bg} ${getRiskColor(activeDetail.risk_label).border}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`h-5 w-5 ${getRiskColor(activeDetail.risk_label).text}`} />
                    <span className={`font-semibold text-lg ${getRiskColor(activeDetail.risk_label).text}`}>
                      {activeDetail.risk_label}
                    </span>
                  </div>
                  <span className={`text-2xl font-bold ${getRiskColor(activeDetail.risk_label).text}`}>
                    {activeDetail.total_score}分
                  </span>
                </div>
                <p className="text-xs mt-2 text-muted-foreground">
                  计算公式: 暴露分({activeDetail.exposure_level}) × TRAEC分({activeDetail.traec_level}) × 置信度分({activeDetail.confidence_level}) = {activeDetail.total_score}
                </p>
              </div>

              {/* 推导路径 */}
              <div>
                <h4 className="font-medium mb-3">推导路径</h4>
                <div className="p-3 bg-muted/30 border border-dashed rounded text-sm flex items-center flex-wrap gap-2">
                  <Badge variant="outline">{productInfo?.name}</Badge>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <Badge className="bg-purple-100 text-purple-800 hover:bg-purple-100 border-purple-200">含有</Badge>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <span className="font-bold text-foreground">{activeDetail.allergen_name}</span>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <Badge className="bg-red-100 text-red-800 hover:bg-red-100 border-red-200">诱发</Badge>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <Badge variant="outline">{selectedSymptom?.name}</Badge>
                </div>
              </div>

              {/* 评分明细 */}
              <div>
                <h4 className="font-medium mb-2">评分明细</h4>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="h-8">维度</TableHead>
                      <TableHead className="h-8">原始值</TableHead>
                      <TableHead className="h-8">区间</TableHead>
                      <TableHead className="h-8">得分</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell className="py-2 font-medium">暴露潜力</TableCell>
                      <TableCell className="py-2">{activeDetail.exposure_score}</TableCell>
                      <TableCell className="py-2 text-xs text-muted-foreground">
                        {activeDetail.exposure_score < 10 ? '5-9' : activeDetail.exposure_score < 16 ? '10-15' : '16-20'}
                      </TableCell>
                      <TableCell className="py-2 font-bold">{activeDetail.exposure_level}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="py-2 font-medium">TRAEC评分</TableCell>
                      <TableCell className="py-2">{activeDetail.traec_score.toFixed(2)}</TableCell>
                      <TableCell className="py-2 text-xs text-muted-foreground">
                        {activeDetail.traec_score < 4 ? '0-4' : activeDetail.traec_score < 8 ? '4-8' : '8-10'}
                      </TableCell>
                      <TableCell className="py-2 font-bold">{activeDetail.traec_level}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="py-2 font-medium">置信度</TableCell>
                      <TableCell className="py-2">{(activeDetail.confidence * 100).toFixed(1)}%</TableCell>
                      <TableCell className="py-2 text-xs text-muted-foreground">
                        {activeDetail.confidence < 0.4 ? '0-0.4' : activeDetail.confidence < 0.8 ? '0.4-0.8' : '0.8-1'}
                      </TableCell>
                      <TableCell className="py-2 font-bold">{activeDetail.confidence_level}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>

              {/* 风险等级说明 */}
              <div>
                <h4 className="font-medium mb-2">风险等级标准</h4>
                <div className="space-y-1.5 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-sm bg-green-500" />
                    <span>低风险: 总分 1-6 分</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-sm bg-orange-500" />
                    <span>中风险: 总分 8-12 分</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-sm bg-red-500" />
                    <span>高风险: 总分 18-27 分</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
