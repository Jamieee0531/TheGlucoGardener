"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../lib/useAuth";
import { useTranslation } from "../../lib/i18n";
import { sendMessageStream } from "../../lib/api";
import { webmToWav } from "../../lib/audioUtils";
import { API_BASE } from "../../lib/config";

export default function WarmupPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { t } = useTranslation();

  const [patterns, setPatterns] = useState(null);
  const [recentCount, setRecentCount] = useState(null);
  const [phase, setPhase] = useState("question");
  const [transitionMsg, setTransitionMsg] = useState("");
  const [inputText, setInputText] = useState("");
  const [aiReply, setAiReply] = useState("");
  const [transcribedText, setTranscribedText] = useState("");
  const [sending, setSending] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  const inputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  // Always show warm up when navigated to directly (no auto-redirect)

  // Fetch exercise patterns + recent exercise count
  useEffect(() => {
    if (!user) return;
    fetch(`${API_BASE}/users/${user.user_id}/exercise-patterns`)
      .then((r) => r.json())
      .then((data) => setPatterns(data.patterns || []))
      .catch(() => setPatterns([]));

    fetch(`${API_BASE}/health/recent-exercise?user_id=${user.user_id}&days=7`)
      .then((r) => r.json())
      .then((data) => setRecentCount(data.count))
      .catch(() => setRecentCount(0));
  }, [user]);

  if (loading || !user || patterns === null || recentCount === null) return null;

  // Find today's pattern (day_of_week is a number: 0=sunday, 1=monday, ...)
  const todayDow = new Date().getDay();
  const todayPattern = patterns.find((p) => Number(p.day_of_week) === todayDow);

  // Scenario A: has pattern for today AND exercised recently
  // Scenario B: no pattern for today OR hasn't exercised in past week
  const showScenarioA = todayPattern && recentCount > 0;

  const logExercise = (exerciseType, startTime, endTime) => {
    const today = new Date().toISOString().slice(0, 10);
    fetch(`${API_BASE}/health/log-exercise`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: user.user_id,
        exercise_type: exerciseType,
        started_at: `${today}T${startTime}:00`,
        ended_at: `${today}T${endTime}:00`,
      }),
    }).catch(() => {});
  };

  const markDoneAndGo = (msg) => {
    setTransitionMsg(msg);
    setPhase("transition");
    const today = new Date().toISOString().slice(0, 10);
    localStorage.setItem(`warmup_done_${user.user_id}_${today}`, "true");
    setTimeout(() => router.push("/"), 1500);
  };

  const handleYesSameAsUsual = () => {
    // Write today's exercise to DB based on pattern
    if (todayPattern) {
      logExercise(todayPattern.activity_type, todayPattern.start_time, todayPattern.end_time);
    }
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

  const sendPlan = ({ text, audio }) => {
    setSending(true);
    let reply = "";
    sendMessageStream({
      userId: user.user_id,
      text,
      audio,
      onToken: (token) => { reply += token; setAiReply(reply); },
      onDone: (data) => {
        if (data.transcribed_text) {
          setTranscribedText(data.transcribed_text);
          setInputText(data.transcribed_text);
        }
        setSending(false);
        setTimeout(() => markDoneAndGo(t("warmup_enjoy_workout")), 2000);
      },
      onError: () => { setSending(false); markDoneAndGo(t("warmup_enjoy_day")); },
    });
  };

  const handleSendPlan = () => {
    const text = inputText.trim();
    if (!text || sending) return;
    sendPlan({ text });
  };

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
          try { sendPlan({ audio: await webmToWav(webmBlob) }); }
          catch { sendPlan({ audio: webmBlob }); }
        }
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch (err) { console.error("Mic access denied:", err); }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    setIsRecording(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendPlan();
    }
  };

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

          {transcribedText && (
            <div className="bg-white/60 rounded-xl px-4 py-2 mb-2 text-right">
              <p className="text-sm text-gray-500 italic">🎙 "{transcribedText}"</p>
            </div>
          )}
          {aiReply && (
            <div className="bg-white/80 rounded-xl px-4 py-3 mb-4 text-left shadow-sm border border-[#e8e0d4]">
              <p className="text-sm text-gray-700">{aiReply}</p>
            </div>
          )}

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
              onClick={isRecording ? stopRecording : startRecording}
              disabled={sending}
              className={`w-10 h-10 rounded-full flex items-center justify-center text-lg transition-all disabled:opacity-40 ${
                isRecording ? "bg-red-400 scale-110" : "bg-gray-200"
              }`}
            >
              🎙
            </button>
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
        <div className="w-full max-w-[340px] text-center">
          <p className="text-2xl font-bold italic text-[#e8927c] mb-2">
            {t("warmup_greeting")} {user.name.split(" ")[0]}! 🌿
          </p>

          {showScenarioA ? (
            <>
              <p className="text-base text-gray-600 mt-4 leading-relaxed">
                {t("warmup_pattern_confirm")} <span className="font-semibold">{todayPattern.activity_type}</span> {t("warmup_pattern_at")} <span className="font-semibold">{todayPattern.start_time}</span>
                {todayPattern.end_time && (
                  <span> — <span className="font-semibold">{todayPattern.end_time}</span> ({(() => {
                    const [sh, sm] = todayPattern.start_time.split(":").map(Number);
                    const [eh, em] = todayPattern.end_time.split(":").map(Number);
                    return (eh * 60 + em) - (sh * 60 + sm);
                  })()} min)</span>
                )}.
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
