"use client";

import { ReactNode } from "react";
import { NextIntlClientProvider } from "next-intl";
import enMessages from "../../messages/en.json";

export function LocaleProvider({ children }: { children: ReactNode }) {
  return (
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {children}
    </NextIntlClientProvider>
  );
}
