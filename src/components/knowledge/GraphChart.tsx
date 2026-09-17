"use client";

import React, { useEffect, useMemo, useRef, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { GraphData } from '@/types';
import http from '@/lib/http';

type Props = {
  data: GraphData;
  onNodeClick?: (nodeId: string) => void;
  showEdgesByDefault?: boolean; // 是否默认显示产品-过敏原边（危害识别模式使用）
};

// 基于main分支的优化配色方案，更好地区分实体类型
const nodeColorMap: Record<string, string> = {
  // 核心实体类型（使用main分支的配色）
  产品: '#5B8FF9',      // 蓝色
  公司: '#5AD8A6',      // 绿色
  化学物质: '#5D7092',   // 灰紫色
  症状: '#F6BD16',      // 黄色
  疾病: '#E8684A',      // 红色
  过敏原: '#6DC8EC',     // 青色
  
  // test分支特有的节点类型（保持兼容性）
  Category: '#5B8FF9',   // 类别：蓝色
  Menu: '#5AD8A6',       // 菜单：绿色  
  Group: '#9C27B0',      // 分组：紫色
  More: '#FF9800',       // 更多：橙色
  Type: '#5B8FF9',       // 类型：蓝色
  Product: '#5B8FF9',    // 产品：蓝色
  Allergen: '#6DC8EC',   // 过敏原：青色
  Symptom: '#F6BD16',    // 症状：黄色
  Recall: '#E8684A',     // 召回：红色
  News: '#5AD8A6',       // 新闻：绿色
  Literature: '#5D7092', // 文献：灰紫色
  AdverseReaction: '#6590F9', // 不良反应：深灰色
};

// 统一所有节点为圆形
const getNodeSymbol = (): string => {
  return 'circle'; // 所有节点都用圆形
};

export default function GraphChart({ data, onNodeClick, showEdgesByDefault = false }: Props) {
  const chartRef = useRef<ReactECharts>(null);
  const [extraEdges, setExtraEdges] = useState<Array<{ from: string; to: string; type: string }>>([]);
  const highlightedPAEdgeIdxRef = useRef<number[]>([]);

  const categories = useMemo(() => {
    const set = new Set<string>();
    data.nodes.forEach(n => {
      const categoryName = n.entityType || n.label;
      set.add(categoryName);
    });
    return Array.from(set).map(name => ({ name }));
  }, [data]);

  // 合并边数组，供 option 与事件索引保持一致
  const allEdges = useMemo(() => {
    return [ ...(data.edges || []), ...(extraEdges || []) ];
  }, [data.edges, extraEdges]);

  // 为"产品-过敏原"关系建立 节点->边索引 映射，仅用于联合悬停
  const paEdgeIndexByNodeId = useMemo(() => {
    const nodeById = new Map<string, any>();
    for (const n of data.nodes) nodeById.set(n.id, n);
    const map = new Map<string, number[]>();
    let paEdgeCount = 0;
    
    allEdges.forEach((e, idx) => {
      const s = nodeById.get(e.from);
      const t = nodeById.get(e.to);
      const isPA = (
        (s?.entityType === 'Product' && t?.entityType === 'Allergen') ||
        (s?.entityType === 'Allergen' && t?.entityType === 'Product') ||
        e.type === '包含过敏原'
      );
      
      if (isPA) {
        paEdgeCount++;
        
        if (!map.has(e.from)) map.set(e.from, []);
        if (!map.has(e.to)) map.set(e.to, []);
        map.get(e.from)!.push(idx);
        map.get(e.to)!.push(idx);
      }
    });

    return map;
  }, [allEdges, data.nodes]);

  const option = useMemo(() => {
    // 建立节点索引，便于判断边的两端类型
    const nodeById = new Map<string, any>();
    for (const n of data.nodes) nodeById.set(n.id, n);
    return {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(50, 50, 50, 0.9)',
        borderColor: '#777',
        borderWidth: 1,
        textStyle: {
          color: '#fff',
          fontSize: 12
        },
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            const entityType = params.data.entityType || params.data.label;
            return `<strong>${params.data.name}</strong><br/>类型: ${entityType}`;
          }
          if (params.dataType === 'edge') {
            return `<strong>${params.data.sourceName}</strong> → <strong>${params.data.targetName}</strong><br/>关系: ${params.data.type}`;
          }
          return '';
        },
      },
      // legend: [{ data: categories.map(c => c.name) }],
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          focusNodeAdjacency: true,
          emphasis: { focus: 'adjacency' },
          blur: { lineStyle: { opacity: 0.12 } },
          animation: true,         // 启用动画，对力导向布局很重要
          animationDuration: 1000, // 动画持续时间
          animationEasing: 'cubicOut', // 动画缓动函数
          progressive: 300,        // 渐进式渲染优化大图性能
          force: ({ 
            repulsion: 1000,       // 增加排斥力，让节点分散更开
            edgeLength: [50, 200], // 边长度范围，让连接更灵活
            gravity: 0.1,          // 稍微增加重力
            friction: 0.6,         // 添加摩擦力，让动画更稳定
            // 产品↔过敏原边对布局不产生作用
            edgeWeight: (edge: any) => {
              const s = nodeById.get(edge.source);
              const t = nodeById.get(edge.target);
              const isPA = (
                (s?.entityType === 'Product' && t?.entityType === 'Allergen') ||
                (s?.entityType === 'Allergen' && t?.entityType === 'Product') ||
                edge.type === '包含过敏原'
              );
              return isPA ? 0 : 1;
            }
          } as any),
          label: {
            show: true,
            position: 'right',
            formatter: (p: any) => {
              // 对于多行文本，不进行截断，让ECharts自己处理换行
              return p.data.name;
            },
            fontSize: 14,
            width: 140, // 设置标签宽度，允许换行
            overflow: 'break', // 允许文字换行
          },
          categories,
          data: data.nodes.map(n => {
            const categoryName = n.entityType || n.label;
            const color = nodeColorMap[categoryName] || nodeColorMap[n.label] || '#999999';

      // 根据节点类型生成多行标签
      let nodeName = n.name;
      if (n.entityType === 'Product' && n.meta) {
        const newsCount = n.meta.newsCount || 0;
        const recallsCount = n.meta.recallsCount || 0;
        // 始终显示统计信息，包括0计数
        nodeName = `${n.name}\n新闻${newsCount}条，召回${recallsCount}条`;
      } else if (n.entityType === 'Allergen' && n.meta) {
        const symptomsCount = n.meta.symptomsCount || 0;
        // const literatureCount = n.meta.literatureCount || 0;
        const productCount = n.meta.productCount || 0;
        // 始终显示统计信息，包括0计数
        nodeName = `${n.name}\n症状${symptomsCount}个, 产品${productCount}个`;
      } else if (n.entityType === 'Type' && n.meta) {
        // 类型节点：可显示其下产品数量（如后端提供）
        const productCount = n.meta.productCount || n.meta.productsCount || 0;
        nodeName = productCount ? `${n.name}\n产品${productCount}个` : n.name;
      }

            const nodeData: any = {
              id: n.id,
              name: nodeName, // 使用格式化后的名称
              label: n.label,
              entityType: n.entityType, // 添加entityType属性
              isMenu: n.isMenu, // 添加isMenu属性  
              isGroup: n.isGroup, // 添加isGroup属性
              isMore: n.isMore, // 添加isMore属性
              category: categories.findIndex(c => c.name === categoryName),
              itemStyle: { 
                color: color,
                borderColor: '#fff',
                borderWidth: 1
              },
              emphasis: {
                itemStyle: {
                  color: color,
                  borderColor: '#333',
                  borderWidth: 2,
                  shadowBlur: 10,
                  shadowColor: 'rgba(0, 0, 0, 0.3)'
                },
                label: {
                  fontSize: 16,
                  fontWeight: 'bold'
                }
              },
              symbol: getNodeSymbol(),
              symbolSize: n.entityType === 'Category' 
                ? 30 
                : (n.entityType === 'Type' 
                  ? 26 
                  : (n.isMenu || n.isGroup 
                    ? 25 
                    : (n.isMore 
                      ? 22 
                      : 20))),
            };
            
            // 处理节点位置：给所有有初始位置的节点设置位置，但只固定明确标记的节点
            if (n.x !== undefined && n.y !== undefined) {
              nodeData.x = n.x;
              nodeData.y = n.y;
              // 只有明确设置fixed=true的节点才固定
              if (n.fixed === true) {
                nodeData.fixed = true;
              }
            }
            
            return nodeData;
          }),
          edges: allEdges.map(e => {
            const sourceNode = nodeById.get(e.from);
            const targetNode = nodeById.get(e.to);
            const isProductAllergenEdge = (
              (sourceNode?.entityType === 'Product' && targetNode?.entityType === 'Allergen') ||
              (sourceNode?.entityType === 'Allergen' && targetNode?.entityType === 'Product') ||
              e.type === '包含过敏原'
            );
            return {
              source: e.from,
              target: e.to,
              type: e.type,
              sourceName: sourceNode?.name,
              targetName: targetNode?.name,
              // 产品-过敏原边不参与力的计算
              ignoreForceLayout: isProductAllergenEdge,
              lineStyle: { 
                curveness: 0,
                width: 2,
                // 产品↔过敏原边：根据模式决定是否默认显示
                opacity: isProductAllergenEdge ? (showEdgesByDefault ? 0.6 : 0) : 0.8,
                color: isProductAllergenEdge ? '#E8684A' : '#666',
              },
              blur: {
                lineStyle: {
                  opacity: isProductAllergenEdge ? (showEdgesByDefault ? 0.2 : 0) : 0.12
                }
              },

              label: { 
                show: false,         // 默认不显示标签
                fontSize: 10,
                color: '#666',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                padding: [2, 4],
                borderRadius: 2
              },
              emphasis: {
                lineStyle: isProductAllergenEdge ? {
                  width: 4,
                  opacity: 0.9,
                  color: '#E8684A',
                  shadowBlur: 8,
                  shadowColor: 'rgba(0, 0, 0, 0.3)'
                } : {
                  width: 3,
                  opacity: 1,
                  color: '#333'
                },
                label: isProductAllergenEdge ? { 
                  show: true,
                  formatter: e.type, 
                  fontSize: 12,
                  fontWeight: 'bold',
                  color: '#1a1a1a',
                  backgroundColor: 'rgba(255, 255, 255, 0.9)',
                  borderColor: '#333',
                  borderWidth: 1,
                  padding: [3, 6]
                } : {
                  show: true,
                  formatter: e.type,
                  fontSize: 11,
                  fontWeight: 'bold',
                  color: '#333'
                }
              },
            } as any;
          }),
        },
      ],
    } as echarts.EChartsOption;
  }, [data, categories, extraEdges]);

  useEffect(() => {
    const inst = chartRef.current?.getEchartsInstance();
    if (!inst) return;
    const handler = (params: any) => {
      if (params.dataType === 'node') onNodeClick?.(params.data.id);
    };
    inst.on('click', handler);
    // 悬停仅加粗（交给 echarts 内置 focus: 'adjacency' 完成），不再触发后端请求
    return () => {
      inst.off('click', handler);
    };
  }, [onNodeClick]);

  // 仅对"产品-过敏原"关系做联合悬停：悬停节点时，手动高亮与其相关的该类边
  useEffect(() => {
    const inst = chartRef.current?.getEchartsInstance();
    if (!inst) return;

    const onMouseOver = (p: any) => {
      if (p.dataType !== 'node') return;
      
      // 只对真实的产品和过敏原节点生效，排除菜单、类别、分组等特殊节点
      const nodeData = p.data;
      
      // 使用entityType或label来判断节点类型
      const nodeType = nodeData.entityType || nodeData.label;
      const isRealNode = (nodeType === 'Product' || nodeType === 'Allergen') && 
                        !nodeData.isMenu && !nodeData.isGroup && !nodeData.isMore && 
                        nodeType !== 'Category';
      
      if (!isRealNode) return;
      
      // 先取消上一次的产品-过敏原边高亮，避免残留造成错亮
      if (highlightedPAEdgeIdxRef.current.length) {
        highlightedPAEdgeIdxRef.current.forEach((edgeIdx) => {
          inst.dispatchAction({ 
            type: 'downplay', 
            seriesIndex: 0, 
            dataIndex: edgeIdx 
          });
        });
        highlightedPAEdgeIdxRef.current = [];
      }

      const nodeId: string = p.data.id;
      const edgeIndices = paEdgeIndexByNodeId.get(nodeId) || [];
      if (!edgeIndices.length) return;
      
      highlightedPAEdgeIdxRef.current = edgeIndices.slice();
      
      // 使用更简单的方法：直接修改option并重新渲染
      const option = inst.getOption() as any;
      const series = option.series[0];
      const edges = series.edges;

      // 高亮产品-过敏原红色边
      edgeIndices.forEach((edgeIdx) => {
        if (edges[edgeIdx]) {
          if (!edges[edgeIdx]._originalOpacity) {
            edges[edgeIdx]._originalOpacity = edges[edgeIdx].lineStyle.opacity;
          }
          edges[edgeIdx].lineStyle.opacity = 0.95;
          edges[edgeIdx].lineStyle.width = 4;
          edges[edgeIdx].lineStyle.color = '#E8684A';
          edges[edgeIdx].lineStyle.shadowBlur = 8;
          edges[edgeIdx].lineStyle.shadowColor = 'rgba(0, 0, 0, 0.3)';
        }
      });
      
      // 静默更新，不触发重新布局
      inst.setOption(option, { silent: true });
    };

    const onMouseOut = (p: any) => {
      // 只在鼠标真正离开节点时才恢复
      if (p.dataType !== 'node' || highlightedPAEdgeIdxRef.current.length === 0) return;
      
      // 恢复边的原始样式
      const option = inst.getOption() as any;
      const series = option.series[0];
      const edges = series.edges;
      
      highlightedPAEdgeIdxRef.current.forEach((edgeIdx) => {
        if (edges[edgeIdx] && edges[edgeIdx]._originalOpacity !== undefined) {
          edges[edgeIdx].lineStyle.opacity = edges[edgeIdx]._originalOpacity;
          edges[edgeIdx].lineStyle.width = 2;
          edges[edgeIdx].lineStyle.color = '#E8684A';
          edges[edgeIdx].lineStyle.shadowBlur = 0;
          edges[edgeIdx].lineStyle.shadowColor = undefined;
          delete edges[edgeIdx]._originalOpacity;
        }
      });
      
      // 静默更新，不触发重新布局
      inst.setOption(option, { silent: true });
      
      highlightedPAEdgeIdxRef.current = [];
    };

    inst.on('mouseover', onMouseOver);
    inst.on('mouseout', onMouseOut);

    return () => {
      inst.off('mouseover', onMouseOver);
      inst.off('mouseout', onMouseOut);
    };
  }, [paEdgeIndexByNodeId]);

  // 首次/数据变更后：一次性补充产品↔过敏原边
  useEffect(() => {
    const productIds = data.nodes.filter(n => n.entityType === 'Product').map(n => n.id.substring(n.id.indexOf(':') + 1));
    const allergenIds = data.nodes.filter(n => n.entityType === 'Allergen').map(n => n.id.substring(n.id.indexOf(':') + 1));
    const productNames = data.nodes.filter(n => n.entityType === 'Product').map(n => n.name);
    const allergenNames = data.nodes.filter(n => n.entityType === 'Allergen').map(n => n.name);
    if (!productIds.length || !allergenIds.length) {
      setExtraEdges([]);
      return;
    }
    (async () => {
      try {
        const res = await http.post<any, Array<{from:string;to:string;type:string}>>('/knowledge/edges/product-allergen', { productIds, allergenIds, productNames, allergenNames });
        const productSet = new Set(productIds);
        const allergenSet = new Set(allergenIds);
        const map: Record<string, { from: string; to: string; type: string }> = {};
        for (const e of (res || [])) {
          const from = productSet.has(e.from) ? `product:${e.from}` : (allergenSet.has(e.from) ? `allergen:${e.from}` : e.from);
          const to = productSet.has(e.to) ? `product:${e.to}` : (allergenSet.has(e.to) ? `allergen:${e.to}` : e.to);
          const type = e.type || '包含过敏原';
          map[`${from}|${to}|${type}`] = { from, to, type };
        }
        setExtraEdges(Object.values(map));
      } catch {
        setExtraEdges([]);
      }
    })();
  }, [data.nodes]);

  return (
    <ReactECharts ref={chartRef} option={option} style={{ height: '100%', width: '100%' }} />
  );
}


