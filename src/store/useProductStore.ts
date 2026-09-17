import { create } from 'zustand';
import type { Category, Product, Allergen, HeaderState, Type } from '@/types';
import http from '@/lib/http';

type Store = {
  categories: Category[];
  products: Product[];
  types: Type[];
  header: HeaderState;

  // 便捷派生字段（供组件直接使用）
  product: string | null; // 当前选中产品名称
  allergen: string | null; // 当前选中过敏原名称
  type: string | null; // 当前选中类型名称
  keywords: string[]; // 当前产品/过敏原关键词

  // actions
  setCategory: (id: string) => void;
  // 兼容传入 id 或 name
  setType: (id: string) => void;
  setProduct: (idOrName: string) => void;
  setAllergen: (allergen: Allergen | null) => void;
  setFeatureName: (name: string) => void;
  setKeywordInput: (v: string) => void;
  setKeywords: (keywords: string[]) => void;
  // 挂载后从本地恢复
  rehydrateFromLocal: () => void;
  fetchAll: () => Promise<void>;

  createCategory: (name: string) => Promise<void>;
  updateCategory: (id: string, name: string) => Promise<void>;
  deleteCategory: (id: string) => Promise<void>;

  createType: (name: string) => Promise<void>;
  updateType: (id: string, name: string) => Promise<void>;
  deleteType: (id: string) => Promise<void>;

  createProduct: (payload: { categoryId: string; name: string; keywords?: string[] }) => Promise<void>;
  updateProduct: (id: string, patch: Partial<Product>) => Promise<void>;
  deleteProduct: (id: string) => Promise<void>;
};

const LOCAL_KEY = 'headerState_v1';
const LAST_COLLECTION_TYPE_KEY = 'lastCollectionType';

const loadLocal = (): Partial<Store> => {
  try {
    const s = localStorage.getItem(LOCAL_KEY);
    if (!s) return {};
    const parsed = JSON.parse(s);
    return parsed || {};
  } catch {
    return {};
  }
};

const persist = (header: HeaderState) => {
  try {
    localStorage.setItem(LOCAL_KEY, JSON.stringify({ header }));
  } catch {}
};

const getLastCollectionType = (): string | null => {
  try {
    return localStorage.getItem(LAST_COLLECTION_TYPE_KEY);
  } catch {
    return null;
  }
};

const setLastCollectionType = (type: string) => {
  try {
    localStorage.setItem(LAST_COLLECTION_TYPE_KEY, type);
  } catch {}
};

// 判断采集源类型分组
const getCollectionGroup = (featureName: string): 'research' | 'product' => {
  // 文献采集、毒性数据库属于研究类
  if (featureName.includes('文献') || featureName.includes('毒性')) {
    return 'research';
  }
  // 新闻采集、召回采集属于产品类
  if (featureName.includes('新闻') || featureName.includes('召回')) {
    return 'product';
  }
  return 'product'; // 默认为产品类
};

