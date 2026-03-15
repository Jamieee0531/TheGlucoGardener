"use client";

import TopBar from "../../components/TopBar";

const FRIENDS = [
  { name: "Friend 1", avatar: "/avatar1.jpg" },
  { name: "Friend 2", avatar: "/avatar2.jpg" },
  { name: "Friend 3", avatar: "/avatar3.jpg" },
];

export default function GardenPage() {
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
          {FRIENDS.map((friend, i) => (
            <div key={friend.name}>
              <div className="flex items-center py-3 px-4 bg-[#f0e6d6] rounded-lg">
                <img
                  src={friend.avatar}
                  alt={friend.name}
                  className="w-[55px] h-[55px] rounded-full object-cover"
                />
                <span className="flex-1" />
                <span className="text-sm font-semibold text-gray-800">Visit&gt;&gt;</span>
              </div>
              {i < FRIENDS.length - 1 && <div className="h-3" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
