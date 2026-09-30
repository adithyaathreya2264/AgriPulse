// Opening splash: a white tile pops in, opens up to spell the name letter by
// letter, settles into an outlined lockup, then the curtain lifts.
import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const WORD = "AGRIPULSE".split("");

const reduced = () =>
  typeof window !== "undefined" &&
  window.matchMedia &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// phase: 0 tile · 1 name opens · 2 outlined · 3 curtain up
export default function Splash({ onDone }) {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const speed = reduced() ? 0.35 : 1;
    const timers = [
      setTimeout(() => setPhase(1), 650 * speed),
      setTimeout(() => setPhase(2), 2250 * speed),
      setTimeout(() => setPhase(3), 2900 * speed),
      setTimeout(() => onDone(), 3750 * speed),
    ];

    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <motion.div
      className="splash"
      role="status"
      aria-label="AgriPulse is loading"
      initial={{ clipPath: "inset(0% 0% 0% 0%)" }}
      animate={{ clipPath: phase === 3 ? "inset(0% 0% 100% 0%)" : "inset(0% 0% 0% 0%)" }}
      transition={{ duration: 0.85, ease: [0.76, 0, 0.24, 1] }}
    >
      <motion.div
        className={`splash-lock ${phase >= 2 ? "splash-outline" : ""}`}
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: phase >= 2 ? 1.12 : 1, opacity: phase === 3 ? 0.4 : 1 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      >
        <motion.span
          className="splash-tile"
          initial={{ width: 44 }}
          animate={{ width: phase >= 2 ? 0 : 44, opacity: phase >= 2 ? 0 : 1, marginRight: phase >= 2 ? 0 : 6 }}
          transition={{ duration: 0.5, ease: [0.76, 0, 0.24, 1] }}
        >
          <svg viewBox="0 0 48 48" width="30" height="30" aria-hidden="true">
            <path d="M8 38C7 24 16 12 40 9c1 20-8 30-32 29z" fill="#0d3b2e" />
            <path d="M6 30h9l4-8 5 14 4-10h10" fill="none" stroke="#f5b83d" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </motion.span>

        <motion.span
          className="splash-name"
          initial={{ width: 0 }}
          animate={{ width: phase >= 1 ? "auto" : 0 }}
          transition={{ duration: 0.75, ease: [0.76, 0, 0.24, 1] }}
        >
          <span className="splash-letters">
            {WORD.map((letter, i) => (
              <span key={i} className="splash-mask">
                <motion.span
                  className="splash-letter"
                  initial={{ y: "115%" }}
                  animate={{ y: phase >= 1 ? "0%" : "115%" }}
                  transition={{ duration: 0.6, delay: phase >= 1 ? 0.25 + i * 0.07 : 0, ease: [0.22, 1, 0.36, 1] }}
                >
                  {letter}
                </motion.span>
              </span>
            ))}
          </span>
        </motion.span>
      </motion.div>

      <span className="splash-caption">
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: phase >= 1 && phase < 3 ? 0.7 : 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          KISANMITRA AI · SMART FARMING
        </motion.span>
      </span>
    </motion.div>
  );
}
