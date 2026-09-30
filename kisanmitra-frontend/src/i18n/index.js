// UI labels in every supported language.
//
// en, hi, kn, te, ta, mr are short hand-written labels (please have a native
// speaker review them). The other files start empty and fall back to English
// until they are generated:  python scripts/generate_ui_translations.py
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
// on demand by the server (for languages without a hand-written file).
export const makeT = (lang, extra = {}) => (key) =>
  (dictionaries[lang] && dictionaries[lang][key]) ||
  extra[key] ||
  en[key] ||
  key;

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
