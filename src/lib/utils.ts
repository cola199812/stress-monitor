import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// 统一将各种日期/时间值转为 YYYY-MM-DD 字符串
// 支持：Date 对象、可被 new Date() 解析的字符串、时间戳数字、'YYYY-MM-DD HH:mm:ss' 等
export function formatDateYMD(value: unknown): string | null {
  if (value == null) return null;
  try {
    // 若已是字符串且像 'YYYY-MM-DD'，直接截取前10位
    if (typeof value === 'string') {
      const v = value.trim();
      if (!v) return null;
      // ISO 或常见格式，取前10位即可
      if (/^\d{4}[-/.]?\d{2}[-/.]?\d{2}/.test(v)) {
        return v.replace(/[/.]/g, '-').slice(0, 10);
      }
      // 其他可被 Date 解析的字符串
      const d = new Date(v);
      if (!isNaN(d.getTime())) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
      }
      return null;
    }
    if (value instanceof Date) {
      const y = value.getFullYear();
      const m = String(value.getMonth() + 1).padStart(2, '0');
      const day = String(value.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    }
    if (typeof value === 'number') {
      // 支持秒或毫秒级时间戳
      const ts = value > 1e12 ? value : value * 1000;
      const d = new Date(ts);
      if (!isNaN(d.getTime())) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
      }
    }
  } catch {}
  return null;
}
