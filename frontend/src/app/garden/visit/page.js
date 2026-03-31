"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "../../../lib/useAuth";
import { TEST_USERS } from "../../../lib/users";
import { useTranslation } from "../../../lib/i18n";

function getFlowerCount(points) {
  return Math.min(Math.floor(points / 500), 25);
}

// Pre-defined grid positions for flowers on the isometric field (row, col)
const GRID_POSITIONS = [
  [2, 2], [1, 3], [3, 1], [0, 2], [2, 4],
  [4, 2], [1, 1], [3, 3], [0, 4], [4, 0],
  [2, 0], [0, 0], [4, 4], [1, 0], [3, 4],
  [0, 1], [2, 3], [4, 3], [1, 4], [3, 0],
  [0, 3], [2, 1], [4, 1], [1, 2], [3, 2],
];

// Mock points for demo (will come from DB later)
const MOCK_POINTS = {
  user_001: 1200,
  user_002: 800,
  user_003: 350,
};

export default function FriendGardenPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading } = useAuth();
  const { t } = useTranslation();

  const friendId = searchParams.get("id");
  const friend = TEST_USERS.find((u) => u.user_id === friendId);

  if (loading || !user) return null;
  if (!friend) {
    router.replace("/garden");
    return null;
  }

  const points = MOCK_POINTS[friendId] || 0;
  const flowerCount = getFlowerCount(points);

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

          {/* Isometric grass platform (no flowers inside) */}
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
            {/* Grid lines */}
            {[1, 2, 3, 4].map((i) => (
              <div key={`h-${i}`} style={{ position: "absolute", top: `${i * 20}%`, left: 0, right: 0, height: 1, backgroundColor: "rgba(255,255,255,0.15)" }} />
            ))}
            {[1, 2, 3, 4].map((i) => (
              <div key={`v-${i}`} style={{ position: "absolute", left: `${i * 20}%`, top: 0, bottom: 0, width: 1, backgroundColor: "rgba(255,255,255,0.15)" }} />
            ))}
          </div>

          {/* Flowers floating above the grass (NOT inside the rotated div) */}
          {Array.from({ length: flowerCount }).map((_, i) => {
            const [row, col] = GRID_POSITIONS[i] || [2, 2];
            // Map grid positions to pixel positions on the isometric projection
            const x = 128 + (col - row) * 22;
            const y = 110 + (col + row) * 13;
            return (
              <img
                key={i}
                src="/flower.jpg"
                alt="Flower"
                style={{
                  position: "absolute",
                  left: x,
                  top: y - 45,
                  width: 50,
                  height: "auto",
                  filter: "drop-shadow(0 4px 4px rgba(0,0,0,0.2))",
                  animation: `sway ${2 + (i % 3) * 0.5}s ease-in-out infinite alternate`,
                  animationDelay: `${i * 0.2}s`,
                }}
              />
            );
          })}

          {/* Empty soil dots on the grass */}
          {GRID_POSITIONS.slice(flowerCount, 10).map(([row, col], i) => {
            const x = 128 + (col - row) * 22;
            const y = 110 + (col + row) * 13;
            return (
              <div
                key={`empty-${i}`}
                style={{
                  position: "absolute",
                  left: x + 18,
                  top: y - 5,
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

      {/* Visit bonus button */}
      <div className="relative z-10 px-8 pb-10">
        <button
          onClick={() => {
            // TODO: connect to backend for actual point update
            alert(t("visited_garden", { name: friend.name }));
          }}
          className="w-full py-3.5 rounded-full text-white font-semibold text-sm shadow-lg transition-all active:scale-95"
          style={{
            background: "linear-gradient(135deg, #7cb342, #558b2f)",
          }}
        >
          {t("water_garden")}
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
