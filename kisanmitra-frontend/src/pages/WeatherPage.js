import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { API_URL, SpeakButton, VoiceMic } from "../voice";
import { serverText } from "../i18n";
import { WeatherArt } from "../ui/art";
import { Button, CountUp, Input, PageHeader, Rise, Skeleton, Stagger } from "../ui/kit";
import { CloudSun, Droplets, MapPin, Search, Sprout, Thermometer } from "../ui/icons";

const skyFor = (condition = "") => {
  const text = condition.toLowerCase();

  if (/thunder|storm/.test(text)) return "sky-storm";
  if (/rain|drizzle|shower/.test(text)) return "sky-rain";
  if (/cloud|overcast|mist|fog|haze/.test(text)) return "sky-cloud";

  return "sky-sun";
};

export default function WeatherPage({ user, lang, t, intent }) {
  const [city, setCity] = useState(user?.district || "");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const handledIntent = useRef(null);
  const auto = useRef(false);

  const getWeather = async (cityOverride) => {
    const cityName = typeof cityOverride === "string" ? cityOverride : city;

    if (!cityName.trim()) return;

    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/weather?city=${encodeURIComponent(cityName)}&lang=${lang}`);

      setResult(await res.json());
    } catch (error) {
      console.error(error);
      setResult({ error: t("weather.unreachable") });
    } finally {
      setLoading(false);
    }
  };

  // Show the farmer's own district the first time this page opens
  useEffect(() => {
    if (!auto.current && city.trim()) {
      auto.current = true;
      getWeather(city);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (intent && intent.action === "weather" && intent.params && intent.params.city && handledIntent.current !== intent.id) {
      handledIntent.current = intent.id;
      setCity(intent.params.city);
      getWeather(intent.params.city);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intent]);

  const ok = result && !result.error;

  return (
    <div className="page">
      <PageHeader
        icon={CloudSun}
        tone="sky"
        title={t("title_weather")}
        subtitle={t("weather.today_s_weather_and_what_it")}
      />

      <div className="card search-card">
        <div className="search-row">
          <Input
            id="weather-city"
            className="grow"
            icon={MapPin}
            placeholder={t("ph_city")}
            aria-label={t("weather.city")}
            value={city}
            onChange={(e) => setCity(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && getWeather()}
          />

          <VoiceMic lang={lang} t={t} onText={(text) => setCity(text)} />

          <Button loading={loading} icon={Search} onClick={() => getWeather()}>
            {t("btn_get_weather")}
          </Button>
        </div>
      </div>

      {loading && !ok && <Skeleton height={260} radius={28} />}

      <AnimatePresence mode="wait">
        {ok && (
          <motion.div key={result.city} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Stagger className="stack">
              <Rise className={`wx-hero ${skyFor(result.sky || result.condition)}`}>
                <div className="wx-hero-text">
                  <p className="wx-city">
                    <MapPin size={16} /> {result.city}
                  </p>

                  <p className="wx-temp">
                    <CountUp value={result.temperature} />
                    <sup>°C</sup>
                  </p>

                  <p className="wx-cond">{result.condition}</p>
                </div>

                <div className="wx-hero-art">
                  <WeatherArt condition={result.sky || result.condition} size={190} />
                </div>
              </Rise>

              <Rise className="duo">
                <div className="card mini-card">
                  <span className="mini-icon tone-red">
                    <Thermometer size={20} />
                  </span>

                  <h4>{t("weather.temperature")}</h4>

                  <p className="mini-big">{Math.round(Number(result.temperature))}°C</p>
                </div>

                <div className="card mini-card">
                  <span className="mini-icon tone-blue">
                    <Droplets size={20} />
                  </span>

                  <h4>{t("weather.humidity")}</h4>

                  <p className="mini-big">{result.humidity}%</p>

                  <div className="meter" aria-hidden="true">
                    <motion.span
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(Number(result.humidity) || 0, 100)}%` }}
                      transition={{ duration: 1.1, ease: "easeOut", delay: 0.3 }}
                    />
                  </div>
                </div>
              </Rise>

              <Rise className="card advice-card">
                <h3 className="card-title">
                  <Sprout size={20} />{" "}{t("weather.farming_advice")}
                </h3>

                <p className="advice-text">{result.advice}</p>

                <SpeakButton lang={lang} t={t} text={`${result.condition}. ${result.advice}`} />
              </Rise>
            </Stagger>
          </motion.div>
        )}
      </AnimatePresence>

      {result && result.error && (
        <div className="card error-card">
          <CloudSun size={22} />
          <p>{serverText(t, result.error)}</p>
        </div>
      )}

      {!result && !loading && (
        <div className="card center-note">
          <CloudSun size={30} />
          <p className="muted">{t("weather.enter_a_city_or_district_to")}</p>
        </div>
      )}
    </div>
  );
}
