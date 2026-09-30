// The frame around every screen after the splash: a header with the hidden
// menu (top left) and the profile (top right). Both open as animated panels.
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { LANGUAGES } from "./i18n";
import { Logo } from "./ui/art";
import { Avatar, Pill, ThemeToggle } from "./ui/kit";
import { ArrowRight, Edit3, LogIn, LogOut, MapPin, Phone, Sprout, Tractor, User, LayoutDashboard } from "./ui/icons";

// [page, label key or text, short description]
export const MENU = [
  ["disease", "nav_disease", "Photo in, disease out"],
  ["price", "nav_price", "Four-week mandi forecast"],
  ["weather", "nav_weather", "Advice for today's sky"],
  ["marketplace", "nav_marketplace", "Rent machines nearby"],
  ["assistant", "nav_assistant", "Ask in your language"],
  ["loan", "nav_loan", "Kisan Credit Card check"],
  ["home", "nav_dashboard", "Your farm at a glance"],
  ["history", "nav_history", "Every scan you made"],
  ["landing", "nav_about", "What AgriPulse can do"],
];

const EASE = [0.76, 0, 0.24, 1];

// three lines that fold into a cross; the circle fills orange when open
function Burger({ open }) {
  return (
    <span className={`burger ${open ? "burger-open" : ""}`} aria-hidden="true">
      <span className="burger-bar b1" />
      <span className="burger-bar b2" />
      <span className="burger-bar b3" />
    </span>
  );
}

// text whose letters rise out of a mask
function RiseText({ children, delay = 0 }) {
  return (
    <span className="rise-mask">
      <motion.span
        className="rise-inner"
        initial={{ y: "112%" }}
        animate={{ y: "0%" }}
        exit={{ y: "112%" }}
        transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
      >
        {children}
      </motion.span>
    </span>
  );
}

