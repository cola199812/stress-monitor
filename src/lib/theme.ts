"use client";

export type ThemePalette = {
  "--primary-100": string;
  "--primary-200": string;
  "--primary-300": string;
  "--accent-100": string;
  "--accent-200": string;
  "--text-100": string;
  "--text-200": string;
  "--bg-100": string;
  "--bg-200": string;
  "--bg-300": string;
  // Typography & sizing tokens
  "--font-size-xs"?: string;   // e.g. 12px
  "--font-size-sm"?: string;   // 13-14px
  "--font-size-md"?: string;   // 14-16px
  "--font-size-lg"?: string;   // 18px
  "--font-size-xl"?: string;   // 20-24px
  "--font-weight-normal"?: string; // 400
  "--font-weight-medium"?: string; // 500
  "--font-weight-semibold"?: string; // 600
  "--line-height-tight"?: string; // 1.2
  "--line-height-normal"?: string; // 1.5
  "--radius-sm"?: string; // 0.375rem
  "--radius-md"?: string; // 0.5rem
  "--radius-lg"?: string; // 0.75rem
  "--space-xs"?: string; // 4px
  "--space-sm"?: string; // 8px
  "--space-md"?: string; // 12px
  "--space-lg"?: string; // 16px
};

export type ThemeDefinition = {
  name: string;
  palette: ThemePalette;
};

export const DEFAULT_THEME_NAME = "default";

export const builtinThemes: ThemeDefinition[] = [
  {
    name: DEFAULT_THEME_NAME,
    palette: {
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
      "--font-size-xs": "12px",
      "--font-size-sm": "13px",
      "--font-size-md": "14px",
      "--font-size-lg": "18px",
      "--font-size-xl": "22px",
      "--font-weight-normal": "400",
      "--font-weight-medium": "500",
      "--font-weight-semibold": "600",
      "--line-height-tight": "1.25",
      "--line-height-normal": "1.5",
      "--radius-sm": "0.375rem",
      "--radius-md": "0.5rem",
      "--radius-lg": "0.75rem",
      "--space-xs": "4px",
      "--space-sm": "8px",
      "--space-md": "12px",
      "--space-lg": "16px",
    },
  },
  {
    name: "soft-blue",
    palette: {
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
      "--font-size-xs": "12px",
      "--font-size-sm": "13px",
      "--font-size-md": "14px",
      "--font-size-lg": "18px",
      "--font-size-xl": "22px",
      "--font-weight-normal": "400",
      "--font-weight-medium": "500",
      "--font-weight-semibold": "600",
      "--line-height-tight": "1.25",
      "--line-height-normal": "1.5",
      "--radius-sm": "0.375rem",
      "--radius-md": "0.5rem",
      "--radius-lg": "0.75rem",
      "--space-xs": "4px",
      "--space-sm": "8px",
      "--space-md": "12px",
      "--space-lg": "16px",
    },
  },
];

export const THEME_KEYS: (keyof ThemePalette)[] = [
  "--primary-100",
  "--primary-200",
  "--primary-300",
  "--accent-100",
  "--accent-200",
  "--text-100",
  "--text-200",
  "--bg-100",
  "--bg-200",
  "--bg-300",
  "--font-size-xs",
  "--font-size-sm",
  "--font-size-md",
  "--font-size-lg",
  "--font-size-xl",
  "--font-weight-normal",
  "--font-weight-medium",
  "--font-weight-semibold",
  "--line-height-tight",
  "--line-height-normal",
  "--radius-sm",
  "--radius-md",
  "--radius-lg",
  "--space-xs",
  "--space-sm",
  "--space-md",
  "--space-lg",
];

export function getDefaultPalette(): ThemePalette {
  const base = builtinThemes.find((t) => t.name === DEFAULT_THEME_NAME) || builtinThemes[0];
  return base.palette;
}

export function hexToHslNumbers(hex: string): string {
  const normalized = hex.replace("#", "");
  const bigint = parseInt(normalized.length === 3
    ? normalized.split("").map((c) => c + c).join("")
    : normalized, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;

  const r1 = r / 255;
  const g1 = g / 255;
  const b1 = b / 255;
  const max = Math.max(r1, g1, b1);
  const min = Math.min(r1, g1, b1);
  let h = 0, s = 0, l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r1:
        h = (g1 - b1) / d + (g1 < b1 ? 6 : 0);
        break;
      case g1:
        h = (b1 - r1) / d + 2;
        break;
      default:
        h = (r1 - g1) / d + 4;
    }
    h /= 6;
  }

  const H = Math.round(h * 360);
  const S = Math.round(s * 100);
  const L = Math.round(l * 100);
  return `${H} ${S}% ${L}%`;
}

