"use client";

import { useState, useCallback, useEffect } from "react";
import { postCGM, postHR, resetToday } from "../lib/gatewayApi";

const SCENARIOS = [
  { file: "marcus_soft_pre_exercise.json", label: "A: Pre-Exercise Soft Alert" },
  { file: "marcus_hard_low_glucose.json", label: "B: Hard Low Glucose" },
  { file: "marcus_no_trigger.json", label: "C: Normal (Control)" },
];

const DEMO_SPEED = 1000; // 1 offset_minute = 1 second

/**
 * Build a recorded_at timestamp from step.demo_time (e.g. "13:31:00")
 * using today's date. Falls back to now if demo_time is not set.
 */
function buildRecordedAt(step) {
  if (!step.demo_time) return new Date().toISOString();
  const today = new Date();
  const [h, m, s] = step.demo_time.split(":").map(Number);
  today.setHours(h, m, s || 0, 0);
  // Use local time format (not toISOString which converts to UTC)
  const pad = (n) => String(n).padStart(2, "0");
  return `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}T${pad(h)}:${pad(m)}:${pad(s || 0)}`;
}

/**
 * Execute a single scenario step against the Gateway API.
 * Returns the API response.
 */
async function executeStep(userId, step) {
  const { endpoint, body } = step;
  const recorded_at = buildRecordedAt(step);

  if (endpoint === "POST /telemetry/hr") {
    return postHR(
      userId,
      body.heart_rate,
      body.gps_lat,
      body.gps_lng,
      recorded_at
    );
  }
  if (endpoint === "POST /telemetry/cgm") {
    return postCGM(userId, body.glucose, recorded_at);
  }
  throw new Error(`Unknown endpoint: ${endpoint}`);
}

