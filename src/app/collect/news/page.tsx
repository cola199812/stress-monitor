"use client";

import NewsCollection from "@/components/collection/news-collection";
import { useProductStore } from "@/store/useProductStore";

export default function NewsCollectPage() {
  const { categories, products, types } = useProductStore();
  
  return (
    <NewsCollection 
      categories={categories || []}
      products={products || []}
      types={types || []}
    />
  );
}