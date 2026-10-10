"use client";

import { useRef, useState } from "react";
import { createPortal } from "react-dom";
import { HardDriveUpload, Loader2 } from "lucide-react";
import { useTranslations, useLocale } from "next-intl";
import { getExportSummary, restoreFromBackup } from "@/lib/export-api";

type State = "idle" | "confirming" | "restoring" | "error";

type Counts = { bills: number; payments: number };

export default function RestoreButton({ label }: { label?: string } = {}) {
  const t = useTranslations("RestoreButton");
  const locale = useLocale();
  const [state, setState] = useState<State>("idle");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [backupCounts, setBackupCounts] = useState<Counts | null>(null);
  const [backupExportedAt, setBackupExportedAt] = useState<string | null>(null);
  const [currentCounts, setCurrentCounts] = useState<Counts | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const exportDateLabel = (() => {
    if (!backupExportedAt) return t("exportDateUnknown");
    const d = new Date(backupExportedAt);
    return isNaN(d.getTime())
      ? t("exportDateUnknown")
      : new Intl.DateTimeFormat(locale, {
          year: "numeric",
          month: "short",
          day: "numeric",
        }).format(d);
  })();

  const isStale =
    currentCounts !== null &&
    backupCounts !== null &&
    (backupCounts.bills < currentCounts.bills ||
      backupCounts.payments < currentCounts.payments);

  function handleButtonClick() {
    fileInputRef.current?.click();
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    if (file.size > 10 * 1024 * 1024) {
      setErrorMsg(t("fileTooLarge"));
      setState("error");
      return;
    }

    let parsed: { bill_templates: unknown; payment_instances: unknown; exported_at?: unknown };
    try {
      parsed = JSON.parse(await file.text());
    } catch {
      setErrorMsg(t("invalidFile"));
      setState("error");
      return;
    }
    if (!Array.isArray(parsed.bill_templates) || !Array.isArray(parsed.payment_instances)) {
      setErrorMsg(t("invalidFile"));
      setState("error");
      return;
    }

    setSelectedFile(file);
    setBackupCounts({
      bills: parsed.bill_templates.length,
      payments: parsed.payment_instances.length,
    });
    setBackupExportedAt(
      typeof parsed.exported_at === "string" ? parsed.exported_at : null
    );
    try {
      const summary = await getExportSummary();
      setCurrentCounts({ bills: summary.bill_count, payments: summary.payment_count });
    } catch {
      setCurrentCounts(null);
    }
    setState("confirming");
  }

  function handleCancel() {
    setState("idle");
    setSelectedFile(null);
    setErrorMsg("");
    setBackupCounts(null);
    setBackupExportedAt(null);
    setCurrentCounts(null);
  }

  async function handleConfirm() {
    if (!selectedFile) return;
    setState("restoring");
    try {
      await restoreFromBackup(selectedFile);
      setState("idle");
      setSelectedFile(null);
      setBackupCounts(null);
      setBackupExportedAt(null);
      setCurrentCounts(null);
      // Reload page so dashboard reflects restored data
      window.location.reload();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : t("error"));
      setState("error");
    }
  }

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        className="hidden"
        onChange={handleFileChange}
      />

      <button
        onClick={handleButtonClick}
        aria-label={t("ariaLabel")}
        className={
          label
            ? "flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 shadow-sm transition-all hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:border-blue-700 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
            : "rounded-lg border border-slate-200 bg-white p-2 text-slate-500 shadow-sm transition-all hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:border-blue-700 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
        }
      >
        <HardDriveUpload size={18} />
        {label && <span>{label}</span>}
      </button>

      {(state === "confirming" || state === "restoring" || state === "error") &&
        createPortal(
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 backdrop-blur-sm"
            onClick={handleCancel}
          >
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="restore-dialog-title"
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:bg-slate-800 dark:border-slate-700"
            >
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400">
                <HardDriveUpload size={22} />
              </div>
              <h2
                id="restore-dialog-title"
                className="mb-1 text-lg font-semibold text-slate-800 dark:text-slate-100"
              >
                {t("dialogTitle")}
              </h2>
              {backupCounts && (
                <div className="mb-4 space-y-1 rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-900/40">
                  <div className="flex justify-between text-slate-600 dark:text-slate-300">
                    <span>{t("currentLabel")}</span>
                    <span>
                      {currentCounts
                        ? t("countsSummary", {
                            bills: currentCounts.bills,
                            payments: currentCounts.payments,
                          })
                        : t("countsUnavailable")}
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-600 dark:text-slate-300">
                    <span>{t("backupLabel")}</span>
                    <span>
                      {t("countsSummary", {
                        bills: backupCounts.bills,
                        payments: backupCounts.payments,
                      })}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 dark:text-slate-500">
                    {exportDateLabel}
                  </div>
                </div>
              )}
              {isStale && (
                <p className="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-400">
                  {t("staleDataWarning")}
                </p>
              )}
              <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
                {t("dialogDescription", { filename: selectedFile?.name ?? "" })}
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleCancel}
                  onKeyDown={(e) => e.key === "Escape" && handleCancel()}
                  disabled={state === "restoring"}
                  autoFocus
                  className="flex-1 rounded-xl border border-slate-200 bg-white py-2.5 text-sm font-medium text-slate-700 shadow-sm transition-all hover:border-slate-300 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  {t("cancel")}
                </button>
                <button
                  onClick={handleConfirm}
                  disabled={state === "restoring"}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-red-600 bg-red-600 py-2.5 text-sm font-medium text-white shadow-sm transition-all hover:border-red-700 hover:bg-red-700 disabled:opacity-50"
                >
                  {state === "restoring" ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      {t("restoring")}
                    </>
                  ) : (
                    t("confirm")
                  )}
                </button>
              </div>
              {state === "error" && (
                <p className="mt-3 text-center text-sm text-red-600 dark:text-red-400">
                  {errorMsg || t("error")}
                </p>
              )}
            </div>
          </div>,
          document.body
        )}
    </>
  );
}
