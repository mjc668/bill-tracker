"use client";

import { useEffect, useRef, useState } from "react";
import { CalendarDays } from "lucide-react";
import { useTranslations } from "next-intl";

interface Props {
  value: string; // "" or "1"–"31"
  onChange: (day: string) => void;
}

const DAYS = Array.from({ length: 31 }, (_, i) => i + 1);

export default function DayPicker({ value, onChange }: Props) {
  const t = useTranslations("DayPicker");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const selected = value ? parseInt(value, 10) : null;

  function handleSelect(day: number) {
    onChange(String(day));
    setOpen(false);
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition-colors hover:border-blue-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 dark:bg-slate-800 dark:border-slate-600 dark:text-slate-100 dark:hover:border-blue-600 dark:focus:border-blue-600 dark:focus:ring-blue-900/40"
        aria-haspopup="true"
        aria-expanded={open}
      >
        <CalendarDays size={15} className="shrink-0 text-slate-400 dark:text-slate-500" />
        <span className={selected ? "text-slate-800 dark:text-slate-100" : "text-slate-400 dark:text-slate-500"}>
          {selected ? t("selectedDay", { day: selected }) : t("placeholder")}
        </span>
      </button>

      {selected != null && selected >= 29 && (
        <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
          {t("shortMonthWarning")}
        </p>
      )}

      {open && (
        <div className="absolute z-20 mt-1.5 w-64 rounded-xl border border-slate-200 bg-white p-3 shadow-lg dark:border-slate-600 dark:bg-slate-800">
          <p className="mb-2 text-center text-xs font-medium text-slate-400 dark:text-slate-500">
            {t("heading")}
          </p>
          <div className="grid grid-cols-7 gap-1">
            {DAYS.map((day) => (
              <button
                key={day}
                type="button"
                onClick={() => handleSelect(day)}
                className={`flex h-8 w-8 items-center justify-center rounded-lg text-sm transition-colors ${
                  day === selected
                    ? "bg-blue-700 font-semibold text-white"
                    : "text-slate-700 hover:bg-blue-50 hover:text-blue-800 dark:text-slate-300 dark:hover:bg-blue-900/30 dark:hover:text-blue-300"
                }`}
              >
                {day}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
