"use client";

import { useState, useEffect, useCallback } from "react";
import TopBar from "../../components/TopBar";
import ScenarioPlayer from "../../components/ScenarioPlayer";
import TelemetryPanel from "../../components/TelemetryPanel";
import { InvestigatorPanelContent } from "../../components/InvestigatorPanel";
import { fetchInterventions } from "../../lib/gatewayApi";
import { useAuth } from "../../lib/useAuth";

/* ── Helper: parse agent_decision JSON ── */
function parseDecision(raw) {
  if (!raw) return null;
  try {
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch {
    return null;
  }
}

function formatTime(ts) {
  if (!ts) return "";
  try {
    return new Date(ts).toLocaleTimeString("en-SG", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return ts;
  }
}

/* ── Reflector sub-module ── */
function ReflectorContent({ interventions = [], polling = false }) {
  const soft = interventions.find((iv) => !iv.trigger_type?.startsWith("hard"));
  const decision = soft ? parseDecision(soft.agent_decision) : null;

  if (!decision) {
    return (
      <p className="text-sm text-gray-400">
        {polling ? "Waiting for agent..." : "No reflector output yet."}
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {/* Risk Assessment */}
      <div>
        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1">Risk Assessment</p>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className={`px-1.5 py-0.5 rounded font-semibold ${
            decision.risk_level === "HIGH" ? "bg-red-100 text-red-700" :
            decision.risk_level === "MEDIUM" ? "bg-yellow-100 text-yellow-700" :
            "bg-green-100 text-green-700"
          }`}>
            Risk: {decision.risk_level}
          </span>
          <span className={`px-1.5 py-0.5 rounded font-semibold ${
            decision.intervention_action === "STRONG_ALERT" ? "bg-red-100 text-red-700" :
            decision.intervention_action === "SOFT_REMIND" ? "bg-yellow-100 text-yellow-700" :
            "bg-gray-100 text-gray-600"
          }`}>
            Action: {decision.intervention_action}
          </span>
          <span className={`px-1.5 py-0.5 rounded font-semibold ${
            decision.confidence === "HIGH" ? "bg-red-100 text-red-700" :
            decision.confidence === "LOW" ? "bg-green-100 text-green-700" :
            "bg-yellow-100 text-yellow-700"
          }`}>
            Confidence: {decision.confidence}
          </span>
        </div>
      </div>

      {/* Reasoning Summary */}
      {decision.reasoning_summary && (
        <div>
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1">Reasoning Summary</p>
          <p className="text-xs text-gray-600 leading-relaxed">{decision.reasoning_summary}</p>
        </div>
      )}

      {/* Supplement Recommendation */}
      {decision.supplement_recommendation && (
        <div>
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1">Supplement Recommendation</p>
          <p className="text-xs text-gray-700">{decision.supplement_recommendation}</p>
        </div>
      )}
    </div>
  );
}

/* ── Communicator sub-module ── */
function CommunicatorContent({ interventions = [], polling = false }) {
  const soft = interventions.find((iv) => !iv.trigger_type?.startsWith("hard") && iv.message_sent);

  if (!soft) {
    return (
      <p className="text-sm text-gray-400">
        {polling ? "Waiting for agent..." : "No message generated yet."}
      </p>
    );
  }

  return (
    <div>
      <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1">Message to User</p>
      <p className="text-sm text-gray-700 italic leading-relaxed">
        &quot;{soft.message_sent}&quot;
      </p>
      <p className="text-xs text-gray-400 mt-1">
        Sent at {formatTime(soft.triggered_at)}
      </p>
    </div>
  );
}

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
        <div className="max-w-2xl mx-auto space-y-4 mt-2">

          {/* ── 1. Scenario Player ── */}
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <h2 className="text-lg font-bold mb-3">Scenario Player</h2>
            <ScenarioPlayer
              userId={userId}
              onStepData={handleStepData}
              onReset={handleReset}
              onScenarioChange={handleScenarioChange}
            />
          </div>

          {/* ── 2. Live Telemetry ── */}
          <TelemetryPanel
            glucose={latestGlucose}
            heartRate={latestHR}
            gps={latestGPS}
            lastUpdate={lastUpdate}
          />

          {/* ── 3. Agent Pipeline ── */}
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <h2 className="text-lg font-bold mb-4">Agent Pipeline</h2>

            <div className="space-y-4">
              {/* 3a. Investigator Node */}
              <div className="border border-gray-200 rounded-lg p-3">
                <h3 className="text-sm font-bold text-gray-600 mb-2">Investigator Node</h3>
                <InvestigatorPanelContent
                  visible={hasPlayed}
                  scenarioId={activeScenario}
                />
              </div>

              {/* 3b. Reflector Node */}
              <div className="border border-gray-200 rounded-lg p-3">
                <h3 className="text-sm font-bold text-gray-600 mb-2">Reflector Node</h3>
                <ReflectorContent interventions={interventions} polling={polling} />
              </div>

              {/* 3c. Communicator Node */}
              <div className="border border-gray-200 rounded-lg p-3">
                <h3 className="text-sm font-bold text-gray-600 mb-2">Communicator Node</h3>
                <CommunicatorContent interventions={interventions} polling={polling} />
              </div>
            </div>
          </div>

          {/* Bottom hint */}
          <p className="text-xs text-gray-400 text-center px-2">
            Soft alerts require Agent processing (~30s). Hard alerts take effect
            immediately. Switch to Home page after playing to see the alert UI.
          </p>
        </div>
      </div>
    </div>
  );
}
