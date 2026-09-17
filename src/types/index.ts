export interface StatsData {
  months: string[];
  literature: number[];
  news: number[];
  recall: number[];
}

export interface Item {
  id: string;
  title: string;
  source: string;
  publishedAt: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  tags: string[];
  url: string;
}

export interface ItemsResponse {
  total: number;
  items: Item[];
}

export interface GraphNode {
  id: string;
  label: string;
  name: string;
  entityType?: string;
  isMenu?: boolean;
  isGroup?: boolean;
  isMore?: boolean;
  url?: string;
  meta?: any;
  x?: number;
  y?: number;
  fixed?: boolean;
}

export interface GraphEdge {
  from: string;
  to: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface QAResponse {
  answer: string;
  refs: { title: string; url: string }[];
}

export interface CommentItem {
  id: string;
  user: string;
  content: string;
  score: number;
  publishedAt: string;
  ip: string;
}

export interface CommentResponse {
  total: number;
  items: CommentItem[];
}

export interface ProductItem {
  id: string;
  uid: string;
  name: string;
  price: number;
  sales: number;
}

export interface ProductResponse {
  total: number;
  items: ProductItem[];
}

export interface WordCloudItem {
  name: string;
  value: number;
}

export interface WordCloudResponse {
  items: WordCloudItem[];
  // 后端生成图片（base64:dataURL）。若存在，前端可优先展示图片
  image?: string;
}

// Dashboard extra APIs
export interface DailyTrendResponse {
  dates: string[];
  count: number[];
}

export interface SourceStatsItem {
  name: string;
  count: number;
}
export interface SourceStatsResponse {
  items: SourceStatsItem[];
}

export interface SentimentSummaryResponse {
  positive: number;
  neutral: number;
  negative: number;
}

// Category aggregated counts
export interface CategoryCountItem {
  categoryId?: number;
  categoryName?: string;
  name?: string;
  products: number;
  allergens: number;
  symptoms: number;
}
export interface CategoryCountsResponse {
  items: CategoryCountItem[];
}

// Header/产品选择相关类型
export type Category = { id: string; name: string };
export type Type = { id: string; categoryId: string; name: string };
export type Product = { id: string; categoryId: string; name: string; keywords?: string[] };
export type Allergen = { id: string; name: string; description?: string };

export type HeaderState = {
  category?: Category | null;
  type?: Type | null;
  productClassName?: string;
  product?: Product | null;
  allergen?: Allergen | null;
  featureName: string;
  keywordInput: string;
};

// 产品-症状热搜榜
export interface ProductSymptomTopItem {
  rank: number;
  id: number;
  product_id: number;
  product_name: string;
  symptom_id: number;
  symptom_name: string;
  confidence: number;
  evidence_count: number;
  updated_at: string | null;
}

export interface ProductSymptomTopResponse {
  code: number;
  message: string;
  data: {
    items: ProductSymptomTopItem[];
    time_range: {
      from: string;
      to: string;
      days: number;
    };
  };
}