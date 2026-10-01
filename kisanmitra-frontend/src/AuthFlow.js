// The first thing a visitor sees: phone + OTP login, then (once) the
// onboarding questions. mode="profile" reuses the same questions to edit them.
//
//   no token                       -> phone number -> OTP
//   token, profile not filled in   -> onboarding questions (3 short steps)
//   mode="profile"                 -> all the questions on one page
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { LANGUAGES, serverText, useT } from "./i18n";
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
const readableError = (detail, t) => {
  if (typeof detail === "string") return serverText(t, detail);

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    const field = first.loc && first.loc[first.loc.length - 1];
    const message = String(first.msg || t("auth.invalid_value")).replace(/^Value error, /, "");

    return field ? `${field}: ${message}` : message;
  }

  return t("auth.something_went_wrong");
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
  [ScanLine, "auth.feat_leaf_title", "auth.feat_leaf_text"],
  [TrendingUp, "auth.feat_forecast_title", "auth.feat_forecast_text"],
  [Tractor, "auth.feat_rent_title", "auth.feat_rent_text"],
  [Mic, "auth.feat_voice_title", "auth.feat_voice_text"],
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
  const t = useT();

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
          <Sprout size={16} />{" "}{t("auth.kisanmitra_ai")}
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          <Greeting />
          <span className="auth-headline">{t("auth.smarter_farming_in_your_own_language")}</span>
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
                <strong>{t(title)}</strong>
                <small>{t(text)}</small>
              </span>
            </motion.li>
          ))}
        </ul>
      </div>

      <div className="auth-hero-art">
        <WheatField />
      </div>

      <div className="auth-float auth-float-1">
        <Globe size={15} />{" "}{t("auth.14_languages")}
      </div>

      <div className="auth-float auth-float-2">
        <ShieldCheck size={15} />{" "}{t("auth.your_data_stays_private")}
      </div>
    </aside>
  );
}

function Stepper({ steps, current }) {
  const t = useT();

  return (
    <ol className="stepper" aria-label={t("common.progress")}>
      {steps.map((name, index) => {
        const done = index < current;
        const active = index === current;

        return (
          <li key={name} className={`${done ? "step-done" : ""} ${active ? "step-active" : ""}`}>
            <span className="step-dot">{done ? <Check size={14} /> : index + 1}</span>
            <span className="step-name">{t(name)}</span>
          </li>
        );
      })}
    </ol>
  );
}