export default function Site({
  page,
  go,
  t,
  lang,
  setLang,
  user,
  signedIn,
  onLogout,
  onLogin,
  theme,
  onToggleTheme,
  children,
}) {
  const [panel, setPanel] = useState(null); // "menu" | "profile" | null
  const [scrolled, setScrolled] = useState(false);

  const close = () => setPanel(null);
  const toggle = (name) => setPanel((old) => (old === name ? null : name));

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!panel) return undefined;

    const onKey = (event) => event.key === "Escape" && close();

    document.addEventListener("keydown", onKey);
    document.body.classList.add("no-scroll");

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("no-scroll");
    };
  }, [panel]);

  const open = (target) => {
    close();
    go(target);
  };

  const solid = page !== "landing" || scrolled || panel;
  const label = (key) => {
    const value = t(key);

    return value === key ? { nav_dashboard: "Dashboard", nav_about: "About AgriPulse" }[key] || key : value;
  };

  return (
    <div className={`site ${page === "landing" ? "site-landing" : "site-app"}`}>
      {/* ------------------------------------------------------------ header */}
      <header className={`site-header ${solid ? "header-solid" : ""} ${panel ? "header-open" : ""}`}>
        <button
          type="button"
          className="hdr-btn hdr-left"
          onClick={() => toggle("menu")}
          aria-expanded={panel === "menu"}
          aria-label={panel === "menu" ? "Close menu" : "Open menu"}
        >
          <span className={`hdr-circle ${panel === "menu" ? "circle-on" : ""}`}>
            <Burger open={panel === "menu"} />
          </span>

          <span className="hdr-label">
            <AnimatePresence mode="wait" initial={false}>
              <motion.span
                key={panel === "menu" ? "c" : "m"}
                initial={{ y: 12, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -12, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                {panel === "menu" ? "Close" : "Menu"}
              </motion.span>
            </AnimatePresence>
          </span>
        </button>

        <button type="button" className="hdr-logo" onClick={() => open("landing")} aria-label="AgriPulse home">
          <Logo size={34} light={!solid || panel === "menu" || panel === "profile"} />
        </button>

        <button
          type="button"
          className="hdr-btn hdr-right"
          onClick={() => toggle("profile")}
          aria-expanded={panel === "profile"}
          aria-label={panel === "profile" ? "Close profile" : "Open profile"}
          title="Your profile"
        >
          <span className="hdr-label">
            <AnimatePresence mode="wait" initial={false}>
              <motion.span
                key={panel === "profile" ? "c" : signedIn ? "n" : "l"}
                initial={{ y: 12, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -12, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                {panel === "profile" ? "Close" : signedIn ? (user.name || "").split(" ")[0] || "Profile" : "Login"}
              </motion.span>
            </AnimatePresence>
          </span>

          <span className={`hdr-circle ${panel === "profile" ? "circle-on" : ""}`}>
            {panel === "profile" ? (
              <Burger open />
            ) : signedIn ? (
              <Avatar name={user.name || user.phone} size={36} />
            ) : (
              <User size={20} />
            )}
          </span>
        </button>
      </header>

      {/* ------------------------------------------------------------- panels */}
      <AnimatePresence>
        {panel && (
          <motion.div
            key="scrim"
            className="panel-scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            onClick={close}
          />
        )}

        {panel === "menu" && (
          <motion.nav
            key="menu"
            className="menu-panel"
            aria-label="Main"
            initial={{ clipPath: "inset(0% 0% 100% 0%)" }}
            animate={{ clipPath: "inset(0% 0% 0% 0%)" }}
            exit={{ clipPath: "inset(0% 0% 100% 0%)" }}
            transition={{ duration: 0.75, ease: EASE }}
          >
            <div className="menu-grid">
              {MENU.map(([id, key, text], index) => (
                <button
                  key={id}
                  type="button"
                  className={`menu-link ${page === id ? "menu-link-on" : ""}`}
                  onClick={() => open(id)}
                  aria-current={page === id ? "page" : undefined}
                >
                  <RiseText delay={0.25 + index * 0.05}>
                    <span className="menu-index">{String(index + 1).padStart(2, "0")}</span>
                    <span className="menu-text">{label(key)}</span>
                  </RiseText>

                  <motion.small
                    className="menu-desc"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ delay: 0.6 + index * 0.05 }}
                  >
                    {text}
                  </motion.small>
                </button>
              ))}
            </div>

            <div className="menu-foot">
              <span className="menu-foot-label">Language</span>

              <div className="menu-langs" role="group" aria-label="Language of the answers">
                {LANGUAGES.map((item, i) => (
                  <motion.button
                    key={item.code}
                    type="button"
                    className={`menu-lang ${item.code === lang ? "menu-lang-on" : ""}`}
                    aria-pressed={item.code === lang}
                    onClick={() => setLang(item.code)}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.7 + i * 0.025 }}
                  >
                    {item.name}
                  </motion.button>
                ))}
              </div>
            </div>
          </motion.nav>
        )}

        {panel === "profile" && (
          <motion.aside
            key="profile"
            className="profile-panel"
            aria-label="Profile"
            initial={{ clipPath: "circle(0px at calc(100% - 34px) 34px)" }}
            animate={{ clipPath: "circle(150% at calc(100% - 34px) 34px)" }}
            exit={{ clipPath: "circle(0px at calc(100% - 34px) 34px)" }}
            transition={{ duration: 0.8, ease: EASE }}
          >
            {signedIn ? (
              <>
                <motion.div
                  className="pp-head"
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3, duration: 0.5 }}
                >
                  <Avatar name={user.name || user.phone} size={68} />

                  <div>
                    <h3>{user.name || user.phone}</h3>

                    <div className="pp-pills">
                      <Pill tone="good">ID #{user.user_code}</Pill>

                      <Pill tone="info" icon={user.role === "owner" ? Tractor : Sprout}>
                        {user.role === "owner" ? "Equipment owner" : "Farmer"}
                      </Pill>
                    </div>
                  </div>
                </motion.div>

                <ul className="pp-facts">
                  <motion.li initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.42 }}>
                    <Phone size={16} /> +91 {user.phone}
                  </motion.li>

                  <motion.li initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 }}>
                    <MapPin size={16} />
                    {[user.village, user.district, user.state].filter(Boolean).join(", ") || "Location not set"}
                  </motion.li>
                </ul>

                <div className="pp-actions">
                  <button type="button" className="pp-link" onClick={() => open("profile")}>
                    <Edit3 size={18} /> <RiseText delay={0.5}>Edit profile</RiseText> <ArrowRight size={16} />
                  </button>

                  <button type="button" className="pp-link" onClick={() => open("home")}>
                    <LayoutDashboard size={18} /> <RiseText delay={0.56}>Dashboard</RiseText> <ArrowRight size={16} />
                  </button>

                  <button type="button" className="pp-link pp-danger" onClick={() => { close(); onLogout(); }}>
                    <LogOut size={18} /> <RiseText delay={0.62}>{t("nav_logout")}</RiseText>
                  </button>
                </div>
              </>
            ) : (
              <>
                <motion.div
                  className="pp-head pp-guest"
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3, duration: 0.5 }}
                >
                  <span className="pp-guest-icon">
                    <User size={30} />
                  </span>

                  <div>
                    <h3>Welcome, farmer</h3>
                    <p>Sign in with your mobile number to use every tool.</p>
                  </div>
                </motion.div>

                <div className="pp-actions">
                  <button type="button" className="pp-cta" onClick={() => { close(); onLogin(); }}>
                    <LogIn size={18} /> <RiseText delay={0.5}>{t("nav_login")}</RiseText> <ArrowRight size={16} />
                  </button>
                </div>
              </>
            )}

            <div className="pp-theme">
              <span>Theme</span>
              <ThemeToggle theme={theme} onToggle={onToggleTheme} />
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* --------------------------------------------------------------- page */}
      <AnimatePresence mode="wait" initial={false}>
        <motion.main
          key={page}
          className={page === "landing" ? "landing-wrap" : "content"}
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
        >
          {children}
        </motion.main>
      </AnimatePresence>

      {page !== "landing" && (
        <footer className="footer">
          <Logo size={26} />

          <p>AgriPulse (KisanMitra AI) · Disease detection · Price forecasts · Weather · Equipment rental · Loan guidance</p>

          <small>&copy; 2026 AgriPulse</small>
        </footer>
      )}
    </div>
  );
}
