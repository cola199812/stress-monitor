export type NavPage = {
  id: string;
  label: string;
  href: string;
};

export type NavModule = {
  id: 'collect' | 'qa';
  label: string;
  basePath: string; // 路径前缀，用于匹配当前模块
  defaultRoute: string;
  children: NavPage[];
};

export const navSchema: NavModule[] = [
  {
    id: 'qa',
    label: '知识问答',
    basePath: '/qa',
    defaultRoute: '/qa',
    children: [],
  },
  {
    id: 'collect',
    label: '数据采集',
    basePath: '/collect',
    defaultRoute: '/collect/literature',
    children: [
      { id: 'literature', label: '文献采集', href: '/collect/literature' },
      { id: 'medical', label: '产品使用数据', href: '/collect/medical' },
      { id: 'toxicity', label: '毒性数据采集', href: '/collect/toxicity' },
      { id: 'news', label: '新闻采集', href: '/collect/news' },
      { id: 'recall', label: '召回采集', href: '/collect/recall' },
    ],
  },
];

export function matchModule(pathname: string): NavModule | null {
  for (const m of navSchema) {
    if (pathname === m.basePath || pathname.startsWith(m.basePath + '/')) return m;
  }
  return null;
}


