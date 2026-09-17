import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { HeaderBar } from "@/components/layout/HeaderBar";
import { Toaster } from "@/components/ui/sonner";
import { cookies } from "next/headers";
import PageTransition from "@/components/layout/page-transition";
import { RouteFeatureSync } from "@/components/layout/RouteFeatureSync";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "化学应激源高关联伤害信息监测系统",
  description: "一个用于监测化学应激源相关伤害信息的系统",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // SSR: 从 Cookie 恢复主题并注入 CSS 变量，避免水合不一致
  const cookieStore = await cookies();
  const selected = cookieStore.get("selectedTheme")?.value || "default";
  const paletteCookie = cookieStore.get("selectedThemePalette")?.value;

  const builtin: Record<string, Record<string, string>> = {
    default: {
      "--primary-100": "#e4e4e7",
      "--primary-200": "#a1a1aa",
      "--primary-300": "#3f3f46",
      "--accent-100": "#93c5fd",
      "--accent-200": "#2563eb",
      "--text-100": "#111827",
      "--text-200": "#374151",
      "--bg-100": "#ffffff",
      "--bg-200": "#f4f4f5",
      "--bg-300": "#e4e4e7",
    },
    "soft-blue": {
      "--primary-100": "#d4eaf7",
      "--primary-200": "#b6ccd8",
      "--primary-300": "#3b3c3d",
      "--accent-100": "#71c4ef",
      "--accent-200": "#00668c",
      "--text-100": "#1d1c1c",
      "--text-200": "#313d44",
      "--bg-100": "#fffefb",
      "--bg-200": "#f5f4f1",
      "--bg-300": "#cccbc8",
    },
  };

  const parseJSON = (s?: string) => {
    if (!s) return null;
    try { return JSON.parse(decodeURIComponent(s)); } catch { return null; }
  };

  const p = parseJSON(paletteCookie) || builtin[selected] || builtin.default;

  const hexToHsl = (hex: string) => {
    const n = hex.replace('#','');
    const b = parseInt(n.length===3 ? n.split('').map(c=>c+c).join('') : n,16);
    const r=(b>>16)&255,g=(b>>8)&255,bl=b&255;const r1=r/255,g1=g/255,b1=bl/255;const max=Math.max(r1,g1,b1),min=Math.min(r1,g1,b1);let h=0,s=0,l=(max+min)/2; if(max!==min){const d=max-min;s=l>0.5?d/(2-max-min):d/(max+min);switch(max){case r1:h=(g1-b1)/d+(g1<b1?6:0);break;case g1:h=(b1-r1)/d+2;break;default:h=(r1-g1)/d+4;}h/=6;} return `${Math.round(h*360)} ${Math.round(s*100)}% ${Math.round(l*100)}%`; };

  const css = `:root{--background:${hexToHsl(p['--bg-100'])};--foreground:${hexToHsl(p['--text-100'])};--card:${hexToHsl(p['--bg-100'])};--card-foreground:${hexToHsl(p['--text-100'])};--popover:${hexToHsl(p['--bg-100'])};--popover-foreground:${hexToHsl(p['--text-100'])};--secondary:${hexToHsl(p['--bg-200'])};--secondary-foreground:${hexToHsl(p['--text-100'])};--muted:${hexToHsl(p['--bg-200'])};--muted-foreground:${hexToHsl(p['--text-200'])};--accent:${hexToHsl(p['--accent-100'])};--accent-foreground:${hexToHsl(p['--text-100'])};--destructive:0 84% 60%;--destructive-foreground:0 0% 98%;--border:${hexToHsl(p['--bg-300'])};--input:${hexToHsl(p['--bg-300'])};--ring:${hexToHsl(p['--accent-200'])};--primary:${hexToHsl(p['--accent-200'])};--primary-foreground:0 0% 98%;}` + `:root{--grad-from:${p['--accent-100']};--grad-mid:${p['--accent-200']};--grad-to:${p['--primary-300']};}` + `:root{--font-size-xs:${p['--font-size-xs']||'12px'};--font-size-sm:${p['--font-size-sm']||'13px'};--font-size-md:${p['--font-size-md']||'14px'};--font-size-lg:${p['--font-size-lg']||'18px'};--font-size-xl:${p['--font-size-xl']||'22px'};--font-weight-normal:${p['--font-weight-normal']||'400'};--font-weight-medium:${p['--font-weight-medium']||'500'};--font-weight-semibold:${p['--font-weight-semibold']||'600'};--line-height-tight:${p['--line-height-tight']||'1.25'};--line-height-normal:${p['--line-height-normal']||'1.5'};--radius-sm:${p['--radius-sm']||'0.375rem'};--radius-md:${p['--radius-md']||'0.5rem'};--radius-lg:${p['--radius-lg']||'0.75rem'};--space-xs:${p['--space-xs']||'4px'};--space-sm:${p['--space-sm']||'8px'};--space-md:${p['--space-md']||'12px'};--space-lg:${p['--space-lg']||'16px'};}`;
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {/* SSR 注入主题变量，彻底避免水合不一致 */}
        <style dangerouslySetInnerHTML={{__html: css}} />
        {/* 装饰性背景元素 */}
        <div className="fixed top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-accent/5 rounded-full blur-3xl animate-pulse delay-1000"></div>
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-muted/5 rounded-full blur-2xl animate-pulse delay-500"></div>
        </div>
        <HeaderBar />
        <RouteFeatureSync />
        <main className="pt-[64px] min-h-[calc(100vh-64px)]">
          <PageTransition>{children}</PageTransition>
        </main>
        <Toaster position="top-center" />
      </body>
    </html>
  );
}