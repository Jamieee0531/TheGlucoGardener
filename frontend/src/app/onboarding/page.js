"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUserId, completeOnboarding, setLanguage, AVATARS } from "../../lib/users";
import { useTranslation } from "../../lib/i18n";

const STEPS = ["avatar", "personal", "health", "language", "done"];

export default function OnboardingPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    avatar: "",
    name: "",
    birth_year: "",
    gender: "",
    height_cm: "",
    weight_kg: "",
    waist_cm: "",
    language: "English",
  });

  const userId = getCurrentUserId();
  if (!userId) {
    router.replace("/login");
    return null;
  }

  const updateField = (field, value) => {
    setForm({ ...form, [field]: value });
  };

  const canNext = () => {
    if (step === 0) return form.avatar !== "";
    if (step === 1) return form.name && form.birth_year && form.gender;
    if (step === 2) return form.height_cm && form.weight_kg && form.waist_cm;
    return true;
  };

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    }
  };

  const handleFinish = () => {
    const profile = {
      ...form,
      birth_year: parseInt(form.birth_year),
      height_cm: parseFloat(form.height_cm),
      weight_kg: parseFloat(form.weight_kg),
      waist_cm: parseFloat(form.waist_cm),
    };
    completeOnboarding(userId, profile);
    setLanguage(form.language);
    router.push("/");
  };

  return (
    <div className="flex flex-col h-full bg-cream relative overflow-hidden">
      {/* Background blobs */}
      <div
        className="absolute z-0"
        style={{
          width: 450, height: 450, borderRadius: "50%",
          backgroundColor: "#CEF7EA",
          top: -150, right: -150,
        }}
      />
      <div
        className="absolute z-0"
        style={{
          width: 400, height: 400, borderRadius: "50%",
          backgroundColor: "#FBE6E1",
          bottom: -150, left: -150,
        }}
      />

      {/* Progress dots */}
      <div className="relative z-10 flex justify-center gap-2 pt-16 mb-6">
        {STEPS.map((_, i) => (
          <div
            key={i}
            className="w-2 h-2 rounded-full transition-all duration-300"
            style={{
              backgroundColor: i <= step ? "#e8927c" : "#d1d5db",
              width: i === step ? 20 : 8,
            }}
          />
        ))}
      </div>

      {/* Content area */}
      <div className="relative z-10 flex-1 flex flex-col px-8">

        {/* Step 0: Welcome + Avatar */}
        {step === 0 && (
          <div className="flex-1 flex flex-col items-center">
            <img
              src="/flower.jpg"
              alt="GlucoGardener"
              className="w-[70px] h-auto object-contain mb-4"
            />
            <h1 className="text-2xl font-bold italic text-[#e8927c] text-center whitespace-pre-line">
              {t("welcome_title")}
            </h1>
            <p className="text-sm text-gray-500 mt-2 mb-8 text-center">
              {t("setup_profile")}
            </p>

            <p className="text-sm font-semibold text-gray-600 mb-4">
              {t("choose_avatar_prompt")}
            </p>
            <div className="flex gap-5">
              {AVATARS.map((av) => (
                <button
                  key={av.id}
                  onClick={() => updateField("avatar", av.src)}
                  className={`w-[80px] h-[80px] rounded-full overflow-hidden ring-4 transition-all duration-200 ${
                    form.avatar === av.src
                      ? "ring-[#e8927c] scale-110"
                      : "ring-transparent hover:ring-gray-200"
                  }`}
                >
                  <img src={av.src} alt="Avatar" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 1: Personal Info */}
        {step === 1 && (
          <div className="flex-1">
            <h2 className="text-xl font-bold italic text-[#e8927c] mb-1">
              {t("tell_about_you")}
            </h2>
            <p className="text-sm text-gray-500 mb-6">
              {t("personalise_experience")}
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-500 font-medium">{t("name")}</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => updateField("name", e.target.value)}
                  placeholder="e.g. Alice Tan"
                  className="w-full mt-1 px-4 py-3 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium">{t("birth_year")}</label>
                <input
                  type="number"
                  value={form.birth_year}
                  onChange={(e) => updateField("birth_year", e.target.value)}
                  placeholder="e.g. 1975"
                  className="w-full mt-1 px-4 py-3 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium">{t("gender")}</label>
                <select
                  value={form.gender}
                  onChange={(e) => updateField("gender", e.target.value)}
                  className="w-full mt-1 px-4 py-3 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
                >
                  <option value="">{t("select_placeholder")}</option>
                  <option value="male">{t("male")}</option>
                  <option value="female">{t("female")}</option>
                  <option value="other">{t("other")}</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Health Info */}
        {step === 2 && (
          <div className="flex-1">
            <h2 className="text-xl font-bold italic text-[#e8927c] mb-1">
              {t("health_profile")}
            </h2>
            <p className="text-sm text-gray-500 mb-6">
              {t("better_insights")}
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-500 font-medium">{t("height_cm")}</label>
                <input
                  type="number"
                  value={form.height_cm}
                  onChange={(e) => updateField("height_cm", e.target.value)}
                  placeholder="e.g. 165"
                  className="w-full mt-1 px-4 py-3 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium">{t("weight_kg")}</label>
                <input
                  type="number"
                  value={form.weight_kg}
                  onChange={(e) => updateField("weight_kg", e.target.value)}
                  placeholder="e.g. 70"
                  className="w-full mt-1 px-4 py-3 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium">{t("waist_circumference")}</label>
                <input
                  type="number"
                  value={form.waist_cm}
                  onChange={(e) => updateField("waist_cm", e.target.value)}
                  placeholder="e.g. 85"
                  className="w-full mt-1 px-4 py-3 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Language */}
        {step === 3 && (
          <div className="flex-1">
            <h2 className="text-xl font-bold italic text-[#e8927c] mb-1">
              {t("choose_your_language")}
            </h2>
            <p className="text-sm text-gray-500 mb-6">
              {t("change_later_settings")}
            </p>

            <div className="space-y-3">
              {[
                { code: "English", label: "English", flag: "\uD83C\uDDEC\uD83C\uDDE7" },
                { code: "Chinese", label: "\u534E\u8BED", flag: "\uD83C\uDDE8\uD83C\uDDF3" },
                { code: "Malay", label: "Bahasa Melayu", flag: "\uD83C\uDDF2\uD83C\uDDFE" },
                { code: "Tamil", label: "\u0BA4\u0BAE\u0BBF\u0BB4\u0BCD", flag: "\uD83C\uDDEE\uD83C\uDDF3" },
              ].map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => updateField("language", lang.code)}
                  className={`flex items-center w-full px-4 py-4 rounded-xl transition-all ${
                    form.language === lang.code
                      ? "bg-[#e8927c]/10 border-2 border-[#e8927c]"
                      : "bg-white border-2 border-transparent"
                  }`}
                >
                  <span className="text-2xl mr-3">{lang.flag}</span>
                  <span className="text-sm font-semibold text-gray-800">{lang.label}</span>
                  <span className="flex-1" />
                  {form.language === lang.code && (
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="#e8927c" className="w-5 h-5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 4: Done */}
        {step === 4 && (
          <div className="flex-1 flex flex-col items-center justify-center">
            <img
              src="/flower.jpg"
              alt="Ready"
              className="w-[100px] h-auto object-contain mb-6"
            />
            <h2 className="text-2xl font-bold italic text-[#e8927c] text-center mb-2">
              {t("all_set")}
            </h2>
            <p className="text-sm text-gray-500 text-center mb-2">
              {t("garden_ready")}
            </p>
            <p className="text-xs text-gray-400 text-center italic">
              {t("complete_tasks_bloom")}
            </p>
          </div>
        )}

        {/* Bottom button */}
        <div className="pb-10 pt-4">
          {step < 4 ? (
            <button
              onClick={handleNext}
              disabled={!canNext()}
              className="w-full py-3.5 rounded-full text-white font-semibold text-sm transition-all disabled:opacity-40"
              style={{ backgroundColor: "#e8927c" }}
            >
              {t("next")}
            </button>
          ) : (
            <button
              onClick={handleFinish}
              className="w-full py-3.5 rounded-full text-white font-semibold text-sm transition-all"
              style={{ backgroundColor: "#7cb342" }}
            >
              {t("start_gardening")}
            </button>
          )}

          {step > 0 && step < 4 && (
            <button
              onClick={() => setStep(step - 1)}
              className="w-full mt-2 py-2 text-sm text-gray-400 text-center"
            >
              {t("back")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
