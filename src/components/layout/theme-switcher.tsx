"use client";

import { useEffect, useState } from "react";
import { addCustomTheme, applyTheme, ensureAppliedOnLoad, getAllThemes, getSelectedThemeName, parsePaletteText, setSelectedThemeName, ThemeDefinition, removeCustomTheme, setActiveTheme } from "@/lib/theme";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Palette, Check } from "lucide-react";

export function ThemeSwitcher() {
  const [themes, setThemes] = useState<ThemeDefinition[]>(() => getAllThemes());
  const [current, setCurrent] = useState<string>(() => getSelectedThemeName() || getAllThemes()[0]?.name || "");
  const [open, setOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [name, setName] = useState("");
  const [bulk, setBulk] = useState("");
  const [editOpen, setEditOpen] = useState<string | null>(null);

  useEffect(() => {
    ensureAppliedOnLoad();
    const list = getAllThemes();
    setThemes(list);
    const selected = getSelectedThemeName() || list[0]?.name || current;
    if (selected && selected !== current) setCurrent(selected);
  }, []);

  const handleChange = (name: string) => {
    const theme = themes.find((t) => t.name === name);
    if (!theme) return;
    setCurrent(name);
    setSelectedThemeName(name);
    applyTheme(theme);
  };

  const handleCreate = async () => {
    if (!name) return;
    const palette = parsePaletteText(bulk);
    const def: ThemeDefinition = {
      name,
      palette,
    };
    // 1) 预留后端：POST /themes 失败回退本地
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "/api"}/themes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(def),
      });
    } catch {}
    addCustomTheme(def);
    const list = getAllThemes();
    setThemes(list);
    setActiveTheme(def);
    setCurrent(def.name);
    setOpen(false);
    setName("");
    setBulk("");
  };

  const handleDelete = async (themeName: string) => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "/api"}/themes/${encodeURIComponent(themeName)}`, { method: "DELETE" });
    } catch {}
    removeCustomTheme(themeName);
    setThemes(getAllThemes());
    const sel = getSelectedThemeName() || getAllThemes()[0]?.name || "";
    if (sel) handleChange(sel);
  };

  return (
    <div className="flex items-center gap-2 relative z-[60] pointer-events-auto">
      <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="切换主题" title="切换主题">
            <Palette className="h-4 w-4 text-primary" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-52">
          {themes.map((t) => (
            <DropdownMenuItem
              key={t.name}
              className="flex items-center justify-between"
            >
              <span onClick={() => handleChange(t.name)} className="flex-1">
                {t.name}
              </span>
              <div className="flex items-center gap-2">
                {current === t.name ? <Check className="h-4 w-4 text-primary" /> : null}
                {t.name !== "default" && (
                  <Button size="sm" variant="ghost" onClick={(e)=>{ e.stopPropagation(); handleDelete(t.name); }}>删除</Button>
                )}
              </div>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setOpen(true)}>+ 新增主题</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新增主题</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3">
            <Input placeholder="主题名称" value={name} onChange={(e) => setName(e.target.value)} />
            <textarea
              placeholder={`按行粘贴，如:\n--primary-100:#d4eaf7;\n--primary-200:#b6ccd8;\n...`}
              className="min-h-[180px] rounded-md border bg-background p-2 text-sm"
              value={bulk}
              onChange={(e) => setBulk(e.target.value)}
            />
            <div className="flex justify-end">
              <Button onClick={handleCreate}>保存主题</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}


