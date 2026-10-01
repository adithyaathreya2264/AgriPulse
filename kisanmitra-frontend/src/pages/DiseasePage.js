import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { API_URL, SpeakButton } from "../voice";
import { notify } from "../ui/notify";
import { ScannerOverlay } from "../ui/art";
import { Button, CountUp, Input, PageHeader, Pill, Rise, Stagger } from "../ui/kit";
import {
  AlertTriangle,
  Bot,
  Camera,
  CheckCircle2,
  CloudSun,
  Droplets,
  IndianRupee,
  Leaf,
  MapPin,
  Pill as PillIcon,
  RefreshCw,
  ScanLine,
  ShieldCheck,
  Thermometer,
  UploadCloud,
  X,
} from "../ui/icons";
import { serverText, useT } from "../i18n";

function ConfidenceRing({ value }) {
  const t = useT();

  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(Math.max(Number(value) || 0, 0), 100);
  const color = pct >= 85 ? "#0f9d58" : pct >= 60 ? "#e8a10b" : "#e0454b";

  return (
    <div className="ring-wrap">
      <svg viewBox="0 0 110 110" className="ring" role="img" aria-label={t("disease.confidence_aria", { pct })}>
        <circle cx="55" cy="55" r={radius} fill="none" stroke="var(--surface-3)" strokeWidth="10" />

        <motion.circle
          cx="55"
          cy="55"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference * (1 - pct / 100) }}
          transition={{ duration: 1.3, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
          transform="rotate(-90 55 55)"
        />
      </svg>

      <div className="ring-text">
        <strong>
          <CountUp value={pct} decimals={pct % 1 ? 1 : 0} suffix="%" />
        </strong>
        <small>{t("disease.confident")}</small>
      </div>
    </div>
  );
}

const SEVERITY_TONE = (text) =>
  /high|severe|serious/i.test(text) ? "bad" : /moderate|medium/i.test(text) ? "warn" : "good";

