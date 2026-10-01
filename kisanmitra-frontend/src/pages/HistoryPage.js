import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { API_URL } from "../voice";
import { notify, confirmDialog } from "../ui/notify";
import { Button, EmptyState, PageHeader, Pill, Skeleton } from "../ui/kit";
import { EmptyArt } from "../ui/art";
import { History, Leaf, Pill as PillIcon, RefreshCw, ScanLine, Trash2 } from "../ui/icons";
import { useT } from "../i18n";

const confidenceOf = (value) => {
  const number = parseFloat(String(value));

  return Number.isFinite(number) ? Math.min(Math.max(number, 0), 100) : null;
};

export default function HistoryPage({ go }) {
  const t = useT();

  const [history, setHistory] = useState(null);
  const [busy, setBusy] = useState(false);

  const fetchHistory = async () => {
    setBusy(true);

    try {
      const res = await fetch(`${API_URL}/predictions`);
      const data = await res.json();

      setHistory(Array.isArray(data) ? data : []);
    } catch (error) {
      console.warn("Could not load the history:", error.message);
      setHistory((old) => old || []);
      notify(t("history.could_not_load_your_history"), "error");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clearHistory = async () => {
    const yes = await confirmDialog(t("history.delete_all_saved_scans_this_cannot"), {
      confirmLabel: t("history.delete_all"),
    });

    if (!yes) return;

    try {
      await fetch(`${API_URL}/predictions`, { method: "DELETE" });
      setHistory([]);
      notify(t("history.history_cleared"), "success");
    } catch (error) {
      notify(t("history.could_not_clear_the_history"), "error");
    }
  };

  return (
    <div className="page">
      <PageHeader
        icon={History}
        tone="forest"
        title={t("history.prediction_history")}
        subtitle={t("history.every_leaf_you_have_scanned_with")}
        actions={
          <>
            <Button variant="ghost" icon={RefreshCw} loading={busy} onClick={fetchHistory}>
              {t("history.refresh")}
            </Button>

            {history && history.length > 0 && (
              <Button variant="danger" icon={Trash2} onClick={clearHistory}>
                {t("history.clear_history")}
              </Button>
            )}
          </>
        }
      />

      {history === null ? (
        <div className="stack">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={96} radius={22} />
          ))}
        </div>
      ) : history.length === 0 ? (
        <EmptyState
          art={
            <EmptyArt>
              <Leaf size={34} />
            </EmptyArt>
          }
          title={t("history.no_scans_yet")}
          text={t("history.scan_your_first_leaf_and_it")}
          action={
            <Button icon={ScanLine} onClick={() => go("disease")}>
              {t("common.scan_a_leaf")}
            </Button>
          }
        />
      ) : (
        <div className="history-list">
          <AnimatePresence>
            {history.map((item, index) => {
              const pct = confidenceOf(item.confidence);

              return (
                <motion.article
                  key={item.id}
                  layout
                  className="card history-card"
                  initial={{ opacity: 0, x: -30 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 30 }}
                  transition={{ delay: Math.min(index, 10) * 0.05 }}
                >
                  <span className="history-icon">
                    <Leaf size={22} />
                  </span>

                  <div className="history-main">
                    <h3>{item.disease}</h3>

                    {item.treatment && (
                      <p>
                        <PillIcon size={14} /> {item.treatment}
                      </p>
                    )}
                  </div>

                  {pct !== null ? (
                    <div className="history-conf">
                      <Pill tone={pct >= 85 ? "good" : pct >= 60 ? "warn" : "bad"}>{Math.round(pct)}%</Pill>

                      <div className="meter">
                        <motion.span
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 0.9, delay: 0.2 + index * 0.05 }}
                        />
                      </div>
                    </div>
                  ) : (
                    <Pill>{String(item.confidence)}</Pill>
                  )}
                </motion.article>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
