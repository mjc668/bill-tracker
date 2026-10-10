"use client";

interface SwitchProps {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  disabled?: boolean;
}

export function Switch({ checked, onChange, label, disabled }: SwitchProps) {
  return (
    <label className={`flex items-center gap-3 ${disabled ? "cursor-not-allowed" : "cursor-pointer"}`}>
      <div className="relative">
        <input
          type="checkbox"
          role="switch"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          aria-checked={checked}
          className="sr-only peer"
        />
        <div className="w-11 h-6 rounded-full border border-slate-200 bg-slate-100 dark:border-slate-600 dark:bg-slate-700 peer-checked:border-blue-600 peer-checked:bg-blue-600 dark:peer-checked:border-blue-500 dark:peer-checked:bg-blue-500 peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500 peer-focus-visible:ring-offset-2 transition-all peer-disabled:opacity-50" />
        <div className="absolute left-0.5 top-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform peer-checked:translate-x-5 peer-disabled:opacity-50" />
      </div>
      <span className="text-sm font-medium text-slate-700 dark:text-slate-300 select-none">
        {label}
      </span>
    </label>
  );
}
