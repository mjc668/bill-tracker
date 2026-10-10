"use client";

import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "border border-blue-700 bg-blue-700 text-white hover:border-blue-800 hover:bg-blue-800 active:bg-blue-900 disabled:opacity-50",
  secondary:
    "border border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700 disabled:opacity-50",
  danger:
    "border border-red-600 bg-red-600 text-white hover:border-red-700 hover:bg-red-700 disabled:opacity-50",
};

export function Button({
  variant = "primary",
  loading,
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled ?? loading}
      className={`rounded-xl px-5 py-2.5 text-sm font-semibold shadow-sm transition-all ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
