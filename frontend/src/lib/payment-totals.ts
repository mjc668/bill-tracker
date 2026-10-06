import type { PaymentInstanceOut } from "./payments-api";

export function createAmountFormatter(locale: string): Intl.NumberFormat {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function parseAmount(value: string | null): number {
  if (value == null) return 0;
  return parseFloat(value) || 0;
}

export function dueAmount(inst: PaymentInstanceOut): number {
  return parseAmount(inst.amount);
}

export function paidAmount(inst: PaymentInstanceOut): number {
  if (inst.paid_amount != null) return parseAmount(inst.paid_amount);
  return inst.status === "paid" ? parseAmount(inst.amount) : 0;
}

export function remainingAmount(inst: PaymentInstanceOut): number {
  return Math.max(parseAmount(inst.amount) - parseAmount(inst.paid_amount), 0);
}

export function sumByCurrency(
  instances: PaymentInstanceOut[],
  valueOf: (inst: PaymentInstanceOut) => number,
): Map<string, number> {
  const totals = new Map<string, number>();
  for (const inst of instances) {
    totals.set(inst.currency, (totals.get(inst.currency) ?? 0) + valueOf(inst));
  }
  return totals;
}

export function formatCurrencyTotals(
  totals: Map<string, number>,
  formatter: Intl.NumberFormat,
): string {
  return [...totals]
    .map(([currency, value]) => `${formatter.format(value)} ${currency}`)
    .join(" · ");
}
