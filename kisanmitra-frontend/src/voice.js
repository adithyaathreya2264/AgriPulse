// Voice for the whole app: microphone input (any text box) and spoken answers.
import { useEffect, useRef, useState } from "react";
import { speechLanguage } from "./i18n";
import { notify } from "./ui/notify";
import { Loader2, Mic, Square, Volume2 } from "./ui/icons";

export const API_URL =
  process.env.REACT_APP_API_URL || "http://127.0.0.1:5556";

const MAX_RECORD_SECONDS = 15;

// ---------------------------------------------------------------------------
// Recording
// ---------------------------------------------------------------------------

// state: "idle" | "recording" | "processing"
export function useVoiceInput({ lang, onText, onError }) {
  const [state, setState] = useState("idle");
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(
    () => () => {
      clearTimeout(timerRef.current);
      const recorder = recorderRef.current;

      if (recorder && recorder.state === "recording") {
        recorder.stream.getTracks().forEach((track) => track.stop());
      }
    },
    []
  );

  const upload = async (blob) => {
    setState("processing");

    try {
      const form = new FormData();
      form.append("file", blob, "voice.webm");
      form.append("lang", lang);

      const res = await fetch(`${API_URL}/voice/transcribe`, {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        onError && onError("voice_not_understood");
        return;
      }

      const data = await res.json();

      if (data.text) onText(data.text, data);
    } catch (error) {
      console.warn("Voice upload failed:", error.message);
      onError && onError("voice_not_understood");
    } finally {
      setState("idle");
    }
  };

  const stop = () => {
    clearTimeout(timerRef.current);

    if (recorderRef.current && recorderRef.current.state === "recording") {
      recorderRef.current.stop();
    }
  };

  const start = async () => {
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      onError && onError("voice_no_mic");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);

      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());

        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });

        if (blob.size > 0) upload(blob);
        else setState("idle");
      };

      recorderRef.current = recorder;
      recorder.start();
      setState("recording");

      // Never record forever
      timerRef.current = setTimeout(stop, MAX_RECORD_SECONDS * 1000);
    } catch (error) {
      console.warn("Microphone error:", error.message);
      onError && onError("voice_no_mic");
    }
  };

  const toggle = () => (state === "recording" ? stop() : state === "idle" && start());

  return { state, toggle };
}

// A round microphone button that fills a text box by voice
export function VoiceMic({ lang, onText, t, className = "" }) {
  const { state, toggle } = useVoiceInput({
    lang,
    onText,
    onError: (key) => notify(t(key), "error"),
  });

  const label =
    state === "recording"
      ? t("voice_listening")
      : state === "processing"
      ? t("voice_processing")
      : t("voice_command");

  return (
    <button
      type="button"
      className={`mic-btn mic-${state} ${className}`}
      onClick={toggle}
      title={label}
      aria-label={label}
    >
      {state === "recording" && <span className="mic-ring" />}
      {state === "recording" ? (
        <Square size={16} fill="currentColor" />
      ) : state === "processing" ? (
        <Loader2 size={18} className="spin" />
      ) : (
        <Mic size={18} />
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Speaking
// ---------------------------------------------------------------------------

let currentAudio = null;

export function stopSpeaking() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }

  if (window.speechSynthesis) window.speechSynthesis.cancel();
}

function browserSpeak(text, lang) {
  if (!window.speechSynthesis) return false;

  const code = speechLanguage(lang);
  const utterance = new SpeechSynthesisUtterance(text);

  utterance.lang = code;

  const voices = window.speechSynthesis.getVoices();
  const voice = voices.find((item) => item.lang === code) ||
    voices.find((item) => item.lang.startsWith(code.split("-")[0]));

  // No voice for this language on the device: better to say so than to
  // read a Kannada sentence in an English voice.
  if (!voice && lang !== "en") return false;

  if (voice) utterance.voice = voice;

  window.speechSynthesis.speak(utterance);

  return true;
}

// Sarvam voice when the server has it, otherwise the device's own voice.
// Resolves to true when something was spoken.
export async function speak(text, lang) {
  stopSpeaking();

  if (!text) return false;

  try {
    const res = await fetch(`${API_URL}/voice/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang }),
    });

    if (res.ok) {
      const data = await res.json();

      if (data.provider === "sarvam" && data.audio_base64) {
        currentAudio = new Audio(`data:${data.mime};base64,${data.audio_base64}`);
        await currentAudio.play();
        return true;
      }
    }
  } catch (error) {
    console.warn("Server voice unavailable:", error.message);
  }

  return browserSpeak(text, lang);
}

// "Listen" button next to any answer
export function SpeakButton({ text, lang, t }) {
  const [speaking, setSpeaking] = useState(false);

  if (!text) return null;

  const toggle = async () => {
    if (speaking) {
      stopSpeaking();
      setSpeaking(false);
      return;
    }

    setSpeaking(true);

    const spoken = await speak(text, lang);

    if (!spoken) notify(t("voice_no_voice"), "error");

    setSpeaking(false);
  };

  return (
    <button type="button" className={`speak-btn ${speaking ? "speaking" : ""}`} onClick={toggle}>
      {speaking ? (
        <span className="wave" aria-hidden="true">
          <i /><i /><i /><i />
        </span>
      ) : (
        <Volume2 size={16} />
      )}
      <span>{speaking ? t("voice_stop") : t("voice_listen")}</span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Voice commands ("show weather in Mysuru")
// ---------------------------------------------------------------------------

export function VoiceCommandButton({ lang, t, onCommand }) {
  const handleText = async (text) => {
    try {
      const res = await fetch(`${API_URL}/voice/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, lang }),
      });

      if (!res.ok) {
        notify(t("voice_not_understood"), "error");
        return;
      }

      const command = await res.json();

      onCommand(command);
      speak(command.reply, command.lang || lang);
    } catch (error) {
      console.warn("Voice command failed:", error.message);
      notify(t("voice_not_understood"), "error");
    }
  };

  const { state, toggle } = useVoiceInput({
    lang,
    onText: handleText,
    onError: (key) => notify(t(key), "error"),
  });

  const label =
    state === "recording"
      ? t("voice_listening")
      : state === "processing"
      ? t("voice_processing")
      : t("voice_command");

  return (
    <button
      type="button"
      className={`voice-fab voice-${state}`}
      onClick={toggle}
      aria-label={label}
    >
      {state === "recording" && (
        <>
          <span className="fab-ring fab-ring-1" />
          <span className="fab-ring fab-ring-2" />
        </>
      )}
      <span className="voice-fab-icon">
        {state === "recording" ? (
          <Square size={20} fill="currentColor" />
        ) : state === "processing" ? (
          <Loader2 size={22} className="spin" />
        ) : (
          <Mic size={22} />
        )}
      </span>
      <span className="voice-fab-label">{label}</span>
    </button>
  );
}
