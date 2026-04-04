"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import TopBar from "../../components/TopBar";
import { useAuth } from "../../lib/useAuth";
import { useTranslation } from "../../lib/i18n";

const API_BASE = "http://localhost:8080";

function getFlowerCount(points) {
  return Math.min(Math.floor(points / 500), 25);
}

export default function GardenPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  const [points, setPoints] = useState(null);
  const [friends, setFriends] = useState([]);

  useEffect(() => {
    if (!user) return;

    // Fetch my points
    fetch(`${API_BASE}/garden/my?user_id=${user.user_id}`)
      .then((r) => r.json())
      .then((data) => setPoints(data))
      .catch((e) => console.error("Failed to fetch garden points:", e));

    // Fetch friends
    fetch(`${API_BASE}/garden/friends?user_id=${user.user_id}`)
      .then((r) => r.json())
      .then((data) => setFriends(data.friends || []))
      .catch((e) => console.error("Failed to fetch friends:", e));
  }, [user]);

  if (loading || !user) return null;

  const flowerCount = points ? getFlowerCount(points.accumulated_points) : 0;

  // Render flowers: center big, sides small, grow from center outward
  const renderFlowers = () => {
    if (flowerCount === 0) return null;
    // Order: center first, then alternate right/left
    const positions = [
      { size: "w-[120px]", mb: "mb-[-10px]" },  // center big
      { size: "w-[65px]", mb: "" },               // right 1
      { size: "w-[65px]", mb: "" },               // left 1
      { size: "w-[65px]", mb: "" },               // right 2
      { size: "w-[65px]", mb: "" },               // left 2
    ];

    const flowers = [];
    for (let i = 0; i < Math.min(flowerCount, 5); i++) {
      flowers.push(
        <img
          key={i}
          src="/flower.jpg"
          alt="Plant"
          className={`${positions[i].size} object-contain ${positions[i].mb}`}
        />
      );
    }

    // Reorder: [left2, left1, center, right1, right2]
    const ordered = [];
    if (flowerCount >= 5) ordered.push(flowers[4]); // left 2
    if (flowerCount >= 3) ordered.push(flowers[2]); // left 1
    ordered.push(flowers[0]); // center (always)
    if (flowerCount >= 2) ordered.push(flowers[1]); // right 1
    if (flowerCount >= 4) ordered.push(flowers[3]); // right 2

    return ordered;
  };

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title={t("garden_title")} transparent />

      {/* ── Garden display ── */}
      <div className="flex items-end justify-center w-full px-2 mt-20 mb-2 overflow-hidden">
        {renderFlowers()}
      </div>

      {/* ── Points display ── */}
      {points && (
        <p className="text-center text-sm text-[#7cb342] font-semibold mb-4">
          {points.accumulated_points} {t("points")}
        </p>
      )}

      {/* ── Friends section ── */}
      <div className="px-6 pb-6">
        <h3 className="text-xl font-bold italic text-[#7cb342] mb-3">{t("friends")}</h3>

        <div>
          {friends.map((friend, i) => (
            <div key={friend.user_id}>
              <div className="flex items-center py-3 px-4 bg-[#f0e6d6] rounded-lg">
                <img
                  src={friend.avatar}
                  alt={friend.name}
                  className="w-[55px] h-[55px] rounded-full object-cover"
                />
                <span className="ml-3 text-sm font-semibold text-gray-700">{friend.name}</span>
                <span className="flex-1" />
                <button
                  onClick={() => router.push(`/garden/visit?id=${friend.user_id}`)}
                  className="text-sm font-semibold text-gray-800 hover:text-[#7cb342] transition-colors"
                >
                  {t("visit")}
                </button>
              </div>
              {i < friends.length - 1 && <div className="h-3" />}
            </div>
          ))}
          {friends.length === 0 && (
            <p className="text-sm text-gray-400 italic">{t("no_friends_yet") || "No friends yet"}</p>
          )}
        </div>
      </div>
    </div>
  );
}
