"use client";

import { RotateCcw } from "lucide-react";
import { useTranslations } from "next-intl";
import { createPortal } from "react-dom";

interface Props {
  billName: string;
  onRestore: () => void;
  onSkip: () => void;
  restoring?: boolean;
}

export default function RestoreDeletedDialog({ billName, onRestore, onSkip, restoring = false }: Props) {
  const t = useTranslations("RestoreDeletedDialog");
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="restore-deleted-dialog-title"
        onKeyDown={(e) => e.key === "Escape" && !restoring && onSkip()}
        className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:bg-slate-800 dark:border-slate-700"
      >
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
          <RotateCcw size={22} />
        </div>
        <h2
          id="restore-deleted-dialog-title"
          className="mb-1 text-lg font-semibold text-slate-800 dark:text-slate-100"
        >
          {t("title")}
        </h2>
        <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
          {t("description", { name: billName })}
        </p>
        <div className="flex gap-3">
          <button
            onClick={onSkip}
            disabled={restoring}
            autoFocus
            className="flex-1 rounded-xl border border-slate-200 bg-white py-2.5 text-sm font-medium text-slate-700 shadow-sm transition-all hover:border-slate-300 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            {t("skip")}
          </button>
          <button
            onClick={onRestore}
            disabled={restoring}
            className="flex-1 rounded-xl border border-blue-700 bg-blue-700 py-2.5 text-sm font-medium text-white shadow-sm transition-all hover:border-blue-800 hover:bg-blue-800 disabled:opacity-50"
          >
            {restoring ? t("restoring") : t("restore")}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
