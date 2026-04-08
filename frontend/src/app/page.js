"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import TopBar from "../components/TopBar";
import SugarChart from "../components/SugarChart";
import { useAuth } from "../lib/useAuth";
import { useTranslation } from "../lib/i18n";
import { fetchInterventions } from "../lib/gatewayApi";

const API_BASE = "http://localhost:8080";

export default function HomePage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { t } = useTranslation();

  // ── Warm-up gate: redirect if not done today ──
  useEffect(() => {
    if (loading || !user) return;
    const today = new Date().toISOString().slice(0, 10);
    if (!localStorage.getItem(`warmup_done_${user.user_id}_${today}`)) {
      router.push("/warmup");
    }
  }, [user, loading, router]);
  const [bmi, setBmi] = useState("—");
  const [mealsLogged, setMealsLogged] = useState("0/3");

  // Alert states
  const [softAlert, setSoftAlert] = useState(null);   // { message_sent, trigger_type, ... }
  const [softDismissedId, setSoftDismissedId] = useState(null); // ID of dismissed intervention
  const [softShowReasoning, setSoftShowReasoning] = useState(false); // show reasoning_summary
  const [softFeedbackMode, setSoftFeedbackMode] = useState(false); // show feedback textarea
  const [softFeedbackText, setSoftFeedbackText] = useState("");
  const [softFeedbackThanks, setSoftFeedbackThanks] = useState(false); // show thanks message
  const [hardAlert, setHardAlert] = useState(null);    // { trigger_type, glucose, ... }
  const [showPush, setShowPush] = useState(null); // "soft" | "hard" | null

  useEffect(() => {
    if (!user) return;
    const uid = user.user_id;

    // Fetch profile for BMI
    fetch(`${API_BASE}/users/${uid}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.height_cm && data.weight_kg && data.height_cm > 0) {
          const val = data.weight_kg / ((data.height_cm / 100) ** 2);
          setBmi(val.toFixed(1));
        }
      })
      .catch(() => {
        // Fall back to local user data
        if (user.height_cm && user.weight_kg && user.height_cm > 0) {
          const val = user.weight_kg / ((user.height_cm / 100) ** 2);
          setBmi(val.toFixed(1));
        }
      });

    // Fetch meals today
    fetch(`${API_BASE}/health/meals-today?user_id=${uid}`)
      .then((res) => res.json())
      .then((data) => {
        setMealsLogged(`${data.count}/${data.total}`);
      })
      .catch(() => {});
  }, [user]);

  // ── Hard alert: check localStorage on mount ──
  useEffect(() => {
    const stored = localStorage.getItem("hard_alert");
    if (stored) {
      try {
        setHardAlert(JSON.parse(stored));
      } catch {}
    }
  }, []);

  // ── Soft alert: poll InterventionLog every 3s ──
  useEffect(() => {
    if (!user) return;
    let active = true;

    const poll = async () => {
      try {
        const data = await fetchInterventions(user.user_id, true);
        if (!active) return;
        // Find the newest unacknowledged soft intervention
        const soft = data.find(
          (iv) => !iv.trigger_type?.startsWith("hard") && iv.message_sent && !iv.user_ack
        );
        if (soft && !softAlert && soft.id !== softDismissedId) {
          setSoftAlert(soft);
        }
      } catch {
        // Gateway not running — silently ignore
      }
    };

    poll();
    const id = setInterval(poll, 3000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [user, softAlert, softDismissedId]);

  // ── Show push notification when alerts arrive ──
  useEffect(() => {
    if (softAlert && !softDismissedId) {
      setShowPush("soft");
      const timer = setTimeout(() => setShowPush((v) => v === "soft" ? null : v), 4000);
      return () => clearTimeout(timer);
    }
  }, [softAlert, softDismissedId]);

  useEffect(() => {
    if (hardAlert) {
      setShowPush("hard");
      const timer = setTimeout(() => setShowPush((v) => v === "hard" ? null : v), 4000);
      return () => clearTimeout(timer);
    }
  }, [hardAlert]);

  // ── Dismiss handlers ──
  const dismissSoftAlert = useCallback(() => {
    if (softAlert?.id) setSoftDismissedId(softAlert.id);
    setSoftAlert(null);
    setSoftShowReasoning(false);
    setSoftFeedbackMode(false);
    setSoftFeedbackText("");
    setSoftFeedbackThanks(false);
  }, [softAlert]);

  const handleSoftFeedbackSubmit = useCallback(() => {
    setSoftFeedbackThanks(true);
    setTimeout(() => {
      dismissSoftAlert();
    }, 1500);
  }, [dismissSoftAlert]);

  const dismissHardAlert = useCallback(() => {
    setHardAlert(null);
    localStorage.removeItem("hard_alert");
  }, []);

  if (loading || !user) return null;

  return (
    <div className="flex flex-col h-full bg-cream relative overflow-hidden">
      {/* ── Background blobs ── */}
      <div
        className="absolute z-0"
        style={{
          width: 500, height: 500, borderRadius: "50%",
          backgroundColor: "#EBE9E9",
          top: 250, left: 100,
        }}
      />
      <div
        className="absolute z-[1]"
        style={{
          width: 580, height: 580, borderRadius: "50%",
          backgroundColor: "#FBE6E1",
          top: -210, left: -250,
        }}
      />
      <div
        className="absolute z-[1]"
        style={{
          width: 650, height: 650, borderRadius: "50%",
          backgroundColor: "#CEF7EA",
          bottom: -300, left: -300,
        }}
      />

      {/* ── TopBar ── */}
      <div className="relative z-30">
        <TopBar title={t("nav_home")} transparent />
      </div>

      {/* ── Content ── */}
      <div className="relative z-10 flex-1 flex flex-col px-5 pb-4">

        {/* ====== SECTION 1: Top-left — Greeting + Soft Alert or Default ====== */}
        <div style={{ minHeight: 255 }}>
          <h2 className="text-2xl font-bold italic text-[#e8927c] mt-1">
            {t("good_morning")} {user.name.split(" ")[0]}!
          </h2>

          <p className="text-base italic text-[#F4B95D] mt-0.5">
            {t("how_feeling")}
          </p>

          <Link
            href="/chat"
            className="inline-block mt-3 px-6 py-2 text-sm font-medium text-gray-700 border border-[#e8c8a0] rounded-full bg-[#fce8d0]/40 hover:bg-[#fce8d0] w-fit"
          >
            {t("chat_with_ai")}
          </Link>

          <img
            src="/healthy_life.jpg"
            alt="Healthy lifestyle"
            className="w-[160px] h-auto object-contain mt-2 -ml-1"
          />
        </div>

        {/* ====== SECTION 2: Middle-right — Snapshot + Stats + Tasks + Flower ====== */}
        <div className="self-end -mt-20 mr-0 text-right w-[55%]">
          <h3 className="text-xl font-bold italic text-[#88B3F9] leading-tight">
            {t("todays_snapshot")}
          </h3>
          <div className="mt-3 space-y-0.5 text-sm text-gray-800 text-right pr-1">
            <p><span className="font-semibold">{t("bmi")}</span> {bmi}</p>
            <p><span className="font-semibold">{t("meals_logged")}</span> {mealsLogged}</p>
          </div>

          <Link
            href="/task"
            className="inline-block mt-3 px-5 py-1.5 text-sm font-medium text-gray-700 border border-gray-400 rounded-full hover:bg-gray-100"
          >
            {t("view_tasks")}
          </Link>

          <img
            src="/flower.jpg"
            alt="Decorative flower"
            className="w-[100px] h-auto object-contain mt-2 ml-auto"
          />
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* ====== SECTION 3: Bottom-left — Check your sugar + Chart ====== */}
        <div className="w-[70%]">
          <h3 className="text-2xl font-bold italic text-[#454545] leading-tight">
            {t("check_sugar")}
          </h3>
          <SugarChart userId={user.user_id} />
        </div>
      </div>

      {/* ── Soft Alert Modal Overlay ── */}
      {softAlert && (
        <>
          <div className="fixed inset-0 bg-black/30 z-40" />
          <div className="fixed inset-0 z-50 flex items-center justify-center px-8">
            <div className="bg-white rounded-2xl p-6 shadow-xl max-w-[340px] w-full border-2 border-yellow-400">
              {/* Icon */}
              <div className="flex justify-center mb-4">
                <div className="w-16 h-16 rounded-xl bg-yellow-50 flex items-center justify-center text-3xl">
                  ⚠️
                </div>
              </div>

              {/* Title */}
              <h3 className="text-xl font-bold text-yellow-600 mb-2 text-center">
                {t("better_safe")}
              </h3>

              {/* Confidence badge */}
              <div className="flex justify-center mb-3">
                {(() => {
                  let confidence;
                  try {
                    const decision = softAlert.agent_decision
                      ? JSON.parse(softAlert.agent_decision) : null;
                    confidence = decision?.confidence || "MEDIUM";
                  } catch { confidence = "MEDIUM"; }
                  const colors = {
                    HIGH: "bg-red-100 text-red-700 border-red-300",
                    MEDIUM: "bg-yellow-100 text-yellow-700 border-yellow-300",
                    LOW: "bg-green-100 text-green-700 border-green-300",
                  };
                  return (
                    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${colors[confidence] || colors.MEDIUM}`}>
                      {t("soft_alert_confidence")}: {confidence}
                    </span>
                  );
                })()}
              </div>

              {/* Message */}
              <p className="text-sm text-gray-600 leading-relaxed text-center">
                {softAlert.message_sent || t("soft_alert_msg")}
              </p>

              {/* State machine: buttons → reasoning → feedback → thanks */}
              {softFeedbackThanks ? (
                <p className="text-center mt-4 text-sm font-semibold text-green-600">
                  {t("soft_alert_feedback_thanks")}
                </p>
              ) : softFeedbackMode ? (
                /* Feedback textarea */
                <div className="mt-4">
                  <textarea
                    className="w-full border border-gray-300 rounded-lg p-2 text-sm resize-none focus:outline-none focus:border-yellow-400"
                    rows={3}
                    placeholder={t("soft_alert_feedback_placeholder")}
                    value={softFeedbackText}
                    onChange={(e) => setSoftFeedbackText(e.target.value)}
                  />
                  <button
                    onClick={handleSoftFeedbackSubmit}
                    disabled={!softFeedbackText.trim()}
                    className="mt-2 w-full py-2 text-sm font-medium text-white bg-yellow-500 rounded-full hover:bg-yellow-600 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {t("soft_alert_feedback_submit")}
                  </button>
                </div>
              ) : softShowReasoning ? (
                /* Reasoning summary + Good Enough / Give Feedback */
                <div className="mt-4">
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                    <p className="text-xs text-gray-700 leading-relaxed">
                      {(() => {
                        try {
                          const decision = softAlert.agent_decision
                            ? JSON.parse(softAlert.agent_decision)
                            : null;
                          return decision?.reasoning_summary || t("soft_alert_demo_reasoning");
                        } catch { return t("soft_alert_demo_reasoning"); }
                      })()}
                    </p>
                  </div>
                  <div className="mt-3 space-y-2">
                    <button
                      onClick={dismissSoftAlert}
                      className="w-full py-2 text-sm font-bold text-white bg-yellow-500 rounded-full hover:bg-yellow-600"
                    >
                      {t("soft_alert_good_enough")}
                    </button>
                    <button
                      onClick={() => setSoftFeedbackMode(true)}
                      className="w-full py-2 text-sm font-medium text-yellow-600 border border-yellow-400 rounded-full hover:bg-yellow-50"
                    >
                      {t("soft_alert_not_helpful")}
                    </button>
                  </div>
                </div>
              ) : (
                /* Initial buttons */
                <div className="mt-5 space-y-2">
                  <button
                    onClick={dismissSoftAlert}
                    className="w-full py-2 text-sm font-bold text-white bg-yellow-500 rounded-full hover:bg-yellow-600"
                  >
                    {t("soft_alert_got_it")}
                  </button>
                  <button
                    onClick={() => setSoftShowReasoning(true)}
                    className="w-full py-2 text-sm font-medium text-yellow-600 border border-yellow-400 rounded-full hover:bg-yellow-50"
                  >
                    {t("soft_alert_why")}
                  </button>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* ── Hard Alert Modal Overlay ── */}
      {hardAlert && (
        <>
          <div className="fixed inset-0 bg-black/30 z-40" />
          <div className="fixed inset-0 z-50 flex items-center justify-center px-8">
            <div className="bg-white rounded-2xl p-6 shadow-xl max-w-[340px] w-full border-2 border-red-400">
              {/* Icon */}
              <div className="flex justify-center mb-4">
                <div className="w-16 h-16 rounded-xl bg-red-100 flex items-center justify-center text-3xl">
                  🍬
                </div>
              </div>

              {/* Title */}
              <h3 className="text-xl font-bold text-red-600 mb-3 text-center">
                {t("alert_hypo")}
              </h3>

              {/* Message */}
              <p className="text-sm text-gray-600 leading-relaxed text-center">
                {t("alert_hypo_msg")}
              </p>

              {hardAlert.glucose && (
                <p className="text-center mt-3 text-sm font-semibold text-red-500">
                  Current glucose: {hardAlert.glucose} mmol/L
                </p>
              )}

              <button
                onClick={dismissHardAlert}
                className="mt-5 w-full py-2 text-sm font-bold text-white bg-red-500 rounded-full hover:bg-red-600"
              >
                {t("soft_alert_got_it")}
              </button>
            </div>
          </div>
        </>
      )}

      {/* ── Simulated Push Notification ── */}
      {showPush && (
        <div
          className="fixed top-4 left-4 right-4 z-[60] animate-slide-down cursor-pointer"
          onClick={() => setShowPush(null)}
        >
          <div className={`flex items-center gap-3 p-3 rounded-2xl shadow-lg backdrop-blur-md ${
            showPush === "hard"
              ? "bg-red-50/95 border border-red-200"
              : "bg-yellow-50/95 border border-yellow-200"
          }`}>
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg shrink-0 ${
              showPush === "hard" ? "bg-red-100" : "bg-yellow-100"
            }`}>
              {showPush === "hard" ? "🍬" : "⚠️"}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-gray-900 uppercase tracking-wide">
                {t(showPush === "hard" ? "hard_push_title" : "soft_push_title")}
              </p>
              <p className="text-xs text-gray-600 truncate">
                {t(showPush === "hard" ? "hard_push_body" : "soft_push_body")}
              </p>
            </div>
            <span className="text-[10px] text-gray-400 shrink-0">now</span>
          </div>
        </div>
      )}
    </div>
  );
}
