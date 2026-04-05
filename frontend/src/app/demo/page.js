"use client";

import { useState, useEffect, useCallback } from "react";
import TopBar from "../../components/TopBar";
import ScenarioPlayer from "../../components/ScenarioPlayer";
import TelemetryPanel from "../../components/TelemetryPanel";
import InvestigatorPanel from "../../components/InvestigatorPanel";
import InterventionTimeline from "../../components/InterventionTimeline";
import { fetchInterventions } from "../../lib/gatewayApi";
import { useAuth } from "../../lib/useAuth";

export default function DemoPage() {
  const { user, loading } = useAuth();
  const userId = "user_002";

  // Telemetry state — updated from ScenarioPlayer step data
  const [latestGlucose, setLatestGlucose] = useState(null);
  const [latestHR, setLatestHR] = useState(null);
  const [latestGPS, setLatestGPS] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Which scenario is active + whether play has started
  const [activeScenario, setActiveScenario] = useState("marcus_soft_pre_exercise");
  const [hasPlayed, setHasPlayed] = useState(false);

  // Intervention timeline
  const [interventions, setInterventions] = useState([]);
  const [polling, setPolling] = useState(false);

  // Handle step data from ScenarioPlayer
  const handleStepData = useCallback((step, response) => {
    const { endpoint, body } = step;
    const now = new Date().toLocaleTimeString("en-SG", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    if (endpoint === "POST /telemetry/cgm") {
      setLatestGlucose(body.glucose);
    }
    if (endpoint === "POST /telemetry/hr") {
      setLatestHR(body.heart_rate);
      if (body.gps_lat != null) {
        setLatestGPS({ lat: body.gps_lat, lng: body.gps_lng });
      }
    }
    setLastUpdate(now);
    setHasPlayed(true);
    // Start polling for interventions after first step
    setPolling(true);
  }, []);

  // Reset handler — clear local state when ScenarioPlayer resets
  const handleReset = useCallback(() => {
    setLatestGlucose(null);
    setLatestHR(null);
    setLatestGPS(null);
    setLastUpdate(null);
    setHasPlayed(false);
    setInterventions([]);
    setPolling(false);
  }, []);

  // Track which scenario is selected
  const handleScenarioChange = useCallback((scenarioId) => {
    setActiveScenario(scenarioId);
  }, []);

  // Poll for interventions every 3s
  useEffect(() => {
    if (!polling) return;
    let active = true;

    const poll = async () => {
      try {
        const data = await fetchInterventions(userId, true);
        if (active) setInterventions(data);
      } catch {
        // Gateway might not be running, ignore
      }
    };

    poll();
    const id = setInterval(poll, 3000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [polling, userId]);

  if (loading || !user) return null;

  return (
    <div className="flex flex-col h-full bg-gray-100">
      <TopBar title="Demo Console" />

      <div className="flex-1 overflow-auto px-4 pb-6">
        {/* Two column layout on wide screens */}
        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
          {/* Left: ScenarioPlayer */}
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <h2 className="text-lg font-bold mb-3">Scenario Player</h2>
            <ScenarioPlayer
              userId={userId}
              onStepData={handleStepData}
              onReset={handleReset}
              onScenarioChange={handleScenarioChange}
            />
          </div>

          {/* Right: Telemetry + Investigator + Interventions */}
          <div className="space-y-4">
            <TelemetryPanel
              glucose={latestGlucose}
              heartRate={latestHR}
              gps={latestGPS}
              lastUpdate={lastUpdate}
            />

            <InvestigatorPanel
              visible={hasPlayed}
              scenarioId={activeScenario}
            />

            <InterventionTimeline
              interventions={interventions}
              polling={polling}
            />
          </div>
        </div>

        {/* Bottom hint */}
        <div className="max-w-5xl mx-auto mt-4 px-2">
          <p className="text-xs text-gray-400 text-center">
            Soft alerts require Agent processing (~30s). Hard alerts take effect
            immediately. Switch to Home page after playing to see the alert UI.
          </p>
        </div>
      </div>
    </div>
  );
}
