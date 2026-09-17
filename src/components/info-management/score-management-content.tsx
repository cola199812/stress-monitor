"use client";

import React, { useState, useEffect } from "react";
import { useProductStore } from "@/store/useProductStore";
import InfoManagementNav from "./info-management-nav";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { 
  Settings, 
  Save,
  RotateCcw,
  Info,
  Edit2,
  CheckCircle2
} from "lucide-react";

const EPIDEMIOLOGY_QUESTIONS = [
  "研究对象的基本信息是否充分，如年龄、性别和 BMI 等？",
  "研究样本量是否充分且合理？",
  "设计方案是否适合验证毒物的特点？例如选取的暴露人群、时间和模式。",
  "是否纳入对照组，如阳性对照、阴性对照、父亲对照或自身对照？",
  "暴露检测或评估的方法是否科学恰当？",
  "是否明确描述研究终点及其测定方法？",
  "是否适当且透明的提供与使用了数据分析的统计方法？",
  "是否清晰和完整的描述了研究结果？",
  "纳入/排除人群以及/或低暴露组的基线数据均衡可比，并控制相要混杂因素。",
  "描述实施过程中的质量控制措施，如现场监督、样品或问卷的质量控制措施等。"
];

const IN_VIVO_QUESTIONS = [
  "是否提供试验验化学物的化学名称、来源以及纯度？",
  "是否使用合适的溶剂（载体）？其在试验浓度下不会干扰结果，并加入溶剂（载体）对照",
  "用于研究试验化学物和选定终点的动物模型是否可靠和敏感？",
  "是否描述动物模型的物种、品系、年龄或生命阶段和性别？",
  "是否有合理的染毒模式？对染毒时间、剂量和途径有明确阐释",
  "是否规定将动物分配到不同染毒组的方法和每个剂量组的动物总数？",
  "是否充分描述所使用的测试和分析方法，以评估结果的可靠性？",
  "是否报告有关于试验终点的所有研究结果？对变化趋势的描述和具有统计意义的结果以表格和图表形式呈现。",
  "各研究组的实验条件是否相同？",
  "结果评估方法是否可靠？"
];

const IN_VITRO_QUESTIONS = [
  "是否提供试验化学物的化学名称、来源及纯度？",
  "是否使用合适的溶剂（载体）？其在试验浓度下不会干扰结果，并加入溶剂（载体）对照。",
  "在适用的情况下，是否有可靠和灵敏的直接测能力的测试系统（如细胞膜系/细胞/组织/器官/胚胎/胚胎/亚细胞组分）用于研究试验化学物和终点？",
  "培养和维持细胞系/细胞/组织/器官/胚胎/亚细胞组分的条件是否合适？（包括温度、湿度、CO2 浓度、培养基配方、传代次数和繁殖染）。",
  "染毒时间和浓度是否适合测试系统和研究终点？",
  "暴露于试验化学物前和之后的条件是否合适？例如CO2（例如使用的培养基、血清、细胞密度、培养温度和CO2 浓度）。",
  "是否使用可靠和敏感的测试和分析方法来调查终点？",
  "是否描述清楚计方法，没有不恰当、不寻常或不熟悉的内容？",
  "各研究组的实验条件是否相同？",
  "结果评估方法是否可靠？"
];

