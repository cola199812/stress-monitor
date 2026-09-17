"use client";

import ToxicityCollection from "@/components/collection/toxicity-collection";
import { useProductStore } from "@/store/useProductStore";

export default function ToxicityCollectPage() {
  const { categories, products, types } = useProductStore();
  
  return (
    <ToxicityCollection 
      categories={categories || []}
      products={products || []}
      types={types || []}
    />
  );
}
