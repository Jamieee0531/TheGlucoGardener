"use client";

import TopBar from "../../../components/TopBar";
import { useAuth } from "../../../lib/useAuth";

export default function TermsPage() {
  const { user, loading } = useAuth();
  if (loading || !user) return null;

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title="Terms" transparent />

      <div className="flex-1 overflow-y-auto px-6 mt-2 pb-6">
        <h2 className="text-lg font-bold text-gray-800 mb-3">Terms & Conditions</h2>
        <div className="text-sm text-gray-600 leading-relaxed space-y-3">
          <p>
            Welcome to The GlucoGardener. By using this application, you agree to the following terms and conditions.
          </p>
          <p>
            <span className="font-semibold">1. Purpose.</span> This application is designed as a health companion tool for diabetes management. It is not a substitute for professional medical advice, diagnosis, or treatment.
          </p>
          <p>
            <span className="font-semibold">2. Data Collection.</span> We collect health-related data including glucose readings, dietary information, and activity data to provide personalized recommendations.
          </p>
          <p>
            <span className="font-semibold">3. User Responsibility.</span> Users are responsible for the accuracy of self-reported data. Always consult your healthcare provider for medical decisions.
          </p>
          <p>
            <span className="font-semibold">4. Disclaimer.</span> The AI-generated advice provided by this application is for informational purposes only and should not replace professional medical guidance.
          </p>
          <p className="text-xs text-gray-400 italic mt-6">
            Last updated: April 2026
          </p>
        </div>
      </div>
    </div>
  );
}
