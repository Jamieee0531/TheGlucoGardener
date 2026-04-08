"use client";

import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import TopBar from "../../components/TopBar";
import SugarChart from "../../components/SugarChart";
import { useAuth } from "../../lib/useAuth";
import { useTranslation } from "../../lib/i18n";

export default function SoftAlertPage() {
  const { user, loading } = useAuth();
  const { t } = useTranslation();

  const [showAlert, setShowAlert] = useState(true);
  const [showReasoning, setShowReasoning] = useState(false);
  const [feedbackMode, setFeedbackMode] = useState(false);
  const [feedbackText, setFeedbackText] = useState("");
  const [feedbackThanks, setFeedbackThanks] = useState(false);
  const [showPush, setShowPush] = useState(true);

  // Auto-dismiss push after 4s
  useEffect(() => {
    const timer = setTimeout(() => setShowPush(false), 4000);
    return () => clearTimeout(timer);
  }, []);

  const dismissAlert = useCallback(() => {
    setShowAlert(false);
    setShowReasoning(false);
    setFeedbackMode(false);
    setFeedbackText("");
    setFeedbackThanks(false);
  }, []);

  const handleFeedbackSubmit = useCallback(() => {
    setFeedbackThanks(true);
    setTimeout(() => dismissAlert(), 1500);
  }, [dismissAlert]);

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

        {/* ====== SECTION 1: Top-left — Greeting ====== */}
        <div style={{ minHeight: 255 }}>
          <h2 className="text-2xl font-bold italic text-[#e8927c] -mt-1">
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
            <p><span className="font-semibold">Step Count:</span> 1234</p>
            <p><span className="font-semibold">{t("bmi")}</span> 23.0</p>
            <p><span className="font-semibold">{t("meals_logged")}</span> 1/3</p>
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
          <SugarChart />
        </div>
      </div>

      {/* ── Soft Alert Modal Overlay ── */}
      {showAlert && (
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
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold border bg-yellow-100 text-yellow-700 border-yellow-300">
                  {t("soft_alert_confidence")}: MEDIUM
                </span>
              </div>

              {/* Message */}
              <p className="text-sm text-gray-600 leading-relaxed text-center">
                {t("soft_alert_msg")}
              </p>

              {/* State machine: buttons → reasoning → feedback → thanks */}
              {feedbackThanks ? (
                <p className="text-center mt-4 text-sm font-semibold text-green-600">
                  {t("soft_alert_feedback_thanks")}
                </p>
              ) : feedbackMode ? (
                /* Feedback textarea */
                <div className="mt-4">
                  <textarea
                    className="w-full border border-gray-300 rounded-lg p-2 text-sm resize-none focus:outline-none focus:border-yellow-400"
                    rows={3}
                    placeholder={t("soft_alert_feedback_placeholder")}
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                  />
                  <button
                    onClick={handleFeedbackSubmit}
                    disabled={!feedbackText.trim()}
                    className="mt-2 w-full py-2 text-sm font-medium text-white bg-yellow-500 rounded-full hover:bg-yellow-600 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {t("soft_alert_feedback_submit")}
                  </button>
                </div>
              ) : showReasoning ? (
                /* Reasoning summary + Good Enough / Give Feedback */
                <div className="mt-4">
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                    <p className="text-xs text-gray-700 leading-relaxed">
                      {t("soft_alert_demo_reasoning")}
                    </p>
                  </div>
                  <div className="mt-3 space-y-2">
                    <button
                      onClick={dismissAlert}
                      className="w-full py-2 text-sm font-bold text-white bg-yellow-500 rounded-full hover:bg-yellow-600"
                    >
                      {t("soft_alert_good_enough")}
                    </button>
                    <button
                      onClick={() => setFeedbackMode(true)}
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
                    onClick={dismissAlert}
                    className="w-full py-2 text-sm font-bold text-white bg-yellow-500 rounded-full hover:bg-yellow-600"
                  >
                    {t("soft_alert_got_it")}
                  </button>
                  <button
                    onClick={() => setShowReasoning(true)}
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

      {/* ── Simulated Push Notification ── */}
      {showPush && (
        <div
          className="fixed top-4 left-4 right-4 z-[60] animate-slide-down cursor-pointer"
          onClick={() => setShowPush(false)}
        >
          <div className="flex items-center gap-3 p-3 rounded-2xl shadow-lg backdrop-blur-md bg-yellow-50/95 border border-yellow-200">
            <div className="w-10 h-10 rounded-xl bg-yellow-100 flex items-center justify-center text-lg shrink-0">
              ⚠️
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-gray-900 uppercase tracking-wide">
                {t("soft_push_title")}
              </p>
              <p className="text-xs text-gray-600 truncate">
                {t("soft_push_body")}
              </p>
            </div>
            <span className="text-[10px] text-gray-400 shrink-0">now</span>
          </div>
        </div>
      )}
    </div>
  );
}