// Six boxes, one real input: paste, autofill and SMS codes all keep working
function OtpBoxes({ value, onChange, onEnter, inputRef }) {
  const t = useT();

  return (
    <div className="otp" onClick={() => inputRef.current && inputRef.current.focus()}>
      <input
        ref={inputRef}
        id="login-otp"
        aria-label={t("auth.6_digit_otp")}
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
  const t = useT();

  const districtHints = regions.districts[form.state] || [];

  return (
    <>
      {parts.includes("who") && (
        <div className="form-grid">
          <Input
            id="ob-name"
            label={t("auth.full_name")}
            icon={User}
            placeholder={t("common.your_name")}
            value={form.name}
            onChange={(e) => setField("name", e.target.value)}
          />

          <Input
            id="ob-dob"
            label={t("auth.date_of_birth")}
            icon={Cake}
            type="date"
            max={minAdultDate()}
            value={form.dob}
            onChange={(e) => setField("dob", e.target.value)}
          />

          <Input
            id="ob-age"
            label={t("common.age")}
            icon={BadgeCheck}
            value={ageFrom(form.dob)}
            readOnly
            placeholder={t("auth.filled_in_from_your_date_of")}
          />
        </div>
      )}

      {parts.includes("where") && (
        <div className="form-grid">
          <Select
            id="ob-state"
            label={t("auth.state")}
            icon={MapPin}
            value={form.state}
            onChange={(e) => setField("state", e.target.value)}
          >
            <option value="">{t("auth.choose_your_state")}</option>
            {regions.states.map((state) => (
              <option key={state} value={state}>
                {state}
              </option>
            ))}
          </Select>

          <Input
            id="ob-district"
            label={t("common.district")}
            icon={MapPin}
            list="district-hints"
            placeholder={t("auth.your_district")}
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
            label={t("auth.village_town_optional")}
            icon={Wheat}
            placeholder={t("auth.village_or_town")}
            value={form.village}
            onChange={(e) => setField("village", e.target.value)}
          />
        </div>
      )}

      {parts.includes("prefs") && (
        <>
          <Select
            id="ob-language"
            label={t("common.language")}
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
              {t("auth.how_will_you_use_agripulse")}
            </span>

            <div className="choice-list" role="group" aria-labelledby="ob-role-label">
              <ChoiceCard
                active={form.role === "renter"}
                icon={Sprout}
                title={t("auth.i_am_a_farmer")}
                text={t("auth.i_may_rent_equipment")}
                onClick={() => setField("role", "renter")}
              />

              <ChoiceCard
                active={form.role === "owner"}
                icon={Tractor}
                title={t("auth.i_own_equipment")}
                text={t("auth.i_want_to_rent_it_out")}
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
const STEP_NAMES = ["auth.step_about", "auth.step_farm", "auth.step_prefs"];

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
  const t = useT();

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
      setError(t("auth.err_phone"));
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
        setError(readableError(data.detail, t));
        return;
      }

      setDemoOtp(data.demo ? data.demo_otp : "");
      setOtpSent(true);
      setCooldown(30);
    } catch (fetchError) {
      setError(t("auth.err_server"));
    } finally {
      setBusy(false);
    }
  };

  const verifyOtp = async () => {
    setError("");

    if (otp.trim().length !== 6) {
      setError(t("auth.err_otp"));
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
        setError(readableError(data.detail, t));
        return;
      }

      setOtp("");
      onLoggedIn(data.token, data.user, data);
    } catch (fetchError) {
      setError(t("auth.err_server"));
    } finally {
      setBusy(false);
    }
  };

  // ------------------------------------------------------------ onboarding
  const validate = (which) => {
    if (which === 0) {
      if (form.name.trim().length < 2) return t("auth.err_name");
      if (!form.dob) return t("auth.err_dob");
    }

    if (which === 1) {
      if (!form.state) return t("auth.err_state");
      if (form.district.trim().length < 2) return t("auth.err_district");
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
        setError(readableError(data.detail, t));
        return;
      }

      onProfileSaved(data);
    } catch (fetchError) {
      setError(t("auth.err_server"));
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
          <User size={20} />{" "}{t("common.your_profile")}
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
            {busy ? t("auth.saving") : t("auth.save")}
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
              <ArrowLeft size={16} />{" "}{t("auth.back_to_agripulse")}
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
                  {t("auth.one_time_setup")}
                </Pill>

                <h2>{t("auth.tell_us_about_yourself")}</h2>

                <p className="auth-sub">
                  {t("auth.a_few_quick_questions_so_we")}
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
                      {t("common.back")}
                    </Button>
                  )}

                  {step < STEP_PARTS.length - 1 ? (
                    <Button block iconRight={ArrowRight} onClick={next}>
                      {t("auth.continue")}
                    </Button>
                  ) : (
                    <Button block loading={busy} icon={Check} onClick={saveProfile}>
                      {busy ? t("auth.saving") : t("auth.finish")}
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

                <h2>{otpSent ? t("auth.verify_title") : t("auth.login")}</h2>

                <p className="auth-sub">
                  {otpSent
                    ? t("auth.sent_code", { phone })
                    : t("auth.login_intro")}
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
                          {t("auth.mobile_number")}
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
                            placeholder={t("auth.10_digit_mobile_number")}
                            value={phone}
                            onChange={(e) => setPhone(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && sendOtp()}
                            autoFocus
                          />
                        </div>
                      </div>

                      {errorLine}

                      <Button size="lg" block loading={busy} iconRight={ArrowRight} onClick={sendOtp}>
                        {busy ? t("auth.sending") : t("auth.send_otp")}
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
                            {t("auth.demo_mode_the_otp_is")}{" "}<strong>{demoOtp}</strong>
                          </span>

                          <button type="button" onClick={() => setOtp(demoOtp)}>
                            {t("auth.fill_it")}
                          </button>
                        </div>
                      )}

                      <OtpBoxes value={otp} onChange={setOtp} onEnter={verifyOtp} inputRef={otpRef} />

                      {errorLine}

                      <Button size="lg" block loading={busy} icon={ShieldCheck} onClick={verifyOtp}>
                        {busy ? t("auth.checking") : t("auth.verify_continue")}
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
                          {t("auth.change_mobile_number")}
                        </button>

                        <button type="button" disabled={cooldown > 0 || busy} onClick={sendOtp}>
                          {cooldown > 0 ? t("auth.resend_in", { seconds: cooldown }) : t("auth.resend_otp")}
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <p className="auth-legal">
                  <ShieldCheck size={14} />{" "}{t("auth.we_only_use_your_number_to")}
                </p>
              </motion.section>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
