// The first thing a visitor sees: phone + OTP login, then (once) the
// onboarding questions. mode="profile" reuses the same questions to edit them.
//
//   no token                       -> phone number -> OTP
//   token, profile not filled in   -> onboarding questions (3 short steps)
//   mode="profile"                 -> all the questions on one page
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { LANGUAGES } from "./i18n";
import { Logo, WheatField } from "./ui/art";
import { Button, ChoiceCard, Input, Select, ThemeToggle, Pill } from "./ui/kit";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Cake,
  Check,
  Globe,
  KeyRound,
  Languages,
  MapPin,
  Mic,
  ScanLine,
  ShieldCheck,
  Smartphone,
  Sprout,
  Tractor,
  TrendingUp,
  User,
  Wheat,
} from "./ui/icons";

const digitsOnly = (text) => text.replace(/\D/g, "");

const minAdultDate = () => {
  const date = new Date();
  date.setFullYear(date.getFullYear() - 18);
  return date.toISOString().split("T")[0];
};

const ageFrom = (dob) => {
  if (!dob) return "";

  const born = new Date(dob);
  const today = new Date();

  let age = today.getFullYear() - born.getFullYear();

  if (
    today.getMonth() < born.getMonth() ||
    (today.getMonth() === born.getMonth() && today.getDate() < born.getDate())
  ) {
    age -= 1;
  }

  return age >= 0 ? age : "";
};

// FastAPI validation errors -> one readable sentence
const readableError = (detail) => {
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    const field = first.loc && first.loc[first.loc.length - 1];
    const message = String(first.msg || "Invalid value").replace(/^Value error, /, "");

    return field ? `${field}: ${message}` : message;
  }

  return "Something went wrong. Please try again.";
};

const GREETINGS = [
  ["नमस्ते", "hi"],
  ["ನಮಸ್ಕಾರ", "kn"],
  ["నమస్కారం", "te"],
  ["வணக்கம்", "ta"],
  ["നമസ്കാരം", "ml"],
  ["নমস্কার", "bn"],
  ["Namaste", "en"],
];

const FEATURES = [
  [ScanLine, "Scan a sick leaf", "Photo in, disease and medicine out"],
  [TrendingUp, "4-week mandi forecast", "Know the best week to sell"],
  [Tractor, "Rent tractors and drones", "From owners within 10 km"],
  [Mic, "Speak in your language", "14 languages, voice first"],
];

function Greeting() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setIndex((old) => (old + 1) % GREETINGS.length), 2200);

    return () => clearInterval(timer);
  }, []);

  return (
    <span className="greeting" aria-hidden="true">
      <AnimatePresence mode="wait">
        <motion.span
          key={index}
          className="greeting-word"
          initial={{ y: 26, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -26, opacity: 0 }}
          transition={{ duration: 0.45 }}
        >
          {GREETINGS[index][0]}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}