export default function ScenarioPlayer({ userId = "user_002", onStepData, onReset, onScenarioChange }) {
  const [scenario, setScenario] = useState(null);
  const [selectedFile, setSelectedFile] = useState(SCENARIOS[0].file);
  const [stepStates, setStepStates] = useState([]); // "pending" | "running" | "done" | "error"
  const [stepResponses, setStepResponses] = useState([]);
  const [playing, setPlaying] = useState(false);
  const [loadError, setLoadError] = useState(null);

  // Load scenario JSON from public/scenarios/
  const loadScenario = useCallback(async (file) => {
    setLoadError(null);
    try {
      const res = await fetch(`/scenarios/${file}`);
      if (!res.ok) throw new Error(`Failed to load ${file}`);
      const data = await res.json();
      setScenario(data);
      setStepStates(data.steps.map(() => "pending"));
      setStepResponses(data.steps.map(() => null));
    } catch (e) {
      setLoadError(e.message);
    }
  }, []);

  // Auto-load the default scenario on mount
  useEffect(() => {
    loadScenario(SCENARIOS[0].file);
  }, [loadScenario]);

  // Load on select change
  const handleSelect = (e) => {
    const file = e.target.value;
    setSelectedFile(file);
    setPlaying(false);
    loadScenario(file);
    // Notify parent which scenario is selected (strip .json for scenarioId)
    if (onScenarioChange) {
      const scenarioId = file.replace(".json", "");
      onScenarioChange(scenarioId);
    }
  };

  // Play all steps with timing
  const playAll = useCallback(async () => {
    if (!scenario || playing) return;
    setPlaying(true);
    setStepStates(scenario.steps.map(() => "pending"));
    setStepResponses(scenario.steps.map(() => null));

    const uid = scenario.user_id || userId;
    let lastOffset = 0;

    for (let i = 0; i < scenario.steps.length; i++) {
      const step = scenario.steps[i];
      const delay = (step.offset_minutes - lastOffset) * DEMO_SPEED;
      if (delay > 0) await new Promise((r) => setTimeout(r, delay));
      lastOffset = step.offset_minutes;

      // Mark running
      setStepStates((prev) => prev.map((s, idx) => (idx === i ? "running" : s)));

      try {
        const response = await executeStep(uid, step);

        setStepStates((prev) => prev.map((s, idx) => (idx === i ? "done" : s)));
        setStepResponses((prev) => prev.map((r, idx) => (idx === i ? response : r)));

        // Notify parent with step data + response
        if (onStepData) {
          onStepData(step, response);
        }

        // If hard trigger fired, write to localStorage for Home page
        if (response.hard_fired) {
          localStorage.setItem(
            "hard_alert",
            JSON.stringify({
              trigger_type: response.trigger_type,
              glucose: step.body.glucose,
              timestamp: new Date().toISOString(),
            })
          );
        }
      } catch (err) {
        setStepStates((prev) => prev.map((s, idx) => (idx === i ? "error" : s)));
        setStepResponses((prev) =>
          prev.map((r, idx) => (idx === i ? { error: err.message } : r))
        );
      }
    }
    setPlaying(false);
  }, [scenario, playing, userId, onStepData]);

  // Reset today's data
  const handleReset = async () => {
    const uid = scenario?.user_id || userId;
    try {
      await resetToday(uid);
      localStorage.removeItem("hard_alert");
      setStepStates(scenario ? scenario.steps.map(() => "pending") : []);
      setStepResponses(scenario ? scenario.steps.map(() => null) : []);
      if (onReset) onReset();
    } catch (err) {
      alert("Reset failed: " + err.message);
    }
  };

  const statusIcon = (state) => {
    if (state === "done") return "\u2705";
    if (state === "running") return "\u23F3";
    if (state === "error") return "\u274C";
    return "\u25CB";
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Scenario selector */}
      <div>
        <label className="text-sm font-semibold text-gray-600 block mb-1">
          Select Scenario
        </label>
        <select
          value={selectedFile}
          onChange={handleSelect}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
        >
          <option value="" disabled>
            -- Choose --
          </option>
          {SCENARIOS.map((s) => (
            <option key={s.file} value={s.file}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {loadError && (
        <p className="text-sm text-red-500">{loadError}</p>
      )}

      {/* Scenario info */}
      {scenario && (
        <div className="bg-gray-50 rounded-lg p-3 text-sm">
          <p className="font-semibold">{scenario.title}</p>
          <p className="text-gray-500 mt-1">{scenario.description}</p>
        </div>
      )}

      {/* Steps */}
      {scenario && (
        <div className="space-y-2">
          {scenario.steps.map((step, i) => (
            <div
              key={i}
              className={`border rounded-lg p-3 text-sm ${
                stepStates[i] === "error"
                  ? "border-red-300 bg-red-50"
                  : stepStates[i] === "done"
                  ? "border-green-300 bg-green-50"
                  : stepStates[i] === "running"
                  ? "border-yellow-300 bg-yellow-50"
                  : "border-gray-200"
              }`}
            >
              <div className="flex items-center gap-2">
                <span>{statusIcon(stepStates[i])}</span>
                <span className="font-mono text-xs">{step.endpoint}</span>
                {step.offset_minutes > 0 && (
                  <span className="text-xs text-gray-400">
                    +{step.offset_minutes}min
                  </span>
                )}
              </div>
              <p className="text-gray-500 mt-1">{step.note}</p>
              <pre className="text-[10px] leading-tight text-gray-400 mt-1 overflow-x-auto">
                {JSON.stringify(step.body, null, 2)}
              </pre>
              {stepResponses[i] && (
                <pre className="text-[10px] leading-tight mt-1 text-blue-600 overflow-x-auto break-all whitespace-pre-wrap">
                  Response: {JSON.stringify(stepResponses[i])}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={playAll}
          disabled={!scenario || playing}
          className="flex-1 py-2 px-4 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {playing ? "Playing..." : "Play All"}
        </button>
        <button
          onClick={handleReset}
          className="py-2 px-4 rounded-lg text-sm font-semibold text-gray-700 border border-gray-300 hover:bg-gray-100"
        >
          Reset Today
        </button>
      </div>

      {/* Hint */}
      {!playing &&
        stepStates.length > 0 &&
        stepStates.every((s) => s === "done") && (
          <p className="text-sm text-green-600 font-medium">
            All steps complete. Switch to Home page to see the alert effect.
          </p>
        )}
    </div>
  );
}
