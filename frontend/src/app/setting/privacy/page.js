"use client";

import { useRouter } from "next/navigation";
import TopBar from "../../../components/TopBar";
import { useAuth } from "../../../lib/useAuth";
import { useTranslation } from "../../../lib/i18n";

export default function PrivacyPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  if (loading || !user) return null;

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title={t("privacy_policy")} transparent />

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
        <h2 className="text-lg font-bold text-gray-800 mb-3">{t("privacy_heading")}</h2>
        <div className="text-sm text-gray-600 leading-relaxed space-y-3">
          <p>{t("privacy_intro")}</p>
          <p>
            <span className="font-semibold">{t("privacy_collect_title")}</span> {t("privacy_collect")}
          </p>
          <p>
            <span className="font-semibold">{t("privacy_use_title")}</span> {t("privacy_use")}
          </p>
          <p>
            <span className="font-semibold">{t("privacy_storage_title")}</span> {t("privacy_storage")}
          </p>
          <p>
            <span className="font-semibold">{t("privacy_clinician_title")}</span> {t("privacy_clinician")}
          </p>
          <p className="text-xs text-gray-400 italic mt-6">
            {t("last_updated")}
          </p>
        </div>
      </div>
    </div>
  );
}
