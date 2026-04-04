"use client";

import { useRouter } from "next/navigation";
import TopBar from "../../../components/TopBar";
import { useAuth } from "../../../lib/useAuth";
import { useTranslation } from "../../../lib/i18n";

export default function AboutPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  if (loading || !user) return null;

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title={t("about")} transparent />

      <div className="flex items-center px-4 pb-2">
        <button
          onClick={() => router.push("/setting")}
          className="flex items-center gap-1 text-gray-500 hover:text-gray-700 transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
          <span className="text-sm">{t("back")}</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 mt-2 pb-6">
        <div className="flex flex-col items-center mt-4 mb-6">
          <img
            src="/flower.jpg"
            alt="GlucoGardener"
            className="w-[60px] h-auto object-contain mb-3"
          />
          <h2 className="text-xl font-bold italic text-[#e8927c]">
            {t("about_heading")}
          </h2>
          <p className="text-xs text-gray-400 mt-1">{t("version")}</p>
        </div>

        <div className="text-sm text-gray-600 leading-relaxed space-y-3">
          <p>{t("about_desc1")}</p>
          <p>{t("about_desc2")}</p>

          <h3 className="font-semibold text-gray-800 mt-4">{t("team")}</h3>
          <p>{t("built_for")}</p>

          <h3 className="font-semibold text-gray-800 mt-4">{t("acknowledgements")}</h3>
          <p>{t("ack_text")}</p>
        </div>
      </div>
    </div>
  );
}
