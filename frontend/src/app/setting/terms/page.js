"use client";

import TopBar from "../../../components/TopBar";
import { useAuth } from "../../../lib/useAuth";
import { useTranslation } from "../../../lib/i18n";

export default function TermsPage() {
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  if (loading || !user) return null;

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title={t("terms_conditions")} transparent />

      <div className="flex-1 overflow-y-auto px-6 mt-2 pb-6">
        <h2 className="text-lg font-bold text-gray-800 mb-3">{t("terms_heading")}</h2>
        <div className="text-sm text-gray-600 leading-relaxed space-y-3">
          <p>{t("terms_intro")}</p>
          <p>
            <span className="font-semibold">{t("terms_purpose_title")}</span> {t("terms_purpose")}
          </p>
          <p>
            <span className="font-semibold">{t("terms_data_title")}</span> {t("terms_data")}
          </p>
          <p>
            <span className="font-semibold">{t("terms_user_title")}</span> {t("terms_user")}
          </p>
          <p>
            <span className="font-semibold">{t("terms_disclaimer_title")}</span> {t("terms_disclaimer")}
          </p>
          <p className="text-xs text-gray-400 italic mt-6">
            {t("last_updated")}
          </p>
        </div>
      </div>
    </div>
  );
}