function AuthHero() {
  return (
    <aside className="auth-hero">
      <div className="auth-hero-glow" />

      <motion.div
        className="auth-hero-top"
        initial={{ opacity: 0, y: -14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <Logo light size={44} />
      </motion.div>

      <div className="auth-hero-copy">
        <motion.p
          className="auth-eyebrow"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Sprout size={16} /> KisanMitra AI
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          <Greeting />
          <span className="auth-headline">Smarter farming, in your own language.</span>
        </motion.h1>

        <ul className="auth-features">
          {FEATURES.map(([Icon, title, text], i) => (
            <motion.li
              key={title}
              initial={{ opacity: 0, x: -24 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.45 + i * 0.12, duration: 0.5 }}
            >
              <span className="auth-feature-icon">
                <Icon size={19} />
              </span>

              <span>
                <strong>{title}</strong>
                <small>{text}</small>
              </span>
            </motion.li>
          ))}
        </ul>
      </div>

      <div className="auth-hero-art">
        <WheatField />
      </div>

      <div className="auth-float auth-float-1">
        <Globe size={15} /> 14 languages
      </div>

      <div className="auth-float auth-float-2">
        <ShieldCheck size={15} /> Your data stays private
      </div>
    </aside>
  );
}

function Stepper({ steps, current }) {
  return (
    <ol className="stepper" aria-label="Progress">
      {steps.map((name, index) => {
        const done = index < current;
        const active = index === current;

        return (
          <li key={name} className={`${done ? "step-done" : ""} ${active ? "step-active" : ""}`}>
            <span className="step-dot">{done ? <Check size={14} /> : index + 1}</span>
            <span className="step-name">{name}</span>
          </li>
        );
      })}
    </ol>
  );
}

// Six boxes, one real input: paste, autofill and SMS codes all keep working
function OtpBoxes({ value, onChange, onEnter, inputRef }) {
  return (
    <div className="otp" onClick={() => inputRef.current && inputRef.current.focus()}>
      <input
        ref={inputRef}
        id="login-otp"
        aria-label="6 digit OTP"
        type="tel"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        value={value}
        onChange={(e) => onChange(digitsOnly(e.target.value))}
        onKeyDown={(e) => e.key === "Enter" && onEnter()}
      />

      {Array.from({ length: 6 }, (_, i) => (
        <span
          key={i}
          className={`otp-cell ${value[i] ? "otp-filled" : ""} ${value.length === i ? "otp-current" : ""}`}
        >
          {value[i] || ""}
        </span>
      ))}
    </div>
  );
}

// The questions themselves; `parts` picks which groups to show
function ProfileFields({ form, setField, regions, parts }) {
  const districtHints = regions.districts[form.state] || [];

  return (
    <>
      {parts.includes("who") && (
        <div className="form-grid">
          <Input
            id="ob-name"
            label="Full name *"
            icon={User}
            placeholder="Your name"
            value={form.name}
            onChange={(e) => setField("name", e.target.value)}
          />

          <Input
            id="ob-dob"
            label="Date of birth *"
            icon={Cake}
            type="date"
            max={minAdultDate()}
            value={form.dob}
            onChange={(e) => setField("dob", e.target.value)}
          />

          <Input
            id="ob-age"
            label="Age"
            icon={BadgeCheck}
            value={ageFrom(form.dob)}
            readOnly
            placeholder="Filled in from your date of birth"
          />
        </div>
      )}

      {parts.includes("where") && (
        <div className="form-grid">
          <Select
            id="ob-state"
            label="State *"
            icon={MapPin}
            value={form.state}
            onChange={(e) => setField("state", e.target.value)}
          >
            <option value="">Choose your state</option>
            {regions.states.map((state) => (
              <option key={state} value={state}>
                {state}
              </option>
            ))}
          </Select>

          <Input
            id="ob-district"
            label="District *"
            icon={MapPin}
            list="district-hints"
            placeholder="Your district"
            value={form.district}
            onChange={(e) => setField("district", e.target.value)}
          />

          <datalist id="district-hints">
            {districtHints.map((district) => (
              <option key={district} value={district} />
            ))}
          </datalist>

          <Input
            id="ob-village"
            label="Village / town (optional)"
            icon={Wheat}
            placeholder="Village or town"
            value={form.village}
            onChange={(e) => setField("village", e.target.value)}
          />
        </div>
      )}

      {parts.includes("prefs") && (
        <>
          <Select
            id="ob-language"
            label="Language"
            icon={Languages}
            value={form.language}
            onChange={(e) => setField("language", e.target.value)}
          >
            {LANGUAGES.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </Select>

          <div className="field">
            <span className="field-label" id="ob-role-label">
              How will you use AgriPulse?
            </span>

            <div className="choice-list" role="group" aria-labelledby="ob-role-label">
              <ChoiceCard
                active={form.role === "renter"}
                icon={Sprout}
                title="I am a farmer"
                text="I may rent equipment"
                onClick={() => setField("role", "renter")}
              />

              <ChoiceCard
                active={form.role === "owner"}
                icon={Tractor}
                title="I own equipment"
                text="I want to rent it out"
                onClick={() => setField("role", "owner")}
              />
            </div>
          </div>
        </>
      )}
    </>
  );
}

const STEP_PARTS = [["who"], ["where"], ["prefs"]];
const STEP_NAMES = ["About you", "Your farm", "Preferences"];

export default function AuthFlow({
  apiUrl,
  token,
  user,
  mode = "login",
  onLoggedIn,
  onProfileSaved,
  onBack,
  theme,
  onToggleTheme,
}) {
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [demoOtp, setDemoOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const [step, setStep] = useState(0);

  const [regions, setRegions] = useState({ states: [], districts: {} });
  const otpRef = useRef(null);

  const [form, setForm] = useState({
    name: user?.name || "",
    dob: user?.dob || "",
    state: user?.state || "",
    district: user?.district || "",
    village: user?.village || "",
    language: user?.language || "en",
    role: user?.role || "renter",
  });

  const needsProfile = Boolean(token) && (mode === "profile" || !user?.onboarded);

  useEffect(() => {
    if (!needsProfile) return;

    (async () => {
      try {
        const res = await fetch(`${apiUrl}/auth/regions`);

        if (res.ok) setRegions(await res.json());
      } catch (fetchError) {
        console.warn("Could not load the states:", fetchError.message);
      }
    })();
  }, [needsProfile, apiUrl]);

  useEffect(() => {
    if (cooldown <= 0) return undefined;

    const timer = setTimeout(() => setCooldown((old) => old - 1), 1000);

    return () => clearTimeout(timer);
  }, [cooldown]);

  useEffect(() => {
    if (otpSent && otpRef.current) otpRef.current.focus();
  }, [otpSent]);

  const setField = (key, value) => setForm((old) => ({ ...old, [key]: value }));

  // ------------------------------------------------------------ login
  const sendOtp = async () => {
    setError("");

    if (digitsOnly(phone).length < 10) {
      setError("Enter your 10 digit mobile number");
      return;
    }

    setBusy(true);

    try {
      const res = await fetch(`${apiUrl}/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(readableError(data.detail));
        return;
      }

      setDemoOtp(data.demo ? data.demo_otp : "");
      setOtpSent(true);
      setCooldown(30);
    } catch (fetchError) {
      setError("Could not reach the server");
    } finally {
      setBusy(false);
    }
  };

  const verifyOtp = async () => {
    setError("");

    if (otp.trim().length !== 6) {
      setError("Enter the 6 digit OTP");
      return;
    }

    setBusy(true);

    try {
      const res = await fetch(`${apiUrl}/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, otp }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(readableError(data.detail));
        return;
      }

      setOtp("");
      onLoggedIn(data.token, data.user, data);
    } catch (fetchError) {
      setError("Could not reach the server");
    } finally {
      setBusy(false);
    }
  };

  // ------------------------------------------------------------ onboarding
  const validate = (which) => {
    if (which === 0) {
      if (form.name.trim().length < 2) return "Please enter your name";
      if (!form.dob) return "Please enter your date of birth";
    }

    if (which === 1) {
      if (!form.state) return "Please choose your state";
      if (form.district.trim().length < 2) return "Please enter your district";
    }

    return "";
  };

  const next = () => {
    const problem = validate(step);

    setError(problem);

    if (!problem) setStep((old) => old + 1);
  };

  const saveProfile = async () => {
    setError("");

    const problem = validate(0) || validate(1);

    if (problem) {
      setError(problem);
      setStep(validate(0) ? 0 : 1);
      return;
    }

    setBusy(true);

    try {
      const res = await fetch(`${apiUrl}/auth/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...form,
          village: form.village.trim() || null,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(readableError(data.detail));
        return;
      }

      onProfileSaved(data);
    } catch (fetchError) {
      setError("Could not reach the server");
    } finally {
      setBusy(false);
    }
  };

  const errorLine = error && (
    <motion.p
      className="auth-error"
      role="alert"
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      key={error}
    >
      {error}
    </motion.p>
  );

  // ------------------------------------------------------------ edit profile (inside the app)
  if (mode === "profile") {
    return (
      <div className="card profile-card">
        <h2 className="card-title">
          <User size={20} /> Your profile
        </h2>

        <div className="profile-form">
          <ProfileFields
            form={form}
            setField={setField}
            regions={regions}
            parts={["who", "where", "prefs"]}
          />
        </div>

        {errorLine}

        <div className="profile-actions">
          <Button loading={busy} icon={Check} onClick={saveProfile}>
            {busy ? "Saving..." : "Save"}
          </Button>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------ the full-screen flow
  return (
    <div className="auth-screen">
      <AuthHero />

      <main className="auth-panel">
        <div className="auth-topbar">
          {onBack ? (
            <button type="button" className="auth-back" onClick={onBack}>
              <ArrowLeft size={16} /> Back to AgriPulse
            </button>
          ) : (
            <span />
          )}

          <span className="auth-mobile-logo">
            <Logo size={32} wordmark={false} />
          </span>

          {onToggleTheme && <ThemeToggle theme={theme} onToggle={onToggleTheme} />}
        </div>

        <div className="auth-card-wrap">
          <AnimatePresence mode="wait">
            {needsProfile ? (
              <motion.section
                key="onboarding"
                className="auth-card"
                initial={{ opacity: 0, x: 40 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -40 }}
                transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              >
                <Pill tone="good" icon={Sprout}>
                  One-time setup
                </Pill>

                <h2>Tell us about yourself</h2>

                <p className="auth-sub">
                  A few quick questions so we can give you advice for your area. You only do this once.
                </p>

                <Stepper steps={STEP_NAMES} current={step} />

                <AnimatePresence mode="wait" initial={false}>
                  <motion.div
                    key={step}
                    className="auth-step"
                    initial={{ opacity: 0, x: 26 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -26 }}
                    transition={{ duration: 0.25 }}
                  >
                    <ProfileFields
                      form={form}
                      setField={setField}
                      regions={regions}
                      parts={STEP_PARTS[step]}
                    />
                  </motion.div>
                </AnimatePresence>

                {errorLine}

                <div className="auth-actions">
                  {step > 0 && (
                    <Button
                      variant="ghost"
                      icon={ArrowLeft}
                      onClick={() => {
                        setError("");
                        setStep(step - 1);
                      }}
                    >
                      Back
                    </Button>
                  )}

                  {step < STEP_PARTS.length - 1 ? (
                    <Button block iconRight={ArrowRight} onClick={next}>
                      Continue
                    </Button>
                  ) : (
                    <Button block loading={busy} icon={Check} onClick={saveProfile}>
                      {busy ? "Saving..." : "Finish"}
                    </Button>
                  )}
                </div>
              </motion.section>
            ) : (
              <motion.section
                key="login"
                className="auth-card"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -40 }}
                transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
              >
                <span className="auth-badge">
                  <motion.span
                    key={otpSent ? "key" : "phone"}
                    initial={{ scale: 0.4, rotate: -30, opacity: 0 }}
                    animate={{ scale: 1, rotate: 0, opacity: 1 }}
                    transition={{ type: "spring", stiffness: 380, damping: 18 }}
                  >
                    {otpSent ? <KeyRound size={28} /> : <Smartphone size={28} />}
                  </motion.span>
                </span>

                <h2>{otpSent ? "Verify your number" : "Login"}</h2>

                <p className="auth-sub">
                  {otpSent
                    ? `We sent a 6 digit code to +91 ${phone}.`
                    : "Enter your mobile number to continue. New here? We will set you up in a minute."}
                </p>

                <AnimatePresence mode="wait" initial={false}>
                  {!otpSent ? (
                    <motion.div
                      key="phone"
                      className="auth-step"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.22 }}
                    >
                      <div className="field">
                        <label htmlFor="login-phone" className="field-label">
                          Mobile number
                        </label>

                        <div className="phone-box">
                          <span className="phone-prefix">
                            <span className="flag">🇮🇳</span> +91
                          </span>

                          <input
                            id="login-phone"
                            type="tel"
                            inputMode="numeric"
                            autoComplete="tel-national"
                            maxLength={14}
                            placeholder="10 digit mobile number"
                            value={phone}
                            onChange={(e) => setPhone(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && sendOtp()}
                            autoFocus
                          />
                        </div>
                      </div>

                      {errorLine}

                      <Button size="lg" block loading={busy} iconRight={ArrowRight} onClick={sendOtp}>
                        {busy ? "Sending..." : "Send OTP"}
                      </Button>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="otp"
                      className="auth-step"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{ duration: 0.22 }}
                    >
                      {demoOtp && (
                        <div className="demo-otp-box">
                          <span>
                            Demo mode: the OTP is <strong>{demoOtp}</strong>
                          </span>

                          <button type="button" onClick={() => setOtp(demoOtp)}>
                            Fill it
                          </button>
                        </div>
                      )}

                      <OtpBoxes value={otp} onChange={setOtp} onEnter={verifyOtp} inputRef={otpRef} />

                      {errorLine}

                      <Button size="lg" block loading={busy} icon={ShieldCheck} onClick={verifyOtp}>
                        {busy ? "Checking..." : "Verify & continue"}
                      </Button>

                      <div className="auth-links">
                        <button
                          type="button"
                          onClick={() => {
                            setOtpSent(false);
                            setOtp("");
                            setError("");
                          }}
                        >
                          Change mobile number
                        </button>

                        <button type="button" disabled={cooldown > 0 || busy} onClick={sendOtp}>
                          {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend OTP"}
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <p className="auth-legal">
                  <ShieldCheck size={14} /> We only use your number to sign you in.
                </p>
              </motion.section>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
