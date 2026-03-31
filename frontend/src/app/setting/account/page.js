"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import TopBar from "../../../components/TopBar";
import { useAuth } from "../../../lib/useAuth";
import { getCurrentUserId, saveProfile, AVATARS } from "../../../lib/users";
import { useTranslation } from "../../../lib/i18n";

export default function AccountPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  const [form, setForm] = useState(null);
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (user) {
      setForm({ ...user });
    }
  }, [user]);

  if (loading || !user || !form) return null;

  const bmi = form.height_cm > 0
    ? (form.weight_kg / ((form.height_cm / 100) ** 2)).toFixed(1)
    : "—";

  const handleSave = () => {
    const userId = getCurrentUserId();
    saveProfile(userId, form);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const updateField = (field, value) => {
    setForm({ ...form, [field]: value });
  };

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title={t("account")} transparent />

      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {/* Avatar */}
        <div className="flex flex-col items-center mt-2 mb-6">
          <button
            onClick={() => setShowAvatarPicker(true)}
            className="relative group"
          >
            <div className="w-[90px] h-[90px] rounded-full overflow-hidden ring-3 ring-[#e8927c]/30">
              <img src={form.avatar} alt="Avatar" className="w-full h-full object-cover" />
            </div>
            <div className="absolute inset-0 rounded-full bg-black/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="text-white text-xs font-semibold">{t("change")}</span>
            </div>
          </button>
          <p className="text-xs text-gray-400 mt-1.5">{t("tap_change_avatar")}</p>
        </div>

        {/* Avatar picker modal */}
        {showAvatarPicker && (
          <>
            <div className="fixed inset-0 bg-black/30 z-40" onClick={() => setShowAvatarPicker(false)} />
            <div className="fixed top-1/3 left-8 right-8 bg-white rounded-2xl z-50 p-5 shadow-xl">
              <h4 className="text-base font-bold mb-4 text-gray-800">{t("choose_avatar")}</h4>
              <div className="flex justify-center gap-4">
                {AVATARS.map((av) => (
                  <button
                    key={av.id}
                    onClick={() => {
                      updateField("avatar", av.src);
                      setShowAvatarPicker(false);
                    }}
                    className={`w-[70px] h-[70px] rounded-full overflow-hidden ring-3 transition-all ${
                      form.avatar === av.src ? "ring-[#e8927c] scale-110" : "ring-transparent"
                    }`}
                  >
                    <img src={av.src} alt="Avatar option" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Personal Info */}
        <div className="mb-5">
          <h3 className="text-sm font-bold text-[#e8927c] uppercase tracking-wide mb-3">
            {t("personal_info")}
          </h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500">{t("name")}</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => updateField("name", e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">{t("birth_year")}</label>
              <input
                type="number"
                value={form.birth_year}
                onChange={(e) => updateField("birth_year", parseInt(e.target.value) || "")}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">{t("gender")}</label>
              <select
                value={form.gender}
                onChange={(e) => updateField("gender", e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              >
                <option value="male">{t("male")}</option>
                <option value="female">{t("female")}</option>
                <option value="other">{t("other")}</option>
              </select>
            </div>
          </div>
        </div>

        {/* Health Info */}
        <div className="mb-5">
          <h3 className="text-sm font-bold text-[#e8927c] uppercase tracking-wide mb-3">
            {t("health_info")}
          </h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500">{t("height_cm")}</label>
              <input
                type="number"
                value={form.height_cm}
                onChange={(e) => updateField("height_cm", parseFloat(e.target.value) || "")}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">{t("weight_kg")}</label>
              <input
                type="number"
                value={form.weight_kg}
                onChange={(e) => updateField("weight_kg", parseFloat(e.target.value) || "")}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">{t("waist_cm")}</label>
              <input
                type="number"
                value={form.waist_cm}
                onChange={(e) => updateField("waist_cm", parseFloat(e.target.value) || "")}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">{t("bmi_auto")}</label>
              <div className="w-full mt-1 px-3 py-2 bg-gray-100 rounded-xl text-sm text-gray-600">
                {bmi}
              </div>
            </div>
          </div>
        </div>

        {/* Save button */}
        <button
          onClick={handleSave}
          className="w-full py-3 rounded-full text-white font-semibold text-sm transition-all"
          style={{ backgroundColor: saved ? "#7cb342" : "#e8927c" }}
        >
          {saved ? t("saved") : t("save_changes")}
        </button>
      </div>
    </div>
  );
}
