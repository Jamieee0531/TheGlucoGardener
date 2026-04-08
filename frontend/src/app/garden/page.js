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

  // Sort friends + self by points (descending) for ranking
  const selfEntry = points ? {
    user_id: user.user_id,
    name: user.name,
    avatar: user.avatar || `/${user.user_id === "user_001" ? "avatar_1" : user.user_id === "user_002" ? "avatar_2" : "avatar_3"}.jpg`,
    accumulated_points: points.accumulated_points || 0,
    isSelf: true,
  } : null;
  const rankedFriends = [...friends, ...(selfEntry ? [selfEntry] : [])].sort(
    (a, b) => (b.accumulated_points || 0) - (a.accumulated_points || 0)
  );

  // Hardcoded messages for demo (Mdm Chen scenario)
  const messages = user.user_id === "user_001"
    ? [
        { from: "Sarah (daughter)", text: "妈妈，加油！💪", time: "Today, 9:12 AM" },
        { from: "Marcus", text: "Keep it up, Mdm Chen! 🌻", time: "Yesterday, 3:45 PM" },
      ]
    : user.user_id === "user_002"
    ? [
        { from: "Sarah (daughter)", text: "爸爸，加油！💪", time: "Today, 8:45 AM" },
        { from: "Mdm Chen", text: "Marcus, you're doing great! 🌸", time: "Today, 10:30 AM" },
      ]
    : [];

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
      <div className="flex-1 overflow-y-auto">

      {/* ── Garden display ── */}
      <div className="flex items-end justify-center w-full px-2 mt-8 mb-2">
        {renderFlowers()}
      </div>

      {/* ── Points display ── */}
      {points && (
        <p className="text-center text-sm text-[#7cb342] font-semibold mb-4">
          {points.accumulated_points} {t("points")}
        </p>
      )}

      {/* ── Message Board ── */}
      {messages.length > 0 && (
        <div className="px-6 mb-4">
          <h3 className="text-xl font-bold italic text-[#7cb342] mb-2">{t("message_board")}</h3>
          <div className="space-y-2">
            {messages.map((msg, i) => (
              <div
                key={i}
                className="bg-white/80 rounded-xl px-4 py-3 shadow-sm border border-[#e8e0d4]"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-bold text-[#5a8a2e]">{msg.from}</span>
                  <span className="text-xs text-gray-400">{msg.time}</span>
                </div>
                <p className="text-sm text-gray-700">{msg.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Friends section ── */}
      <div className="px-6 pb-6">
        <h3 className="text-xl font-bold italic text-[#7cb342] mb-3">{t("friends")}</h3>

        <div>
          {rankedFriends.map((friend, i) => (
            <div key={friend.user_id}>
              <div className="flex items-center py-3 px-4 bg-[#f0e6d6] rounded-lg">
                {/* Rank */}
                <span className="text-lg font-bold italic text-[#7cb342] w-6 text-center mr-2">
                  {i + 1}
                </span>
                <img
                  src={friend.avatar}
                  alt={friend.name}
                  className="w-[55px] h-[55px] rounded-full object-cover"
                />
                <div className="ml-3 flex-1">
                  <span className="text-sm font-semibold text-gray-700">
                    {friend.name}{friend.isSelf ? " (You)" : ""}
                  </span>
                  <p className="text-xs text-[#7cb342]">
                    🌸 ×{getFlowerCount(friend.accumulated_points || 0)} {t("flowers")}
                  </p>
                </div>
                {!friend.isSelf && (
                  <button
                    onClick={() => router.push(`/garden/visit?id=${friend.user_id}`)}
                    className="text-sm font-semibold text-gray-800 hover:text-[#7cb342] transition-colors"
                  >
                    {t("visit")}
                  </button>
                )}
              </div>
              {i < rankedFriends.length - 1 && <div className="h-3" />}
            </div>
          ))}
          {friends.length === 0 && (
            <p className="text-sm text-gray-400 italic">{t("no_friends_yet") || "No friends yet"}</p>
          )}
        </div>
      </div>
      </div>
    </div>
  );
}
