"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Search, ShieldAlert, FileText, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { GraphData } from "@/types";
import http from "@/lib/http";

interface Literature {
  id: number;
  title: string;
  authors: string;
  source: string;
  pmid: string;
  publish_date: string;
  link: string;
  evidence_strength: number;
}

interface Symptom {
  symptom_id: string;
  symptom_name: string;
  traec_score: number;
  viewpoint_id: string;
  literatures: Literature[];
}

interface AssessmentResponse {
  code: number;
  data?: {
    allergen: {
      id: number;
      name: string;
      cas_number?: string;
      description?: string;
    };
    symptoms: Symptom[];
    graph_data: {
      nodes: any[];
      edges: any[];
    };
  };
  message?: string;
}

interface HazardAssessmentPanelProps {
  onGraphDataChange?: (data: GraphData | null) => void;
}

export default function HazardAssessmentPanel({ onGraphDataChange }: HazardAssessmentPanelProps) {
  const [chemicalQuery, setChemicalQuery] = useState("");
  const [symptoms, setSymptoms] = useState<Symptom[]>([]);
  const [allergenInfo, setAllergenInfo] = useState<{id: number; name: string; cas_number?: string} | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [activeDetail, setActiveDetail] = useState<Symptom | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!chemicalQuery.trim()) return;
    
    setLoading(true);
    setHasSearched(true);
    setError(null);
    
    try {
      const data: AssessmentResponse = await http.post('/hazard-assessment/assess', {
        query: chemicalQuery.trim()
      });
      
      if (data.code === 200 && data.data) {
        setAllergenInfo(data.data.allergen);
        setSymptoms(data.data.symptoms);
        
        // 将图谱数据传递给父组件，用于在左侧显示
        if (onGraphDataChange && data.data.graph_data) {
          // 转换API返回的图谱数据格式为组件需要的格式
          const graphData: GraphData = {
            nodes: data.data.graph_data.nodes.map((node: any) => ({
              id: String(node.id),
              label: node.label || '',
              name: node.data?.name || node.label || '',
              entityType: node.type === 'allergen' ? 'Allergen' : 
                         node.type === 'symptom' ? 'Symptom' :
                         node.type === 'adverse_reaction' ? 'AdverseReaction' : node.type,
              // 将完整的data存储在meta中，包含文献详情
              meta: node.data
            })),
            edges: data.data.graph_data.edges.map((edge: any) => ({
              from: String(edge.source),
              to: String(edge.target),
              type: edge.label || edge.type || ''
            }))
          };
          onGraphDataChange(graphData);
        }
      } else {
        setError(data.message || '查询失败');
        setSymptoms([]);
        setAllergenInfo(null);
        // 清空图谱数据
        if (onGraphDataChange) {
          onGraphDataChange(null);
        }
      }
    } catch (err) {
      setError('网络请求失败，请检查服务器连接');
      setSymptoms([]);
      setAllergenInfo(null);
    } finally {
      setLoading(false);
    }
  };

  const getRiskLevel = (score: number) => {
    if (score >= 8) return { level: "critical", label: "极高风险", color: "bg-red-600", variant: "destructive" };
    if (score >= 5) return { level: "high", label: "高风险", color: "bg-orange-500", variant: "destructive" };
    if (score >= 2) return { level: "medium", label: "中等风险", color: "bg-yellow-500", variant: "secondary" };
    return { level: "low", label: "低风险", color: "bg-green-500", variant: "outline" };
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex flex-col gap-4 mb-4 flex-shrink-0">
        <div className="space-y-1">
          <h3 className="text-lg font-medium">化学品危害评估</h3>
        </div>
        
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="输入化学物质名称或 CAS 号"
              className="pl-8"
              value={chemicalQuery}
              onChange={(e) => setChemicalQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
          </div>
          <Button onClick={handleSearch} disabled={loading || !chemicalQuery.trim()}>
            {loading ? "分析中..." : "评估"}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 space-y-4 pr-1">
        {hasSearched && (
          <>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="text-xl font-medium">{allergenInfo?.name || chemicalQuery}</div>
                    {allergenInfo?.cas_number && (
                      <div className="text-sm text-muted-foreground font-mono">CAS: {allergenInfo.cas_number}</div>
                    )}
                    <Badge variant="secondary" className="mt-1">化学物质</Badge>
                  </div>
                  <div className="text-right">
                     <div className="text-sm text-muted-foreground">关联风险数量</div>
                     <div className="text-2xl font-bold text-orange-500">{symptoms.length}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                 <h4 className="text-sm font-medium flex items-center">
                   <ShieldAlert className="h-4 w-4 mr-1.5 text-orange-500" />
                   关联不良反应
                 </h4>
                 <span className="text-xs text-muted-foreground">共 {symptoms.length} 项</span>
              </div>
              
              <div className="space-y-3">
                {loading ? (
                  <div className="text-center py-8 text-muted-foreground">正在分析模型...</div>
                ) : error ? (
                  <div className="text-center py-8 text-red-500">{error}</div>
                ) : symptoms.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">未发现关联数据</div>
                ) : (
                  symptoms.map((item, index) => {
                    const riskLevel = getRiskLevel(item.traec_score);
                    return (
                      <Card key={index} className={`overflow-hidden transition-colors hover:bg-muted/50 ${riskLevel.level === 'high' || riskLevel.level === 'critical' ? 'border-red-200 bg-red-50/30' : ''}`}>
                        <CardContent className="p-3">
                          <div className="flex justify-between items-start mb-2">
                            <span className="font-medium">{item.symptom_name}</span>
                            <Badge variant={riskLevel.variant as any} className="text-[10px] h-5 px-1.5">
                              {riskLevel.label}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
                            TRAEC评分: {item.traec_score.toFixed(2)} | 佐证文献: {item.literatures.length}篇
                          </p>
                          
                          <div className="flex items-center gap-2">
                               <Progress value={Math.min(item.traec_score * 10, 100)} className={`h-1.5 flex-1 [&>div]:${riskLevel.color}`} />
                               <span className="text-xs w-8 text-right">{item.traec_score.toFixed(1)}</span>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })
                )}
              </div>
            </div>
          </>
        )}
      </div>

      <Sheet open={detailOpen} onOpenChange={setDetailOpen}>
        <SheetContent className="w-[400px] sm:max-w-[540px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle>佐证文献详情</SheetTitle>
            <SheetDescription>
              "{activeDetail?.symptom_name}" 的相关研究文献
            </SheetDescription>
          </SheetHeader>
          
          {activeDetail && (
            <div className="mt-6 space-y-6">
               <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
                  <h4 className="font-semibold text-orange-800 flex items-center mb-2">
                    <AlertTriangle className="h-4 w-4 mr-2" />
                    风险评估
                  </h4>
                  <p className="text-sm text-orange-700">
                    TRAEC评分: {activeDetail.traec_score.toFixed(2)} | 风险等级: {getRiskLevel(activeDetail.traec_score).label}
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium flex items-center">
                    <FileText className="h-4 w-4 mr-2" />
                    佐证文献 ({activeDetail.literatures.length}篇)
                  </h4>
                  <div className="space-y-3">
                    {activeDetail.literatures.length > 0 ? (
                      activeDetail.literatures.map((lit: Literature) => (
                        <div key={lit.id} className="p-3 border rounded-md">
                          <div className="font-medium text-sm mb-1 line-clamp-2">{lit.title}</div>
                          <div className="text-xs text-muted-foreground space-y-1">
                            {lit.authors && <div>作者: {lit.authors}</div>}
                            <div className="flex gap-4">
                              <span>来源: {lit.source}</span>
                              {lit.pmid && <span>PMID: {lit.pmid}</span>}
                            </div>
                            <div className="flex gap-4">
                              <span>证据强度: {lit.evidence_strength.toFixed(1)}</span>
                              {lit.publish_date && <span>发布日期: {lit.publish_date}</span>}
                            </div>
                            {lit.link && (
                              <div>
                                <a href={lit.link} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                                  查看原文
                                </a>
                              </div>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-4 text-muted-foreground">暂无佐证文献</div>
                    )}
                  </div>
                </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
