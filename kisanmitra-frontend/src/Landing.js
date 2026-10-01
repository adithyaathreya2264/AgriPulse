// The scrollable "what can AgriPulse do" page shown after the splash.
import { useRef, useState } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { LANGUAGES, useT } from "./i18n";
import { Logo, WheatField } from "./ui/art";
import { CountUp, Modal, ModalHead } from "./ui/kit";
import {
  ArrowRight,
  Bot,
  CloudSun,
  Globe,
  Landmark,
  Mic,
  ScanLine,
  Smartphone,
  Tractor,
  TrendingUp,
} from "./ui/icons";

// The AgriPulse WhatsApp bot (Twilio sandbox: the join phrase is already typed in the message)
const WHATSAPP_LINK = "https://wa.me/14155238886?text=join%20could-carry";

// A phone or tablet cannot scan its own screen, so there the logo opens WhatsApp itself
function isPhone() {
  if (typeof navigator === "undefined") return false;

  return /Android|iPhone|iPad|iPod|Mobi/i.test(navigator.userAgent || "");
}

const SERVICES = [
  ["disease", ScanLine, "nav_disease", "landing.svc_disease_text"],
  ["price", TrendingUp, "landing.svc_price_title", "landing.svc_price_text"],
  ["weather", CloudSun, "title_weather", "landing.svc_weather_text"],
  ["marketplace", Tractor, "title_marketplace", "landing.svc_market_text"],
  ["loan", Landmark, "nav_loan", "landing.svc_loan_text"],
  ["assistant", Bot, "nav_assistant", "landing.svc_assistant_text"],
];

const FACTS = [
  [14, "", "landing.fact_languages"],
  [4, "landing.unit_wk", "landing.fact_forecast"],
  [10, "landing.unit_km", "landing.fact_radius"],
  [8, "", "landing.fact_documents"],
];

const STEPS = [
  ["01", "landing.step1_title", "landing.step1_text"],
  ["02", "landing.step2_title", "landing.step2_text"],
  ["03", "landing.step3_title", "landing.step3_text"],
];

// Words go from faint to solid as the section scrolls past
function ScrubText({ text, className = "" }) {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 0.85", "end 0.45"] });
  const words = text.split(" ");

  return (
    <p ref={ref} className={`scrub ${className}`}>
      {words.map((word, i) => (
        <Word key={i} progress={scrollYProgress} range={[i / words.length, (i + 1) / words.length]}>
          {word}
        </Word>
      ))}
    </p>
  );
}

function Word({ children, progress, range }) {
  const opacity = useTransform(progress, range, [0.18, 1]);

  return (
    <>
      <motion.span style={{ opacity }}>{children}</motion.span>{" "}
    </>
  );
}

function Tag({ index, children }) {
  return (
    <div className="lp-tag">
      <span className="lp-tag-box">{index}</span>
      <span className="lp-tag-fill">{children}</span>
    </div>
  );
}

function ArrowButton({ children, onClick, dark = false }) {
  return (
    <motion.button
      type="button"
      className={`lp-btn ${dark ? "lp-btn-light" : ""}`}
      onClick={onClick}
      whileHover="hover"
      whileTap={{ scale: 0.97 }}
    >
      <span>{children}</span>

      <motion.span className="lp-btn-arrow" variants={{ hover: { x: 4 } }}>
        <ArrowRight size={16} />
      </motion.span>
    </motion.button>
  );
}

function HeroCard({ label, onClick, children }) {
  return (
    <motion.button
      type="button"
      className="hero-card"
      onClick={onClick}
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 1.6, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -6 }}
    >
      <span className="hero-card-art">{children}</span>

      <span className="hero-card-bar">
        {label} <ArrowRight size={12} />
      </span>
    </motion.button>
  );
}

// The WhatsApp logo; clicking it shows the QR code of the AgriPulse bot
function WhatsAppButton({ onClick, label }) {
  return (
    <motion.button
      type="button"
      className="hero-wa"
      onClick={onClick}
      aria-label={label}
      title={label}
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 1.75, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -6, scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <path
          fill="#fff"
          d="M16.02 4C9.4 4 4.04 9.35 4.04 15.95c0 2.1.55 4.15 1.6 5.96L4 28l6.27-1.6a11.93 11.93 0 0 0 5.75 1.46h.01c6.61 0 11.98-5.35 11.98-11.95A11.9 11.9 0 0 0 16.02 4zm0 21.8h-.01a9.9 9.9 0 0 1-5.04-1.38l-.36-.21-3.72.95.99-3.62-.24-.37a9.85 9.85 0 0 1-1.51-5.2c0-5.45 4.46-9.88 9.94-9.88 2.65 0 5.14 1.03 7.01 2.9a9.78 9.78 0 0 1 2.9 6.99c0 5.45-4.46 9.82-9.96 9.82zm5.46-7.38c-.3-.15-1.77-.87-2.04-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.47-.89-.79-1.49-1.76-1.66-2.06-.17-.3-.02-.46.13-.61.14-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.62-.92-2.22-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48 0 1.46 1.07 2.88 1.22 3.08.15.2 2.1 3.2 5.08 4.48.71.31 1.26.49 1.69.63.71.22 1.36.19 1.87.12.57-.08 1.77-.72 2.02-1.42.25-.7.25-1.3.17-1.42-.07-.12-.27-.2-.57-.35z"
        />
      </svg>
    </motion.button>
  );
}

