"use client";

import { useState, useRef, useEffect } from "react";
import { sendMessageStream } from "../lib/api";
import { useTranslation } from "../lib/i18n";

export default function MiniChat({ userId, imageFile, onConfirmEaten, onClose }) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const scrollRef = useRef(null);
  const msgIdRef = useRef(0);

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

    sendMessageStream({
      userId,
      sessionId,
      text,
      image: isFirstMessage ? imageFile : undefined,
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
    <div className="flex flex-col" style={{ height: "50vh" }}>
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
              {msg.content || "..."}
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
            onClick={handleSend}
            disabled={!inputText.trim() || sending}
            className="bg-white text-[#7bb5e0] rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold disabled:opacity-40"
          >
            ↑
          </button>
        </div>

        {/* Confirm eaten button */}
        <button
          onClick={onConfirmEaten}
          className="w-full mt-2 py-2 rounded-full text-white font-semibold text-sm"
          style={{ backgroundColor: "#7cb342" }}
        >
          {t("mini_chat_eaten")}
        </button>
      </div>
    </div>
  );
}
