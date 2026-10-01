import { useEffect, useRef, useState } from "react";
import { MotionConfig, motion } from "framer-motion";
import "./styles/base.css";
import "./styles/art.css";
import "./styles/auth.css";
import "./styles/shell.css";
import "./styles/site.css";
import "./styles/pages.css";
import { I18nProvider, makeT, missingLabels } from "./i18n";
import { API_URL, VoiceCommandButton } from "./voice";
import { notify } from "./ui/notify";
import { UIProvider, useTheme } from "./ui/kit";
import AuthFlow from "./AuthFlow";
import Site from "./Site";
import Splash from "./Splash";
import Landing from "./Landing";
import LoanAdvisor from "./LoanAdvisor";
import HomePage from "./pages/HomePage";
import DiseasePage from "./pages/DiseasePage";
import PricePage from "./pages/PricePage";
import WeatherPage from "./pages/WeatherPage";
import MarketplacePage from "./pages/MarketplacePage";
import HistoryPage from "./pages/HistoryPage";
import AssistantPage from "./pages/AssistantPage";
import ProfilePage from "./pages/ProfilePage";

const PAGES = ["landing", "auth", "home", "disease", "price", "weather", "marketplace", "history", "assistant", "loan", "profile"];

const readSaved = (key, fallback) => {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch (error) {
    return fallback;
  }
};

const GROUP = (page) => (page === "landing" ? "landing" : page === "auth" ? "auth" : "app");

const CURTAIN_LABEL = {
  disease: "app.curtain_disease",
  price: "app.curtain_price",
  weather: "app.curtain_weather",
  marketplace: "app.curtain_market",
  assistant: "app.curtain_assistant",
  loan: "app.curtain_loan",
  home: "app.curtain_home",
  history: "app.curtain_history",
  profile: "app.curtain_profile",
  landing: "app.curtain_landing",
  auth: "app.curtain_auth",
};

// The colour sheet that sweeps over the screen while the page changes
function Curtain({ curtain }) {
  return (
    <motion.div
      className="curtain"
      aria-hidden="true"
      initial={{ clipPath: "inset(100% 0% 0% 0%)" }}
      animate={{ clipPath: curtain.phase === "in" ? "inset(0% 0% 0% 0%)" : "inset(0% 0% 100% 0%)" }}
      transition={{ duration: 0.7, ease: [0.76, 0, 0.24, 1] }}
    >
      <motion.span
        className="curtain-label"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: curtain.phase === "in" ? 1 : 0, y: curtain.phase === "in" ? 0 : -24 }}
        transition={{ duration: 0.45, delay: curtain.phase === "in" ? 0.3 : 0 }}
      >
        {curtain.label}
      </motion.span>
    </motion.div>
  );
}

