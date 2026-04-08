"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import TopBar from "../../components/TopBar";
import { useAuth } from "../../lib/useAuth";

const API = "http://localhost:8001";


const STEP_LABELS = ["Setup", "Rule Engine", "Park Selection", "Task Copy", "Arrival"];

export default function TaskDemoPage() {
  const { user } = useAuth();
  const USER_ID = user?.user_id || "user_003";
  const [step, setStep] = useState(0);       // 0=idle, 1=triggered, 2=park, 3=copy, 4=done
  const [loading, setLoading] = useState(false);
  const [log, setLog] = useState([]);
  const [error, setError] = useState(null);

  const [taskId, setTaskId] = useState(null);
  const [parks, setParks] = useState([]);
  const [selectedPark, setSelectedPark] = useState(null);
  const [ruleResult, setRuleResult] = useState(null);
  const [taskContent, setTaskContent] = useState(null);
  const [points, setPoints] = useState(null);
  const [profile, setProfile] = useState(null);  // loaded from DB

  const pollRef = useRef(null);
  const router = useRouter();

  const addLog = (msg) => setLog((prev) => [...prev, msg]);

  // Load profile from DB when user is ready
  useEffect(() => {
    if (!user) return;
    fetch(`${API}/internal/user-context/${USER_ID}`)
      .then((r) => r.json())
      .then((data) => {
        const u = data.context?.user_profile || {};
        const rr = data.rule_result || {};
        const ctx = data.context || {};
        const age = u.birth_year ? new Date().getFullYear() - u.birth_year : null;
        setProfile({
          name: u.name || USER_ID,
          age,
          bmi: u.bmi,
          location: "Bishan, Singapore",
          caloriesToday: Math.round(ctx.calories_burned_today || 0),
          caloriesTarget: rr.adjusted_target || "—",
          glucose: ctx.avg_bg_last_2h ? ctx.avg_bg_last_2h.toFixed(1) : "—",
          seedLat: ctx.last_gps?.lat ?? 1.3526,
          seedLng: ctx.last_gps?.lng ?? 103.8352,
        });
      })
      .catch(() => {});
  }, [user, USER_ID]);

  // ── Step 0 → 1: Setup + Trigger ─────────────────────────────────────────
  async function handleStart() {
    setLoading(true);
    setError(null);
    setLog([]);
    setParks([]);
    setTaskId(null);
    setRuleResult(null);
    setTaskContent(null);
    setSelectedPark(null);
    setPoints(null);

    try {
      // 1. Reset today's tasks
      addLog("🗑  Resetting today's tasks...");
      await fetch(`${API}/internal/test/reset-tasks?user_id=${USER_ID}`, { method: "DELETE" });

      // 2. Inject today's exercise: 80 kcal morning walk
      addLog("🏃 Seeding morning walk (80 kcal)...");
      await fetch(`${API}/internal/mock/sync-data`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID, calories_burned: 80, cgm_value: 7.2, lat: profile?.seedLat ?? 1.3526, lng: profile?.seedLng ?? 103.8352 }),
      });

      // 3. Inject afternoon walk: 30 kcal → total 110 kcal today
      addLog("🏃 Seeding afternoon walk (30 kcal)...");
      await fetch(`${API}/internal/mock/sync-data`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID, calories_burned: 30, cgm_value: 5.6, lat: profile?.seedLat ?? 1.3526, lng: profile?.seedLng ?? 103.8352 }),
      });

      // 4. Trigger rule engine
      addLog("⚙️  Triggering rule engine...");
      await fetch(`${API}/internal/agent/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID }),
      });

      // 5. Fetch rule engine result (real data)
      addLog("📊 Fetching rule engine result...");
      const ctxRes = await fetch(`${API}/internal/user-context/${USER_ID}`);
      const ctxData = await ctxRes.json();
      const rr = ctxData.rule_result;
      const ctx = ctxData.context;

      // 6. Fetch active task
      addLog("📋 Fetching active task...");
      const res = await fetch(`${API}/tasks/dynamic/active?user_id=${USER_ID}`);
      const data = await res.json();

      if (!data.task_id) throw new Error("Rule engine did not trigger a task.");

      // Refresh profile card with post-seed real data
      setProfile((prev) => ({
        ...prev,
        caloriesToday: Math.round(ctx.calories_burned_today || 0),
        caloriesTarget: rr.adjusted_target || prev?.caloriesTarget,
        glucose: ctx.avg_bg_last_2h ? ctx.avg_bg_last_2h.toFixed(1) : prev?.glucose,
      }));

      setTaskId(data.task_id);
      setParks(data.parks || []);
      setRuleResult({
        triggered: rr.should_trigger,
        caloriesToday: Math.round(ctx.calories_burned_today || 0),
        caloriesTarget: rr.adjusted_target,
        deficit: rr.deficit_kcal,
        ratio: rr.adjusted_target > 0
          ? ((ctx.calories_burned_today || 0) / rr.adjusted_target).toFixed(2)
          : "0.00",
        glucose: ctx.avg_bg_last_2h ?? "—",
        lowBgGuard: rr.low_bg_guard,
      });

      addLog(`✅ Task created (id=${data.task_id}), ${data.parks?.length || 0} parks found`);
      setStep(1);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Step 2: Select park ──────────────────────────────────────────────────
  async function handleSelectPark(parkIndex) {
    setLoading(true);
    setError(null);
    const park = parks[parkIndex];
    try {
      addLog(`🌳 Selecting "${park.name}"...`);
      await fetch(`${API}/tasks/dynamic/${taskId}/select-destination?user_id=${USER_ID}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ park_index: parkIndex }),
      });

      setSelectedPark(park);
      addLog("⏳ Writer generating task copy via SEA-LION...");
      setStep(3);
      startPollingCopy(park);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Step 3: Poll until copy is ready ─────────────────────────────────────
  function startPollingCopy(park) {
    if (pollRef.current) clearInterval(pollRef.current);
    let retries = 0;
    const MAX_RETRIES = 30; // 90 s
    pollRef.current = setInterval(async () => {
      retries++;
      try {
        const res = await fetch(`${API}/tasks/dynamic/active?user_id=${USER_ID}`);
        const data = await res.json();
        if (data.task_content?.title) {
          clearInterval(pollRef.current);
          setTaskContent(data.task_content);
          addLog("✅ Task copy generated!");
          setStep(4);
          return;
        }
      } catch {
        // silently retry
      }
      if (retries >= MAX_RETRIES) {
        clearInterval(pollRef.current);
        // Show a fallback card so the demo can continue
        setTaskContent({
          title: `Time for a walk, ${profile?.name ?? "Auntie Lin"}!`,
          body: `Head to ${park?.name || "the park"} for a 30-minute moderate walk.`,
          cta: "I have arrived",
          _timeout: true,
        });
        addLog("⚠️ Copy timeout — showing fallback");
        setStep(4);
      }
    }, 3000);
  }

  useEffect(() => () => clearInterval(pollRef.current), []);

  // ── Step 4: Go to Task page to upload proof ──────────────────────────────
  function handleGoToTask() {
    addLog("📲 Redirecting to Task page to upload proof photo...");
    router.push("/task");
  }

  function handleReset() {
    setStep(0);
    setLog([]);
    setError(null);
    setTaskId(null);
    setParks([]);
    setSelectedPark(null);
    setRuleResult(null);
    setTaskContent(null);
    setPoints(null);
    clearInterval(pollRef.current);
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full bg-[#f5f0e8]">
      <TopBar title="Task Publish Demo" />

      <div className="flex-1 overflow-y-auto px-4 pb-8">

        {/* Profile Card */}
        <div className="bg-[#A7CBED] rounded-2xl p-4 mt-2 mb-4">
          <p className="text-white font-bold text-lg italic">👵 {profile?.name ?? "…"}</p>
          <p className="text-white/90 text-sm mt-1">
            {profile?.age ? `${profile.age}y · ` : ""}BMI {profile?.bmi != null ? Number(profile.bmi).toFixed(1) : "…"} · {profile?.location ?? "Singapore"}
          </p>
          {profile?.seedLat && (
            <p className="text-white/70 text-xs mt-0.5">
              📍 {Number(profile.seedLat).toFixed(4)}, {Number(profile.seedLng).toFixed(4)}
            </p>
          )}
          <div className="mt-2 grid grid-cols-3 gap-2 text-center">
            <div className="bg-white/30 rounded-xl py-2">
              <p className="text-white text-xs">Target</p>
              <p className="text-white font-bold">{profile?.caloriesTarget ?? "…"} kcal</p>
            </div>
            <div className="bg-white/30 rounded-xl py-2">
              <p className="text-white text-xs">Burned today</p>
              <p className="text-white font-bold">{profile?.caloriesToday ?? "…"} kcal</p>
            </div>
            <div className="bg-white/30 rounded-xl py-2">
              <p className="text-white text-xs">Blood glucose</p>
              <p className="text-white font-bold">{profile?.glucose ?? "…"} mmol/L</p>
            </div>
          </div>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-between mb-4 px-1">
          {STEP_LABELS.map((label, i) => (
            <div key={i} className="flex flex-col items-center" style={{ flex: 1 }}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold
                ${step > i ? "bg-green-400 text-white"
                  : step === i ? "bg-[#7bb5e0] text-white"
                  : "bg-gray-200 text-gray-400"}`}>
                {step > i ? "✓" : i + 1}
              </div>
              <p className="text-[9px] text-gray-500 mt-0.5 text-center leading-tight">{label}</p>
            </div>
          ))}
        </div>

        {/* Step 0: Start */}
        {step === 0 && (
          <div className="bg-white rounded-2xl p-5 shadow-sm text-center">
            <p className="text-sm text-gray-600 mb-1">Today {profile?.name ?? "Auntie Lin"} has only burned <strong>110 kcal</strong></p>
            <p className="text-sm text-gray-600 mb-4">but her adjusted target is <strong>{profile?.caloriesTarget ?? 330} kcal</strong> — will the system trigger?</p>
            <button
              onClick={handleStart}
              disabled={loading}
              className="w-full py-3 rounded-full text-white font-bold text-sm"
              style={{ backgroundColor: "#7bb5e0" }}
            >
              {loading ? "Setting up..." : "▶ Start Demo"}
            </button>
          </div>
        )}

        {/* Step 1: Rule Engine Result */}
        {step >= 1 && ruleResult && (
          <div className="bg-white rounded-2xl p-4 shadow-sm mb-3">
            <p className="font-bold text-sm text-gray-800 mb-2">⚙️ Rule Engine Result</p>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Calories burned</span>
                <span className="font-medium">{ruleResult.caloriesToday} kcal</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Adjusted target</span>
                <span className="font-medium">{ruleResult.caloriesTarget} kcal</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Ratio</span>
                <span className="font-medium text-orange-500">{ruleResult.ratio} &lt; 0.60 → TRIGGER ✅</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Blood glucose</span>
                <span className="font-medium text-green-600">{ruleResult.glucose} mmol/L — safe ✅</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Calorie deficit</span>
                <span className="font-medium">{ruleResult.deficit} kcal</span>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Park Selection */}
        {step === 1 && parks.length > 0 && (
          <div className="bg-white rounded-2xl p-4 shadow-sm mb-3">
            <p className="font-bold text-sm text-gray-800 mb-3">🌳 Choose a park near Auntie Lin</p>
            <div className="space-y-2">
              {parks.map((park, i) => (
                <button
                  key={i}
                  onClick={() => { setStep(2); handleSelectPark(i); }}
                  disabled={loading}
                  className="w-full text-left p-3 rounded-xl border border-gray-200 hover:border-[#7bb5e0] hover:bg-blue-50 transition-colors"
                >
                  <p className="font-semibold text-sm text-gray-800">{park.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{park.distance_m}m away · {park.lat?.toFixed(4)}, {park.lng?.toFixed(4)}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Copy generating */}
        {step === 3 && (
          <div className="bg-white rounded-2xl p-5 shadow-sm mb-3 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <svg className="animate-spin h-5 w-5 text-[#7bb5e0]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <p className="text-sm font-semibold text-gray-700">SEA-LION generating personalised copy...</p>
            </div>
            <p className="text-xs text-gray-400">Destination: {selectedPark?.name}</p>
          </div>
        )}

        {/* Step 4: Task copy ready */}
        {step >= 4 && taskContent && (
          <div className="bg-[#F4BAC1] rounded-2xl p-4 shadow-sm mb-3">
            <p className="font-bold text-sm text-white mb-2">📱 Generated Push Notification</p>
            <div className="bg-white/80 rounded-xl p-3">
              <p className="font-bold text-sm text-gray-800">{taskContent.title}</p>
              <p className="text-sm text-gray-600 mt-1">{taskContent.body}</p>
            </div>
          </div>
        )}

        {/* Step 4: Go to Task page */}
        {step === 4 && selectedPark && (
          <div className="bg-white rounded-2xl p-4 shadow-sm mb-3">
            <p className="text-sm text-gray-600 mb-1">
              Your quest is ready! Head to <strong>{selectedPark.name}</strong> and log your proof photo.
            </p>
            <p className="text-xs text-gray-400 mb-3">Task page will show your personalised quest.</p>
            <button
              onClick={handleGoToTask}
              className="w-full py-3 rounded-full text-white font-bold text-sm"
              style={{ backgroundColor: "#7bb5e0" }}
            >
              📲 View Quest in Task Page
            </button>
          </div>
        )}


        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3 mb-3">
            <p className="text-red-600 text-xs font-semibold">Error</p>
            <p className="text-red-500 text-xs mt-0.5">{error}</p>
            <button onClick={handleReset} className="mt-2 text-xs text-red-400 underline">Reset</button>
          </div>
        )}

        {/* Activity Log */}
        {log.length > 0 && (
          <div className="bg-gray-900 rounded-2xl p-4 mt-2">
            <p className="text-gray-400 text-xs font-mono mb-2">Activity Log</p>
            {log.map((line, i) => (
              <p key={i} className="text-green-400 text-xs font-mono leading-5">{line}</p>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
