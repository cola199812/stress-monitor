"use client";

import { useState } from 'react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import KnowledgeGraph from "@/components/knowledge/knowledge-graph";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import ChatInterface from "@/components/qa/ChatInterface";
import HazardAssessmentPanel from "@/components/qa/HazardAssessmentPanel";
import SourceTracingPanel from "@/components/qa/SourceTracingPanel";
import { GraphData } from "@/types";

type QAMode = 'qa' | 'hazard' | 'tracing';

export default function QAPage() {
  const [currentMode, setCurrentMode] = useState<QAMode>('qa');
  const [graphData, setGraphData] = useState<GraphData | null>(null);

  return (
    <div className="flex flex-col h-[810px] overflow-hidden bg-transparent">
      <main className="container mx-auto px-4 pt-4 pb-8">
        <div className="px-0 h-full space-y-[var(--space-lg)]">
          <ResizablePanelGroup direction="horizontal" className="h-full w-full min-h-0 overflow-hidden">
            {/* 知识图谱面板 (左侧) */}
            <ResizablePanel defaultSize={60}>
              <div className="h-[700px] rounded-xl border ">
                <KnowledgeGraph 
                  externalGraphData={graphData} 
                  hideProductSelector={currentMode === 'hazard' || currentMode === 'tracing'}
                  showEdgesByDefault={currentMode === 'tracing'}
                />
              </div>
            </ResizablePanel>
            <ResizableHandle withHandle className="opacity-0" />

            {/* 功能交互面板 (右侧) */}
            <ResizablePanel defaultSize={40}>
              <div className="flex flex-col h-[700px] p-4 rounded-xl border shadow">
                {/* 顶部模式切换下拉框 */}
                <div className="mb-4 flex items-center justify-between border-b pb-3">
                  <Select value={currentMode} onValueChange={(v) => {
                    setCurrentMode(v as QAMode);
                    // 切换模式时清空图谱数据，恢复默认视图
                    if (v !== 'hazard' && v !== 'tracing') {
                      setGraphData(null);
                    }
                  }}>
                    <SelectTrigger className="w-[180px]">
                      <SelectValue placeholder="选择功能模式" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="qa">知识问答</SelectItem>
                      <SelectItem value="hazard">危害评估</SelectItem>
                      <SelectItem value="tracing">危害识别</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* 内容区域 */}
                <div className="flex-1 min-h-0 overflow-hidden">
                  {currentMode === 'qa' && <ChatInterface />}
                  {currentMode === 'hazard' && <HazardAssessmentPanel onGraphDataChange={setGraphData} />}
                  {currentMode === 'tracing' && <SourceTracingPanel onGraphDataChange={setGraphData} />}
                </div>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>
      </main>
    </div>
  );
}