function App() {
  // Every visit starts on the information page (after the splash)
  const [page, setPage] = useState("landing");
  const [splashDone, setSplashDone] = useState(false);
  const [authTarget, setAuthTarget] = useState(null);
  const [curtain, setCurtain] = useState(null);
  const busy = useRef(false);
  const pageRef = useRef("landing");
  const [lang, setLang] = useState(localStorage.getItem("lang") || "en");
  const [extraLabels, setExtraLabels] = useState({});
  const t = makeT(lang, extraLabels);
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [user, setUser] = useState(readSaved("user", null));
  const [theme, toggleTheme] = useTheme();

  // The assistant chat lives here so a diagnosis can start a conversation
  const [chatMessages, setChatMessages] = useState([]);

  // A spoken command ("show weather in Mysuru") is handed to the page it opens
  const [intent, setIntent] = useState(null);

  const authHeaders = (extra = {}) => ({
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  });

  const jsonHeaders = () => authHeaders({ "Content-Type": "application/json" });

  const logout = () => {
    setToken("");
    setUser(null);
    switchPage("landing");
    setChatMessages([]);
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  };

  // A protected request came back 401: the session is over
  const sessionExpired = () => {
    logout();
    notify(t("app.your_session_has_expired_please_login"), "error");
  };

  const saveSession = (newToken, newUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem("token", newToken);
    localStorage.setItem("user", JSON.stringify(newUser));
  };

  // OTP verified: a returning farmer goes straight in, a new one onboards first
  const handleLoggedIn = (newToken, newUser) => {
    saveSession(newToken, newUser);

    if (newUser.onboarded) {
      if (newUser.language) setLang(newUser.language);
      switchPage(authTarget || "home");
      setAuthTarget(null);
    }
  };

  const handleProfileSaved = (newUser) => {
    saveSession(token, newUser);

    if (newUser.language) setLang(newUser.language);

    notify(t("app.profile_saved"), "success");
    switchPage(authTarget || "home");
    setAuthTarget(null);
  };

  const signedIn = Boolean(token && user && user.onboarded);

  // Moving between the information page, the login and the tools plays a
  // colour transition; moving between two tools keeps the quick fade.
  const switchPage = (target, label) => {
    if (busy.current) return;

    if (GROUP(pageRef.current) === GROUP(target)) {
      setPage(target);
      return;
    }

    busy.current = true;
    setCurtain({ phase: "in", label: t(label || CURTAIN_LABEL[target]) });

    setTimeout(() => {
      window.scrollTo({ top: 0 });
      setPage(target);
      setCurtain((old) => old && { ...old, phase: "out" });
    }, 850);

    setTimeout(() => {
      setCurtain(null);
      busy.current = false;
    }, 1650);
  };

  // The information page is public; every tool needs a signed-in farmer
  const go = (target) => {
    window.scrollTo({ top: 0 });

    if (target !== "landing" && target !== "auth" && !signedIn) {
      setAuthTarget(target);
      switchPage("auth", CURTAIN_LABEL[target]);
      return;
    }

    switchPage(target);
  };

  const goLogin = () => {
    setAuthTarget(page === "landing" ? null : page);
    switchPage("auth");
  };

  const handleVoiceCommand = (command) => {
    const target = PAGES.includes(command.page) ? command.page : page;

    setIntent({
      id: Date.now(),
      page: target,
      action: command.action,
      params: command.params || {},
    });

    setPage(target);
  };

  useEffect(() => {
    pageRef.current = page;

    // A spoken command only belongs to the page it opened
    setIntent((old) => (old && old.page !== page ? null : old));
  }, [page]);

  // Languages without hand-written labels: the server translates them once
  // (and caches them), we keep a copy in the browser too.
  useEffect(() => {
    const missing = missingLabels(lang);

    if (Object.keys(missing).length === 0) {
      setExtraLabels({});
      return;
    }

    const cacheKey = `ui_labels_${lang}_${Object.keys(missing).length}`;

    try {
      const cached = JSON.parse(localStorage.getItem(cacheKey) || "null");

      if (cached) {
        setExtraLabels(cached);
        return;
      }
    } catch (error) {
      // ignore a broken cache
    }

    setExtraLabels({});

    let cancelled = false;

    (async () => {
      const entries = Object.entries(missing);
      const received = {};

      try {
        for (let from = 0; from < entries.length; from += 150) {
          const res = await fetch(`${API_URL}/i18n/translate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lang, labels: Object.fromEntries(entries.slice(from, from + 150)) }),
          });

          if (!res.ok) break;

          const data = await res.json();

          if (cancelled || !data.labels) return;

          Object.assign(received, data.labels);
          setExtraLabels({ ...received });
        }

        // Only keep a complete result, so missing labels are asked again later
        if (Object.keys(received).length === entries.length) {
          try {
            localStorage.setItem(cacheKey, JSON.stringify(received));
          } catch (error) {
            // storage full or blocked: not a problem
          }
        }
      } catch (error) {
        console.warn("Could not translate the labels:", error.message);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [lang]);

  useEffect(() => {
    localStorage.setItem("lang", lang);
    document.documentElement.setAttribute("lang", lang);
    // Urdu is written right to left
    document.documentElement.setAttribute("dir", lang === "ur" ? "rtl" : "ltr");
  }, [lang]);

  // Refresh the profile from the database when the app opens; an expired
  // token logs the farmer out quietly.
  useEffect(() => {
    if (!token) return;

    (async () => {
      try {
        const res = await fetch(`${API_URL}/auth/me`, { headers: authHeaders() });

        if (res.status === 401) {
          logout();
        } else if (res.ok) {
          const fresh = await res.json();

          // Only trust a real profile (never overwrite it with an odd reply)
          if (fresh && typeof fresh === "object" && fresh.id) {
            setUser(fresh);
            localStorage.setItem("user", JSON.stringify(fresh));
          }
        }
      } catch (error) {
        console.warn("Could not refresh the profile:", error.message);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // A diagnosis opens a conversation about it
  const handleDiagnosed = (data) => {
    const report = data.report;

    setChatMessages([
      {
        sender: "assistant",
        text:
          t("app.diag_disease", { disease: report.disease }) + "\n\n" +
          t("app.diag_confidence", { confidence: report.confidence }) + "\n\n" +
          t("app.diag_medicine", { medicine: report.medicine }) + "\n\n" +
          t("app.diag_cost", { cost: report.estimated_cost }) + "\n\n" +
          t("app.diag_ask"),
      },
    ]);
  };

  // ---------------------------------------------------------------- render
  const views = {
    landing: <Landing ready={splashDone} go={go} signedIn={signedIn} />,
    home: signedIn && <HomePage user={user} lang={lang} t={t} go={go} />,
    disease: signedIn && <DiseasePage user={user} lang={lang} t={t} onDiagnosed={handleDiagnosed} go={go} />,
    price: signedIn && (
      <PricePage
        token={token}
        lang={lang}
        t={t}
        jsonHeaders={jsonHeaders}
        sessionExpired={sessionExpired}
        goLogin={goLogin}
        intent={intent && intent.page === "price" ? intent : null}
      />
    ),
    weather: signedIn && (
      <WeatherPage user={user} lang={lang} t={t} intent={intent && intent.page === "weather" ? intent : null} />
    ),
    marketplace: signedIn && (
      <MarketplacePage
        token={token}
        user={user}
        lang={lang}
        t={t}
        jsonHeaders={jsonHeaders}
        sessionExpired={sessionExpired}
        goLogin={goLogin}
      />
    ),
    history: signedIn && <HistoryPage go={go} />,
    assistant: signedIn && (
      <AssistantPage
        user={user}
        lang={lang}
        t={t}
        messages={chatMessages}
        setMessages={setChatMessages}
        intent={intent && intent.page === "assistant" ? intent : null}
      />
    ),
    loan: signedIn && <LoanAdvisor apiUrl={API_URL} user={user} token={token} lang={lang} t={t} onLogin={goLogin} />,
    profile: signedIn && (
      <ProfilePage apiUrl={API_URL} token={token} user={user} onProfileSaved={handleProfileSaved} />
    ),
  };

  return (
    <I18nProvider lang={lang} t={t}>
    <MotionConfig reducedMotion="user">
      <UIProvider>
        {page === "auth" ? (
          <AuthFlow
            apiUrl={API_URL}
            token={token}
            user={user}
            onLoggedIn={handleLoggedIn}
            onProfileSaved={handleProfileSaved}
            onBack={() => switchPage("landing")}
            theme={theme}
            onToggleTheme={toggleTheme}
          />
        ) : (
          <>
            <Site
              page={page}
              go={go}
              t={t}
              lang={lang}
              setLang={setLang}
              user={user}
              signedIn={signedIn}
              onLogout={logout}
              onLogin={goLogin}
              theme={theme}
              onToggleTheme={toggleTheme}
            >
              {views[page]}
            </Site>

            {/* Speak a command from any page */}
            {signedIn && page !== "landing" && <VoiceCommandButton lang={lang} t={t} onCommand={handleVoiceCommand} />}
          </>
        )}

        {curtain && <Curtain curtain={curtain} />}

        {!splashDone && <Splash onDone={() => setSplashDone(true)} />}
      </UIProvider>
    </MotionConfig>
    </I18nProvider>
  );
}

export default App;