export function applyTheme(theme: ThemeDefinition) {
  if (typeof window === "undefined") return;
  const root = document.documentElement;
  const p = theme.palette;

  const set = (key: string, value: string) => root.style.setProperty(key, value);
  const hsl = (hex: string) => hexToHslNumbers(hex);

  set("--background", hsl(p["--bg-100"]));
  set("--foreground", hsl(p["--text-100"]));
  set("--card", hsl(p["--bg-100"]));
  set("--card-foreground", hsl(p["--text-100"]));
  set("--popover", hsl(p["--bg-100"]));
  set("--popover-foreground", hsl(p["--text-100"]));
  set("--secondary", hsl(p["--bg-200"]));
  set("--secondary-foreground", hsl(p["--text-100"]));
  set("--muted", hsl(p["--bg-200"]));
  set("--muted-foreground", hsl(p["--text-200"]));
  set("--accent", hsl(p["--accent-100"]));
  set("--accent-foreground", hsl(p["--text-100"]));
  set("--destructive", "0 84% 60%");
  set("--destructive-foreground", "0 0% 98%");
  set("--border", hsl(p["--bg-300"]));
  set("--input", hsl(p["--bg-300"]));
  set("--ring", hsl(p["--accent-200"]));
  set("--primary", hsl(p["--accent-200"]));
  set("--primary-foreground", "0 0% 98%");

  // gradients could reference accent as well
  root.style.setProperty("--grad-from", p["--accent-100"]);
  root.style.setProperty("--grad-mid", p["--accent-200"]);
  root.style.setProperty("--grad-to", p["--primary-300"]);

  // Typography & sizing tokens
  const opt = (k: keyof ThemePalette, v?: string) => {
    const val = (p as any)[k] || v
    if (val) root.style.setProperty(k, String(val))
  }
  opt("--font-size-xs")
  opt("--font-size-sm")
  opt("--font-size-md")
  opt("--font-size-lg")
  opt("--font-size-xl")
  opt("--font-weight-normal")
  opt("--font-weight-medium")
  opt("--font-weight-semibold")
  opt("--line-height-tight")
  opt("--line-height-normal")
  opt("--radius-sm")
  opt("--radius-md")
  opt("--radius-lg")
  opt("--space-xs")
  opt("--space-sm")
  opt("--space-md")
  opt("--space-lg")
}

const CUSTOM_THEMES_KEY = "customThemes";
const SELECTED_THEME_KEY = "selectedTheme";
const SELECTED_THEME_PALETTE_KEY = "selectedThemePalette";

function setCookie(name: string, value: string, maxAgeSeconds = 31536000) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSeconds}`;
}

export function getAllThemes(): ThemeDefinition[] {
  if (typeof window === "undefined") return builtinThemes;
  const raw = window.localStorage.getItem(CUSTOM_THEMES_KEY);
  const list: ThemeDefinition[] = raw ? JSON.parse(raw) : [];
  return [...builtinThemes, ...list];
}

export function getSelectedThemeName(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(SELECTED_THEME_KEY);
}

export function setSelectedThemeName(name: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SELECTED_THEME_KEY, name);
  setCookie(SELECTED_THEME_KEY, name);
}

export function setActiveTheme(theme: ThemeDefinition) {
  if (typeof window === "undefined") return;
  setSelectedThemeName(theme.name);
  window.localStorage.setItem(SELECTED_THEME_PALETTE_KEY, JSON.stringify(theme.palette));
  setCookie(SELECTED_THEME_PALETTE_KEY, JSON.stringify(theme.palette));
  applyTheme(theme);
}

export function addCustomTheme(def: ThemeDefinition) {
  if (typeof window === "undefined") return;
  const raw = window.localStorage.getItem(CUSTOM_THEMES_KEY);
  const list: ThemeDefinition[] = raw ? JSON.parse(raw) : [];
  const filtered = list.filter((t) => t.name !== def.name);
  filtered.push(def);
  window.localStorage.setItem(CUSTOM_THEMES_KEY, JSON.stringify(filtered));
}

export function removeCustomTheme(name: string) {
  if (typeof window === "undefined") return;
  const raw = window.localStorage.getItem(CUSTOM_THEMES_KEY);
  const list: ThemeDefinition[] = raw ? JSON.parse(raw) : [];
  const filtered = list.filter((t) => t.name !== name);
  window.localStorage.setItem(CUSTOM_THEMES_KEY, JSON.stringify(filtered));
  // 如果当前选中就是被删主题，回退到内置默认
  const current = getSelectedThemeName();
  if (current === name) {
    setActiveTheme({ name: DEFAULT_THEME_NAME, palette: getDefaultPalette() });
  }
}

export function ensureAppliedOnLoad() {
  if (typeof window === "undefined") return;
  const selected = getSelectedThemeName();
  const all = getAllThemes();
  const target = selected ? all.find((t) => t.name === selected) : all[0];
  if (target) applyTheme(target);
}

export function parsePaletteText(text: string, fallback?: ThemePalette): ThemePalette {
  const base = { ...(fallback || getDefaultPalette()) } as ThemePalette;
  const lines = text.split(/\n|;/).map((s) => s.trim()).filter(Boolean);
  for (const line of lines) {
    const m = line.match(/^--[A-Za-z0-9-]+\s*:\s*#[0-9A-Fa-f]{3,8}$/);
    if (!m) continue;
    const [prop, value] = line.split(":");
    const key = prop.trim() as keyof ThemePalette;
    const val = value.trim();
    if ((THEME_KEYS as string[]).includes(key) && /^#[0-9A-Fa-f]{3,8}$/.test(val)) {
      (base as any)[key] = val;
    }
  }
  return base;
}


