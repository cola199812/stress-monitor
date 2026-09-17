"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  {
    href: "/info-management/entity-management",
    label: "实体管理",
    description: "管理产品，化学应急源，症状"
  },
  {
    href: "/info-management/ralationship-management", 
    label: "关系管理",
    description: "管理三种实体之间的关系"
  },
  {
    href: "/info-management/data-management",
    label: "数据管理", 
    description: "管理文献等多源数据和内容"
  },
  {
    href: "/info-management/score-management",
    label: "评分管理", 
    description: "管理评分模型以及具体细节"
  }
];

export default function InfoManagementNav() {
  const pathname = usePathname();

  return (
    <div className="flex space-x-1 bg-muted p-1 rounded-lg mb-6">
      {navItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={cn(
            "flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors text-center",
            pathname === item.href
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
          title={item.description}
        >
          {item.label}
        </Link>
      ))}
    </div>
  );
}
