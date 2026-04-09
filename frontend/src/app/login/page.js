"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { TEST_USERS, loginUser, isOnboardingCompleted, createNewUserId } from "../../lib/users";
import { useTranslation } from "../../lib/i18n";
import { API_BASE } from "../../lib/config";

export default function LoginPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);

  useEffect(() => {
    fetch(`${API_BASE}/users/list`)
      .then((res) => res.json())
      .then((data) => {
        if (data.users && data.users.length > 0) {
          setUsers(data.users);
        } else {
          setUsers(TEST_USERS);
        }
      })
      .catch(() => {
        setUsers(TEST_USERS);
      });
  }, []);

  const handleSelect = (userId) => {
    loginUser(userId);
    if (isOnboardingCompleted(userId)) {
      router.push("/");
    } else {
      router.push("/onboarding");
    }
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
            {t("app_name")}
          </h1>
          <p className="text-sm text-gray-500 mt-1.5 italic">
            {t("app_tagline")}
          </p>
        </div>

        {/* User selection */}
        <p className="text-base font-semibold text-gray-600 mb-5">
          {t("who_is_gardening")}
        </p>

        <div className="flex gap-5">
          {users.map((user) => (
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

        {/* Create New Account */}
        <button
          onClick={() => {
            const newId = createNewUserId();
            loginUser(newId);
            router.push("/onboarding");
          }}
          className="mt-6 px-6 py-2.5 rounded-full text-sm font-semibold text-[#e8927c] border-2 border-[#e8927c]/30 bg-white/50 backdrop-blur-sm hover:bg-[#e8927c]/10 active:scale-95 transition-all duration-200"
        >
          {t("create_account")}
        </button>
      </div>

      {/* Bottom decoration */}
      <div className="relative z-10 pb-8 text-center">
        <p className="text-[10px] text-gray-400 italic">
          {t("sg_innovation")}
        </p>
      </div>
    </div>
  );
}