export const useProductStore = create<Store>((set, get) => {
  const initHeader: HeaderState = {
    featureName: '数据看板',
    keywordInput: '',
  } as HeaderState;

  // 移除所有内置本地数据，首次渲染后从后端加载
  const builtinProducts: Product[] = [];
  const builtinTypes: Type[] = [];
  const builtinCategories: Category[] = [];
  let selectedCategory: Category | null = null;
  let selectedType: Type | null = null;
  let selectedProduct: Product | null = null;
  const defaultKeyword = '';
  const headerFull: HeaderState = {
    ...initHeader,
    category: selectedCategory,
    type: selectedType,
    product: selectedProduct,
    productClassName: undefined,
    keywordInput: defaultKeyword,
  };

  const store: Store = {
    categories: builtinCategories,
    types: builtinTypes,
    products: builtinProducts,
    header: headerFull,
    product: headerFull.product?.name || null,
    type: headerFull.type?.name || null,
    allergen: headerFull.allergen?.name || null,
    keywords: [],

    setCategory: (id) => {
      const cat = get().categories.find(c => c.id === id) || null;
      const header = { ...get().header, category: cat, productClassName: cat?.name, allergen: null };
      set({ header, product: header.product?.name || null, allergen: null, keywords: [] });
      persist(header);
    },
    setType: (id) => {
      const type = get().types.find(t => t.id === id) || null;
      const header = { ...get().header, type, productClassName: type?.name, allergen: null };
      set({ header, product: header.product?.name || null, allergen: null, keywords: [] });
      persist(header);
    },
    setProduct: (idOrName) => {
      const st = get();
      const product = st.products.find(p => p.id === idOrName || p.name === idOrName) || null;
      const category = product ? st.categories.find(c => c.id === product.categoryId) || null : st.header.category || null;
      // 不自动填充输入框，保持用户原有输入
      const header: HeaderState = { ...st.header, product, category, productClassName: category?.name, allergen: null };
      set({ header, product: header.product?.name || null, allergen: null, keywords: [] });
      persist(header);
    },
    setAllergen: (allergen) => {
      const st = get();
      // 选择过敏原时：同步类别、清空产品，不自动填充输入框
      const category = allergen ? (st.categories.find(c => c.id === allergen.categoryId) || null) : st.header.category || null;
      const header: HeaderState = { ...st.header, allergen, product: null, category, productClassName: category?.name };
      set({ header, product: null, allergen: allergen?.name || null, keywords: [] });
      persist(header);
    },
    setFeatureName: (name) => {
      const currentState = get();
      const currentGroup = getCollectionGroup(currentState.header.featureName);
      const newGroup = getCollectionGroup(name);
      
      // 如果是不同组别之间的切换，需要重置状态
      const shouldReset = currentGroup !== newGroup;
      
      let header: HeaderState;
      let newProduct: string | null;
      let newAllergen: string | null; 
      let newKeywords: string[];
      
      if (shouldReset) {
        // 重置状态：清除产品和过敏原选择，关键词输入框清空
        header = { 
          ...currentState.header, 
          featureName: name, 
          product: null, 
          allergen: null,
          category: null,
          productClassName: undefined,
          keywordInput: ''  // 清空输入框
        };
        newProduct = null;
        newAllergen = null;
        newKeywords = [];
        
        console.log('跨组切换，重置状态:', {
          from: currentState.header.featureName,
          to: name,
          fromGroup: currentGroup,
          toGroup: newGroup
        });
      } else {
        // 同组内切换：文献采集时也清空输入框
        const shouldClearInput = name.includes('文献') || name.includes('毒性');
        header = { 
          ...currentState.header, 
          featureName: name,
          keywordInput: shouldClearInput ? '' : currentState.header.keywordInput  // 文献/毒性采集时清空输入框
        };
        newProduct = currentState.product;
        newAllergen = currentState.allergen;
        newKeywords = [];  // 清空 keywords
        
        console.log('同组内切换:', {
          from: currentState.header.featureName,
          to: name,
          group: currentGroup,
          shouldClearInput,
          product: newProduct,
          allergen: newAllergen
        });
      }
      
      set({ header, product: newProduct, allergen: newAllergen, keywords: newKeywords });
      persist(header);
      setLastCollectionType(name);
    },
    setKeywordInput: (v) => {
      const header = { ...get().header, keywordInput: v };
      set({ header });
      persist(header);
    },
    setKeywords: (newKeywords) => {
      const st = get();
      const header: HeaderState = { ...st.header, keywordInput: (newKeywords || []).filter(k => !!k && String(k).trim()).join('、') };
      set({ header, keywords: newKeywords });
      persist(header);
    },
    rehydrateFromLocal: undefined as unknown as never,
    async fetchAll() {
      // 加载类别（Product1）
      const cats: any = await http.get('/categories');
      const categories: Category[] = (cats?.items || []) as Category[];
      // 加载类型（Product2）
      const typeResp: any = await http.get('/types');
      const types: Type[] = (typeResp?.items || []) as Type[];
      // 加载产品（Product3）
      const prods: any = await http.get('/products');
      const products: Product[] = (prods?.items || []).map((p: any) => ({ id: p.id, name: p.name, categoryId: p.categoryId, keywords: p.keywords || [] }));

      // 若当前选中产品在新列表中不存在，则清空选择；不自动选择默认项
      const st = get();
      const selectedProduct = st.header.product ? (products.find(p => p.id === st.header.product!.id) || null) : null;
      // 注意：Product3.categoryId 指向的是 Type(Product2).id
      const selectedType = selectedProduct
        ? (types.find(t => t.id === selectedProduct.categoryId) || null)
        : (st.header.type ? (types.find(t => t.id === st.header.type!.id) || null) : null);
      // Type.categoryId 指向 Category(Product1).id
      const selectedCategory = selectedType
        ? (categories.find(c => c.id === selectedType.categoryId) || null)
        : (st.header.category ? (categories.find(c => c.id === st.header.category!.id) || null) : null);

      const header: HeaderState = {
        ...st.header,
        product: selectedProduct,
        type: selectedType as any,
        category: selectedCategory,
        productClassName: selectedCategory?.name,
        // 不自动填充 keywordInput，保持用户输入
      };

      set({ categories, types, products, header, product: header.product?.name || null, type: header.type?.name || null, allergen: header.allergen?.name || null, keywords: [] });
    },
    

    // CRUD（此处先本地实现，后续可替换为 API）
    async createCategory(name) {
      const res = await http.post('/categories', { name });
      await (get() as any).fetchAll();
    },
    async updateCategory(id, name) {
      await http.patch(`/categories/${id}`, { name });
      await (get() as any).fetchAll();
    },
    async deleteCategory(id) {
      await http.delete(`/categories/${id}`);
      await (get() as any).fetchAll();
    },
    
    async createType(name) {
      await http.post('/types', { name });
      await (get() as any).fetchAll();
    },
    async updateType(id, name) {
      await http.patch(`/types/${id}`, { name });
      await (get() as any).fetchAll();
    },
    async deleteType(id) {
      await http.delete(`/types/${id}`);
      await (get() as any).fetchAll();
    },

    async createProduct(payload) {
      await http.post('/products', payload);
      await (get() as any).fetchAll();
    },
    async updateProduct(id, patch) {
      await http.patch(`/products/${id}`, patch);
      await (get() as any).fetchAll();
    },
    async deleteProduct(id) {
      await http.delete(`/products/${id}`);
      await (get() as any).fetchAll();
    },
  };

  // 将 rehydrateFromLocal 作为闭包中定义的函数挂到 store 上
  (store as unknown as { rehydrateFromLocal: () => void }).rehydrateFromLocal = () => {
    if (typeof window === 'undefined') return;
    const saved = loadLocal();
    if (!saved || !saved.header) return;
    const st = get();
    const savedHeader = saved.header as HeaderState;
    // 如果本地保存的产品名称存在于当前产品列表，则对齐引用；否则沿用保存的对象
    const matched = savedHeader.product
      ? st.products.find(p => p.id === savedHeader.product!.id || p.name === savedHeader.product!.name) || null
      : null;
    const category = matched ? st.categories.find(c => c.id === matched.categoryId) || null : savedHeader.category || null;
    // 保持 localStorage 中保存的 keywordInput，如果没有则为空字符串（不自动填充）
    const keywordInput = savedHeader.keywordInput || '';
    const header: HeaderState = { ...st.header, ...savedHeader, product: matched ?? savedHeader.product ?? null, category, productClassName: category?.name, keywordInput };
    set({ header, product: header.product?.name || null, allergen: header.allergen?.name || null, keywords: [] });
  };

  return store;
});