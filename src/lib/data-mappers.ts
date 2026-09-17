import { StatsData } from "@/types";

export type TrendPoint = { name: string; 文献: number; 新闻: number; 召回: number };

export function mapStatsToTrend(stats: any): TrendPoint[] {
  if (!stats || !Array.isArray(stats)) return [];
  // 新的API直接返回趋势数据，直接使用
  return stats.map(item => ({
    name: item.name,
    文献: item.文献 || 0,
    新闻: item.新闻 || 0,
    召回: item.召回 || 0,
  }));
}

// 用于“月度趋势对比”图：将后端的 文献/新闻/召回 映射为 产品/过敏原/症状 三个维度
export type ComparePoint = { name: string; 产品: number; 过敏原: number; 症状: number };
export function mapStatsToCompare(stats: StatsData | null): ComparePoint[] {
  if (!stats) return [];
  const all = stats.months.map((m, i) => ({
    name: m,
    产品: stats.literature[i] ?? 0,
    过敏原: stats.news[i] ?? 0,
    症状: (stats as any).recall?.[i] ?? 0,
  }));
  return all.slice(-6);
}


