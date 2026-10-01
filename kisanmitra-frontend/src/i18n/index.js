// UI labels in every supported language.
//
// en, hi, kn, te, ta, mr are short hand-written labels (please have a native
// speaker review them). The other files start empty and fall back to English
// until they are generated:  python scripts/generate_ui_translations.py
import { createContext, createElement, useContext, useMemo } from "react";
import en from "./en.json";
import hi from "./hi.json";
import kn from "./kn.json";
import te from "./te.json";
import ta from "./ta.json";
import ml from "./ml.json";
import mr from "./mr.json";
import bn from "./bn.json";
import gu from "./gu.json";
import pa from "./pa.json";
import or from "./or.json";
import ur from "./ur.json";
import as from "./as.json";
import bho from "./bho.json";

export const LANGUAGES = [
  { code: "en", name: "English", speech: "en-IN" },
  { code: "hi", name: "हिन्दी", speech: "hi-IN" },
  { code: "kn", name: "ಕನ್ನಡ", speech: "kn-IN" },
  { code: "te", name: "తెలుగు", speech: "te-IN" },
  { code: "ta", name: "தமிழ்", speech: "ta-IN" },
  { code: "ml", name: "മലയാളം", speech: "ml-IN" },
  { code: "mr", name: "मराठी", speech: "mr-IN" },
  { code: "bn", name: "বাংলা", speech: "bn-IN" },
  { code: "gu", name: "ગુજરાતી", speech: "gu-IN" },
  { code: "pa", name: "ਪੰਜਾਬੀ", speech: "pa-IN" },
  { code: "or", name: "ଓଡ଼ିଆ", speech: "or-IN" },
  { code: "ur", name: "اردو", speech: "ur-IN" },
  { code: "as", name: "অসমীয়া", speech: "as-IN" },
  { code: "bho", name: "भोजपुरी", speech: "hi-IN" },
];

const dictionaries = { en, hi, kn, te, ta, ml, mr, bn, gu, pa, or, ur, as, bho };

// Returns a t("key") function for a language. `extra` holds labels translated
// on demand by the server (for languages without a complete label file).
// t("key", {name: "Ramu"}) fills {name} in the sentence.
export const makeT = (lang, extra = {}) => (key, params) => {
  const text =
    (dictionaries[lang] && dictionaries[lang][key]) ||
    extra[key] ||
    en[key] ||
    key;

  return params
    ? text.replace(/\{(\w+)\}/g, (match, name) =>
        params[name] === undefined ? match : String(params[name])
      )
    : text;
};

// Every component reads its translator from here, so no text has to be
// passed down as props. The default is English.
const I18nContext = createContext({ lang: "en", t: makeT("en") });

export function I18nProvider({ lang, t, children }) {
  const value = useMemo(() => ({ lang, t }), [lang, t]);

  return createElement(I18nContext.Provider, { value }, children);
}

export const useT = () => useContext(I18nContext).t;
export const useLang = () => useContext(I18nContext).lang;

// Messages that the server sends in English (errors and validation), mapped
// to their server.* labels so they can be shown in the farmer's language.
const serverKeyByText = Object.fromEntries(
  Object.entries(en)
    .filter(([key]) => key.startsWith("server."))
    .map(([key, text]) => [text, key])
);

export const serverText = (t, text) =>
  typeof text === "string" && serverKeyByText[text] ? t(serverKeyByText[text]) : text;

// A value from the server such as a status ("Confirmed", "Available") shown
// through its status.* label when there is one.
export const enumText = (t, prefix, value) => {
  const key = prefix + String(value).toLowerCase().replace(/[^a-z0-9]+/g, "_");

  return en[key] ? t(key) : value;
};

// English labels that this language has no translation for yet
export const missingLabels = (lang) => {
  if (lang === "en") return {};

  const known = dictionaries[lang] || {};

  return Object.fromEntries(
    Object.entries(en).filter(([key]) => !known[key])
  );
};

export const speechLanguage = (lang) =>
  (LANGUAGES.find((item) => item.code === lang) || LANGUAGES[0]).speech;
