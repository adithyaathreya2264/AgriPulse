import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { API_URL, SpeakButton, VoiceMic } from "../voice";
import { notify } from "../ui/notify";
import { Button, CountUp, EmptyState, Input, PageHeader, Pill, Rise, Select, Skeleton, Stagger } from "../ui/kit";
import {
  ArrowRight,
  Bell,
  Calendar,
  Check,
  MapPin,
  Search,
  Sparkles,
  TrendingUp,
  Wheat,
  X,
  Zap,
} from "../ui/icons";
import { serverText, useT } from "../i18n";

const rupees = (value) => `₹${Number(value || 0).toLocaleString("en-IN")}`;

// Today's price + 4 weekly forecasts with a confidence band, drawn on load
function ForecastChart({ current, forecast }) {
  const t = useT();

  if (!forecast || forecast.length === 0) return null;

  const width = 560;
  const height = 250;
  const pad = { left: 58, right: 20, top: 20, bottom: 38 };

  const points = [{ days: 0, price: current, low: current, high: current }, ...forecast];

  const prices = points.flatMap((p) => [p.low, p.high, p.price]);
  const min = Math.min(...prices) * 0.97;
  const max = Math.max(...prices) * 1.03;
  const maxDays = points[points.length - 1].days;

  const x = (days) => pad.left + (days / maxDays) * (width - pad.left - pad.right);
  const y = (price) => pad.top + (1 - (price - min) / (max - min || 1)) * (height - pad.top - pad.bottom);

  const linePath = points.map((p, i) => `${i ? "L" : "M"}${x(p.days)},${y(p.price)}`).join(" ");
  const areaPath = `${linePath} L${x(maxDays)},${height - pad.bottom} L${x(0)},${height - pad.bottom} Z`;
  const bandPath =
    points.map((p, i) => `${i ? "L" : "M"}${x(p.days)},${y(p.high)}`).join(" ") +
    " " +
    [...points].reverse().map((p) => `L${x(p.days)},${y(p.low)}`).join(" ") +
    " Z";

  const best = points.reduce((a, b) => (b.price > a.price ? b : a), points[0]);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="forecast-chart" role="img" aria-label={t("price.price_forecast_for_the_next_4")}>
      <defs>
        <linearGradient id="fc-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#0f9d58" stopOpacity=".28" />
          <stop offset="1" stopColor="#0f9d58" stopOpacity="0" />
        </linearGradient>
      </defs>

      {[0, 0.5, 1].map((tick) => {
        const price = min + (max - min) * tick;

        return (
          <g key={tick}>
            <line x1={pad.left} x2={width - pad.right} y1={y(price)} y2={y(price)} stroke="var(--line)" strokeDasharray="4 6" />

            <text x={pad.left - 8} y={y(price) + 4} textAnchor="end" fontSize="11" fill="var(--ink-3)">
              {Math.round(price)}
            </text>
          </g>
        );
      })}

      <motion.path d={bandPath} fill="#0f9d58" opacity="0.13" initial={{ opacity: 0 }} animate={{ opacity: 0.13 }} transition={{ delay: 0.9, duration: 0.8 }} />

      <motion.path d={areaPath} fill="url(#fc-area)" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8, duration: 0.9 }} />

      <motion.path
        d={linePath}
        fill="none"
        stroke="#0f9d58"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.4, ease: "easeInOut" }}
      />

      {points.map((p, i) => (
        <g key={p.days}>
          <motion.circle
            cx={x(p.days)}
            cy={y(p.price)}
            r={p === best ? 6.5 : 4.5}
            fill={p === best ? "#f5b83d" : "#0f9d58"}
            stroke="var(--surface)"
            strokeWidth="2.5"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.3 + i * 0.28, type: "spring", stiffness: 400, damping: 16 }}
            style={{ transformOrigin: `${x(p.days)}px ${y(p.price)}px` }}
          />

          <text x={x(p.days)} y={height - 14} textAnchor="middle" fontSize="11.5" fill="var(--ink-3)">
            {p.days === 0 ? t("price.today") : t("price.days_short", { n: p.days })}
          </text>
        </g>
      ))}
    </svg>
  );
}

const trendTone = (text = "") =>
  /up|rise|increas|bull/i.test(text) ? "good" : /down|fall|decreas|bear/i.test(text) ? "bad" : "info";

