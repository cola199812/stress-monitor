"use client";

import { usePathname } from "next/navigation";

export default function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div
      key={pathname}
      className="h-full animate-in fade-in-0 slide-in-from-bottom-1 duration-300 ease-out"
    >
      {children}
    </div>
  );
}


