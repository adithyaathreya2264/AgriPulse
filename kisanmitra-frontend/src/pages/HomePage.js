import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { API_URL } from "../voice";
import { WeatherArt, WheatField } from "../ui/art";
import { Button, CountUp, Pill, Reveal, Skeleton, Stagger, Rise } from "../ui/kit";
import {
  ArrowRight,
  Bot,
  CloudSun,
  Droplets,
  Landmark,
  MapPin,
  Mic,
  ScanLine,
  Tractor,
  TrendingUp,
  Wheat,
} from "../ui/icons";
import { categoryIcon } from "./marketplaceParts";

const ACTIONS = [
  ["disease", ScanLine, "nav_disease", "Photograph a leaf, get the disease and the medicine.", "grad-green"],
  ["price", TrendingUp, "nav_price", "Four-week mandi forecast and the best week to sell.", "grad-gold"],
  ["weather", CloudSun, "nav_weather", "Weather and what it means for your crop today.", "grad-sky"],
  ["marketplace", Tractor, "nav_marketplace", "Rent tractors and drones from owners nearby.", "grad-earth"],
  ["loan", Landmark, "nav_loan", "Kisan Credit Card eligibility in three minutes.", "grad-plum"],
  ["assistant", Bot, "nav_assistant", "Ask anything about your farm, in your language.", "grad-forest"],
];

const STAT_ITEMS = [
  ["total_predictions", "Leaf scans", ScanLine],
  ["total_equipment", "Machines listed", Tractor],
  ["total_rentals", "Rentals booked", Wheat],
  ["total_users", "Farmers", MapPin],
];

const greetingFor = () => {
  const hour = new Date().getHours();

  return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
};

export default function HomePage({ user, lang, t, go }) {
  const [stats, setStats] = useState(null);
  const [equipment, setEquipment] = useState(null);
  const [weather, setWeather] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const load = async (path, setter) => {
      try {
        const res = await fetch(`${API_URL}${path}`);

        if (res.ok && !cancelled) setter(await res.json());
      } catch (error) {
        console.warn("Backend not reachable:", error.message);
      }
    };

    load("/dashboard-stats", setStats);
    load("/equipment", (data) => setEquipment(Array.isArray(data) ? data : []));

    if (user && user.district) {
      load(
        `/weather?city=${encodeURIComponent(user.district)}&lang=${lang}`,
        (data) => !data.error && setWeather(data)
      );
    }

    return () => {
      cancelled = true;
    };
  }, [user, lang]);

  const firstName = (user.name || "").trim().split(/\s+/)[0] || "friend";

  const featured = (equipment || [])
    .slice()
    .sort((a, b) => Number(b.availability === "Available") - Number(a.availability === "Available"))
    .slice(0, 8);

  return (
    <div className="home">
      {/* -------------------------------------------------------------- hero */}
      <section className="hero">
        <div className="hero-art">
          <WheatField stalks={32} />
        </div>

        <div className="hero-body">
          <motion.p
            className="hero-kicker"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            {greetingFor()}
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 22 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
          >
            Namaste, <span className="hero-name">{firstName}</span>
          </motion.h1>

          <motion.p
            className="hero-text"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.6 }}
          >
            {user.district
              ? `Here is what is worth your attention in ${user.district} today.`
              : "Here is what is worth your attention today."}
          </motion.p>

          <motion.div
            className="hero-actions"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.6 }}
          >
            <Button variant="gold" size="lg" icon={ScanLine} onClick={() => go("disease")}>
              Scan a leaf
            </Button>

            <Button variant="light" size="lg" icon={Bot} onClick={() => go("assistant")}>
              Ask the AI
            </Button>
          </motion.div>

          <p className="hero-voice">
            <Mic size={15} /> Tip: tap the microphone and just say what you need, in your language.
          </p>
        </div>

        <motion.aside
          className="hero-weather"
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ delay: 0.45, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          onClick={() => go("weather")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && go("weather")}
          aria-label="Open weather"
        >
          {weather ? (
            <>
              <WeatherArt condition={weather.condition} size={104} />

              <div>
                <p className="hw-place">
                  <MapPin size={14} /> {weather.city}
                </p>

                <p className="hw-temp">
                  <CountUp value={weather.temperature} decimals={0} />°
                </p>

                <p className="hw-cond">{weather.condition}</p>

                <p className="hw-meta">
                  <Droplets size={13} /> {weather.humidity}% humidity
                </p>
              </div>
            </>
          ) : (
            <div className="hw-empty">
              <CloudSun size={34} />

              <p>{user.district ? "Weather loading..." : "Add your district to see local weather"}</p>
            </div>
          )}
        </motion.aside>
      </section>

      {/* ---------------------------------------------------- quick actions */}
      <section className="section">
        <div className="section-head">
          <h2>What would you like to do?</h2>
        </div>

        <Stagger className="action-grid">
          {ACTIONS.map(([id, Icon, key, text, grad]) => (
            <Rise key={id}>
              <motion.button
                type="button"
                className={`action ${grad}`}
                onClick={() => go(id)}
                whileHover={{ y: -6 }}
                whileTap={{ scale: 0.98 }}
              >
                <span className="action-icon">
                  <Icon size={26} />
                </span>

                <span className="action-title">{t(key)}</span>
                <span className="action-text">{text}</span>

                <span className="action-go">
                  <ArrowRight size={18} />
                </span>

                <Icon size={130} className="action-watermark" />
              </motion.button>
            </Rise>
          ))}
        </Stagger>
      </section>

      {/* ------------------------------------------------------------ stats */}
      <section className="section">
        <div className="stat-grid">
          {STAT_ITEMS.map(([key, label, Icon], i) => (
            <Reveal key={key} delay={i * 0.08} className="card stat">
              <span className="stat-icon">
                <Icon size={20} />
              </span>

              <strong className="stat-number">
                {stats ? <CountUp value={stats[key] || 0} /> : <Skeleton width={70} height={32} />}
              </strong>

              <span className="stat-label">{label}</span>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------------------------------------------------- featured rent */}
      <section className="section">
        <div className="section-head">
          <h2>Machines near you</h2>

          <button type="button" className="link-btn" onClick={() => go("marketplace")}>
            See all <ArrowRight size={15} />
          </button>
        </div>

        {equipment === null ? (
          <div className="rail">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} height={190} width={250} radius={22} />
            ))}
          </div>
        ) : featured.length === 0 ? (
          <div className="card rail-empty">
            <Tractor size={28} />
            <p>No equipment is listed yet. Be the first to list a machine.</p>

            <Button size="sm" variant="soft" onClick={() => go("marketplace")}>
              Open marketplace
            </Button>
          </div>
        ) : (
          <div className="rail">
            {featured.map((item, i) => {
              const Icon = categoryIcon(item.category);

              return (
                <Reveal key={item.id} delay={i * 0.05} className="rail-card card card-hover" onClick={() => go("marketplace")}>
                  <span className={`rail-icon cat-${String(item.category || "Other").replace(/\s+/g, "-").toLowerCase()}`}>
                    <Icon size={26} />
                  </span>

                  <h3>{item.equipment_name}</h3>

                  <p className="rail-place">
                    <MapPin size={13} /> {item.location}
                  </p>

                  <div className="rail-foot">
                    <strong>₹{item.price_per_day}</strong>
                    <small>/ day</small>

                    <Pill tone={item.availability === "Available" ? "good" : "warn"}>{item.availability}</Pill>
                  </div>
                </Reveal>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
