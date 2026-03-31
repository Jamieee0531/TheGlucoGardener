"use client";

import { useRouter } from "next/navigation";
import { TEST_USERS, loginUser } from "../../lib/users";

export default function LoginPage() {
  const router = useRouter();

  const handleSelect = (userId) => {
    loginUser(userId);
    router.push("/");
  };

  return (
    <div className="flex flex-col h-full bg-cream relative overflow-hidden">
      {/* ── Background blobs (same style as Home/Alert pages) ── */}
      <div
        className="absolute z-0"
        style={{
          width: 520, height: 520, borderRadius: "50%",
          backgroundColor: "#FBE6E1",
          top: -180, right: -200,
        }}
      />
      <div
        className="absolute z-0"
        style={{
          width: 600, height: 600, borderRadius: "50%",
          backgroundColor: "#CEF7EA",
          bottom: -280, left: -280,
        }}
      />
      <div
        className="absolute z-0"
        style={{
          width: 350, height: 350, borderRadius: "50%",
          backgroundColor: "#EBE9E9",
          bottom: 120, right: -120,
        }}
      />

      {/* ── Content ── */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-8">
        {/* App branding */}
        <div className="mb-12 text-center">
          <img
            src="/flower.jpg"
            alt="GlucoGardener"
            className="w-[80px] h-auto object-contain mx-auto mb-4"
          />
          <h1 className="text-3xl font-bold italic text-[#e8927c]">
            The GlucoGardener
          </h1>
          <p className="text-sm text-gray-500 mt-1.5 italic">
            Your health companion
          </p>
        </div>

        {/* User selection */}
        <p className="text-base font-semibold text-gray-600 mb-5">
          Who is gardening today?
        </p>

        <div className="flex gap-5">
          {TEST_USERS.map((user) => (
            <button
              key={user.user_id}
              onClick={() => handleSelect(user.user_id)}
              className="flex flex-col items-center gap-2.5 p-3 rounded-2xl
                bg-white/70 backdrop-blur-sm shadow-md
                hover:shadow-lg hover:scale-105
                active:scale-95
                transition-all duration-200"
            >
              <div className="w-[76px] h-[76px] rounded-full overflow-hidden ring-3 ring-white shadow-sm">
                <img
                  src={user.avatar}
                  alt={user.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <span className="text-xs font-semibold text-gray-700 max-w-[80px] text-center leading-tight">
                {user.name}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Bottom decoration */}
      <div className="relative z-10 pb-8 text-center">
        <p className="text-[10px] text-gray-400 italic">
          SG Innovation Challenge 2026
        </p>
      </div>
    </div>
  );
}
