import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "@/locales/en.json";
import ar from "@/locales/ar.json";

const saved = localStorage.getItem("acrqa-lang") ?? "en";

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ar: { translation: ar },
  },
  lng: saved,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export function setLanguage(lang: "en" | "ar") {
  i18n.changeLanguage(lang);
  localStorage.setItem("acrqa-lang", lang);
  document.documentElement.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");
  document.documentElement.setAttribute("lang", lang);
}

// Apply persisted direction on load
document.documentElement.setAttribute("dir", saved === "ar" ? "rtl" : "ltr");
document.documentElement.setAttribute("lang", saved);

export default i18n;
