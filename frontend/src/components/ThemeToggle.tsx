"use client";

import { useState } from "react";
import { Sun, Moon } from "lucide-react";
import { useTranslations } from "next-intl";

export default function ThemeToggle() {
  const t = useTranslations("ThemeToggle");
  const [dark, setDark] = useState(
    () => typeof window !== "undefined" && document.documentElement.classList.contains("dark"),
  );

  function toggle() {
    const isDark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("theme", isDark ? "dark" : "light");
    setDark(isDark);
  }

  return (
    <button
      onClick={toggle}
      aria-label={t("ariaLabel")}
      suppressHydrationWarning
      className="rounded-lg border border-slate-200 bg-white p-2 text-slate-500 shadow-sm transition-all hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:border-blue-700 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
    >
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
