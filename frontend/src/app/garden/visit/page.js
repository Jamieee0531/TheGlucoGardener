"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "../../../lib/useAuth";
import { useTranslation } from "../../../lib/i18n";
import { API_BASE } from "../../../lib/config";

function getFlowerCount(points) {
  return Math.min(Math.floor(points / 500), 9);
}

// 3x3 grid positions (row, col), ordered from center outward
const GRID_POSITIONS = [
  [1, 1], // center
  [0, 1], // top-center
  [2, 1], // bottom-center
  [1, 0], // center-left
  [1, 2], // center-right
  [0, 0], // top-left
  [0, 2], // top-right
  [2, 0], // bottom-left
  [2, 2], // bottom-right
];

export default function FriendGardenPageWrapper() {
  return (
    <Suspense fallback={null}>
      <FriendGardenPage />
    </Suspense>
  );
}

function FriendGardenPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading } = useAuth();
  const { t } = useTranslation();

  const friendId = searchParams.get("id");
  const [friend, setFriend] = useState(null);
  const [points, setPoints] = useState(0);
  const [watered, setWatered] = useState(false);

  useEffect(() => {
    if (!user || !friendId) return;

    // Fetch friend's data from the friends list
    fetch(`${API_BASE}/garden/friends?user_id=${user.user_id}`)
      .then((r) => r.json())
      .then((data) => {
        const f = (data.friends || []).find((fr) => fr.user_id === friendId);
        if (f) {
          setFriend(f);
          setPoints(f.accumulated_points);
        }
      })
      .catch((e) => console.error("Failed to fetch friend:", e));
  }, [user, friendId]);

  if (loading || !user) return null;
  if (!friendId) {
    router.replace("/garden");
    return null;
  }

  const flowerCount = getFlowerCount(points);

  const handleWater = async () => {
    if (watered) return;
    try {
      const res = await fetch(`${API_BASE}/garden/water`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, friend_id: friendId }),
      });
      if (res.ok) {
        setWatered(true);
        // Refresh friend's points from backend
        const refreshRes = await fetch(`${API_BASE}/garden/friends?user_id=${user.user_id}`);
        const refreshData = await refreshRes.json();
        const updated = (refreshData.friends || []).find((fr) => fr.user_id === friendId);
        if (updated) setPoints(updated.accumulated_points);
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to water");
      }
    } catch (e) {
      console.error("Water failed:", e);
    }
  };

  // Show loading while fetching friend data
  if (!friend) {
    return (
      <div className="flex flex-col h-full bg-cream items-center justify-center">
        <p className="text-gray-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-cream relative overflow-hidden">
      {/* Soft background gradient */}
      <div
        className="absolute inset-0 z-0"
        style={{
          background: "radial-gradient(ellipse at 50% 30%, #e8f5e9 0%, #FEF8EB 60%)",
        }}
      />

      {/* Back button */}
      <div className="relative z-10 flex items-center px-4 pt-14 pb-2">
        <button
          onClick={() => router.push("/garden")}
          className="flex items-center gap-1 text-gray-500 hover:text-gray-700 transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
          <span className="text-sm">{t("back")}</span>
        </button>
      </div>

      {/* Friend info */}
      <div className="relative z-10 flex flex-col items-center mt-2 mb-4">
        <div className="w-[64px] h-[64px] rounded-full overflow-hidden ring-3 ring-[#7cb342]/30 shadow-md">
          <img src={friend.avatar} alt={friend.name} className="w-full h-full object-cover" />
        </div>
        <h2 className="text-lg font-bold italic text-[#5a8a2e] mt-2">
          {friend.name}{t("garden_of")}
        </h2>
        <p className="text-xs text-[#7cb342] font-semibold mt-0.5">
          {points} {t("points")}
        </p>
      </div>

      {/* Garden area */}
      <div className="relative z-10 flex-1 flex items-center justify-center">
        <div className="relative" style={{ width: 300, height: 300 }}>

          {/* Isometric grass platform */}
          <div
            style={{
              width: 220,
              height: 220,
              position: "absolute",
              left: "50%",
              top: "55%",
              transform: "translate(-50%, -50%) rotateX(55deg) rotateZ(45deg)",
              borderRadius: 12,
              background: "linear-gradient(135deg, #a8d870 0%, #8bc34a 40%, #7cb342 100%)",
              boxShadow: "0 8px 0 #5a8a2e, 0 12px 0 #4a7a20, 0 16px 8px rgba(0,0,0,0.15)",
            }}
          >
            {/* 3x3 grid lines */}
            {[1, 2].map((i) => (
              <div key={`h-${i}`} style={{ position: "absolute", top: `${i * 33.33}%`, left: 0, right: 0, height: 1, backgroundColor: "rgba(255,255,255,0.2)" }} />
            ))}
            {[1, 2].map((i) => (
              <div key={`v-${i}`} style={{ position: "absolute", left: `${i * 33.33}%`, top: 0, bottom: 0, width: 1, backgroundColor: "rgba(255,255,255,0.2)" }} />
            ))}
          </div>

          {/* Flowers — 3x3 grid cell centers */}
          {Array.from({ length: flowerCount }).map((_, i) => {
            const [row, col] = GRID_POSITIONS[i] || [1, 1];
            const cx = 153 + (col - row) * 52;
            const cy = 73 + (col + row) * 30;
            return (
              <img
                key={i}
                src="/flower.jpg"
                alt="Flower"
                style={{
                  position: "absolute",
                  left: cx - 27,
                  top: cy - 55,
                  width: 55,
                  height: "auto",
                  zIndex: row + col,
                  filter: "drop-shadow(0 4px 4px rgba(0,0,0,0.2))",
                  animation: `sway ${2 + (i % 3) * 0.5}s ease-in-out infinite alternate`,
                  animationDelay: `${i * 0.2}s`,
                }}
              />
            );
          })}

          {/* Empty soil dots on unfilled grid cells */}
          {GRID_POSITIONS.slice(flowerCount, 9).map(([row, col], i) => {
            const cx = 143 + (col - row) * 52;
            const cy = 103 + (col + row) * 30;
            return (
              <div
                key={`empty-${i}`}
                style={{
                  position: "absolute",
                  left: cx - 5,
                  top: cy - 3,
                  width: 10,
                  height: 6,
                  borderRadius: "50%",
                  backgroundColor: "rgba(90,138,46,0.35)",
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Water button */}
      <div className="relative z-10 px-8 pb-10">
        <button
          onClick={handleWater}
          disabled={watered}
          className="w-full py-3.5 rounded-full text-white font-semibold text-sm shadow-lg transition-all active:scale-95 disabled:opacity-50"
          style={{
            background: watered
              ? "linear-gradient(135deg, #9e9e9e, #757575)"
              : "linear-gradient(135deg, #7cb342, #558b2f)",
          }}
        >
          {watered ? t("watered") || "Watered!" : t("water_garden")}
        </button>
        <p className="text-center text-xs text-gray-400 mt-2 italic">
          {t("visit_once_per_day")}
        </p>
      </div>

      {/* Sway animation */}
      <style jsx>{`
        @keyframes sway {
          0% { transform: rotate(-2deg); }
          100% { transform: rotate(2deg); }
        }
      `}</style>
    </div>
  );
}