function Marquee({ items, reverse = false }) {
  const row = [...items, ...items];

  return (
    <div className="marquee">
      <div className={`marquee-track ${reverse ? "marquee-reverse" : ""}`}>
        {row.map((item, i) => (
          <span key={i} className="marquee-item">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function Landing({ ready, go, signedIn }) {
  const t = useT();
  const headline = t("landing.headline").split(" ");

  const [showQr, setShowQr] = useState(false);

  const heroRef = useRef(null);
  const stepsRef = useRef(null);

  const { scrollYProgress: heroScroll } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const artY = useTransform(heroScroll, [0, 1], ["0%", "18%"]);
  const textY = useTransform(heroScroll, [0, 1], ["0%", "-25%"]);
  const fade = useTransform(heroScroll, [0, 0.8], [1, 0]);

  const { scrollYProgress: stepsScroll } = useScroll({ target: stepsRef, offset: ["start 0.7", "end 0.7"] });
  const lineScale = useTransform(stepsScroll, [0, 1], [0, 1]);

  const start = () => go(signedIn ? "home" : "home");

  const openWhatsApp = () => {
    if (isPhone()) {
      window.open(WHATSAPP_LINK, "_blank", "noopener");
    } else {
      setShowQr(true);
    }
  };

  return (
    <div className="lp">
      {/* -------------------------------------------------------------- hero */}
      <section className="lp-hero" ref={heroRef}>
        <motion.div className="lp-hero-art" style={{ y: artY }}>
          <div className="lp-hero-glow" />
          <WheatField stalks={40} />
        </motion.div>

        <motion.div className="lp-hero-body" style={{ y: textY, opacity: fade }}>
          <h1 aria-label={headline.join(" ")}>
            {headline.map((word, i) => (
              <span key={i} className="rise-mask hero-word">
                <motion.span
                  className="rise-inner"
                  initial={{ y: "115%" }}
                  animate={{ y: ready ? "0%" : "115%" }}
                  transition={{ duration: 0.9, delay: ready ? 0.15 + i * 0.09 : 0, ease: [0.22, 1, 0.36, 1] }}
                >
                  {word}&nbsp;
                </motion.span>
              </span>
            ))}
          </h1>

          <motion.p
            className="lp-mono hero-stat"
            initial={{ opacity: 0 }}
            animate={{ opacity: ready ? 1 : 0 }}
            transition={{ delay: 1.1, duration: 0.8 }}
          >
            <span>{t("landing.ai_for_the_field")}</span>
            <span>{t("landing.14_languages_voice_first")}</span>
          </motion.p>
        </motion.div>

        <div className="hero-cards">
          <HeroCard label={t("landing.detect_disease")} onClick={() => go("disease")}>
            <svg viewBox="0 0 200 110" aria-hidden="true">
              <path d="M40 92C36 50 70 14 150 8c4 50-26 84-110 84z" fill="#2fae63" />
              <path d="M40 92L120 30" stroke="#0b7a47" strokeWidth="3" />
              <circle cx="96" cy="58" r="7" fill="#e0454b" />
              <circle cx="122" cy="44" r="5" fill="#e0454b" />
              <rect x="14" y="10" width="172" height="90" rx="8" fill="none" stroke="#a7f3d0" strokeWidth="2" strokeDasharray="14 10" />
            </svg>
            <span className="hero-scan" />
          </HeroCard>

          <HeroCard label={t("landing.price_forecast")} onClick={() => go("price")}>
            <svg viewBox="0 0 200 110" aria-hidden="true">
              <rect width="200" height="110" fill="#0d3b2e" />
              <path d="M10 88L50 70L90 76L130 44L190 22" fill="none" stroke="#f5b83d" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M10 88L50 70L90 76L130 44L190 22V110H10Z" fill="#f5b83d" fillOpacity=".18" />
              <circle cx="190" cy="22" r="6" fill="#fde68a" />
            </svg>
          </HeroCard>

          <WhatsAppButton label={t("landing.whatsapp_aria")} onClick={openWhatsApp} />
        </div>

        <motion.div className="hero-scroll" style={{ opacity: fade }}>
          <span>{t("landing.scroll")}</span>
          <i />
        </motion.div>
      </section>

      {/* ------------------------------------------------------------- about */}
      <section className="lp-section lp-light" id="about">
        <Tag index="S.01">{t("landing.about_us")}</Tag>

        <ScrubText
          className="lp-big"
          text={t("landing.agripulse_is_an_ai_companion_for")}
        />

        <div className="lp-facts">
          {FACTS.map(([value, suffix, label], i) => (
            <motion.div
              key={label}
              className="lp-fact"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ delay: i * 0.1, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            >
              <strong>
                <CountUp value={value} suffix={suffix ? " " + t(suffix) : ""} />
              </strong>

              <span className="lp-mono">{t(label).toUpperCase()}</span>
            </motion.div>
          ))}
        </div>

        <div className="lp-about-row">
          <motion.div
            className="lp-about-visual"
            initial={{ clipPath: "inset(100% 0% 0% 0%)" }}
            whileInView={{ clipPath: "inset(0% 0% 0% 0%)" }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 1.1, ease: [0.76, 0, 0.24, 1] }}
          >
            <WheatField stalks={18} />
          </motion.div>

          <div className="lp-about-copy">
            <p>
              {t("landing.built_for_the_way_farming_really")}
            </p>

            <ArrowButton onClick={() => go("assistant")}>{t("landing.try_the_assistant")}</ArrowButton>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------- services */}
      <section className="lp-section lp-light lp-alt" id="services">
        <Tag index="S.02">{t("landing.what_you_can_do")}</Tag>

        <ScrubText
          className="lp-big"
          text={t("landing.six_tools_that_cover_the_season")}
        />

        <div className="service-grid">
          {SERVICES.map(([id, Icon, title, text], i) => (
            <motion.button
              key={id}
              type="button"
              className="service-card"
              onClick={() => go(id)}
              initial={{ clipPath: "inset(100% 0% 0% 0%)", opacity: 0 }}
              whileInView={{ clipPath: "inset(0% 0% 0% 0%)", opacity: 1 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.9, delay: (i % 3) * 0.12, ease: [0.76, 0, 0.24, 1] }}
            >
              <span className="service-top">
                <span className="lp-mono">{String(i + 1).padStart(2, "0")}</span>

                <span className="service-icon">
                  <Icon size={22} />
                </span>
              </span>

              <h3>{t(title)}</h3>
              <p>{t(text)}</p>

              <span className="service-go">
                {t("landing.open")}{" "}<ArrowRight size={14} />
              </span>
            </motion.button>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------------- steps */}
      <section className="lp-section lp-dark" id="how" ref={stepsRef}>
        <Tag index="S.03">{t("landing.how_it_works")}</Tag>

        <ScrubText className="lp-big lp-big-dark" text={t("landing.three_steps_one_minute_and_it")} />

        <div className="steps">
          <div className="steps-rail">
            <motion.span className="steps-line" style={{ scaleY: lineScale }} />
          </div>

          {STEPS.map(([n, title, text], i) => (
            <motion.div
              key={n}
              className="step"
              initial={{ opacity: 0, x: 40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-20% 0px" }}
              transition={{ duration: 0.8, delay: i * 0.05, ease: [0.22, 1, 0.36, 1] }}
            >
              <span className="step-num">{n}</span>

              <div>
                <h3>{t(title)}</h3>
                <p>{t(text)}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* --------------------------------------------------------- languages */}
      <section className="lp-section lp-light" id="languages">
        <Tag index="S.04">{t("landing.every_language")}</Tag>

        <ScrubText
          className="lp-big"
          text={t("landing.speak_listen_or_type_agripulse_underst")}
        />

        <div className="marquees">
          <Marquee items={LANGUAGES.map((item) => item.name)} />
          <Marquee items={LANGUAGES.map((item) => item.name).reverse()} reverse />
        </div>

        <div className="channel-row">
          {[
            [Mic, "landing.ch_voice_title", "landing.ch_voice_text"],
            [Smartphone, "landing.ch_whatsapp_title", "landing.ch_whatsapp_text"],
            [Globe, "landing.ch_language_title", "landing.ch_language_text"],
          ].map(([Icon, title, text], i) => (
            <motion.div
              key={title}
              className="channel"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ delay: i * 0.12, duration: 0.7 }}
            >
              <span className="channel-icon">
                <Icon size={22} />
              </span>

              <h4>{t(title)}</h4>
              <p>{t(text)}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* --------------------------------------------------------------- cta */}
      <section className="lp-cta">
        <motion.h2
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        >
          {t("landing.ready_to_grow_smarter")}
        </motion.h2>

        <ArrowButton dark onClick={start}>
          {signedIn ? t("landing.open_dashboard") : t("landing.get_started")}
        </ArrowButton>

        <div className="lp-cta-foot">
          <Logo light size={30} />

          <span className="lp-mono">{t("landing.2026_agripulse_kisanmitra_ai")}</span>
        </div>
      </section>

      <Modal open={showQr} onClose={() => setShowQr(false)} title={t("landing.whatsapp_title")} size="sm">
        <ModalHead title={t("landing.whatsapp_title")} subtitle={t("landing.whatsapp_text")} onClose={() => setShowQr(false)} />

        <div className="wa-qr">
          <img src="/whatsapp-qr.png" alt={t("landing.whatsapp_aria")} width="240" height="240" />
        </div>
      </Modal>
    </div>
  );
}
