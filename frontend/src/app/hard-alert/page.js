"use client";

import { useState } from "react";
import Link from "next/link";
import TopBar from "../../components/TopBar";
import SugarChart from "../../components/SugarChart";

export default function HardAlertPage() {
  const [showAlert, setShowAlert] = useState(true);

  return (
    <div className="flex flex-col h-full bg-cream relative overflow-hidden">
      {/* ── Background blobs ── */}
      {/* Gray/beige circle - LOWEST z, middle-right */}
      <div
        className="absolute z-0"
        style={{
          width: 500, height: 500, borderRadius: "50%",
          backgroundColor: "#e8ddd4",
          top: 250, left: 100,
        }}
      />
      {/* Pink circle - HIGH z, top-left quarter visible */}
      <div
        className="absolute z-[1]"
        style={{
          width: 580, height: 580, borderRadius: "50%",
          backgroundColor: "#f5cdc6",
          top: -210, left: -250,
        }}
      />
      {/* Mint circle - MID z, bottom-left, only top-right quarter visible */}
      <div
        className="absolute z-[1]"
        style={{
          width: 650, height: 650, borderRadius: "50%",
          backgroundColor: "#b8e6da",
          bottom: -300, left: -300,
        }}
      />

      {/* ── TopBar ── */}
      <div className="relative z-30">
        <TopBar title="Home" transparent />
      </div>

      {/* ── Content (same as Home) ── */}
      <div className="relative z-10 flex-1 flex flex-col px-5 pb-4">

        {/* ====== SECTION 1: Top-left — Greeting + Chat + Illustration ====== */}
        <div>
          <h2 className="text-2xl font-bold italic text-[#e8927c] mt-1">
            Good Morning, User!
          </h2>
          <p className="text-base italic text-[#d4a44a] mt-0.5">
            How are you feeling today?
          </p>

          <Link
            href="/chat"
            className="inline-block mt-3 px-6 py-2 text-sm font-medium text-gray-700 border border-[#e8c8a0] rounded-full bg-[#fce8d0]/40 hover:bg-[#fce8d0] w-fit"
          >
            &gt;&gt;Chat with AI
          </Link>

          <img
            src="/healthy_life.jpg"
            alt="Healthy lifestyle"
            className="w-[160px] h-auto object-contain mt-2 -ml-1"
          />
        </div>

        {/* ====== SECTION 2: Middle-right — Snapshot + Stats + Tasks + Flower ====== */}
        <div className="self-end -mt-20 mr-0 text-right w-[55%]">
          <h3 className="text-xl font-bold italic text-[#6b7ec2] leading-tight">
            Today&apos;s<br />Snapshot
          </h3>
          <div className="mt-3 space-y-0.5 text-sm text-gray-800 text-right pr-1">
            <p><span className="font-semibold">Step Count:</span> 1234</p>
            <p><span className="font-semibold">BMI:</span> 23.0</p>
            <p><span className="font-semibold">Meals logged:</span> 1/3</p>
          </div>

          <Link
            href="/task"
            className="inline-block mt-3 px-5 py-1.5 text-sm font-medium text-gray-700 border border-gray-400 rounded-full hover:bg-gray-100"
          >
            &gt;&gt;View your tasks
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
          <h3 className="text-2xl font-bold italic text-[#d4a44a] leading-tight">
            Check your<br />sugar
          </h3>
          <SugarChart />
        </div>
      </div>

      {/* ── Hard Alert Modal Overlay ── */}
      {showAlert && (
        <>
          <div className="fixed inset-0 bg-black/30 z-40" />
          <div className="fixed inset-0 z-50 flex items-center justify-center px-8">
            <div className="bg-white rounded-2xl p-6 shadow-xl relative max-w-[340px] w-full">
              {/* Close button */}
              <button
                onClick={() => setShowAlert(false)}
                className="absolute top-3 right-3 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 text-lg"
              >
                &times;
              </button>

              {/* Candy icon on yellow background */}
              <div className="flex justify-center mb-4">
                <div className="w-16 h-16 rounded-xl bg-[#fef9e7] flex items-center justify-center text-3xl">
                  🍬
                </div>
              </div>

              {/* Title */}
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                Alert! Potential Hypoglycemia
              </h3>

              {/* Description */}
              <p className="text-base text-gray-400 leading-relaxed">
                Your blood sugar level appears to be low. Please consider having a quick source of sugar and check your level again.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
