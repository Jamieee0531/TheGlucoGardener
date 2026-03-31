"use client";

import Link from "next/link";
import TopBar from "../components/TopBar";
import SugarChart from "../components/SugarChart";
import { useAuth } from "../lib/useAuth";
import { useTranslation } from "../lib/i18n";

export default function HomePage() {
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  if (loading || !user) return null;

  return (
    <div className="flex flex-col h-full bg-cream relative overflow-hidden">
      {/* ── Background blobs ── */}
      {/* Gray/beige circle - LOWEST z, middle-right */}
      <div
        className="absolute z-0"
        style={{
          width: 500, height: 500, borderRadius: "50%",
          backgroundColor: "#EBE9E9",
          top: 250, left: 100,
        }}
      />
      {/* Pink circle - HIGH z, top-left quarter visible */}
      <div
        className="absolute z-[1]"
        style={{
          width: 580, height: 580, borderRadius: "50%",
          backgroundColor: "#FBE6E1",
          top: -210, left: -250,
        }}
      />
      {/* Mint circle - MID z, bottom-left, only top-right quarter visible */}
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
    </div>
  );
}
