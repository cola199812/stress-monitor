"use client";

import { useRouter, usePathname } from "next/navigation";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface CollectionMenuItem {
  id: string;
  label: string;
  path: string;
}

const menuItems: CollectionMenuItem[] = [
  {
    id: "literature",
    label: "文献采集",
    path: "/collect/literature",
  },
  {
    id: "news",
    label: "新闻采集",
    path: "/collect/news",
  },
  {
    id: "recall",
    label: "召回采集",
    path: "/collect/recall",
  },
  {
    id: "toxicity",
    label: "毒性数据采集",
    path: "/collect/toxicity",
  },
  {
    id: "medical",
    label: "儿童行为征导入",
    path: "/collect/medical",
  },
];

export default function CollectionSidebar() {
  const router = useRouter();
  const pathname = usePathname();

  // 根据当前路径找到对应的菜单项
  const currentItem = menuItems.find(item => pathname === item.path);
  const currentValue = currentItem?.id || "literature";

  const handleChange = (value: string) => {
    const item = menuItems.find(i => i.id === value);
    if (item) {
      router.push(item.path);
    }
  };

  return (
    <Select value={currentValue} onValueChange={handleChange}>
      <SelectTrigger className="w-[150px]">
        <SelectValue placeholder="选择采集类型" />
      </SelectTrigger>
      <SelectContent>
        {menuItems.map((item) => (
          <SelectItem key={item.id} value={item.id}>
            {item.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
