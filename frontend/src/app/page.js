"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import TopBar from "../components/TopBar";
import SugarChart from "../components/SugarChart";
import { useAuth } from "../lib/useAuth";
import { useTranslation } from "../lib/i18n";
import { fetchInterventions } from "../lib/gatewayApi";

const API_BASE = "http://localhost:8080";

export default function HomePage() {
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  const [bmi, setBmi] = useState("—");
  const [mealsLogged, setMealsLogged] = useState("0/3");

  // Alert states
  const [softAlert, setSoftAlert] = useState(null);   // { message_sent, trigger_type, ... }
  const [softDismissedId, setSoftDismissedId] = useState(null); // ID of dismissed intervention
  const [hardAlert, setHardAlert] = useState(null);    // { trigger_type, glucose, ... }

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

  // ── Dismiss handlers ──
  const dismissSoftAlert = useCallback(() => {
    if (softAlert?.id) setSoftDismissedId(softAlert.id);
    setSoftAlert(null);
  }, [softAlert]);

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

          {softAlert ? (
            <>
              {/* Soft alert state */}
              <h3 className="text-lg font-bold italic text-[#F4B95D] mt-1.5">
                {t("heads_up")}
              </h3>
              <p className="text-base italic text-[#F4B95D] mt-1 leading-snug max-w-[260px]">
                {softAlert.message_sent}
              </p>

              <Link
                href="/chat"
                className="inline-block mt-2 px-6 py-2 text-sm font-medium text-gray-700 border border-[#e8c8a0] rounded-full bg-[#fce8d0]/40 hover:bg-[#fce8d0] w-fit"
              >
                {t("chat_with_ai")}
              </Link>

              <button
                onClick={dismissSoftAlert}
                className="block mt-2 px-5 py-1.5 text-sm font-bold text-white bg-[#e8927c] rounded-full hover:bg-[#d4816c]"
              >
                Mark as read
              </button>
            </>
          ) : (
            <>
              {/* Default state */}
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
            </>
          )}
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

      {/* ── Hard Alert Modal Overlay ── */}
      {hardAlert && (
        <>
          <div className="fixed inset-0 bg-black/30 z-40" />
          <div className="fixed inset-0 z-50 flex items-center justify-center px-8">
            <div className="bg-white rounded-2xl p-6 shadow-xl relative max-w-[340px] w-full border-2 border-red-400">
              {/* Close button */}
              <button
                onClick={dismissHardAlert}
                className="absolute top-3 right-3 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 text-lg"
              >
                &times;
              </button>

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
              <p className="text-base text-gray-600 leading-relaxed text-center">
                {t("alert_hypo_msg")}
              </p>

              {hardAlert.glucose && (
                <p className="text-center mt-3 text-sm font-semibold text-red-500">
                  Current glucose: {hardAlert.glucose} mmol/L
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
