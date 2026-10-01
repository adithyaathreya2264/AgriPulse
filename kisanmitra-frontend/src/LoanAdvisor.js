// Kisan Credit Card (KCC) eligibility advisor: a 4 step form and a report.
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { SpeakButton } from "./voice";
import { notify } from "./ui/notify";
import {
  Button,
  CountUp,
  Input,
  PageHeader,
  Pill,
  Rise,
  Select,
  Stagger,
} from "./ui/kit";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  CheckCircle2,
  FileText,
  Landmark,
  Navigation,
  Printer,
  Sparkles,
  Banknote,
  Wheat,
  Leaf,
  ShieldCheck,
  Plus,
  X,
  Edit3,
  ListChecks,
} from "./ui/icons";
import { serverText, useT } from "./i18n";

const DOCUMENTS = [
  ["aadhaar", "loan.doc_aadhaar"],
  ["bank_passbook", "loan.doc_bank_passbook"],
  ["photo", "loan.doc_photo"],
  ["land_record", "loan.doc_land_record"],
  ["lease_agreement", "loan.doc_lease"],
  ["soil_health_card", "loan.doc_soil_card"],
  ["pan", "loan.doc_pan"],
  ["voter_id", "loan.doc_voter"],
];

const THIS_YEAR = new Date().getFullYear();

const emptyCrop = () => ({
  crop: "",
  season: "kharif",
  year: THIS_YEAR - 1,
  area_acres: "",
  yield_quintal_per_acre: "",
});

const emptyForm = (user) => ({
  farmer_name: (user && user.name) || "",
  age: (user && user.age) || "",
  district: (user && user.district) || "",
  land: { survey_number: "", extent_acres: "", ownership: "owner", irrigated: false },
  crops: [emptyCrop()],
  planned_crops: [],
  soil: { ph: "", oc_percent: "", n_kg_ha: "", p_kg_ha: "", k_kg_ha: "", ec_dsm: "" },
  existing_loan_outstanding: "",
  has_default: false,
  documents: [],
  land_source: "self_declared",
  soil_source: "self_declared",
});

// "" -> null, "12.5" -> 12.5
const num = (value) =>
  value === "" || value === null || value === undefined ? null : Number(value);

const rupees = (value) => `₹${Number(value || 0).toLocaleString("en-IN")}`;

const VERDICT_CLASS = {
  eligible: "verdict-eligible",
  conditional: "verdict-conditional",
  not_eligible: "verdict-blocked",
};

function ScoreGauge({ score }) {
  const t = useT();

  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const value = Math.min(Math.max(score, 0), 100);
  const color = score >= 70 ? "#0f9d58" : score >= 45 ? "#e8a10b" : "#e0454b";

  return (
    <div className="gauge">
      <svg viewBox="0 0 100 100" className="score-gauge" role="img" aria-label={`Score ${score} out of 100`}>
        <circle cx="50" cy="50" r={radius} fill="none" stroke="var(--surface-3)" strokeWidth="9" />

        <motion.circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference * (1 - value / 100) }}
          transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
          transform="rotate(-90 50 50)"
        />
      </svg>

      <div className="gauge-text">
        <strong>
          <CountUp value={value} />
        </strong>
        <small>{t("loan.out_of_100")}</small>
      </div>
    </div>
  );
}

const STEPS = ["loan.step_farm", "loan.step_crops", "loan.step_soil", "loan.step_documents"];

// Server names for the parts of the score, risk levels and data sources, shown in the farmer's language
const serverName = (t, prefix, name) => {
  const key = prefix + name;
  const text = t(key);

  return text === key ? String(name).replace(/_/g, " ") : text;
};

