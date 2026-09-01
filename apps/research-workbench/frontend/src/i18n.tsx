import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Language = "zh" | "en";

interface I18nValue {
  language: Language;
  setLanguage: (language: Language) => void;
  pick: (zh: string, en: string) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<Language>(() => localStorage.getItem("workbench-language") === "en" ? "en" : "zh");
  useEffect(() => {
    localStorage.setItem("workbench-language", language);
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  }, [language]);
  const value = useMemo<I18nValue>(() => ({
    language,
    setLanguage,
    pick: (zh, en) => language === "zh" ? zh : en,
  }), [language]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useI18n must be used inside I18nProvider");
  return value;
}
