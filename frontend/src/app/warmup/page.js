"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../lib/useAuth";
import { useTranslation } from "../../lib/i18n";
import { sendMessageStream } from "../../lib/api";

const API_BASE = "http://localhost:8080";

export default function WarmupPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { t } = useTranslation();

  const [patterns, setPatterns] = useState(null);    // null = loading
  const [phase, setPhase] = useState("question");    // question | input | transition
  const [transitionMsg, setTransitionMsg] = useState("");
  const [inputText, setInputText] = useState("");
  const [aiReply, setAiReply] = useState("");
  const [sending, setSending] = useState(false);

  const inputRef = useRef(null);

  // Check if already done today
  useEffect(() => {
    const today = new Date().toISOString().slice(0, 10);
    if (localStorage.getItem(`warmup_done_${today}`)) {
      router.replace("/");
      return;
    }
  }, [router]);

  // Fetch exercise patterns
  useEffect(() => {
    if (!user) return;
    fetch(`${API_BASE}/users/${user.user_id}/exercise-patterns`)
      .then((r) => r.json())
      .then((data) => setPatterns(data.patterns || []))
      .catch(() => setPatterns([]));
  }, [user]);

  if (loading || !user || patterns === null) return null;

  const hasPattern = patterns.length > 0;

  // Find today's pattern (match day_of_week)
  const days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
  const todayDay = days[new Date().getDay()];
  const todayPattern = patterns.find((p) => p.day_of_week?.toLowerCase() === todayDay);

  const markDoneAndGo = (msg) => {
    setTransitionMsg(msg);
    setPhase("transition");
    const today = new Date().toISOString().slice(0, 10);
    localStorage.setItem(`warmup_done_${today}`, "true");
    setTimeout(() => router.push("/"), 1500);
  };

  const handleYesSameAsUsual = () => {
    markDoneAndGo(t("warmup_enjoy_workout"));
  };

  const handleNoDifferentPlan = () => {
    setPhase("input");
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const handleNotToday = () => {
    markDoneAndGo(t("warmup_enjoy_day"));
  };

  const handleYesLetsPlan = () => {
    setPhase("input");
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const handleSendPlan = () => {
    const text = inputText.trim();
    if (!text || sending) return;
    setSending(true);

    let reply = "";
    sendMessageStream({
      userId: user.user_id,
      text,
      onToken: (token) => {
        reply += token;
        setAiReply(reply);
      },
      onDone: () => {
        setSending(false);
        // After AI confirms, wait a moment then transition
        setTimeout(() => markDoneAndGo(t("warmup_enjoy_workout")), 2000);
      },
      onError: () => {
        setSending(false);
        markDoneAndGo(t("warmup_enjoy_day"));
      },
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendPlan();
    }
  };

  // ── Render ──
  return (
    <div className="flex flex-col h-full bg-cream items-center justify-center px-8">
      {phase === "transition" ? (
        <div className="text-center animate-pulse">
          <p className="text-2xl font-bold italic text-[#7cb342]">{transitionMsg}</p>
        </div>
      ) : phase === "input" ? (
        <div className="w-full max-w-[340px] text-center">
          <p className="text-lg font-semibold italic text-[#e8927c] mb-4">
            {t("warmup_what_plan")}
          </p>

          {/* AI reply */}
          {aiReply && (
            <div className="bg-white/80 rounded-xl px-4 py-3 mb-4 text-left shadow-sm border border-[#e8e0d4]">
              <p className="text-sm text-gray-700">{aiReply}</p>
            </div>
          )}

          {/* Input */}
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("warmup_input_placeholder")}
              className="flex-1 bg-white rounded-full px-4 py-3 text-sm outline-none border border-gray-200"
              disabled={sending}
            />
            <button
              onClick={handleSendPlan}
              disabled={!inputText.trim() || sending}
              className="bg-[#7cb342] text-white rounded-full w-10 h-10 flex items-center justify-center text-lg disabled:opacity-40"
            >
              ↑
            </button>
          </div>
        </div>
      ) : (
        /* ── Question phase ── */
        <div className="w-full max-w-[340px] text-center">
          {/* Greeting */}
          <p className="text-2xl font-bold italic text-[#e8927c] mb-2">
            {t("warmup_greeting")} {user.name.split(" ")[0]}! 🌿
          </p>

          {hasPattern && todayPattern ? (
            /* Scenario A — has exercise habit */
            <>
              <p className="text-base text-gray-600 mt-4 leading-relaxed">
                {t("warmup_pattern_confirm")} <span className="font-semibold">{todayPattern.activity_type}</span> {t("warmup_pattern_at")} <span className="font-semibold">{todayPattern.start_time}</span>.
              </p>
              <p className="text-base text-gray-600 mt-2">
                {t("warmup_keep_plan")}
              </p>

              <div className="flex flex-col gap-3 mt-6">
                <button
                  onClick={handleYesSameAsUsual}
                  className="w-full py-3 rounded-full text-white font-semibold text-sm"
                  style={{ backgroundColor: "#7cb342" }}
                >
                  {t("warmup_yes")}
                </button>
                <button
                  onClick={handleNoDifferentPlan}
                  className="w-full py-3 rounded-full text-gray-600 font-semibold text-sm bg-gray-200"
                >
                  {t("warmup_no")}
                </button>
              </div>
            </>
          ) : (
            /* Scenario B — no recent exercise */
            <>
              <p className="text-base text-gray-600 mt-4 leading-relaxed">
                {t("warmup_no_exercise")}
              </p>

              <div className="flex flex-col gap-3 mt-6">
                <button
                  onClick={handleYesLetsPlan}
                  className="w-full py-3 rounded-full text-white font-semibold text-sm"
                  style={{ backgroundColor: "#7cb342" }}
                >
                  {t("warmup_yes_plan")}
                </button>
                <button
                  onClick={handleNotToday}
                  className="w-full py-3 rounded-full text-gray-600 font-semibold text-sm bg-gray-200"
                >
                  {t("warmup_not_today")}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