export default function LoanAdvisor({ apiUrl, user, token, lang, t, onLogin }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(() => emptyForm(user));
  const [report, setReport] = useState(null);
  const [nearby, setNearby] = useState(null);
  const [busy, setBusy] = useState(false);
  const [demoNote, setDemoNote] = useState("");

  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  // Continue where the farmer stopped
  useEffect(() => {
    if (!token) return;

    (async () => {
      try {
        const res = await fetch(`${apiUrl}/loan/profile`, { headers });

        if (!res.ok) return;

        const saved = await res.json();
        const blank = emptyForm(user);

        const fill = (source, target) =>
          Object.fromEntries(
            Object.keys(target).map((key) => [key, source && source[key] !== null && source[key] !== undefined ? source[key] : target[key]])
          );

        setForm({
          ...blank,
          ...fill(saved, blank),
          land: fill(saved.land, blank.land),
          soil: fill(saved.soil, blank.soil),
          crops: saved.crops && saved.crops.length
            ? saved.crops.map((crop) => fill(crop, emptyCrop()))
            : blank.crops,
          planned_crops: saved.planned_crops || [],
        });
      } catch (error) {
        console.warn("Could not load the saved profile:", error.message);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (!token) {
    return (
      <div className="page">
        <PageHeader icon={Landmark} tone="gold" title={t("nav_loan")} />

        <div className="card center-note">
          <p>{t("loan.please_login_to_check_your_kisan")}</p>

          <Button onClick={onLogin}>{t("nav_login")}</Button>
        </div>
      </div>
    );
  }

  const setField = (key, value) => setForm((old) => ({ ...old, [key]: value }));
  const setLand = (key, value) =>
    setForm((old) => ({ ...old, land: { ...old.land, [key]: value } }));
  const setSoil = (key, value) =>
    setForm((old) => ({ ...old, soil: { ...old.soil, [key]: value } }));
  const setCrop = (index, key, value) =>
    setForm((old) => ({
      ...old,
      crops: old.crops.map((crop, i) => (i === index ? { ...crop, [key]: value } : crop)),
    }));

  const toggleDocument = (code) =>
    setForm((old) => ({
      ...old,
      documents: old.documents.includes(code)
        ? old.documents.filter((item) => item !== code)
        : [...old.documents, code],
    }));

  const fetchDigiLocker = async () => {
    if (!form.land.survey_number.trim()) {
      notify(t("loan.enter_your_survey_number_first"), "error");
      return;
    }

    try {
      const res = await fetch(`${apiUrl}/loan/digilocker/fetch`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          survey_number: form.land.survey_number,
          district: form.district || null,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        notify(serverText(t, data.detail) || t("loan.record_fetch_failed"), "error");
        return;
      }

      setForm((old) => ({
        ...old,
        land: {
          ...old.land,
          extent_acres: data.land.extent_acres,
          ownership: data.land.ownership,
          irrigated: data.land.irrigated,
        },
        soil: {
          ...old.soil,
          ph: data.soil.ph,
          oc_percent: data.soil.oc_percent,
          n_kg_ha: data.soil.n_kg_ha,
          p_kg_ha: data.soil.p_kg_ha,
          k_kg_ha: data.soil.k_kg_ha,
          ec_dsm: data.soil.ec_dsm,
        },
        land_source: `digilocker_${data.provider}`,
        soil_source: `digilocker_${data.provider}`,
      }));

      setDemoNote(
        data.provider === "mock"
          ? t("loan.demo_note")
          : t("loan.fetched")
      );
    } catch (error) {
      notify(t("common.could_not_reach_the_server"), "error");
    }
  };

  const buildProfile = () => {
    const hasSoil = Object.values(form.soil).some((value) => value !== "" && value !== null);

    return {
      farmer_name: form.farmer_name || null,
      age: num(form.age),
      district: form.district,
      land: {
        survey_number: form.land.survey_number,
        extent_acres: num(form.land.extent_acres) || 0,
        ownership: form.land.ownership,
        irrigated: form.land.irrigated,
      },
      crops: form.crops
        .filter((crop) => crop.crop.trim() && num(crop.area_acres) > 0)
        .map((crop) => ({
          crop: crop.crop,
          season: crop.season,
          year: Number(crop.year),
          area_acres: num(crop.area_acres),
          yield_quintal_per_acre: num(crop.yield_quintal_per_acre),
        })),
      planned_crops: form.planned_crops
        .filter((crop) => crop.crop.trim() && num(crop.area_acres) > 0)
        .map((crop) => ({ crop: crop.crop, area_acres: num(crop.area_acres) })),
      soil: hasSoil
        ? {
            ph: num(form.soil.ph),
            oc_percent: num(form.soil.oc_percent),
            n_kg_ha: num(form.soil.n_kg_ha),
            p_kg_ha: num(form.soil.p_kg_ha),
            k_kg_ha: num(form.soil.k_kg_ha),
            ec_dsm: num(form.soil.ec_dsm),
          }
        : null,
      existing_loan_outstanding: num(form.existing_loan_outstanding) || 0,
      has_default: form.has_default,
      documents: form.documents,
      land_source: form.land_source,
      soil_source: form.soil_source,
    };
  };

  const checkEligibility = async () => {
    if (!form.district.trim()) {
      notify(t("loan.please_enter_your_district"), "error");
      setStep(1);
      return;
    }

    setBusy(true);
    setNearby(null);

    try {
      const saved = await fetch(`${apiUrl}/loan/profile`, {
        method: "POST",
        headers,
        body: JSON.stringify(buildProfile()),
      });

      if (!saved.ok) {
        const error = await saved.json();
        notify(
          typeof error.detail === "string"
            ? serverText(t, error.detail)
            : "Please check the details you entered",
          "error"
        );
        return;
      }

      const res = await fetch(`${apiUrl}/loan/report`, {
        method: "POST",
        headers,
        body: JSON.stringify({ lang }),
      });

      const data = await res.json();

      if (!res.ok) {
        notify(serverText(t, data.detail) || t("loan.report_failed"), "error");
        return;
      }

      setReport(data.report);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      console.error(error);
      notify(t("common.could_not_reach_the_server"), "error");
    } finally {
      setBusy(false);
    }
  };

  const findNearby = () => {
    if (!navigator.geolocation) {
      notify(t("common.location_is_not_supported_by_this"), "error");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const res = await fetch(
            `${apiUrl}/loan/nearby?lat=${position.coords.latitude}&lng=${position.coords.longitude}&radius_km=60&limit=6`
          );

          setNearby(await res.json());
        } catch (error) {
          notify(t("common.could_not_reach_the_server"), "error");
        }
      },
      () => notify(t("common.could_not_get_your_location_please"), "error")
    );
  };

  // ----------------------------------------------------------------------
  // Report
  // ----------------------------------------------------------------------

  if (report) {
    const limit = report.estimated_limit;

    return (
      <div className="page loan-report">
        <Stagger className="stack">
          <Rise className="card loan-report-head">
            <ScoreGauge score={report.score} />

            <div className="loan-verdict">
              <span className={`verdict-badge ${VERDICT_CLASS[report.verdict_code]}`}>{report.verdict}</span>

              <p className="loan-explanation">{report.explanation}</p>

              <SpeakButton lang={lang} t={t} text={report.explanation} />
            </div>
          </Rise>

          {report.blockers.length > 0 && (
            <Rise className="card loan-blockers">
              <h3 className="card-title">
                <AlertTriangle size={20} />{" "}{t("loan.must_be_fixed_first")}
              </h3>

              <ul className="bullets bullets-bad">
                {report.blockers.map((item) => (
                  <li key={item}>
                    <X size={16} /> {item}
                  </li>
                ))}
              </ul>
            </Rise>
          )}

          <Rise className="card">
            <h3 className="card-title">
              <Banknote size={20} />{" "}{t("loan.estimated_kisan_credit_card_limit")}
            </h3>

            <p className="loan-limit">
              <CountUp value={Number(limit.estimated_limit) || 0} prefix="₹" />
            </p>

            <div className="loan-rows">
              <span>{t("loan.cultivation_cost")}</span>
              <strong>{rupees(limit.cultivation_cost)}</strong>
              <span>{t("loan.post_harvest_allowance")}</span>
              <strong>{rupees(limit.post_harvest_allowance)}</strong>
              <span>{t("loan.maintenance_allowance")}</span>
              <strong>{rupees(limit.maintenance_allowance)}</strong>
              <span>{t("loan.existing_loans")}</span>
              <strong>− {rupees(limit.existing_loan_outstanding)}</strong>
              <span className="row-total">{t("loan.available_now")}</span>
              <strong className="row-total">{rupees(limit.available_limit)}</strong>
            </div>

            {limit.collateral_free && (
              <p className="callout callout-tip">
                <CheckCircle2 size={16} /> {t("loan.collateral_free", { amount: rupees(limit.collateral_free_up_to) })}
              </p>
            )}

            <p className="note">{limit.interest_note}</p>
          </Rise>

          <Rise className="card">
            <h3 className="card-title">
              <Sparkles size={20} />{" "}{t("loan.how_the_score_was_worked_out")}
            </h3>

            {Object.entries(report.score_breakdown).map(([name, part], index) => (
              <div key={name} className="score-row">
                <span>{serverName(t, "loan.score_", name)}</span>

                <div className="score-bar">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(part.score / part.max) * 100}%` }}
                    transition={{ duration: 0.9, delay: 0.3 + index * 0.1 }}
                  />
                </div>

                <strong>
                  {Math.round(part.score)}/{part.max}
                </strong>
              </div>
            ))}
          </Rise>

          {report.weather_risk && (
            <Rise className="card">
              <h3 className="card-title">
                <Leaf size={20} /> {t("loan.weather_risk_title")}: {serverName(t, "loan.level_", report.weather_risk.level)}
              </h3>

              {report.weather_risk.notes.map((note) => (
                <p key={note} className="note">
                  {note}
                </p>
              ))}
            </Rise>
          )}

          {report.missing_documents.length > 0 && (
            <Rise className="card">
              <h3 className="card-title">
                <FileText size={20} />{" "}{t("loan.documents_to_collect")}
              </h3>

              <ul className="bullets">
                {report.missing_documents.map((doc) => (
                  <li key={doc.code}>
                    <FileText size={16} /> {doc.label}
                  </li>
                ))}
              </ul>
            </Rise>
          )}

          {report.improvement_tips.length > 0 && (
            <Rise className="card">
              <h3 className="card-title">
                <ListChecks size={20} />{" "}{t("loan.what_to_do_next")}
              </h3>

              <ul className="bullets bullets-good">
                {report.improvement_tips.map((tip) => (
                  <li key={tip}>
                    <ArrowRight size={16} /> {tip}
                  </li>
                ))}
              </ul>
            </Rise>
          )}

          <Rise className="card">
            <h3 className="card-title">
              <Building2 size={20} />{" "}{t("loan.nearest_bank_common_service_centre")}
            </h3>

            {!nearby && (
              <Button variant="soft" icon={Navigation} onClick={findNearby}>
                {t("loan.find_near_me")}
              </Button>
            )}

            {nearby && nearby.results.length === 0 && (
              <p className="note">{t("loan.no_branches_found_within_60_km")}</p>
            )}

            {nearby &&
              nearby.results.map((place) => (
                <div key={`${place.name}-${place.lat}`} className="nearby-row">
                  <span className="nearby-name">
                    {place.type === "csc" ? <Building2 size={16} /> : <Landmark size={16} />} {place.name}
                  </span>

                  <Pill>{t("common.km_value", { n: place.distance_km })}</Pill>

                  <a href={place.directions_url} target="_blank" rel="noreferrer">
                    {t("loan.directions")}
                  </a>
                </div>
              ))}

            {nearby && <p className="note">{t("loan.sample_data")}</p>}
          </Rise>

          <Rise>
            <p className="note">
              {t("loan.data_used", {
                land: serverName(t, "loan.src_", report.data_sources.land),
                soil: serverName(t, "loan.src_", report.data_sources.soil),
              })}
            </p>

            <p className="loan-disclaimer">{report.disclaimer}</p>
          </Rise>

          <Rise className="loan-nav">
            <Button variant="ghost" icon={Edit3} onClick={() => setReport(null)}>
              {t("loan.edit_my_details")}
            </Button>

            <Button variant="soft" icon={Printer} onClick={() => window.print()}>
              {t("loan.print_save_as_pdf")}
            </Button>
          </Rise>
        </Stagger>
      </div>
    );
  }

  // ----------------------------------------------------------------------
  // Form
  // ----------------------------------------------------------------------

  return (
    <div className="page loan-page">
      <PageHeader
        icon={Landmark}
        tone="gold"
        title={t("nav_loan")}
        subtitle={t("loan.check_your_kisan_credit_card_kcc")}
      />

      <ol className="stepper loan-stepper" aria-label={t("common.progress")}>
        {STEPS.map((name, index) => {
          const number = index + 1;

          return (
            <li key={name} className={step > number ? "step-done" : step === number ? "step-active" : ""}>
              <button type="button" className="step-btn" onClick={() => setStep(number)}>
                <span className="step-dot">{step > number ? <Check size={14} /> : number}</span>
                <span className="step-name">
                  {number}. {t(name)}
                </span>
              </button>
            </li>
          );
        })}
      </ol>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={step}
          className="card loan-card"
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -30 }}
          transition={{ duration: 0.22 }}
        >
          {step === 1 && (
            <div className="form-grid">
              <div className="two-col">
                <Input
                  id="loan-name"
                  label={t("common.your_name")}
                  placeholder={t("common.your_name")}
                  value={form.farmer_name}
                  onChange={(e) => setField("farmer_name", e.target.value)}
                />

                <Input
                  id="loan-age"
                  label={t("common.age")}
                  type="number"
                  placeholder={t("common.age")}
                  value={form.age}
                  onChange={(e) => setField("age", e.target.value)}
                />
              </div>

              <Input
                id="loan-district"
                label={t("common.district")}
                placeholder={t("common.district")}
                value={form.district}
                onChange={(e) => setField("district", e.target.value)}
              />

              <div className="inline-fetch">
                <Input
                  id="loan-survey"
                  className="grow"
                  label={t("loan.survey_number")}
                  placeholder={t("loan.survey_number")}
                  value={form.land.survey_number}
                  onChange={(e) => setLand("survey_number", e.target.value)}
                />

                <Button variant="soft" icon={Sparkles} onClick={fetchDigiLocker}>
                  {t("loan.fetch_from_digilocker_demo")}
                </Button>
              </div>

              {demoNote && (
                <p className="callout callout-warn">
                  <AlertTriangle size={16} /> {demoNote}
                </p>
              )}

              <div className="two-col">
                <Input
                  id="loan-acres"
                  label={t("loan.land_area_in_acres")}
                  type="number"
                  placeholder={t("loan.land_area_in_acres")}
                  value={form.land.extent_acres}
                  onChange={(e) => setLand("extent_acres", e.target.value)}
                />

                <Select
                  id="loan-ownership"
                  label={t("loan.ownership")}
                  value={form.land.ownership}
                  onChange={(e) => setLand("ownership", e.target.value)}
                  options={[
                    ["owner", t("loan.own_land")],
                    ["tenant", t("loan.tenant")],
                    ["sharecropper", t("loan.sharecropper")],
                  ]}
                />
              </div>

              <label className="check-row">
                <input
                  type="checkbox"
                  checked={form.land.irrigated}
                  onChange={(e) => setLand("irrigated", e.target.checked)}
                />
                <span>{t("loan.irrigated_land")}</span>
              </label>
            </div>
          )}

          {step === 2 && (
            <div className="form-grid">
              <h3 className="card-title">
                <Wheat size={20} />{" "}{t("loan.crops_you_grew_in_the_last")}
              </h3>

              {form.crops.map((crop, index) => (
                <div key={index} className="crop-row">
                  <Input
                    id={`crop-${index}`}
                    label={index === 0 ? t("common.crop") : undefined}
                    aria-label={t("common.crop")}
                    placeholder={t("loan.crop_e_g_tomato")}
                    value={crop.crop}
                    onChange={(e) => setCrop(index, "crop", e.target.value)}
                  />

                  <Select
                    id={`season-${index}`}
                    label={index === 0 ? t("loan.season") : undefined}
                    aria-label={t("loan.season")}
                    value={crop.season}
                    onChange={(e) => setCrop(index, "season", e.target.value)}
                    options={[
                      ["kharif", t("loan.kharif")],
                      ["rabi", t("loan.rabi")],
                      ["summer", t("loan.summer")],
                    ]}
                  />

                  <Input
                    id={`year-${index}`}
                    label={index === 0 ? t("loan.year") : undefined}
                    aria-label={t("loan.year")}
                    type="number"
                    placeholder={t("loan.year")}
                    value={crop.year}
                    onChange={(e) => setCrop(index, "year", e.target.value)}
                  />

                  <Input
                    id={`acres-${index}`}
                    label={index === 0 ? t("loan.acres") : undefined}
                    aria-label={t("loan.acres")}
                    type="number"
                    placeholder={t("loan.acres")}
                    value={crop.area_acres}
                    onChange={(e) => setCrop(index, "area_acres", e.target.value)}
                  />

                  <Input
                    id={`yield-${index}`}
                    label={index === 0 ? t("loan.yield_quintal_acre") : undefined}
                    aria-label={t("loan.yield")}
                    type="number"
                    placeholder={t("loan.yield_quintal_acre")}
                    value={crop.yield_quintal_per_acre}
                    onChange={(e) => setCrop(index, "yield_quintal_per_acre", e.target.value)}
                  />

                  {form.crops.length > 1 && (
                    <button
                      type="button"
                      className="crop-remove"
                      aria-label={t("loan.remove_this_season")}
                      onClick={() => setField("crops", form.crops.filter((_, i) => i !== index))}
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>
              ))}

              <div>
                <Button variant="soft" size="sm" icon={Plus} onClick={() => setField("crops", [...form.crops, emptyCrop()])}>
                  {t("loan.add_another_season")}
                </Button>
              </div>

              <h3 className="card-title spaced">
                <Sparkles size={20} />{" "}{t("loan.crops_you_plan_to_grow_next")}
              </h3>

              <p className="note">{t("loan.if_you_leave_this_empty_the")}</p>

              {form.planned_crops.map((crop, index) => (
                <div key={index} className="crop-row crop-row-short">
                  <Input
                    id={`plan-crop-${index}`}
                    aria-label={t("loan.planned_crop")}
                    placeholder={t("common.crop")}
                    value={crop.crop}
                    onChange={(e) =>
                      setField(
                        "planned_crops",
                        form.planned_crops.map((item, i) =>
                          i === index ? { ...item, crop: e.target.value } : item
                        )
                      )
                    }
                  />

                  <Input
                    id={`plan-acres-${index}`}
                    aria-label={t("loan.planned_acres")}
                    type="number"
                    placeholder={t("loan.acres")}
                    value={crop.area_acres}
                    onChange={(e) =>
                      setField(
                        "planned_crops",
                        form.planned_crops.map((item, i) =>
                          i === index ? { ...item, area_acres: e.target.value } : item
                        )
                      )
                    }
                  />

                  <button
                    type="button"
                    className="crop-remove"
                    aria-label={t("loan.remove_this_crop")}
                    onClick={() => setField("planned_crops", form.planned_crops.filter((_, i) => i !== index))}
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}

              <div>
                <Button
                  variant="soft"
                  size="sm"
                  icon={Plus}
                  onClick={() => setField("planned_crops", [...form.planned_crops, { crop: "", area_acres: "" }])}
                >
                  {t("loan.add_planned_crop")}
                </Button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="form-grid">
              <h3 className="card-title">
                <Leaf size={20} />{" "}{t("loan.soil_health_card_values_if_you")}
              </h3>

              <div className="soil-grid">
                {[
                  ["ph", "loan.soil_ph"],
                  ["oc_percent", "loan.soil_oc"],
                  ["n_kg_ha", "loan.soil_n"],
                  ["p_kg_ha", "loan.soil_p"],
                  ["k_kg_ha", "loan.soil_k"],
                  ["ec_dsm", "loan.soil_ec"],
                ].map(([key, label]) => (
                  <Input
                    key={key}
                    id={`soil-${key}`}
                    label={t(label)}
                    aria-label={t(label)}
                    type="number"
                    placeholder={t(label)}
                    value={form.soil[key]}
                    onChange={(e) => setSoil(key, e.target.value)}
                  />
                ))}
              </div>

              <h3 className="card-title spaced">
                <Banknote size={20} />{" "}{t("loan.existing_loans")}
              </h3>

              <Input
                id="loan-outstanding"
                type="number"
                aria-label={t("loan.loan_still_to_be_repaid")}
                placeholder={t("loan.total_loan_amount_still_to_be")}
                value={form.existing_loan_outstanding}
                onChange={(e) => setField("existing_loan_outstanding", e.target.value)}
              />

              <label className="check-row">
                <input
                  type="checkbox"
                  checked={form.has_default}
                  onChange={(e) => setField("has_default", e.target.checked)}
                />
                <span>{t("loan.i_have_an_overdue_defaulted_loan")}</span>
              </label>
            </div>
          )}

          {step === 4 && (
            <div className="form-grid">
              <h3 className="card-title">
                <ShieldCheck size={20} />{" "}{t("loan.documents_you_already_have")}
              </h3>

              <div className="doc-grid">
                {DOCUMENTS.map(([code, label]) => (
                  <label key={code} className={`doc-tile ${form.documents.includes(code) ? "doc-on" : ""}`}>
                    <input
                      type="checkbox"
                      checked={form.documents.includes(code)}
                      onChange={() => toggleDocument(code)}
                    />

                    <span className="doc-tick">{form.documents.includes(code) && <Check size={14} />}</span>

                    <span>{t(label)}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      <div className="loan-nav">
        {step > 1 && (
          <Button variant="ghost" icon={ArrowLeft} onClick={() => setStep(step - 1)}>
            {t("common.back")}
          </Button>
        )}

        {step < 4 ? (
          <Button iconRight={ArrowRight} onClick={() => setStep(step + 1)}>
            {t("loan.next")}
          </Button>
        ) : (
          <Button size="lg" loading={busy} icon={Sparkles} onClick={checkEligibility}>
            {busy ? t("loan.checking") : t("loan.check_eligibility")}
          </Button>
        )}
      </div>

      <p className="loan-disclaimer">
        {t("loan.advisory_estimate_only_not_a_bank")}
      </p>
    </div>
  );
}
