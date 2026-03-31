"use client";

import { useRouter } from "next/navigation";
import TopBar from "../../components/TopBar";
import { useAuth } from "../../lib/useAuth";
import { TEST_USERS } from "../../lib/users";

export default function GardenPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  if (loading || !user) return null;

  const friends = TEST_USERS.filter((u) => u.user_id !== user.user_id);

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title="Garden" transparent />

      {/* ── Garden display — one row of flowers, big center small sides, bottoms aligned ── */}
      <div className="flex items-end justify-center w-full px-2 mt-20 mb-6 overflow-hidden">
        <img src="/flower.jpg" alt="Plant" className="w-[65px] object-contain" />
        <img src="/flower.jpg" alt="Plant" className="w-[65px] object-contain" />
        <img src="/flower.jpg" alt="Plant" className="w-[120px] object-contain mb-[-10px]" />
        <img src="/flower.jpg" alt="Plant" className="w-[65px] object-contain" />
        <img src="/flower.jpg" alt="Plant" className="w-[65px] object-contain" />
      </div>

      {/* ── Friends section ── */}
      <div className="px-6 pb-6">
        <h3 className="text-xl font-bold italic text-[#7cb342] mb-3">Friends</h3>

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
                  Visit&gt;&gt;
                </button>
              </div>
              {i < friends.length - 1 && <div className="h-3" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
