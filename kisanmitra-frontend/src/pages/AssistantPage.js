import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { API_URL, SpeakButton, VoiceMic } from "../voice";
import { Avatar, Button, PageHeader } from "../ui/kit";
import { Bot, Send, Sparkles, Trash2 } from "../ui/icons";

const SUGGESTIONS = ["assistant.q_aphids", "assistant.q_fertilizer", "assistant.q_ragi", "assistant.q_paddy"];

export default function AssistantPage({ user, lang, t, messages, setMessages, intent }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);
  const handledIntent = useRef(null);

  const send = async (override) => {
    const question = typeof override === "string" ? override : input;

    if (!question.trim() || loading) return;

    setMessages((prev) => [...prev, { sender: "user", text: question }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/ai-chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, lang }),
      });

      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        { sender: "assistant", text: data.answer || data.Message || t("assistant.no_answer") },
      ]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [...prev, { sender: "assistant", text: t("assistant.no_server") }]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (intent && intent.action === "ask" && intent.params && intent.params.question && handledIntent.current !== intent.id) {
      handledIntent.current = intent.id;
      send(intent.params.question);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intent]);

  useEffect(() => {
    if (endRef.current && endRef.current.scrollIntoView) {
      endRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, loading]);

  return (
    <div className="page chat-page">
      <PageHeader
        icon={Bot}
        tone="forest"
        title={t("assistant.ai_agriculture_assistant")}
        subtitle={t("assistant.ask_about_crops_disease_weather_prices")}
        actions={
          messages.length > 0 && (
            <Button variant="ghost" icon={Trash2} onClick={() => setMessages([])}>
              {t("assistant.clear_chat")}
            </Button>
          )
        }
      />

      <div className="chat-box card">
        {messages.length === 0 && (
          <div className="welcome-chat">
            <motion.span className="welcome-orb" animate={{ scale: [1, 1.08, 1] }} transition={{ duration: 3.2, repeat: Infinity }}>
              <Sparkles size={34} />
            </motion.span>

            <h2>{t("assistant.agripulse_ai")}</h2>

            <p>{t("assistant.ask_anything_about_your_crop_disease")}</p>

            <div className="suggestions">
              {SUGGESTIONS.map((key, i) => (
                <motion.button
                  key={key}
                  type="button"
                  className="suggestion"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 + i * 0.08 }}
                  whileHover={{ y: -2 }}
                  onClick={() => send(t(key))}
                >
                  {t(key)}
                </motion.button>
              ))}
            </div>
          </div>
        )}

        <div className="messages" aria-live="polite">
          <AnimatePresence initial={false}>
            {messages.map((msg, index) => {
              const mine = msg.sender === "user";

              return (
                <motion.div
                  key={index}
                  className={`msg-row ${mine ? "msg-user" : "msg-ai"}`}
                  initial={{ opacity: 0, y: 14, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  {mine ? (
                    <Avatar name={user.name || user.phone} size={34} />
                  ) : (
                    <span className="ai-avatar">
                      <Bot size={18} />
                    </span>
                  )}

                  <div className="bubble-wrap">
                    <div className={`bubble ${mine ? "bubble-user" : "bubble-ai"}`}>{msg.text}</div>

                    {!mine && <SpeakButton lang={lang} t={t} text={msg.text} />}
                  </div>
                </motion.div>
              );
            })}

            {loading && (
              <motion.div key="typing" className="msg-row msg-ai" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <span className="ai-avatar">
                  <Bot size={18} />
                </span>

                <div className="bubble bubble-ai typing" aria-label={t("assistant.the_assistant_is_typing")}>
                  <i />
                  <i />
                  <i />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div ref={endRef} />
        </div>
      </div>

      <div className="chat-input-area">
        <VoiceMic lang={lang} t={t} onText={(text) => setInput(text)} />

        <input
          value={input}
          aria-label={t("assistant.your_question")}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t("ph_ask")}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />

        <Button icon={Send} disabled={!input.trim() || loading} onClick={() => send()}>
          {t("btn_send")}
        </Button>
      </div>
    </div>
  );
}
