"use client";

import { useState, useRef, useEffect } from "react";
import { sendMessageStream } from "../lib/api";
import { webmToWav } from "../lib/audioUtils";
import { useTranslation } from "../lib/i18n";

export default function MiniChat({ userId, imageFile, onConfirmEaten, onClose }) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const scrollRef = useRef(null);
  const msgIdRef = useRef(0);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  const nextId = () => ++msgIdRef.current;

  // Generate image preview on mount
  useEffect(() => {
    if (imageFile) {
      const url = URL.createObjectURL(imageFile);
      setImagePreview(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [imageFile]);

  // Auto-scroll on new messages
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        const webmBlob = new Blob(chunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        if (webmBlob.size > 1000) {
          try {
            const wavBlob = await webmToWav(webmBlob);
            handleSendAudio(wavBlob);
          } catch {
            handleSendAudio(webmBlob);
          }
        }
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Mic access denied:", err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    setIsRecording(false);
  };

  const handleSendAudio = (audioBlob) => {
    const userMsgId = nextId();
    setMessages((prev) => [...prev, { id: userMsgId, role: "user", content: "", pendingVoice: true }]);
    const aiMsgId = nextId();
    setMessages((prev) => [...prev, { id: aiMsgId, role: "assistant", content: "" }]);
    setSending(true);

    const isFirstVoiceWithImage = messages.length === 0 && imageFile;

    sendMessageStream({
      userId,
      sessionId,
      audio: audioBlob,
      mode: "task",
      onToken: (token) => {
        if (!isFirstVoiceWithImage) {
          setMessages((prev) => prev.map((m) => (m.id === aiMsgId ? { ...m, content: m.content + token } : m)));
        }
      },
      onDone: (data) => {
        if (!sessionId) setSessionId(data.session_id);
        // Show transcription first
        setMessages((prev) => prev.map((m) => {
          if (m.id === userMsgId) return {
            ...m,
            pendingVoice: false,
            content: data.transcribed_text
              ? "🎙 " + data.transcribed_text
              : "🎙 " + (t("voice_unclear") || "（听不清楚）"),
          };
          return m;
        }));
        if (isFirstVoiceWithImage) {
          // Stream mock response after transcription appears
          let i = 0;
          const words = DEMO_RESPONSE.split(" ");
          const interval = setInterval(() => {
            if (i < words.length) {
              const token = (i === 0 ? "" : " ") + words[i];
              setMessages((prev) =>
                prev.map((m) => (m.id === aiMsgId ? { ...m, content: m.content + token } : m))
              );
              i++;
            } else {
              clearInterval(interval);
              setSending(false);
            }
          }, 60);
        } else {
          if (data.reply) {
            setMessages((prev) =>
              prev.map((m) => (m.id === aiMsgId ? { ...m, content: data.reply } : m))
            );
          }
          setSending(false);
        }
      },
      onError: () => {
        setMessages((prev) => prev.map((m) => {
          if (m.id === aiMsgId) return { ...m, content: "Sorry, something went wrong." };
          if (m.id === userMsgId) return { ...m, pendingVoice: false, content: "🎙 Voice message" };
          return m;
        }));
        setSending(false);
      },
    });
  };

  // ── Demo mock: first message with image triggers hardcoded contextual response ──
  const DEMO_TRIGGER = /dinner|can i have|eat this|好吗|可以吃|晚餐/i;
  const DEMO_RESPONSE =
    "Wanton noodles — the wontons and choy sum are actually not bad, " +
    "but that char siu glaze is pretty sugary and the noodles add up fast on the GI. " +
    "Your glucose is looking okay right now, so you can have it — " +
    "try asking for less noodles, skip the extra sauce drizzle, " +
    "and the choy sum on the side will help slow things down. 👍";

  const handleSend = () => {
    const text = inputText.trim();
    if (!text || sending) return;
    setInputText("");

    // Add user message
    const userMsgId = nextId();
    setMessages((prev) => [...prev, { id: userMsgId, role: "user", content: text }]);

    // Add empty assistant bubble
    const aiMsgId = nextId();
    setMessages((prev) => [...prev, { id: aiMsgId, role: "assistant", content: "" }]);

    setSending(true);

    // Only send image on first message
    const isFirstMessage = messages.length === 0;

    // ── Demo mode: intercept first message with image ──
    if (isFirstMessage && imageFile) {
      let i = 0;
      const words = DEMO_RESPONSE.split(" ");
      const interval = setInterval(() => {
        if (i < words.length) {
          const token = (i === 0 ? "" : " ") + words[i];
          setMessages((prev) =>
            prev.map((m) => (m.id === aiMsgId ? { ...m, content: m.content + token } : m))
          );
          i++;
        } else {
          clearInterval(interval);
          setSending(false);
        }
      }, 60);
      return;
    }

    sendMessageStream({
      userId,
      sessionId,
      text,
      image: isFirstMessage ? imageFile : undefined,
      mode: "task",
      onToken: (token) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === aiMsgId ? { ...m, content: m.content + token } : m))
        );
      },
      onDone: (data) => {
        if (!sessionId) setSessionId(data.session_id);
        if (data.reply) {
          setMessages((prev) =>
            prev.map((m) => (m.id === aiMsgId ? { ...m, content: data.reply } : m))
          );
        }
        setSending(false);
      },
      onError: () => {
        setMessages((prev) =>
          prev.map((m) => (m.id === aiMsgId ? { ...m, content: "Sorry, something went wrong." } : m))
        );
        setSending(false);
      },
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col relative" style={{ height: "50vh" }}>
      {/* Header with image + close */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/30">
        <div className="flex items-center gap-2">
          {imagePreview && (
            <img src={imagePreview} alt="Food" className="w-[50px] h-[50px] rounded-lg object-cover" />
          )}
          <span className="text-sm font-semibold text-white/90">🍽 Food Chat</span>
        </div>
        <button onClick={onClose} className="text-white/70 text-lg font-bold px-2">✕</button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-3 py-2 rounded-2xl text-sm ${
                msg.role === "user"
                  ? "bg-white/90 text-gray-800"
                  : "bg-white/40 text-gray-900"
              }`}
            >
              {msg.pendingVoice ? (
                <span className="flex items-center gap-1.5 text-gray-500">
                  <span>🎙</span>
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0.15s]" />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0.3s]" />
                </span>
              ) : msg.role === "assistant" && !msg.content ? (
                <div className="flex gap-1 py-0.5">
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0.15s]" />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0.3s]" />
                </div>
              ) : msg.role === "assistant" ? (
                <span>🌿 {msg.content}</span>
              ) : msg.content}
            </div>
          </div>
        ))}
      </div>

      {/* Input bar */}
      <div className="px-3 py-2 border-t border-white/30">
        <div className="flex items-center gap-2">
          <input
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t("mini_chat_placeholder")}
            className="flex-1 bg-white/80 rounded-full px-3 py-2 text-sm outline-none"
            disabled={sending}
          />
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={sending}
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm transition-all disabled:opacity-40 ${
              isRecording ? "bg-red-400 scale-110" : "bg-white/70"
            }`}
          >
            🎙
          </button>
          <button
            onClick={handleSend}
            disabled={!inputText.trim() || sending}
            className="bg-white text-[#7bb5e0] rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold disabled:opacity-40"
          >
            ↑
          </button>
        </div>

        {/* Confirm eaten button */}
        <button
          onClick={() => setShowConfirm(true)}
          className="w-full mt-2 py-2 rounded-full text-white font-semibold text-sm"
          style={{ backgroundColor: "#7cb342" }}
        >
          {t("mini_chat_eaten")}
        </button>
      </div>

      {/* Confirmation modal */}
      {showConfirm && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/40 rounded-2xl">
          <div className="bg-white rounded-2xl p-5 mx-6 shadow-lg text-center">
            <p className="text-sm font-semibold text-gray-800 mb-1">Log this meal?</p>
            <p className="text-xs text-gray-500 mb-4">This will save the record and earn you points.</p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 py-2 rounded-full text-sm font-semibold text-gray-600 bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={() => { setShowConfirm(false); onConfirmEaten(); }}
                className="flex-1 py-2 rounded-full text-sm font-semibold text-white"
                style={{ backgroundColor: "#7cb342" }}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