function MarketList({ title, tone, markets, onPick }) {
  const t = useT();

  if (markets.length === 0) return null;

  return (
    <div className="market-group">
      <h4 className={`market-heading heading-${tone}`}>
        <span className="dot" /> {title}
      </h4>

      <div className="market-list">
        {markets.map((item, index) => (
          <motion.button
            type="button"
            key={`${item.district}-${item.market}-${index}`}
            className="market-card"
            onClick={() => onPick(item)}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(index, 12) * 0.035 }}
            whileHover={{ y: -3 }}
            whileTap={{ scale: 0.98 }}
          >
            <span className="market-name">{item.market}</span>

            <span className="market-district">
              <MapPin size={12} /> {item.district}
            </span>

            <span className="market-price">
              {rupees(item.current_price_available ? item.current_price : item.latest_price)}
              <small>{" "}{t("price.quintal")}</small>
            </span>

            <span className="market-date">{item.current_price_available ? item.date : item.latest_price_date}</span>
          </motion.button>
        ))}
      </div>
    </div>
  );
}

export default function PricePage({ token, lang, t, jsonHeaders, sessionExpired, goLogin, intent }) {
  const [crop, setCrop] = useState("");
  const [market, setMarket] = useState("");
  const [district, setDistrict] = useState("");
  const [marketOptions, setMarketOptions] = useState([]);
  const [marketSearch, setMarketSearch] = useState("");
  const [priceResult, setPriceResult] = useState(null);
  const [searching, setSearching] = useState(false);
  const [predicting, setPredicting] = useState(false);
  const [searched, setSearched] = useState(false);
  const [alertKind, setAlertKind] = useState("best_time");
  const [notifications, setNotifications] = useState([]);
  const handledIntent = useRef(null);

  const searchMarkets = async (cropOverride) => {
    const cropName = typeof cropOverride === "string" ? cropOverride : crop;

    if (!cropName.trim()) {
      setPriceResult({ error: t("price.err_crop") });
      return;
    }

    setSearching(true);
    setSearched(true);

    try {
      const response = await fetch(`${API_URL}/predict-price?crop=${encodeURIComponent(cropName)}&lang=${lang}`);
      const data = await response.json();

      if (data.error) {
        setMarketOptions([]);
        setPriceResult(data);
        return;
      }

      setMarketOptions(data.markets || []);
      setMarketSearch("");
      setMarket("");
      setDistrict("");
      setPriceResult(null);
    } catch (error) {
      console.error(error);
      setPriceResult({ error: t("price.err_markets") });
    } finally {
      setSearching(false);
    }
  };

  // "Show the price of tomato" said out loud
  useEffect(() => {
    if (intent && intent.action === "price" && intent.params && intent.params.crop && handledIntent.current !== intent.id) {
      handledIntent.current = intent.id;
      setCrop(intent.params.crop);
      searchMarkets(intent.params.crop);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intent]);

  const fetchNotifications = async () => {
    if (!token) return;

    try {
      const res = await fetch(`${API_URL}/notifications`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) setNotifications(await res.json());
    } catch (error) {
      console.warn("Notifications unavailable:", error.message);
    }
  };

  useEffect(() => {
    fetchNotifications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const predictPrice = async () => {
    setPredicting(true);

    try {
      const response = await fetch(
        `${API_URL}/predict-price?crop=${encodeURIComponent(crop)}&district=${encodeURIComponent(district)}&market=${encodeURIComponent(market)}&lang=${lang}`
      );

      setPriceResult(await response.json());
    } catch (error) {
      setPriceResult({ error: t("price.err_prediction") });
    } finally {
      setPredicting(false);
    }
  };

  const createPriceAlert = async () => {
    if (!token) {
      notify(t("price.please_login_to_get_price_alerts"), "error");
      goLogin();
      return;
    }

    try {
      const res = await fetch(`${API_URL}/alerts`, {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify({
          crop: priceResult.crop,
          district: priceResult.district,
          market: priceResult.market,
          kind: alertKind,
          threshold_percent: 5,
          whatsapp: true,
        }),
      });

      if (res.status === 401) {
        sessionExpired();
        return;
      }

      if (!res.ok) {
        notify(t("price.could_not_create_the_alert"), "error");
        return;
      }

      notify(t("price.alert_created_we_will_notify_you"), "success");
      fetchNotifications();
    } catch (error) {
      console.error(error);
      notify(t("common.could_not_reach_the_server"), "error");
    }
  };

  const pick = (item) => {
    setMarket(item.market);
    setDistrict(item.district);
    setMarketOptions([]);
    setMarketSearch("");
  };

  const matching = marketOptions.filter((item) =>
    `${item.district} ${item.market}`.toLowerCase().includes(marketSearch.toLowerCase())
  );

  const today = matching.filter((item) => item.current_price_available);
  const latest = matching.filter((item) => !item.current_price_available);

  const step = priceResult && !priceResult.error ? 3 : market ? 2 : marketOptions.length > 0 ? 2 : 1;
  const best = priceResult && priceResult.best_time_to_sell;

  return (
    <div className="page">
      <PageHeader
        icon={TrendingUp}
        tone="gold"
        title={t("title_price")}
        subtitle={t("price.pick_a_crop_and_a_mandi")}
      />

      <ol className="mini-steps">
        {["price.step_crop", "price.step_market", "price.step_forecast"].map((name, index) => (
          <li key={name} className={step > index + 1 ? "ms-done" : step === index + 1 ? "ms-on" : ""}>
            <span>{step > index + 1 ? <Check size={13} /> : index + 1}</span>
            {t(name)}
          </li>
        ))}
      </ol>

      {/* ------------------------------------------------------------ search */}
      <div className="card search-card">
        <div className="search-row">
          <Input
            id="price-crop"
            className="grow"
            icon={Wheat}
            placeholder={t("ph_search_crop")}
            aria-label={t("common.crop")}
            value={crop}
            onChange={(e) => {
              setCrop(e.target.value);
              setMarket("");
              setDistrict("");
              setMarketOptions([]);
              setPriceResult(null);
              setSearched(false);
            }}
            onKeyDown={(e) => e.key === "Enter" && searchMarkets()}
          />

          <VoiceMic lang={lang} t={t} onText={(text) => setCrop(text)} />

          <Button loading={searching} icon={Search} onClick={() => searchMarkets()}>
            {t("btn_search")}
          </Button>
        </div>

        <div className="chip-row quick-crops">
          {["Rice", "Wheat", "Maize", "Cotton", "Groundnut", "Bajra", "Jowar", "Bengal gram"].map((name) => (
            <button
              key={name}
              type="button"
              className="chip"
              onClick={() => {
                setCrop(name);
                searchMarkets(name);
              }}
            >
              {t("price.crop_" + name.toLowerCase().replace(" ", "_"))}
            </button>
          ))}
        </div>
      </div>

      {/* ----------------------------------------------------- market picker */}
      {searching && (
        <div className="market-list market-loading">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} height={110} radius={18} />
          ))}
        </div>
      )}

      {!searching && marketOptions.length > 0 && (
        <div className="card">
          <Input
            id="market-filter"
            icon={Search}
            placeholder={t("price.search_district_or_market_2")}
            aria-label={t("price.search_district_or_market")}
            value={marketSearch}
            onChange={(e) => setMarketSearch(e.target.value)}
          />

          <MarketList title={t("price.today_s_price_available")} tone="good" markets={today} onPick={pick} />
          <MarketList title={t("price.latest_available_price")} tone="warn" markets={latest} onPick={pick} />

          {matching.length === 0 && <p className="note center-note">{t("price.no_market_matches", { query: marketSearch })}</p>}
        </div>
      )}

      {!searching && searched && marketOptions.length === 0 && !market && !priceResult && (
        <EmptyState icon={Search} title={t("price.no_markets_found")} text={t("price.check_the_spelling_of_the_crop")} />
      )}

      {/* ----------------------------------------------------- selected market */}
      <AnimatePresence>
        {market && (
          <motion.div
            className="card selected-market"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <span className="mini-icon tone-gold-soft">
              <MapPin size={20} />
            </span>

            <div className="selected-text">
              <small>{t("price.selected_market")}</small>
              <strong>{market}</strong>
              <span>{district}</span>
            </div>

            <Button size="lg" loading={predicting} disabled={!crop || !market || !district} iconRight={ArrowRight} onClick={predictPrice}>
              {t("price.get_price_prediction")}
            </Button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* --------------------------------------------------------------- error */}
      {priceResult && priceResult.error && (
        <motion.div className="card error-card" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <X size={20} />
          <p>{serverText(t, priceResult.error)}</p>
        </motion.div>
      )}

      {/* -------------------------------------------------------------- result */}
      {priceResult && !priceResult.error && (
        <Stagger className="stack price-result">
          <Rise className="price-hero">
            <div>
              <p className="ph-crop">
                <Wheat size={16} /> {priceResult.crop}
              </p>

              <p className="ph-place">
                {priceResult.market}, {priceResult.district}
              </p>

              {priceResult.current_price_available ? (
                <>
                  <p className="ph-price">
                    <CountUp value={priceResult.current_price} prefix="₹" />
                    <small>{" "}{t("price.quintal")}</small>
                  </p>

                  <p className="ph-date">
                    <Calendar size={14} /> {priceResult.date}
                  </p>
                </>
              ) : (
                <>
                  <p className="ph-price">
                    <CountUp value={priceResult.latest_price} prefix="₹" />
                    <small>{" "}{t("price.quintal")}</small>
                  </p>

                  <p className="ph-date">
                    <Calendar size={14} /> {t("price.weekly_price_note", { date: priceResult.latest_price_date })}
                  </p>
                </>
              )}
            </div>

            <div className="ph-side">
              {priceResult.current_price_available && (
                <div className="ph-range">
                  <span>
                    <small>{t("price.min")}</small>
                    <strong>{rupees(priceResult.min_price)}</strong>
                  </span>

                  <span>
                    <small>{t("price.max")}</small>
                    <strong>{rupees(priceResult.max_price)}</strong>
                  </span>
                </div>
              )}

              <div className="ph-predicted">
                <small>{t("price.predicted_period", { period: priceResult.prediction_period })}</small>
                <strong>{rupees(priceResult.predicted_price)}</strong>
                <Pill tone={trendTone(priceResult.trend)} icon={TrendingUp}>
                  {priceResult.trend}
                </Pill>
              </div>
            </div>
          </Rise>

          {priceResult.forecast && (
            <Rise className="card">
              <h3 className="card-title">
                <Sparkles size={20} />{" "}{t("price.4_week_price_forecast")}{" "}<small className="unit">{t("price.per_quintal")}</small>
              </h3>

              <ForecastChart current={priceResult.current_price ?? priceResult.latest_price} forecast={priceResult.forecast} />

              {best && (
                <div className={`best-time ${best.action === "wait" ? "best-wait" : "best-sell"}`}>
                  <span className="best-icon">
                    <Zap size={20} />
                  </span>

                  <p>{best.message}</p>

                  <SpeakButton lang={lang} t={t} text={`${priceResult.recommendation} ${best.message}`} />
                </div>
              )}

              {priceResult.model_metrics && priceResult.model_metrics.mae !== undefined && (
                <p className="note model-line">
                  {t("price.model_line_short", {
                    model: priceResult.model_metrics.model,
                    error: priceResult.model_metrics.mae,
                  })}
                  {priceResult.model_metrics.beats_baseline ? " " + t("price.better_than_no_change") : ""}
                </p>
              )}

              <div className="alert-row">
                <Select
                  id="alert-kind"
                  aria-label={t("price.alert_type")}
                  value={alertKind}
                  onChange={(e) => setAlertKind(e.target.value)}
                  options={[
                    ["best_time", t("price.alert_best_time")],
                    ["rise", t("price.alert_rise")],
                    ["fall", t("price.alert_fall")],
                  ]}
                />

                <Button variant="gold" icon={Bell} onClick={createPriceAlert}>
                  {t("price.alert_me")}
                </Button>
              </div>
            </Rise>
          )}

          {priceResult.recommendation && (
            <Rise className="callout callout-tip">
              <strong>{t("price.advice")}</strong>
              <p>{priceResult.recommendation}</p>
            </Rise>
          )}
        </Stagger>
      )}

      {/* ------------------------------------------------------- notifications */}
      {notifications.length > 0 && (
        <div className="card">
          <h3 className="card-title">
            <Bell size={20} />{" "}{t("price.your_price_notifications")}
          </h3>

          <ul className="timeline">
            {notifications.slice(0, 5).map((item) => (
              <li key={item.id}>
                <span className="tl-dot" />
                <small>{item.created_at.slice(0, 10)}</small>
                <p>{item.message}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
