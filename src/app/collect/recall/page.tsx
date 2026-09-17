"use client";

import RecallCollection from "@/components/collection/recall-collection";
import { useProductStore } from "@/store/useProductStore";

export default function RecallCollectPage() {
  const { categories, products, types } = useProductStore();
  
  return (
    <RecallCollection 
      categories={categories || []}
      products={products || []}
      types={types || []}
    />
  );
}


