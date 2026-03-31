"use client";

import TopBar from "../../../components/TopBar";
import { useAuth } from "../../../lib/useAuth";

export default function AboutPage() {
  const { user, loading } = useAuth();
  if (loading || !user) return null;

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title="About" transparent />

      <div className="flex-1 overflow-y-auto px-6 mt-2 pb-6">
        <div className="flex flex-col items-center mt-4 mb-6">
          <img
            src="/flower.jpg"
            alt="GlucoGardener"
            className="w-[60px] h-auto object-contain mb-3"
          />
          <h2 className="text-xl font-bold italic text-[#e8927c]">
            The GlucoGardener
          </h2>
          <p className="text-xs text-gray-400 mt-1">Version 1.0.0</p>
        </div>

        <div className="text-sm text-gray-600 leading-relaxed space-y-3">
          <p>
            An AI-powered chronic disease management platform for Type 2 diabetes patients in Singapore.
          </p>
          <p>
            The GlucoGardener combines a multimodal health companion chatbot, personalized task management, two-tier risk alerts, and gamified health tracking to support patients in their daily diabetes management journey.
          </p>

          <h3 className="font-semibold text-gray-800 mt-4">Team AAAMedMaster</h3>
          <p>
            Built for the NUS-SYNAPXE-IMDA AI Innovation Challenge 2026.
          </p>

          <h3 className="font-semibold text-gray-800 mt-4">Acknowledgements</h3>
          <p>
            We gratefully acknowledge AISG for SEA-LION and MERaLiON model support, and IMDA for mentorship guidance.
          </p>
        </div>
      </div>
    </div>
  );
}
