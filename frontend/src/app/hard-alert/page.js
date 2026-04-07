"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import TopBar from "../../components/TopBar";
import SugarChart from "../../components/SugarChart";
import { useAuth } from "../../lib/useAuth";
import { useTranslation } from "../../lib/i18n";

export default function HardAlertPage() {
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  const [showAlert, setShowAlert] = useState(true);
  const [showPush, setShowPush] = useState(true);

  // Auto-dismiss push after 4s
  useEffect(() => {
    const timer = setTimeout(() => setShowPush(false), 4000);
    return () => clearTimeout(timer);
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

      {/* ── Content (same as Home) ── */}
      <div className="relative z-10 flex-1 flex flex-col px-5 pb-4">

        {/* ====== SECTION 1: Top-left — Greeting + Chat + Illustration ====== */}
        <div>
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

      {/* ── Hard Alert Modal Overlay ── */}
      {showAlert && (
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

              <button
                onClick={() => setShowAlert(false)}
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
          onClick={() => setShowPush(false)}
        >
          <div className="flex items-center gap-3 p-3 rounded-2xl shadow-lg backdrop-blur-md bg-red-50/95 border border-red-200">
            <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center text-lg shrink-0">
              🍬
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-gray-900 uppercase tracking-wide">
                {t("hard_push_title")}
              </p>
              <p className="text-xs text-gray-600 truncate">
                {t("hard_push_body")}
              </p>
            </div>
            <span className="text-[10px] text-gray-400 shrink-0">now</span>
          </div>
        </div>
      )}
    </div>
  );
}
