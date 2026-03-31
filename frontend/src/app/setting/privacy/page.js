"use client";

import TopBar from "../../../components/TopBar";
import { useAuth } from "../../../lib/useAuth";

export default function PrivacyPage() {
  const { user, loading } = useAuth();
  if (loading || !user) return null;

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title="Privacy" transparent />

      <div className="flex-1 overflow-y-auto px-6 mt-2 pb-6">
        <h2 className="text-lg font-bold text-gray-800 mb-3">Privacy Policy</h2>
        <div className="text-sm text-gray-600 leading-relaxed space-y-3">
          <p>
            The GlucoGardener is committed to protecting your privacy and personal health data.
          </p>
          <p>
            <span className="font-semibold">Data We Collect.</span> Health metrics (glucose levels, heart rate), dietary logs, exercise data, and conversation history with the AI companion.
          </p>
          <p>
            <span className="font-semibold">How We Use It.</span> Your data is used solely to provide personalized health insights, task recommendations, and alert notifications. We do not sell or share your data with third parties.
          </p>
          <p>
            <span className="font-semibold">Data Storage.</span> All data is securely stored in encrypted databases. You may request deletion of your data at any time.
          </p>
          <p>
            <span className="font-semibold">Clinician Access.</span> Aggregated, anonymized health summaries may be shared with your designated healthcare provider to support clinical decisions.
          </p>
          <p className="text-xs text-gray-400 italic mt-6">
            Last updated: April 2026
          </p>
        </div>
      </div>
    </div>
  );
}
