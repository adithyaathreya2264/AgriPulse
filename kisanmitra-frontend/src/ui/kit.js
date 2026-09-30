// The shared building blocks of the interface: buttons, fields, modals,
// toasts, the language picker and the small motion helpers.
import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { registerNotifier } from "./notify";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronDown,
  Info,
  Languages,
  Loader2,
  Moon,
  Sun,
  X,
} from "./icons";

// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------

const readTheme = () => {
  try {
    const saved = localStorage.getItem("theme");

    if (saved === "dark" || saved === "light") return saved;
  } catch (error) {
    // storage blocked: fall through to the system setting
  }

  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

export function useTheme() {
  const [theme, setTheme] = useState(readTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);

    try {
      localStorage.setItem("theme", theme);
    } catch (error) {
      // not a problem
    }
  }, [theme]);

  return [theme, () => setTheme((old) => (old === "dark" ? "light" : "dark"))];
}

export function ThemeToggle({ theme, onToggle }) {
  return (
    <button
      type="button"
      className="icon-btn"
      onClick={onToggle}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      title={theme === "dark" ? "Light mode" : "Dark mode"}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={theme}
          className="icon-swap"
          initial={{ rotate: -80, opacity: 0, scale: 0.6 }}
          animate={{ rotate: 0, opacity: 1, scale: 1 }}
          exit={{ rotate: 80, opacity: 0, scale: 0.6 }}
          transition={{ duration: 0.22 }}
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </motion.span>
      </AnimatePresence>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Toasts and confirm dialog
// ---------------------------------------------------------------------------

const TOAST_ICON = { success: CheckCircle2, error: AlertTriangle, info: Info };

export function UIProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const [asking, setAsking] = useState(null);
  const counter = useRef(0);

  const toast = useCallback((message, type = "info") => {
    counter.current += 1;
    const id = counter.current;

    setToasts((old) => [...old.slice(-3), { id, message: String(message), type }]);

    setTimeout(() => setToasts((old) => old.filter((item) => item.id !== id)), 5200);
  }, []);

  const confirm = useCallback(
    (message, options = {}) =>
      new Promise((resolve) => setAsking({ message, options, resolve })),
    []
  );

  useEffect(() => {
    registerNotifier(toast, confirm);

    return () => registerNotifier(null, null);
  }, [toast, confirm]);

  const answer = (value) => {
    asking.resolve(value);
    setAsking(null);
  };

  return (
    <>
      {children}

      <div className="toast-stack" role="status" aria-live="polite">
        <AnimatePresence>
          {toasts.map((item) => {
            const Icon = TOAST_ICON[item.type] || Info;

            return (
              <motion.div
                key={item.id}
                layout
                className={`toast toast-${item.type}`}
                initial={{ opacity: 0, y: -18, scale: 0.94 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 40, scale: 0.94 }}
                transition={{ type: "spring", stiffness: 420, damping: 30 }}
              >
                <span className="toast-icon">
                  <Icon size={18} />
                </span>

                <span className="toast-text">{item.message}</span>

                <button
                  type="button"
                  className="toast-close"
                  aria-label="Dismiss"
                  onClick={() => setToasts((old) => old.filter((t) => t.id !== item.id))}
                >
                  <X size={15} />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      <Modal open={Boolean(asking)} onClose={() => answer(false)} size="sm" title="Please confirm">
        {asking && (
          <>
            <p className="confirm-text">{asking.message}</p>

            <div className="modal-actions">
              <Button variant="ghost" onClick={() => answer(false)}>
                {asking.options.cancelLabel || "Cancel"}
              </Button>

              <Button onClick={() => answer(true)}>{asking.options.confirmLabel || "Yes, continue"}</Button>
            </div>
          </>
        )}
      </Modal>
    </>
  );
}

// ---------------------------------------------------------------------------
// Motion helpers
// ---------------------------------------------------------------------------

export function Reveal({ children, delay = 0, y = 22, className = "", as = "div", ...rest }) {
  const Tag = motion[as] || motion.div;

  return (
    <Tag
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.55, delay, ease: [0.22, 1, 0.36, 1] }}
      {...rest}
    >
      {children}
    </Tag>
  );
}

// A list whose children rise in one after another
export function Stagger({ children, className = "", gap = 0.07, ...rest }) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="show"
      variants={{ hidden: {}, show: { transition: { staggerChildren: gap } } }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

export const riseIn = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
};

export function Rise({ children, className = "", as = "div", ...rest }) {
  const Tag = motion[as] || motion.div;

  return (
    <Tag className={className} variants={riseIn} {...rest}>
      {children}
    </Tag>
  );
}

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Number that counts up to its value
export function CountUp({ value, duration = 1100, prefix = "", suffix = "", decimals = 0 }) {
  const target = Number(value);
  const valid = Number.isFinite(target);
  const [shown, setShown] = useState(valid && !prefersReducedMotion() ? 0 : target);

  useEffect(() => {
    if (!valid) return undefined;

    if (prefersReducedMotion()) {
      setShown(target);
      return undefined;
    }

    let frame;
    const started = performance.now();

    const tick = (now) => {
      const progress = Math.min((now - started) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 4);

      setShown(target * eased);

      if (progress < 1) frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(frame);
  }, [target, duration, valid]);

  if (!valid) return <>{value}</>;

  return (
    <>
      {prefix}
      {shown.toLocaleString("en-IN", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
      {suffix}
    </>
  );
}

// ---------------------------------------------------------------------------
// Buttons and fields
// ---------------------------------------------------------------------------

export function Button({
  variant = "primary",
  size = "md",
  icon: Icon,
  iconRight: IconRight,
  loading = false,
  block = false,
  className = "",
  children,
  disabled,
  type = "button",
  ...rest
}) {
  return (
    <motion.button
      type={type}
      className={`btn btn-${variant} btn-${size} ${block ? "btn-block" : ""} ${className}`}
      disabled={disabled || loading}
      whileTap={disabled || loading ? undefined : { scale: 0.96 }}
      whileHover={disabled || loading ? undefined : { y: -1 }}
      {...rest}
    >
      {loading ? <Loader2 size={17} className="spin" /> : Icon ? <Icon size={17} /> : null}
      {children !== undefined && children !== null && <span>{children}</span>}
      {!loading && IconRight ? <IconRight size={17} /> : null}
    </motion.button>
  );
}

export function IconButton({ icon: Icon, label, className = "", ...rest }) {
  return (
    <motion.button
      type="button"
      className={`icon-btn ${className}`}
      aria-label={label}
      title={label}
      whileTap={{ scale: 0.9 }}
      {...rest}
    >
      <Icon size={18} />
    </motion.button>
  );
}

// label + input (+ optional leading icon and hint) that stay linked for screen readers
export function Input({ id, label, icon: Icon, hint, error, className = "", trailing, ...rest }) {
  return (
    <div className={`field ${error ? "field-error" : ""} ${className}`}>
      {label && (
        <label htmlFor={id} className="field-label">
          {label}
        </label>
      )}

      <div className="field-box">
        {Icon && <Icon size={18} className="field-icon" />}
        <input id={id} className={Icon ? "has-icon" : ""} {...rest} />
        {trailing}
      </div>

      {hint && !error && <p className="field-hint">{hint}</p>}
      {error && <p className="field-msg">{error}</p>}
    </div>
  );
}

export function TextArea({ id, label, className = "", ...rest }) {
  return (
    <div className={`field ${className}`}>
      {label && (
        <label htmlFor={id} className="field-label">
          {label}
        </label>
      )}

      <div className="field-box">
        <textarea id={id} {...rest} />
      </div>
    </div>
  );
}

export function Select({ id, label, icon: Icon, options, children, className = "", ...rest }) {
  return (
    <div className={`field ${className}`}>
      {label && (
        <label htmlFor={id} className="field-label">
          {label}
        </label>
      )}

      <div className="field-box select-box">
        {Icon && <Icon size={18} className="field-icon" />}

        <select id={id} className={Icon ? "has-icon" : ""} {...rest}>
          {children ||
            options.map((item) => {
              const [value, text] = Array.isArray(item) ? item : [item, item];

              return (
                <option key={value} value={value}>
                  {text}
                </option>
              );
            })}
        </select>

        <ChevronDown size={17} className="select-chevron" />
      </div>
    </div>
  );
}

// Pill switch: [ By the day | By the hour ]
export function Segmented({ options, value, onChange, className = "", ariaLabel }) {
  return (
    <div className={`segmented ${className}`} role="tablist" aria-label={ariaLabel}>
      {options.map(([code, text]) => (
        <button
          key={code}
          type="button"
          role="tab"
          aria-selected={value === code}
          className={value === code ? "seg-on" : ""}
          onClick={() => onChange(code)}
        >
          {value === code && (
            <motion.span layoutId={`seg-${ariaLabel || "x"}`} className="seg-thumb" transition={{ type: "spring", stiffness: 500, damping: 36 }} />
          )}
          <span className="seg-text">{text}</span>
        </button>
      ))}
    </div>
  );
}

export function Chip({ active, icon: Icon, children, className = "", ...rest }) {
  return (
    <button type="button" className={`chip ${active ? "chip-on" : ""} ${className}`} {...rest}>
      {Icon && <Icon size={15} />}
      {children}
    </button>
  );
}

// A selectable option card (role choice, language choice ...)
export function ChoiceCard({ active, icon: Icon, title, text, onClick }) {
  return (
    <motion.button
      type="button"
      className={`choice ${active ? "choice-on" : ""}`}
      onClick={onClick}
      whileTap={{ scale: 0.98 }}
      aria-pressed={active}
    >
      <span className="choice-icon">{Icon && <Icon size={22} />}</span>

      <span className="choice-body">
        <strong>{title}</strong>
        {text && <small>{text}</small>}
      </span>

      <span className="choice-tick">{active && <Check size={15} />}</span>
    </motion.button>
  );
}

export function Pill({ tone = "neutral", icon: Icon, children, className = "" }) {
  return (
    <span className={`pill pill-${tone} ${className}`}>
      {Icon && <Icon size={13} />}
      {children}
    </span>
  );
}

export function Avatar({ name = "", size = 40 }) {
  const initials =
    name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((word) => Array.from(word)[0])
      .join("")
      .toUpperCase() || "•";

  return (
    <span className="avatar" style={{ width: size, height: size, fontSize: size * 0.4 }} aria-hidden="true">
      {initials}
    </span>
  );
}

export function Spinner({ label }) {
  return (
    <span className="spinner-wrap" role="status">
      <Loader2 size={20} className="spin" />
      {label && <span>{label}</span>}
    </span>
  );
}

export function Skeleton({ height = 16, width = "100%", radius = 10, className = "" }) {
  return <span className={`skeleton ${className}`} style={{ height, width, borderRadius: radius }} />;
}

export function EmptyState({ art, icon: Icon, title, text, action }) {
  return (
    <motion.div
      className="empty-state"
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
    >
      {art || (
        <span className="empty-icon">
          {Icon && <Icon size={30} />}
        </span>
      )}

      <h3>{title}</h3>
      {text && <p>{text}</p>}
      {action}
    </motion.div>
  );
}

export function PageHeader({ icon: Icon, title, subtitle, actions, tone = "green" }) {
  return (
    <motion.header
      className="page-header"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
    >
      <span className={`page-header-badge badge-${tone}`}>
        <Icon size={26} />
      </span>

      <div className="page-header-text">
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>

      {actions && <div className="page-header-actions">{actions}</div>}
    </motion.header>
  );
}

// ---------------------------------------------------------------------------
// Modal / bottom sheet
// ---------------------------------------------------------------------------

export function Modal({ open, onClose, title, children, size = "md", className = "" }) {
  const panelRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    const onKey = (event) => event.key === "Escape" && onClose();

    document.addEventListener("keydown", onKey);
    document.body.classList.add("no-scroll");

    const timer = setTimeout(() => panelRef.current && panelRef.current.focus(), 60);

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("no-scroll");
      clearTimeout(timer);
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="modal-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onMouseDown={(event) => event.target === event.currentTarget && onClose()}
        >
          <motion.div
            ref={panelRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            className={`modal modal-${size} ${className}`}
            initial={{ opacity: 0, y: 60, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 60, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 380, damping: 34 }}
          >
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function ModalHead({ title, subtitle, onClose, onBack }) {
  return (
    <div className="modal-head">
      {onBack && (
        <button type="button" className="icon-btn" onClick={onBack} aria-label="Back">
          <ChevronDown size={18} className="rot-90" />
        </button>
      )}

      <div className="modal-head-text">
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>

      <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
        <X size={18} />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Language picker
// ---------------------------------------------------------------------------

export function LanguagePicker({ lang, languages, onChange, variant = "bar" }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const current = languages.find((item) => item.code === lang) || languages[0];

  useEffect(() => {
    if (!open) return undefined;

    const away = (event) => rootRef.current && !rootRef.current.contains(event.target) && setOpen(false);
    const esc = (event) => event.key === "Escape" && setOpen(false);

    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", esc);

    return () => {
      document.removeEventListener("mousedown", away);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  return (
    <div className={`lang-picker lang-${variant}`} ref={rootRef}>
      <button
        type="button"
        className="lang-trigger"
        title="Language of the answers"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((old) => !old)}
      >
        <Languages size={17} />
        <span className="lang-current">{current.name}</span>
        <ChevronDown size={15} className={open ? "rot-180" : ""} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.ul
            className="lang-menu"
            role="listbox"
            aria-label="Languages"
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.16 }}
          >
            {languages.map((item) => (
              <li key={item.code} role="presentation">
                <button
                  type="button"
                  role="option"
                  aria-selected={item.code === lang}
                  className={item.code === lang ? "lang-item lang-item-on" : "lang-item"}
                  onClick={() => {
                    onChange(item.code);
                    setOpen(false);
                  }}
                >
                  <span>{item.name}</span>
                  {item.code === lang && <Check size={15} />}
                </button>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
