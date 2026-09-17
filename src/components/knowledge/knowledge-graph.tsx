"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { GraphData } from "@/types";
import { formatDateYMD } from "@/lib/utils";
import http from "@/lib/http";
import { useProductStore } from "@/store/useProductStore";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import GraphChart from "./GraphChart";

// 产品表格组件
const ProductTable = ({ 
  data, 
  onItemClick, 
  entityTypeMap 
}: { 
  data: Array<{ id: string; name?: string; title?: string; entityType: string; url?: string; source?: string; publishDate?: string }>;
  onItemClick: (item: any) => void;
  entityTypeMap: Record<string, string>;
}) => {
  return (
    <Table className="w-full max-w-2xl">
      <TableHeader>
        <TableRow>
          <TableHead className="w-16">序号</TableHead>
          <TableHead className="w-1/3">产品名称</TableHead>
          <TableHead className="w-20">类型</TableHead>
          <TableHead className="w-28">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item, index) => (
          <TableRow key={item.id || index}>
            <TableCell className="font-medium w-16">{index + 1}</TableCell>
            <TableCell className="font-medium w-96">{item.name || item.title}</TableCell>
            <TableCell className="w-20">{entityTypeMap[item.entityType] || item.entityType}</TableCell>
            <TableCell className="w-28">
              <Button
                size="sm"
                variant="outline"
                onClick={() => onItemClick(item)}
              >
                查看
              </Button>
              {item.url && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="ml-2"
                  onClick={() => window.open(item.url, '_blank')}
                >
                  链接
                </Button>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

// 过敏原表格组件（单表：产品、症状、佐证文献）
const AllergenTable = ({ 
  data, 
  onItemClick, 
  entityTypeMap,
  onShowAllLiterature,
}: { 
  data: Array<{ id: string; name: string; entityType: string; symptoms?: Array<{ name: string }>; literature?: Array<{ title: string; url?: string }> }>;
  onItemClick: (item: any) => void;
  entityTypeMap: Record<string, string>;
  onShowAllLiterature: (literature: Array<{ title: string; url?: string }>) => void;
}) => {
  // 收集所有症状和文献
  const allSymptoms = new Set<string>();
  const allLiterature = new Set<{ title: string; url?: string }>();
  
  (data || []).forEach(product => {
    // 收集症状
    (product.symptoms || []).forEach(symptom => {
      if (symptom.name) {
        allSymptoms.add(symptom.name);
      }
    });
    
    // 收集文献（现在直接从product.literature获取）
    (product.literature || []).forEach(lit => {
      if (lit.title) {
        allLiterature.add({ title: lit.title, url: lit.url });
      }
    });
  });

  const symptomsArray = Array.from(allSymptoms);
  const literatureArray = Array.from(allLiterature);


  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-30">产品</TableHead>
          <TableHead className="w-64">症状</TableHead>
          <TableHead className="w-80">佐证文献</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow>
          <TableCell className="font-medium w-30">
            <div className="text-sm">
              {data.length === 0 ? (
                <span className="text-muted-foreground">—</span>
              ) : (
                data.map(product => product.name).join('、')
              )}
            </div>
          </TableCell>
          <TableCell className="w-64">
            <div className="text-sm">
              {symptomsArray.length === 0 ? (
                <span className="text-muted-foreground">—</span>
              ) : (
                <span className="relative group">
                  {symptomsArray.length <= 3 ? (
                    symptomsArray.join('、')
                  ) : (
                    <>
                      {symptomsArray.slice(0, 3).join('、')}等{symptomsArray.length}种症状
                      <div className="absolute bottom-full left-0 mb-2 p-3 bg-white border rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 w-80">
                        <div className="text-xs text-gray-600">
                          <div className="font-medium mb-2">所有症状:</div>
                          <div className="text-sm">
                            {symptomsArray.join('、')}
                          </div>
                        </div>
                      </div>
                    </>
                  )}
                </span>
              )}
            </div>
          </TableCell>
          <TableCell className="w-80">
            <div className="text-sm">
              {literatureArray.length === 0 ? (
                <span className="text-muted-foreground">—</span>
              ) : literatureArray.length <= 2 ? (
                <div className="space-y-1">
                  {literatureArray.map((lit, li) => (
                    <a 
                      key={`lit-${li}`}
                      href={lit.url || '#'} 
                      target="_blank" 
                      rel="noreferrer" 
                      className="text-blue-600 hover:text-blue-800 underline break-words block"
                    >
                      {lit.title}
                    </a>
                  ))}
                </div>
              ) : (
                <span 
                  className="text-blue-600 cursor-pointer hover:text-blue-800 underline"
                  onClick={() => onShowAllLiterature(literatureArray)}
                >
                  共{literatureArray.length}篇佐证文献
                </span>
              )}
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  );
};

// 新闻/召回表格组件
const NewsRecallTable = ({ 
  data, 
  onItemClick, 
  entityTypeMap 
}: { 
  data: Array<{ 
    id: string; 
    title?: string; 
    name?: string; 
    entityType: string; 
    url?: string; 
    link?: string; 
    source?: string; 
    publishedAt?: string;
    publishTime?: string;
    time?: string;
    publishDate?: string;
  }>;
  onItemClick: (item: any) => void;
  entityTypeMap: Record<string, string>;
}) => {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-16">序号</TableHead>
          <TableHead className="w-2/5">标题</TableHead>
          <TableHead>来源</TableHead>
          <TableHead>发布日期</TableHead>
          <TableHead>链接</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item, index) => (
          <TableRow key={`${item.entityType}-${item.id}-${index}`}>
            <TableCell className="font-medium">{index + 1}</TableCell>
            <TableCell className="font-medium">{item.title || item.name}</TableCell>
            <TableCell>
              <span className={`px-2 py-1 rounded-full text-xs ${
                item.entityType === 'News' 
                  ? 'bg-blue-100 text-blue-800' 
                  : 'bg-red-100 text-red-800'
              }`}>
                {item.source || (item.entityType === 'News' ? '新闻' : '召回公告')}
              </span>
            </TableCell>
            <TableCell>
              {formatDateYMD(
                item.publishedAt || (item as any).publishDate || (item as any).publishTime || (item as any).time
              ) || '-'}
            </TableCell>
            <TableCell>
              {item.url ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => window.open(item.url, '_blank')}
                >
                  查看
                </Button>
              ) : (
                <span className="text-muted-foreground">-</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

// 通用表格组件（用于其他类型的节点）
const GeneralTable = ({ 
  data, 
  onItemClick, 
  entityTypeMap 
}: { 
  data: Array<{ id: string; name?: string; title?: string; entityType: string; url?: string; source?: string; publishDate?: string }>;
  onItemClick: (item: any) => void;
  entityTypeMap: Record<string, string>;
}) => {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>序号</TableHead>
          <TableHead className="w-1/4">名称</TableHead>
          <TableHead>类型</TableHead>
          <TableHead>操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item, index) => (
          <TableRow key={item.id || `${item.entityType}-${index}`}>
            <TableCell className="font-medium">{index + 1}</TableCell>
            <TableCell className="font-medium">{item.name || item.title}</TableCell>
            <TableCell>{entityTypeMap[item.entityType] || item.entityType}</TableCell>
            <TableCell>
              <Button
                size="sm"
                variant="outline"
                onClick={() => onItemClick(item)}
              >
                查看
              </Button>
              {item.url && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="ml-2"
                  onClick={() => window.open(item.url, '_blank')}
                >
                  链接
                </Button>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

// 文献专用表格组件
const LiteratureTable = ({
  data
}: {
  data: Array<{ id?: string; name?: string; title?: string; url?: string; entityType?: string }>
}) => {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>序号</TableHead>
          <TableHead>文献名</TableHead>
          <TableHead>链接</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item, index) => (
          <TableRow key={item.id || index}>
            <TableCell className="font-medium">{index + 1}</TableCell>
            <TableCell>{item.name || item.title || '文献'}</TableCell>
            <TableCell>
              {item.url ? (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary hover:underline"
                >
                  打开
                </a>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

const entityTypeMap: Record<string, string> = {
  Product: '产品',
  Allergen: '过敏原',
  Symptom: '症状',
  Recall: '召回',
  News: '新闻',
  Literature: '文献',
  Category: '类别',
  Menu: '菜单',
  Group: '分组',
  More: '更多',
  '化学物质': '化学物质',
  '公司': '公司',
  '疾病': '疾病',
};

interface KnowledgeGraphProps {
  externalGraphData?: GraphData | null;
  onGraphDataChange?: (data: GraphData | null) => void;
  hideProductSelector?: boolean;
  showEdgesByDefault?: boolean; // 是否默认显示产品-过敏原边（危害识别模式使用）
}

export default function KnowledgeGraph({ externalGraphData, onGraphDataChange, hideProductSelector, showEdgesByDefault = false }: KnowledgeGraphProps = {}) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState<GraphData[]>([]);
  const [results, setResults] = useState<{ id: string; name: string; label: string }[]>([]);
  const [initialGraph, setInitialGraph] = useState<GraphData | null>(null);
  const [moreModal, setMoreModal] = useState<{
    open: boolean;
    title: string;
    data: Array<{ id: string; name?: string; title?: string; entityType: string; url?: string; source?: string; publishDate?: string; authors?: string; pmid?: string; evidenceStrength?: number; reliability?: number; relevance?: number; riskIntensity?: number; concentrationWeight?: number }>;
    loading: boolean;
    tableType?: 'product' | 'allergen' | 'general' | 'literature' | 'news_recall' | 'hazard_literature';
    allergenId?: string;
  }>({
    open: false,
    title: '',
    data: [],
    loading: false,
    tableType: 'general',
    allergenId: undefined,
  });
  
  // 文献弹窗状态
  const [literatureModal, setLiteratureModal] = useState<{
    open: boolean;
    title: string;
    data: Array<{ title: string; url?: string }>;
  }>({
    open: false,
    title: '',
    data: [],
  });
  
  // 表格历史栈，用于返回上一级表格
  const [tableHistory, setTableHistory] = useState<Array<{
    title: string;
    data: Array<{ id: string; name?: string; title?: string; entityType: string; url?: string; source?: string; publishDate?: string; authors?: string; pmid?: string; evidenceStrength?: number; reliability?: number; relevance?: number; riskIntensity?: number; concentrationWeight?: number }>;
    tableType?: 'product' | 'allergen' | 'general' | 'literature' | 'news_recall' | 'hazard_literature';
    allergenId?: string;
  }>>([]);
  const autoDrawRef = useRef<boolean>(false);
  const { header, categories, products, setCategory, setProduct, fetchAll } = useProductStore();

  // 确保类别/产品数据可用
  useEffect(() => {
    if ((categories?.length || 0) === 0 || (products?.length || 0) === 0) {
      (async () => {
        try { await fetchAll(); } catch {}
      })();
    }
  }, [categories?.length, products?.length, fetchAll]);

  // 监听外部图谱数据变化
  useEffect(() => {
    if (externalGraphData) {
      setGraphData(externalGraphData);
      setInitialGraph(externalGraphData);
      setHistory([]);
      setLoading(false);
    }
  }, [externalGraphData]);

  useEffect(() => {
    // 如果有外部图谱数据，不执行默认加载
    if (externalGraphData) return;
    
    // 等待类别数据加载完成
    if (!categories || categories.length === 0) {
      setLoading(true);
      return;
    }
    
    // 初始化：根据当前类别ID直接加载菜单视图
    setLoading(true);
    const categoryId = header?.category?.id || (categories.length > 0 ? categories[0].id : '1');
    
    (async () => {
      if (categoryId) {
        try {
          console.log(`[Knowledge Graph] Loading data for category: ${categoryId}`);
          // 加载：Category 节点 + 直连 Type 节点 + 过敏原菜单展开
          const menuData = await http.get<any, GraphData>(`/knowledge/category/${categoryId}/menus`);
          const typesData = await http.get<any, GraphData>(`/knowledge/category/${categoryId}/types`);
          const allergensData = await http.get<any, GraphData>(`/knowledge/category/${categoryId}/allergens`);

          const expandedData = mergeGraph(mergeGraph(menuData, typesData), allergensData);
          console.log(`[Knowledge Graph] Loaded data:`, expandedData);

          setGraphData(expandedData);
          setInitialGraph(expandedData);
          setHistory([]);
          
          // 同时搜索相关实体供左侧列表展示
          const categoryName = header?.category?.name || (categories.find(c => c.id === categoryId)?.name) || '';
          if (categoryName) {
            const list = await http.get<any, { id: string; name: string; label: string }[]>(`/knowledge/search`, { 
              params: { q: categoryName, label: '类别', synonyms: true, mode: 'auto', limit: 10 } 
            });
            setResults(list || []);
          }
        } catch (e) {
          console.error('Failed to load category menus:', e);
          setGraphData({ nodes: [], edges: [] });
          setInitialGraph({ nodes: [], edges: [] });
          setResults([]);
        }
      } else {
        // 无类别时清空
        setGraphData({ nodes: [], edges: [] });
        setInitialGraph({ nodes: [], edges: [] });
        setResults([]);
      }
      
      autoDrawRef.current = false;
      setLoading(false);
    })();
  }, [header?.category?.id, header?.category?.name, externalGraphData, categories]);

  // 首次加载：如果图为空但已有搜索结果，则自动绘制第一个结果的一跳邻居
  useEffect(() => {
    const run = async () => {
      if (autoDrawRef.current) return;
      if (graphData && (graphData.nodes?.length || 0) > 0) return;
      if (!results || results.length === 0) return;
      try {
        const center = results[0];
        const data = await http.get<any, GraphData>(`/knowledge/node/${encodeURIComponent(center.id)}/neighbors`, { params: { name: center.name } });
        setGraphData(data);
        setInitialGraph(data);
        autoDrawRef.current = true;
      } catch {}
    };
    run();
  }, [results, graphData]);

  const hasData = useMemo(() => (graphData?.nodes.length || 0) > 0, [graphData]);

  const mergeGraph = useCallback((base: GraphData, incoming: GraphData): GraphData => {
    const nodeMap = new Map(base.nodes.map(n => [n.id, n] as const));
    for (const n of incoming.nodes) nodeMap.set(n.id, n);
    const edgeKey = (e: any) => `${e.from}|${e.to}|${e.type}`;
    const edgeMap = new Map(base.edges.map(e => [edgeKey(e), e] as const));
    for (const e of incoming.edges) edgeMap.set(edgeKey(e), e);
    return { nodes: Array.from(nodeMap.values()), edges: Array.from(edgeMap.values()) };
  }, []);

  // 打开新表格，可选择是否保存当前表格到历史栈
  const openNewTable = useCallback((
    title: string, 
    data: any[], 
    saveHistory: boolean = false, 
    tableType: 'product' | 'allergen' | 'general' | 'literature' | 'news_recall' | 'hazard_literature' = 'general',
    allergenId?: string
  ) => {
    if (saveHistory && moreModal.open && moreModal.data.length > 0) {
      setTableHistory(prev => [...prev, {
        title: moreModal.title,
        data: moreModal.data,
        tableType: moreModal.tableType,
        allergenId: moreModal.allergenId
      }]);
    }
    setMoreModal({
      open: true,
      loading: false,
      title,
      data,
      tableType,
      allergenId
    });
  }, [moreModal]);

  // 显示所有文献弹窗
  const showAllLiterature = useCallback((literature: Array<{ title: string; url?: string }>) => {
    setLiteratureModal({
      open: true,
      title: '所有佐证文献',
      data: literature
    });
  }, []);

  // 返回上一级表格
  const goBackTable = useCallback(() => {
    if (tableHistory.length > 0) {
      const lastTable = tableHistory[tableHistory.length - 1];
      setMoreModal({
        open: true,
        loading: false,
        title: lastTable.title,
        data: lastTable.data,
        tableType: lastTable.tableType || 'general',
        allergenId: lastTable.allergenId
      });
      setTableHistory(prev => prev.slice(0, -1));
    }
  }, [tableHistory]);

  const handleNodeClick = useCallback(async (nodeId: string) => {
    if (!graphData) return;
    
    // 查找被点击的节点
    const clickedNode = graphData.nodes.find(n => n.id === nodeId);
    if (!clickedNode) return;
    
    // 处理末端节点：新闻、召回、文献 - 直接打开链接
    if (clickedNode.entityType === 'News' || clickedNode.entityType === 'Recall' || clickedNode.entityType === 'Literature') {
      if (clickedNode.url) {
        window.open(clickedNode.url, '_blank');
        return;
      }
    }
    
    try {
      setHistory(prev => [...prev, graphData]);
      let newData: GraphData;
      
      // 根据节点类型决定调用哪个API
      if (clickedNode.isMenu) {
        // 菜单节点：展开产品或过敏原列表
        if (nodeId.includes(':products')) {
          const categoryId = nodeId.split(':')[2];
          const productsData = await http.get<any, GraphData>(`/knowledge/category/${categoryId}/products`);
          // 合并当前图与产品数据
          newData = mergeGraph(graphData, productsData);
        } else if (nodeId.includes(':allergens')) {
          const categoryId = nodeId.split(':')[2];
          const allergensData = await http.get<any, GraphData>(`/knowledge/category/${categoryId}/allergens`);
          newData = mergeGraph(graphData, allergensData);
        } else {
          // 操作菜单暂时为空
          return;
        }
      } else if (clickedNode.entityType === 'Type') {
        // 类型节点：切换显示/隐藏该类型下的产品
        const typeElementId = nodeId.substring(nodeId.indexOf(':') + 1);
        // 已显示则移除该类型下的产品节点与边；否则先收起其他类型的产品，再加载并合并当前类型
        const typeProductEdges = graphData.edges.filter(e => e.type === 'HAS_PRODUCT');
        const hasProducts = typeProductEdges.some(e => e.from === nodeId);

        // 先移除其他类型下已展开的产品
        const otherTypeProductNodeIds = new Set(
          typeProductEdges
            .filter(e => e.from !== nodeId)
            .map(e => e.to)
        );
        let intermediateNodes = graphData.nodes.filter(n => !otherTypeProductNodeIds.has(n.id));
        let intermediateEdges = graphData.edges.filter(e => !(e.type === 'HAS_PRODUCT' && e.from !== nodeId));

        if (hasProducts) {
          // 当前类型已展开 -> 收起当前类型
          const currentTypeProductNodeIds = new Set(
            intermediateEdges
              .filter(e => e.type === 'HAS_PRODUCT' && e.from === nodeId)
              .map(e => e.to)
          );
          const nodes = intermediateNodes.filter(n => !currentTypeProductNodeIds.has(n.id));
          const edges = intermediateEdges.filter(e => !(e.type === 'HAS_PRODUCT' && e.from === nodeId));
          newData = { nodes, edges };
        } else {
          // 当前类型未展开 -> 加载该类型产品
          const productsData = await http.get<any, GraphData>(`/knowledge/type/${typeElementId}/products`);
          // 合并在“已收起其他类型产品”的中间图上
          newData = mergeGraph({ nodes: intermediateNodes, edges: intermediateEdges }, productsData);
        }
      } else if (clickedNode.entityType === 'Product') {
        // 产品节点：直接弹窗显示所有子节点
        const productId = nodeId.substring(nodeId.indexOf(':') + 1);
        setMoreModal({ open: true, loading: true, title: `产品 "${clickedNode.name}" 的相关信息`, data: [] });

        try {
            const [recalls, news] = await Promise.all([
                http.get<any, any[]>(`/knowledge/product/${productId}/recalls/all`),
                http.get<any, any[]>(`/knowledge/product/${productId}/news/all`)
            ]);
            const combinedData = [...(recalls || []), ...(news || [])];
            openNewTable(`产品 "${clickedNode.name}" 的相关信息`, combinedData, false, 'news_recall');
        } catch (e) {
            // 静默处理错误('Failed to load product children:', e);
            setMoreModal(prev => ({ ...prev, loading: false }));
        }
        return; // 阻止后续图更新
      } else if (clickedNode.entityType === 'Allergen') {
        // 过敏原节点：直接弹窗显示产品-症状-文献单表
        const allergenId = nodeId.substring(nodeId.indexOf(':') + 1);
        setMoreModal({ open: true, loading: true, title: `过敏原 "${clickedNode.name}" 的相关信息`, data: [], tableType: 'allergen' });

        try {
          const list = await http.get<any, Array<{ id: string; name?: string; entityType: string; symptoms?: Array<{ name?: string }>; literature?: Array<{ title?: string; url?: string }> }>>(
            `/knowledge/allergen/${allergenId}/product-symptom-evidence`
          );
          // 规整结构并确保 name 存在
          const normalized = (list || []).map((it) => ({
            id: it.id,
            name: it.name || '',
            entityType: 'Product',
            symptoms: (it.symptoms || []).map(s => ({
              name: s?.name || ''
            })),
            literature: (it.literature || []).map(l => ({ 
              title: l?.title, 
              url: l?.url 
            }))
          }));
          console.log('规整后的数据:', normalized);
          openNewTable(`过敏原 "${clickedNode.name}" 的相关信息`, normalized as any, false, 'allergen', allergenId);
        } catch (e) {
          setMoreModal(prev => ({ ...prev, loading: false }));
        }
        return; // 阻止后续图更新
      } else if (clickedNode.isGroup) {
        // 分组节点：展开叶子节点
        if (nodeId.includes(':recalls')) {
          // 格式: group:product:{elementId}:recalls - 提取elementId部分
          const parts = nodeId.split(':');
          const productId = parts.slice(2, -1).join(':'); // 重新组合elementId，排除最后的recalls
          const recallsData = await http.get<any, GraphData>(`/knowledge/product/${productId}/recalls`);
          newData = mergeGraph(graphData, recallsData);
        } else if (nodeId.includes(':news')) {
          // 格式: group:product:{elementId}:news - 提取elementId部分
          const parts = nodeId.split(':');
          const productId = parts.slice(2, -1).join(':'); // 重新组合elementId，排除最后的news
          const newsData = await http.get<any, GraphData>(`/knowledge/product/${productId}/news`);
          newData = mergeGraph(graphData, newsData);
        } else if (nodeId.includes(':symptoms')) {
          // 格式: group:allergen:{elementId}:symptoms - 提取elementId部分
          const parts = nodeId.split(':');
          const allergenId = parts.slice(2, -1).join(':'); // 重新组合elementId，排除最后的symptoms
          const symptomsData = await http.get<any, GraphData>(`/knowledge/allergen/${allergenId}/symptoms`);
          newData = mergeGraph(graphData, symptomsData);
        } else if (nodeId.includes(':literature')) {
          // 格式: group:allergen:{elementId}:literature - 提取elementId部分
          const parts = nodeId.split(':');
          const allergenId = parts.slice(2, -1).join(':'); // 重新组合elementId，排除最后的literature
          const literatureData = await http.get<any, GraphData>(`/knowledge/allergen/${allergenId}/literature`);
          newData = mergeGraph(graphData, literatureData);
        } else {
          return;
        }
      } else if (clickedNode.isMore) {
        // 更多节点：打开表格Modal
        const target = clickedNode.meta?.target;
        
        setMoreModal(prev => ({ ...prev, open: true, loading: true }));
        
        if (target === 'products') {
          const categoryId = nodeId.split(':')[2];
          setMoreModal(prev => ({ ...prev, title: '该类别的所有产品' }));
          const listData = await http.get<any, { id: string; name: string; entityType: string; url?: string }[]>(
            `/knowledge/category/${categoryId}/products/all`
          );
          setMoreModal(prev => ({
            ...prev,
            data: listData || [],
            loading: false,
            tableType: 'product'
          }));
        } else if (target === 'allergens') {
          const categoryId = nodeId.split(':')[2];
          setMoreModal(prev => ({ ...prev, title: '该类别的所有过敏原' }));
          const listData = await http.get<any, { id: string; name: string; entityType: string; url?: string }[]>(
            `/knowledge/category/${categoryId}/allergens/all`
          );
          setMoreModal(prev => ({
            ...prev,
            data: listData || [],
            loading: false,
            tableType: 'general'
          }));
        } else if (target === 'symptoms') {
          const parts = nodeId.split(':');
          const allergenId = parts.slice(2, -1).join(':'); // 提取allergenId
          setMoreModal(prev => ({ ...prev, title: '该过敏原的所有症状' }));
          const listData = await http.get<any, { id: string; name: string; entityType: string; url?: string }[]>(
            `/knowledge/allergen/${allergenId}/symptoms/all`
          );
          setMoreModal(prev => ({
            ...prev,
            data: listData || [],
            loading: false,
            tableType: 'allergen'
          }));
        } else if (target === 'literature') {
          const parts = nodeId.split(':');
          const allergenId = parts.slice(2, -1).join(':'); // 提取allergenId
          setMoreModal(prev => ({ ...prev, title: '该过敏原的所有文献' }));
          const listData = await http.get<any, { id: string; name: string; entityType: string; url?: string }[]>(
            `/knowledge/allergen/${allergenId}/literature/all`
          );
          setMoreModal(prev => ({
            ...prev,
            data: listData || [],
            loading: false,
            tableType: 'literature'
          }));
        } else if (target === 'recalls') {
          // 格式: more:product:{elementId}:recalls - 提取elementId部分
          const parts = nodeId.split(':');
          const productId = parts.slice(2, -1).join(':'); // 重新组合elementId，排除最后的recalls
          setMoreModal(prev => ({ ...prev, title: '该产品的所有召回信息' }));
          const listData = await http.get<any, { id: string; name: string; entityType: string; url?: string }[]>(
            `/knowledge/product/${productId}/recalls/all`
          );
          setMoreModal(prev => ({
            ...prev,
            data: listData || [],
            loading: false,
            tableType: 'general'
          }));
        } else if (target === 'news') {
          // 格式: more:product:{elementId}:news - 提取elementId部分
          const parts = nodeId.split(':');
          const productId = parts.slice(2, -1).join(':'); // 重新组合elementId，排除最后的news
          setMoreModal(prev => ({ ...prev, title: '该产品的所有新闻' }));
          const listData = await http.get<any, { id: string; name: string; entityType: string; url?: string }[]>(
            `/knowledge/product/${productId}/news/all`
          );
          setMoreModal(prev => ({
            ...prev,
            data: listData || [],
            loading: false,
            tableType: 'general'
          }));
        }
        return;
      } else if (clickedNode.entityType === 'Symptom') {
        // 症状节点：显示佐证该症状的相关文献
        const symptomName = clickedNode.name;
        
        // 检查节点meta中是否已有文献数据（来自危害评估）
        if (clickedNode.meta?.literatures && clickedNode.meta.literatures.length > 0) {
          // 从症状节点的meta中获取symptom_id，然后调用API获取详细评分
          const symptomId = clickedNode.id.replace('symptom_', '');
          setMoreModal({ open: true, loading: true, title: `症状 "${symptomName}" 的佐证文献`, data: [] });
          
          try {
            // 调用新的API获取文献详细评分数据
            const response = await http.get<any, any>(`/hazard-assessment/literature-scores/${symptomId}`);
            console.log('API响应:', response);
            
            // 检查响应结构，API返回格式为 {code: 200, data: [...], message: '...'}
            const literatureScores = response.data || response;
            
            if (literatureScores && literatureScores.length > 0) {
              const literatures = literatureScores.map((lit: any) => ({
                id: lit.id,
                name: lit.title,
                title: lit.title,
                entityType: 'Literature',
                url: lit.link,
                authors: lit.authors,
                source: lit.source,
                publishDate: lit.publish_date,
                pmid: lit.pmid,
                evidenceStrength: lit.evidence_strength,
                // 从API获取的实际评分数据
                reliability: lit.reliability || 0,
                relevance: lit.relevance || 0,
                riskIntensity: lit.risk_intensity || 0,
                concentrationWeight: lit.concentration_weight || 0
              }));
              
              openNewTable(
                `症状 "${symptomName}" 的佐证文献 (${literatures.length}篇)`, 
                literatures, 
                false, 
                'hazard_literature'
              );
            } else {
              // 如果API没有返回数据，使用节点中的基础数据
              const literatures = clickedNode.meta.literatures.map((lit: any) => ({
                id: lit.id,
                name: lit.title,
                title: lit.title,
                entityType: 'Literature',
                url: lit.link,
                authors: lit.authors,
                source: lit.source,
                publishDate: lit.publish_date,
                pmid: lit.pmid,
                evidenceStrength: lit.evidence_strength || 0,
                reliability: 0,
                relevance: 0,
                riskIntensity: 0,
                concentrationWeight: 0
              }));
              
              openNewTable(
                `症状 "${symptomName}" 的佐证文献 (${literatures.length}篇)`, 
                literatures, 
                false, 
                'hazard_literature'
              );
            }
          } catch (e) {
            // API调用失败时，使用节点中的基础数据
            const literatures = clickedNode.meta.literatures.map((lit: any) => ({
              id: lit.id,
              name: lit.title,
              title: lit.title,
              entityType: 'Literature',
              url: lit.link,
              authors: lit.authors,
              source: lit.source,
              publishDate: lit.publish_date,
              pmid: lit.pmid,
              evidenceStrength: lit.evidence_strength || 0,
              reliability: 0,
              relevance: 0,
              riskIntensity: 0,
              concentrationWeight: 0
            }));
            
            openNewTable(
              `症状 "${symptomName}" 的佐证文献 (${literatures.length}篇)`, 
              literatures, 
              false, 
              'hazard_literature'
            );
          }
          return;
        }
        
        // 否则通过API获取文献
        setMoreModal({ open: true, loading: true, title: `症状 "${symptomName}" 的相关文献`, data: [] });
        try {
          const literature = await http.get<any, any[]>(`/knowledge/symptom/${encodeURIComponent(symptomName)}/literature/all`);
          openNewTable(`症状 "${symptomName}" 的相关文献`, literature || [], false, 'literature');
        } catch (e) {
          // 静默处理错误('Failed to load symptom literature from node click:', e);
          setMoreModal(prev => ({ ...prev, loading: false }));
        }
        return;
      } else {
        // 其他节点：使用原有的邻居查询
        const encoded = encodeURIComponent(nodeId);
        newData = await http.get<any, GraphData>(`/knowledge/node/${encoded}/neighbors`);
      }
      
      setGraphData(newData);
    } catch (e) {
      // 静默处理错误('Node click failed:', e);
    }
  }, [graphData, mergeGraph]);


  if (loading) {
    return (
      <div className="h-full w-full flex items-center justify-center">
        <div className="text-muted-foreground">加载中...</div>
      </div>
    );
  }

  return (
    <div className="h-full w-full relative">
      {/* 左上角：头部信息（类别/产品选择），在危害评估/溯源排查模式下隐藏 */}
      {!hideProductSelector && (
        <div className="absolute top-2 left-2 z-10 flex items-center gap-[var(--space-xs)]">
          <Select value={header?.category?.id} onValueChange={(v) => setCategory(v)}>
            <SelectTrigger className="h-8 w-36 text-[length:var(--font-size-md)] px-2">
              <SelectValue placeholder="驱蚊产品" />
            </SelectTrigger>
            <SelectContent>
              {(categories || []).map(c => (
                <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      {!hasData ? (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          暂无图谱数据，请更换搜索关键词或选择其他产品。
        </div>
      ) : (
        <GraphChart data={graphData!} onNodeClick={handleNodeClick} showEdgesByDefault={showEdgesByDefault} />
      )}
      
      {/* More节点的表格Modal */}
      <Dialog open={moreModal.open} onOpenChange={(open) => {
        if (!open) {
          // 关闭弹窗时清空历史栈
          setTableHistory([]);
        }
        setMoreModal(prev => ({ ...prev, open }));
      }}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <DialogTitle className="flex-1">{moreModal.title}</DialogTitle>
            {tableHistory.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={goBackTable}
                className="ml-2"
              >
                返回
              </Button>
            )}
          </DialogHeader>
          <div className="flex-1 overflow-y-auto">
            {moreModal.loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-muted-foreground">加载中...</div>
              </div>
            ) : (
              <>
                {moreModal.tableType === 'product' && (
                  <ProductTable 
                    data={moreModal.data} 
                    onItemClick={async (item) => {
                      try {
                        if (item.entityType === 'Product') {
                          const productId = item.id;
                          setMoreModal({ open: true, loading: true, title: `产品 "${item.name}" 的相关信息`, data: [] });
                          try {
                            const [recalls, news] = await Promise.all([
                              http.get<any, any[]>(`/knowledge/product/${productId}/recalls/all`),
                              http.get<any, any[]>(`/knowledge/product/${productId}/news/all`)
                            ]);
                            const combinedData = [...(recalls || []), ...(news || [])];
                            openNewTable(`产品 "${item.name}" 的相关信息`, combinedData, true, 'news_recall');
                          } catch (e) {
                            // 静默处理错误('Failed to load product children from table action:', e);
                            setMoreModal(prev => ({ ...prev, loading: false }));
                          }
                        } else if (item.entityType === 'News' || item.entityType === 'Recall' || item.entityType === 'Literature') {
                          if ((item as any).url) {
                            window.open((item as any).url, '_blank');
                          }
                        }
                      } catch (e) {
                        // 静默处理错误('Failed to handle product table click:', e);
                      }
                    }}
                    entityTypeMap={entityTypeMap}
                  />
                )}
                {moreModal.tableType === 'allergen' && (
                  <AllergenTable 
                    data={moreModal.data as any} 
                    onItemClick={() => { /* no-op for new single-table */ }}
                    entityTypeMap={entityTypeMap}
                    onShowAllLiterature={showAllLiterature}
                  />
                )}
                {moreModal.tableType === 'general' && (
                  <GeneralTable 
                    data={moreModal.data} 
                    onItemClick={async (item) => {
                      try {
                        if (item.entityType === 'Product') {
                          const productId = item.id;
                          setMoreModal({ open: true, loading: true, title: `产品 "${item.name}" 的相关信息`, data: [] });
                          try {
                            const [recalls, news] = await Promise.all([
                              http.get<any, any[]>(`/knowledge/product/${productId}/recalls/all`),
                              http.get<any, any[]>(`/knowledge/product/${productId}/news/all`)
                            ]);
                            const combinedData = [...(recalls || []), ...(news || [])];
                            openNewTable(`产品 "${item.name}" 的相关信息`, combinedData, true, 'news_recall');
                          } catch (e) {
                            // 静默处理错误('Failed to load product children from table action:', e);
                            setMoreModal(prev => ({ ...prev, loading: false }));
                          }
                        } else if (item.entityType === 'Allergen') {
                          const allergenId = item.id;
                          setMoreModal({ open: true, loading: true, title: `过敏原 "${item.name}" 的相关信息`, data: [] });
                          try {
                            const allergenData = await http.get<any, Array<{ id: string; name?: string; entityType: string; symptoms?: Array<{ name?: string }>; literature?: Array<{ title?: string; url?: string }> }>>(
                              `/knowledge/allergen/${allergenId}/product-symptom-evidence`
                            );
                            // 规整结构并确保 name 存在
                            const normalized = (allergenData || []).map((it) => ({
                              id: it.id,
                              name: it.name || '',
                              entityType: 'Product',
                              symptoms: (it.symptoms || []).map(s => ({
                                name: s?.name || ''
                              })),
                              literature: (it.literature || []).map(l => ({ 
                                title: l?.title, 
                                url: l?.url 
                              }))
                            }));
                            openNewTable(`过敏原 "${item.name}" 的相关信息`, normalized as any, true, 'allergen', item.id);
                          } catch (e) {
                            // 静默处理错误('Failed to load allergen children from table action:', e);
                            setMoreModal(prev => ({ ...prev, loading: false }));
                          }
                        } else if (item.entityType === 'Symptom') {
                          const symptomName = item.name;
                          setMoreModal({ open: true, loading: true, title: `症状 "${symptomName}" 的相关文献`, data: [] });
                          try {
                            const literature = await http.get<any, any[]>(`/knowledge/symptom/${encodeURIComponent(symptomName)}/literature/all`);
                            openNewTable(`症状 "${symptomName}" 的相关文献`, literature || [], true, 'literature');
                          } catch (e) {
                            // 静默处理错误('Failed to load symptom literature:', e);
                            setMoreModal(prev => ({ ...prev, loading: false }));
                          }
                        } else if (item.entityType === 'News' || item.entityType === 'Recall' || item.entityType === 'Literature') {
                          if ((item as any).url) {
                            window.open((item as any).url, '_blank');
                          }
                        }
                      } catch (e) {
                        // 静默处理错误('Failed to handle general table click:', e);
                      }
                    }}
                    entityTypeMap={entityTypeMap}
                  />
                )}
                {moreModal.tableType === 'literature' && (
                  <LiteratureTable
                    data={moreModal.data as any}
                  />
                )}
                {moreModal.tableType === 'news_recall' && (
                  <NewsRecallTable
                    data={moreModal.data}
                    onItemClick={async (item) => {
                      // 新闻/召回项目点击时直接打开链接
                      if (item.url) {
                        window.open(item.url, '_blank');
                      }
                    }}
                    entityTypeMap={entityTypeMap}
                  />
                )}
                {moreModal.tableType === 'hazard_literature' && (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">序号</TableHead>
                        <TableHead className="w-1/3">文献标题</TableHead>
                        <TableHead className="w-20">可靠性</TableHead>
                        <TableHead className="w-20">相关性</TableHead>
                        <TableHead className="w-20">风险强度</TableHead>
                        <TableHead className="w-20">浓度权重</TableHead>
                        <TableHead className="w-20">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {moreModal.data.map((item, index) => (
                        <TableRow key={item.id || index}>
                          <TableCell className="font-medium">{index + 1}</TableCell>
                          <TableCell>
                            <div className="space-y-1">
                              <div className="font-medium text-sm line-clamp-2">{item.title || item.name}</div>
                              {item.authors && (
                                <div className="text-xs text-muted-foreground line-clamp-1">作者: {item.authors}</div>
                              )}
                              {item.pmid && (
                                <div className="text-xs text-muted-foreground">PMID: {item.pmid}</div>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              (item.reliability || 0) >= 8 ? 'bg-green-100 text-green-800' :
                              (item.reliability || 0) >= 5 ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {(item.reliability || 0).toFixed(1)}
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              (item.relevance || 0) >= 8 ? 'bg-green-100 text-green-800' :
                              (item.relevance || 0) >= 5 ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {(item.relevance || 0).toFixed(1)}
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              (item.riskIntensity || 0) >= 8 ? 'bg-red-100 text-red-800' :
                              (item.riskIntensity || 0) >= 5 ? 'bg-orange-100 text-orange-800' :
                              'bg-green-100 text-green-800'
                            }`}>
                              {(item.riskIntensity || 0).toFixed(1)}
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                              {(item.concentrationWeight || 0).toFixed(2)}
                            </span>
                          </TableCell>
                          <TableCell>
                            {item.url ? (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => window.open(item.url, '_blank')}
                              >
                                原文
                              </Button>
                            ) : (
                              <span className="text-muted-foreground text-xs">—</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
      
      {/* 文献弹窗 */}
      <Dialog open={literatureModal.open} onOpenChange={(open) => {
        setLiteratureModal(prev => ({ ...prev, open }));
      }}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>{literatureModal.title}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">序号</TableHead>
                  <TableHead>文献标题</TableHead>
                  <TableHead className="w-24">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {literatureModal.data.map((lit, index) => (
                  <TableRow key={index}>
                    <TableCell className="font-medium">{index + 1}</TableCell>
                    <TableCell className="break-words">{lit.title}</TableCell>
                    <TableCell>
                      {lit.url ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => window.open(lit.url, '_blank')}
                        >
                          打开
                        </Button>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}