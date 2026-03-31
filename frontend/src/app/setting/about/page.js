"use client";

import TopBar from "../../../components/TopBar";
import { useAuth } from "../../../lib/useAuth";
import { useTranslation } from "../../../lib/i18n";

export default function AboutPage() {
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  if (loading || !user) return null;

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title={t("about")} transparent />

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