export default function ScoreManagementContent() {
  const { setFeatureName } = useProductStore();
  const [activeSection, setActiveSection] = useState<'chemical-reaction' | 'product-exposure'>('chemical-reaction');

  useEffect(() => {
    setFeatureName("评分管理");
  }, [setFeatureName]);

  return (
    <div className="container mx-auto px-4 pt-4 pb-8 space-y-6 h-full overflow-auto">
      <InfoManagementNav />
      
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h2 className="text-2xl font-bold tracking-tight">评分规则配置中心</h2>
            <p className="text-muted-foreground">
              配置化学物质-不良反应评分规则和产品暴露潜力评分标准，系统将在数据管理中自动应用这些规则
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline">
              <RotateCcw className="mr-2 h-4 w-4" /> 恢复默认规则
            </Button>
            <Button>
              <Save className="mr-2 h-4 w-4" /> 保存配置
            </Button>
          </div>
        </div>

        <Tabs value={activeSection} onValueChange={(v) => setActiveSection(v as any)} className="space-y-6">
          <TabsList className="grid w-[600px] grid-cols-2">
            <TabsTrigger value="chemical-reaction">
              化学物质-不良反应评分规则（Y轴）
            </TabsTrigger>
            <TabsTrigger value="product-exposure">
              产品暴露潜力评分规则（X轴）
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chemical-reaction" className="space-y-6">
            <Card className="border-2 border-blue-200 bg-blue-50/30">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5 text-blue-600" />
                  综合评分矩阵配置
                </CardTitle>
                <CardDescription>
                  配置证据权重（Y轴）与暴露潜力（X轴）的交叉评分矩阵，用于最终风险等级判定
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="border rounded-lg overflow-hidden bg-white">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-700 hover:bg-slate-700">
                        <TableHead className="text-white font-bold">证据权重(Y轴)</TableHead>
                        <TableHead className="text-center text-white font-bold">Low[1分]</TableHead>
                        <TableHead className="text-center text-white font-bold">Medium[2分]</TableHead>
                        <TableHead className="text-center text-white font-bold">High[3分]</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow className="bg-red-50">
                        <TableCell className="font-bold">High[4分]</TableCell>
                        <TableCell className="text-center">
                          <Input type="number" defaultValue="5" className="w-16 text-center mx-auto" />
                        </TableCell>
                        <TableCell className="text-center bg-red-200">
                          <Input type="number" defaultValue="6" className="w-16 text-center mx-auto bg-red-100" />
                        </TableCell>
                        <TableCell className="text-center bg-red-400">
                          <Input type="number" defaultValue="7" className="w-16 text-center mx-auto bg-red-300" />
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-bold">Medium-high[3分]</TableCell>
                        <TableCell className="text-center">
                          <Input type="number" defaultValue="4" className="w-16 text-center mx-auto" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input type="number" defaultValue="5" className="w-16 text-center mx-auto" />
                        </TableCell>
                        <TableCell className="text-center bg-red-200">
                          <Input type="number" defaultValue="6" className="w-16 text-center mx-auto bg-red-100" />
                        </TableCell>
                      </TableRow>
                      <TableRow className="bg-green-50">
                        <TableCell className="font-bold">Medium[2分]</TableCell>
                        <TableCell className="text-center bg-green-200">
                          <Input type="number" defaultValue="3" className="w-16 text-center mx-auto bg-green-100" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input type="number" defaultValue="4" className="w-16 text-center mx-auto" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input type="number" defaultValue="5" className="w-16 text-center mx-auto" />
                        </TableCell>
                      </TableRow>
                      <TableRow className="bg-green-100">
                        <TableCell className="font-bold">Low[1分]</TableCell>
                        <TableCell className="text-center bg-green-300">
                          <Input type="number" defaultValue="2" className="w-16 text-center mx-auto bg-green-200" />
                        </TableCell>
                        <TableCell className="text-center bg-green-200">
                          <Input type="number" defaultValue="3" className="w-16 text-center mx-auto bg-green-100" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input type="number" defaultValue="4" className="w-16 text-center mx-auto" />
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>

                <div className="grid grid-cols-3 gap-3 p-4 bg-slate-50 rounded-lg border">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-green-300 rounded"></div>
                    <span className="text-sm">低优先级 (2-3分)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-orange-200 rounded"></div>
                    <span className="text-sm">一般关注 (4-5分)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-red-300 rounded"></div>
                    <span className="text-sm">重点关注 (≥6分)</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>证据权重等级阈值配置</CardTitle>
                <CardDescription>
                  配置综合得分如何映射到4个证据权重等级（Low/Medium/Medium-high/High）
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Low[1分] 阈值范围</Label>
                    <div className="flex items-center gap-2">
                      <Input type="number" placeholder="最小值" defaultValue="0" className="w-24" />
                      <span>-</span>
                      <Input type="number" placeholder="最大值" defaultValue="25" className="w-24" />
                      <span className="text-sm text-muted-foreground">分</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Medium[2分] 阈值范围</Label>
                    <div className="flex items-center gap-2">
                      <Input type="number" placeholder="最小值" defaultValue="26" className="w-24" />
                      <span>-</span>
                      <Input type="number" placeholder="最大值" defaultValue="50" className="w-24" />
                      <span className="text-sm text-muted-foreground">分</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Medium-high[3分] 阈值范围</Label>
                    <div className="flex items-center gap-2">
                      <Input type="number" placeholder="最小值" defaultValue="51" className="w-24" />
                      <span>-</span>
                      <Input type="number" placeholder="最大值" defaultValue="75" className="w-24" />
                      <span className="text-sm text-muted-foreground">分</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>High[4分] 阈值范围</Label>
                    <div className="flex items-center gap-2">
                      <Input type="number" placeholder="最小值" defaultValue="76" className="w-24" />
                      <span>-</span>
                      <Input type="number" placeholder="最大值" defaultValue="100" className="w-24" />
                      <span className="text-sm text-muted-foreground">分</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>可靠性评分问题列表</CardTitle>
                <CardDescription>
                  配置流行病学、体内实验、体外实验三种研究类型的评估问题及其分值（满足1分，部分满足0.5分，不满足0分）
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="epidemiology" className="space-y-4">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="epidemiology">流行病学研究 (0-10分)</TabsTrigger>
                    <TabsTrigger value="in-vivo">体内研究 (0-10分)</TabsTrigger>
                    <TabsTrigger value="in-vitro">体外研究 (0-10分)</TabsTrigger>
                  </TabsList>

                  <TabsContent value="epidemiology" className="space-y-3">
                    <div className="space-y-2">
                      {EPIDEMIOLOGY_QUESTIONS.map((question, idx) => (
                        <div key={idx} className="flex items-start gap-3 p-3 border rounded-lg bg-muted/30">
                          <div className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-200 text-slate-700 text-xs font-bold shrink-0 mt-0.5">
                            {idx + 1}
                          </div>
                          <div className="flex-1">
                            <p className="text-sm mb-2">{question}</p>
                            <div className="grid grid-cols-3 gap-2">
                              <div className="flex items-center gap-2">
                                <Label className="text-xs">满足:</Label>
                                <Input type="number" defaultValue="1" className="w-16 h-8" step="0.1" />
                                <span className="text-xs">分</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Label className="text-xs">部分满足:</Label>
                                <Input type="number" defaultValue="0.5" className="w-16 h-8" step="0.1" />
                                <span className="text-xs">分</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Label className="text-xs">不满足:</Label>
                                <Input type="number" defaultValue="0" className="w-16 h-8" step="0.1" />
                                <span className="text-xs">分</span>
                              </div>
                            </div>
                          </div>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <Edit2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </TabsContent>

                  <TabsContent value="in-vivo" className="space-y-3">
                    <div className="space-y-2">
                      {IN_VIVO_QUESTIONS.map((question, idx) => (
                        <div key={idx} className="flex items-start gap-3 p-3 border rounded-lg bg-muted/30">
                          <div className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-200 text-slate-700 text-xs font-bold shrink-0 mt-0.5">
                            {idx + 1}
                          </div>
                          <div className="flex-1">
                            <p className="text-sm mb-2">{question}</p>
                            <div className="grid grid-cols-3 gap-2">
                              <div className="flex items-center gap-2">
                                <Label className="text-xs">满足:</Label>
                                <Input type="number" defaultValue="1" className="w-16 h-8" step="0.1" />
                                <span className="text-xs">分</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Label className="text-xs">部分满足:</Label>
                                <Input type="number" defaultValue="0.5" className="w-16 h-8" step="0.1" />
                                <span className="text-xs">分</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Label className="text-xs">不满足:</Label>
                                <Input type="number" defaultValue="0" className="w-16 h-8" step="0.1" />
                                <span className="text-xs">分</span>
                              </div>
                            </div>
                          </div>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <Edit2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </TabsContent>

                  <TabsContent value="in-vitro" className="space-y-3">
                    <div className="space-y-2">
                      {IN_VITRO_QUESTIONS.map((question, idx) => (
                        <div key={idx} className="flex items-start gap-3 p-3 border rounded-lg bg-muted/30">
                          <div className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-200 text-slate-700 text-xs font-bold shrink-0 mt-0.5">
                            {idx + 1}
                          </div>
                          <div className="flex-1">
                            <p className="text-sm mb-2">{question}</p>
                            <div className="grid grid-cols-3 gap-2">
                              <div className="flex items-center gap-2">
                                <Label className="text-xs">满足:</Label>
                                <Input type="number" defaultValue="1" className="w-16 h-8" step="0.1" />
                                <span className="text-xs">分</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Label className="text-xs">部分满足:</Label>
                                <Input type="number" defaultValue="0.5" className="w-16 h-8" step="0.1" />
                                <span className="text-xs">分</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Label className="text-xs">不满足:</Label>
                                <Input type="number" defaultValue="0" className="w-16 h-8" step="0.1" />
                                <span className="text-xs">分</span>
                              </div>
                            </div>
                          </div>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <Edit2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>相关性评分规则</CardTitle>
                <CardDescription>
                  配置不同相关性类型的分值
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>正相关</Label>
                    <div className="flex items-center gap-2">
                      <Input type="number" defaultValue="1" className="w-24" step="0.1" />
                      <span className="text-sm text-muted-foreground">分</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>无显著相关</Label>
                    <div className="flex items-center gap-2">
                      <Input type="number" defaultValue="0" className="w-24" step="0.1" />
                      <span className="text-sm text-muted-foreground">分</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>负相关</Label>
                    <div className="flex items-center gap-2">
                      <Input type="number" defaultValue="-1" className="w-24" step="0.1" />
                      <span className="text-sm text-muted-foreground">分</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>效应强度评分规则</CardTitle>
                <CardDescription>
                  配置效应量（Cohen's d 或 Hedges'g）的阈值和分值映射
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>高效应强度 (1分)</Label>
                      <p className="text-xs text-muted-foreground">N&lt;50时，g≥0.8；N≥50时，d&gt;0.8</p>
                      <Input type="number" defaultValue="1" className="w-24" step="0.1" />
                    </div>
                    <div className="space-y-2">
                      <Label>中等效应强度 (0.8分)</Label>
                      <p className="text-xs text-muted-foreground">N&lt;50时，0.5≤g≤0.8；N≥50时，0.5&lt;d≤0.8</p>
                      <Input type="number" defaultValue="0.8" className="w-24" step="0.1" />
                    </div>
                    <div className="space-y-2">
                      <Label>低效应强度 (0.4分)</Label>
                      <p className="text-xs text-muted-foreground">N&lt;50时，|g|≤0.5；N&gt;50时，d≤0.5</p>
                      <Input type="number" defaultValue="0.4" className="w-24" step="0.1" />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="product-exposure" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>产品-化学应激源暴露潜力评分规则（X轴）</CardTitle>
                <CardDescription>
                  配置5个维度的评分标准，总分0-20分，用于计算产品暴露潜力等级
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-100">
                        <TableHead className="font-bold w-[150px]">暴露维度</TableHead>
                        <TableHead className="text-center font-bold">1分</TableHead>
                        <TableHead className="text-center font-bold">2分</TableHead>
                        <TableHead className="text-center font-bold">3分</TableHead>
                        <TableHead className="text-center font-bold">4分</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow>
                        <TableCell className="font-medium">年龄</TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="8-13" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="7-9" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="4-6" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="0-3" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                      </TableRow>
                      <TableRow className="bg-muted/30">
                        <TableCell className="font-medium">产品形态</TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="固体" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="凝胶" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="非按压泵液体" className="w-32 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="按压泵液体(粉末)" className="w-36 text-center mx-auto h-8" />
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">含量</TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="<0.1%" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="0.1%-1%" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="1-10%" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue=">10%" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                      </TableRow>
                      <TableRow className="bg-muted/30">
                        <TableCell className="font-medium">使用频率</TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="<每月一次" className="w-28 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="每月几次" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="每周几次" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="每天" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">使用时间</TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="<1 min" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="1-60 min" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="1-8 h" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                        <TableCell className="text-center">
                          <Input defaultValue="9-24 h" className="w-24 text-center mx-auto h-8" />
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>

                <Card className="border-2 border-purple-200 bg-purple-50/30">
                  <CardHeader>
                    <CardTitle className="text-base">暴露潜力等级划分规则</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label>Low[1分] 阈值范围</Label>
                        <div className="flex items-center gap-2">
                          <Input type="number" defaultValue="0" className="w-20" />
                          <span>-</span>
                          <Input type="number" defaultValue="6" className="w-20" />
                          <span className="text-sm">分</span>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>Medium[2分] 阈值范围</Label>
                        <div className="flex items-center gap-2">
                          <Input type="number" defaultValue="7" className="w-20" />
                          <span>-</span>
                          <Input type="number" defaultValue="13" className="w-20" />
                          <span className="text-sm">分</span>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>High[3分] 阈值范围</Label>
                        <div className="flex items-center gap-2">
                          <Input type="number" defaultValue="14" className="w-20" />
                          <span>-</span>
                          <Input type="number" defaultValue="20" className="w-20" />
                          <span className="text-sm">分</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-2">
                  <Info className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
                  <div className="text-sm text-blue-900">
                    <p className="font-medium mb-1">使用说明</p>
                    <p>
                      在数据管理中录入产品数据时，系统会根据用户选择的年龄、产品形态、含量、使用频率、使用时间，
                      自动计算总分（0-20分），然后根据上述阈值映射到Low/Medium/High等级，作为X轴坐标。
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <Card className="border-2 border-green-200 bg-green-50/30">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
              <div className="space-y-2">
                <h4 className="font-semibold text-green-900">配置完成后的应用流程</h4>
                <ul className="text-sm text-green-800 space-y-1 list-disc list-inside">
                  <li>在<strong>数据管理</strong>中录入文献数据时，系统会根据这些规则引导用户完成打分</li>
                  <li>在<strong>知识问答-危害评估</strong>中，展示化学物质的证据权重等级（Y轴）</li>
                  <li>在<strong>知识问答-溯源排查</strong>中，综合X轴和Y轴，根据评分矩阵计算最终风险等级</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
