// The scrollable "what can AgriPulse do" page shown after the splash.
import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { LANGUAGES } from "./i18n";
import { Logo, WheatField } from "./ui/art";
import { CountUp } from "./ui/kit";
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

const HEADLINE = ["Your", "trusted", "partner", "in", "every", "season"];

const SERVICES = [
  ["disease", ScanLine, "Disease Detection", "Photograph a sick leaf. A vision model names the disease, suggests the medicine and estimates the cost, in your language."],
  ["price", TrendingUp, "Price Forecast", "Today's mandi price and a four-week forecast, with the best week to sell and alerts on WhatsApp."],
  ["weather", CloudSun, "Weather Advisory", "Live weather for your district, turned into plain advice for spraying, sowing and irrigation."],
  ["marketplace", Tractor, "Equipment Marketplace", "Rent tractors, harvesters and drones from owners within 10 km, by the day or the hour, paid by UPI."],
  ["loan", Landmark, "Loan Advisor", "Check Kisan Credit Card eligibility, see your estimated limit and the documents still missing."],
  ["assistant", Bot, "AI Assistant", "Ask any farming question by typing or speaking. Answers come back in your language, with a voice."],
];

const FACTS = [
  [14, "", "Languages"],
  [4, " wk", "Price forecast"],
  [10, " km", "Rental search radius"],
  [8, "", "Loan documents checked"],
];

const STEPS = [
  ["01", "Sign in with your phone", "Enter your mobile number and the OTP. No password to remember."],
  ["02", "Tell us about your farm", "Name, district and language, once. Every answer after that is tuned to your area."],
  ["03", "Use every tool", "Scan leaves, check prices, rent a machine or ask the assistant, by text or by voice."],
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
  const heroRef = useRef(null);
  const stepsRef = useRef(null);

  const { scrollYProgress: heroScroll } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const artY = useTransform(heroScroll, [0, 1], ["0%", "18%"]);
  const textY = useTransform(heroScroll, [0, 1], ["0%", "-25%"]);
  const fade = useTransform(heroScroll, [0, 0.8], [1, 0]);

  const { scrollYProgress: stepsScroll } = useScroll({ target: stepsRef, offset: ["start 0.7", "end 0.7"] });
  const lineScale = useTransform(stepsScroll, [0, 1], [0, 1]);

  const start = () => go(signedIn ? "home" : "home");

  return (
    <div className="lp">
      {/* -------------------------------------------------------------- hero */}
      <section className="lp-hero" ref={heroRef}>
        <motion.div className="lp-hero-art" style={{ y: artY }}>
          <div className="lp-hero-glow" />
          <WheatField stalks={40} />
        </motion.div>

        <motion.div className="lp-hero-body" style={{ y: textY, opacity: fade }}>
          <h1 aria-label={HEADLINE.join(" ")}>
            {HEADLINE.map((word, i) => (
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
            <span>AI FOR THE FIELD</span>
            <span>+ 14 LANGUAGES · VOICE FIRST</span>
          </motion.p>
        </motion.div>

        <div className="hero-cards">
          <HeroCard label="DETECT DISEASE" onClick={() => go("disease")}>
            <svg viewBox="0 0 200 110" aria-hidden="true">
              <path d="M40 92C36 50 70 14 150 8c4 50-26 84-110 84z" fill="#2fae63" />
              <path d="M40 92L120 30" stroke="#0b7a47" strokeWidth="3" />
              <circle cx="96" cy="58" r="7" fill="#e0454b" />
              <circle cx="122" cy="44" r="5" fill="#e0454b" />
              <rect x="14" y="10" width="172" height="90" rx="8" fill="none" stroke="#a7f3d0" strokeWidth="2" strokeDasharray="14 10" />
            </svg>
            <span className="hero-scan" />
          </HeroCard>

          <HeroCard label="PRICE FORECAST" onClick={() => go("price")}>
            <svg viewBox="0 0 200 110" aria-hidden="true">
              <rect width="200" height="110" fill="#0d3b2e" />
              <path d="M10 88L50 70L90 76L130 44L190 22" fill="none" stroke="#f5b83d" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M10 88L50 70L90 76L130 44L190 22V110H10Z" fill="#f5b83d" fillOpacity=".18" />
              <circle cx="190" cy="22" r="6" fill="#fde68a" />
            </svg>
          </HeroCard>
        </div>

        <motion.div className="hero-scroll" style={{ opacity: fade }}>
          <span>SCROLL</span>
          <i />
        </motion.div>
      </section>

      {/* ------------------------------------------------------------- about */}
      <section className="lp-section lp-light" id="about">
        <Tag index="S.01">ABOUT US</Tag>

        <ScrubText
          className="lp-big"
          text="AgriPulse is an AI companion for Indian farmers. It reads your crops, watches the market and the sky, and answers in the language you think in."
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
                <CountUp value={value} suffix={suffix} />
              </strong>

              <span className="lp-mono">{label.toUpperCase()}</span>
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
              Built for the way farming really works: a phone in one hand, a field in front of you, and little time to
              read. Every screen can be used by voice, and the same assistant is available on WhatsApp.
            </p>

            <ArrowButton onClick={() => go("assistant")}>TRY THE ASSISTANT</ArrowButton>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------- services */}
      <section className="lp-section lp-light lp-alt" id="services">
        <Tag index="S.02">WHAT YOU CAN DO</Tag>

        <ScrubText
          className="lp-big"
          text="Six tools that cover the season, from the first seed to the last sale, and the loan in between."
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

              <h3>{title}</h3>
              <p>{text}</p>

              <span className="service-go">
                OPEN <ArrowRight size={14} />
              </span>
            </motion.button>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------------- steps */}
      <section className="lp-section lp-dark" id="how" ref={stepsRef}>
        <Tag index="S.03">HOW IT WORKS</Tag>

        <ScrubText className="lp-big lp-big-dark" text="Three steps, one minute, and it remembers you next time." />

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
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* --------------------------------------------------------- languages */}
      <section className="lp-section lp-light" id="languages">
        <Tag index="S.04">EVERY LANGUAGE</Tag>

        <ScrubText
          className="lp-big"
          text="Speak, listen or type. AgriPulse understands fourteen Indian languages and talks back."
        />

        <div className="marquees">
          <Marquee items={LANGUAGES.map((item) => item.name)} />
          <Marquee items={LANGUAGES.map((item) => item.name).reverse()} reverse />
        </div>

        <div className="channel-row">
          {[
            [Mic, "Voice first", "Tap the microphone on any screen and just say what you need."],
            [Smartphone, "On WhatsApp too", "Send a leaf photo or a voice note to the AgriPulse WhatsApp number."],
            [Globe, "Your language", "Answers, advice and spoken replies follow the language you choose."],
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

              <h4>{title}</h4>
              <p>{text}</p>
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
          Ready to grow smarter?
        </motion.h2>

        <ArrowButton dark onClick={start}>
          {signedIn ? "OPEN YOUR DASHBOARD" : "GET STARTED"}
        </ArrowButton>

        <div className="lp-cta-foot">
          <Logo light size={30} />

          <span className="lp-mono">© 2026 AGRIPULSE · KISANMITRA AI</span>
        </div>
      </section>
    </div>
  );
}