export default function DiseasePage({ user, lang, t, onDiagnosed, go }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [city, setCity] = useState(user?.district || "");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [dragging, setDragging] = useState(false);
  const pickerRef = useRef(null);
  const cameraRef = useRef(null);

  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview]
  );

  const choose = (picked) => {
    if (!picked) return;

    if (!picked.type.startsWith("image/")) {
      notify(t("disease.please_choose_a_photo_jpg_or"), "error");
      return;
    }

    setFile(picked);
    setPreview(URL.createObjectURL(picked));
    setResult(null);
  };

  const clear = () => {
    setFile(null);
    setPreview("");
    setResult(null);
  };

  const handleUpload = async () => {
    if (!file) {
      notify(t("disease.please_select_an_image"), "error");
      return;
    }

    if (!city.trim()) {
      notify(t("disease.please_enter_your_city"), "error");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("city", city);
    formData.append("lang", lang);

    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/detect-disease`, { method: "POST", body: formData });
      const data = await res.json();

      if (!data.report) {
        notify(serverText(t, typeof data.detail === "string" ? data.detail : data.error) || t("disease.read_failed"), "error");
        return;
      }

      setResult(data);
      onDiagnosed && onDiagnosed(data);
    } catch (err) {
      console.error(err);
      notify(t("disease.upload_failed_please_check_your_connec"), "error");
    } finally {
      setLoading(false);
    }
  };

  const report = result && result.report;
  const analysis = report && typeof report.analysis === "object" ? report.analysis : null;
  const uncertain = report && /uncertain|unknown|not sure/i.test(String(report.disease));

  return (
    <div className="page">
      <PageHeader
        icon={ScanLine}
        title={t("nav_disease")}
        subtitle={t("disease.take_a_clear_photo_of_one")}
      />

      <div className={`split ${report ? "split-result" : ""}`}>
        {/* ------------------------------------------------------- upload */}
        <div className="card upload-card">
          <div
            className={`dropzone ${dragging ? "drag" : ""} ${preview ? "has-image" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              choose(e.dataTransfer.files && e.dataTransfer.files[0]);
            }}
          >
            <AnimatePresence mode="wait">
              {preview ? (
                <motion.div
                  key="preview"
                  className="preview"
                  initial={{ opacity: 0, scale: 0.94 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <img src={preview} alt={t("disease.selected_leaf")} />
                  {loading && <ScannerOverlay />}

                  {!loading && (
                    <button type="button" className="preview-clear" onClick={clear} aria-label={t("disease.remove_photo")}>
                      <X size={16} />
                    </button>
                  )}
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  className="drop-empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <span className="drop-icon">
                    <UploadCloud size={34} />
                  </span>

                  <h3>{t("disease.drop_a_leaf_photo_here")}</h3>
                  <p>{t("disease.or_pick_one_from_your_phone")}</p>

                  <div className="drop-buttons">
                    <Button icon={Camera} onClick={() => cameraRef.current && cameraRef.current.click()}>
                      {t("disease.take_photo")}
                    </Button>

                    <Button variant="ghost" icon={UploadCloud} onClick={() => pickerRef.current && pickerRef.current.click()}>
                      {t("disease.choose_file")}
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <input
              ref={pickerRef}
              type="file"
              accept="image/*"
              hidden
              aria-label={t("disease.choose_a_leaf_photo")}
              onChange={(e) => choose(e.target.files[0])}
            />

            <input
              ref={cameraRef}
              type="file"
              accept="image/*"
              capture="environment"
              hidden
              aria-label={t("disease.take_a_leaf_photo")}
              onChange={(e) => choose(e.target.files[0])}
            />
          </div>

          <Input
            id="disease-city"
            label={t("disease.your_city_or_district")}
            icon={MapPin}
            placeholder={t("disease.enter_your_city")}
            hint={t("disease.we_use_today_s_weather_to")}
            value={city}
            onChange={(e) => setCity(e.target.value)}
          />

          <Button size="lg" block loading={loading} icon={ScanLine} onClick={handleUpload} disabled={!file}>
            {loading ? t("disease.scanning") : t("disease.diagnose")}
          </Button>

          <ul className="tips">
            <li>
              <CheckCircle2 size={15} />{" "}{t("disease.one_leaf_filling_most_of_the")}
            </li>
            <li>
              <CheckCircle2 size={15} />{" "}{t("disease.daylight_no_flash_sharp_focus")}
            </li>
            <li>
              <CheckCircle2 size={15} />{" "}{t("disease.show_both_healthy_and_damaged_parts")}
            </li>
          </ul>
        </div>

        {/* ------------------------------------------------------- result */}
        <AnimatePresence>
          {report && (
            <motion.div
              key="report"
              className="result-col"
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
              <Stagger className="stack">
                <Rise className={`card diagnosis ${uncertain ? "diagnosis-warn" : ""}`}>
                  <ConfidenceRing value={report.confidence} />

                  <div className="diagnosis-text">
                    <Pill tone={uncertain ? "warn" : "good"} icon={uncertain ? AlertTriangle : Leaf}>
                      {uncertain ? t("disease.not_sure") : t("disease.diagnosis")}
                    </Pill>

                    <h2>{report.disease}</h2>

                    {uncertain && (
                      <p className="note">
                        {t("disease.the_photo_was_not_clear_enough")}
                      </p>
                    )}

                    <div className="diagnosis-actions">
                      <SpeakButton
                        lang={lang}
                        t={t}
                        text={`${report.disease}. ${report.medicine || ""}. ${analysis ? analysis.recommendation || "" : ""}`}
                      />

                      <Button size="sm" variant="soft" icon={Bot} onClick={() => go("assistant")}>
                        {t("disease.ask_the_ai_about_this")}
                      </Button>
                    </div>
                  </div>
                </Rise>

                {report.weather && (
                  <Rise className="chip-row">
                    <span className="info-chip">
                      <MapPin size={15} /> {report.weather.city}
                    </span>

                    <span className="info-chip">
                      <Thermometer size={15} /> {report.weather.temperature}°C
                    </span>

                    <span className="info-chip">
                      <Droplets size={15} /> {report.weather.humidity}%
                    </span>

                    <span className="info-chip">
                      <CloudSun size={15} /> {report.weather.condition}
                    </span>
                  </Rise>
                )}

                <Rise className="duo">
                  <div className="card mini-card">
                    <span className="mini-icon tone-green">
                      <PillIcon size={20} />
                    </span>

                    <h4>{t("disease.medicine")}</h4>
                    <p>{report.medicine}</p>
                  </div>

                  <div className="card mini-card">
                    <span className="mini-icon tone-gold-soft">
                      <IndianRupee size={20} />
                    </span>

                    <h4>{t("disease.estimated_cost")}</h4>
                    <p>{report.estimated_cost}</p>
                  </div>
                </Rise>

                <Rise className="card">
                  <h3 className="card-title">
                    <ShieldCheck size={20} />{" "}{t("disease.ai_recommendation")}
                  </h3>

                  {analysis ? (
                    <div className="analysis">
                      <dl>
                        <div>
                          <dt>{t("disease.cause")}</dt>
                          <dd>{analysis.cause}</dd>
                        </div>

                        <div>
                          <dt>{t("disease.severity")}</dt>
                          <dd>
                            <Pill tone={SEVERITY_TONE(String(analysis.severity))}>{analysis.severity}</Pill>
                          </dd>
                        </div>

                        <div>
                          <dt>{t("disease.weather_risk")}</dt>
                          <dd>{analysis.weather_risk}</dd>
                        </div>

                        <div>
                          <dt>{t("disease.how_to_use_the_medicine")}</dt>
                          <dd>{analysis.medicine_usage}</dd>
                        </div>
                      </dl>

                      <div className="callout">
                        <strong>{t("disease.recommendation")}</strong>
                        <p>{analysis.recommendation}</p>
                      </div>

                      {analysis.precautions && analysis.precautions.length > 0 && (
                        <>
                          <h4 className="sub-title">{t("disease.precautions")}</h4>

                          <ul className="checklist">
                            {analysis.precautions.map((item, index) => (
                              <motion.li
                                key={index}
                                initial={{ opacity: 0, x: -12 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.5 + index * 0.08 }}
                              >
                                <CheckCircle2 size={17} />
                                <span>{item}</span>
                              </motion.li>
                            ))}
                          </ul>
                        </>
                      )}
                    </div>
                  ) : (
                    <p className="prewrap">{report.analysis}</p>
                  )}
                </Rise>

                <Rise>
                  <Button variant="ghost" icon={RefreshCw} onClick={clear}>
                    {t("disease.scan_another_leaf")}
                  </Button>
                </Rise>
              </Stagger>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
