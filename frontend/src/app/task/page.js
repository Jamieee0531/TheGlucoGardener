"use client";

import { useState, useEffect, useRef } from "react";
import TopBar from "../../components/TopBar";
import MiniChat from "../../components/MiniChat";
import { useAuth } from "../../lib/useAuth";
import { useTranslation } from "../../lib/i18n";

const API_BASE = "http://localhost:8080";
const TASK_AGENT_API = "http://localhost:8001";

const TASKS = [
  {
    id: "meals",
    titleKey: "task_log_meals",
    emoji: "🍽",
    color: "#A7CBED",
    descKey: "task_log_meals_desc",
    logType: "photo",
    completable: true,
    completedKey: "task_meal_logged",
    buttonColor: "#7bb5e0",
  },
  {
    id: "body",
    titleKey: "task_body_checkin",
    emoji: "✏️",
    color: "#F5C19E",
    descKey: "task_body_checkin_desc",
    logType: "form",
    completable: true,
    completedKey: "task_checked_in",
    buttonColor: "#e8a878",
  },
];

const PTS_PER_TASK = 20;
const MAX_DAILY_PTS = 60;
const MAX_PLANT_PTS = 100;

export default function TaskPage() {
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  const [expandedId, setExpandedId] = useState(null);
  const [completedTasks, setCompletedTasks] = useState(new Set());
  const [showPhotoModal, setShowPhotoModal] = useState(false);
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [showBodyModal, setShowBodyModal] = useState(false);
  const [bodyForm, setBodyForm] = useState({ waist: "", weight: "" });

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const dynFileRef = useRef(null);

  const [dynTask, setDynTask] = useState(null);
  const [dynCompleted, setDynCompleted] = useState(false);
  const [dynUploading, setDynUploading] = useState(false);
  const [dynPoints, setDynPoints] = useState(null);
  const [dynEarned, setDynEarned] = useState(null);
  const [dynTitle, setDynTitle] = useState(null);
  const [totalPts, setTotalPts] = useState(0);
  const [plantProgress, setPlantProgress] = useState(0);
  const [dbDailyCompleted, setDbDailyCompleted] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [resultModal, setResultModal] = useState(null); // { success, title, message }
  const [mealChatOpen, setMealChatOpen] = useState(false);
  const [mealImageFile, setMealImageFile] = useState(null);

  useEffect(() => {
    if (!user) return;
    const uid = user.user_id;

    // Fetch points from reward_log
    fetch(`${API_BASE}/garden/my?user_id=${uid}`)
      .then((r) => r.json())
      .then((data) => {
        setTotalPts(data.total_points || 0);
        setPlantProgress(data.accumulated_points % 500);
      })
      .catch(() => {});

    // Fetch today's completed routine tasks
    fetch(`${API_BASE}/health/daily-tasks?user_id=${uid}`)
      .then((r) => r.json())
      .then((data) => setDbDailyCompleted(data.completed || 0))
      .catch(() => {});

    // Check which tasks are already completed
    fetch(`${API_BASE}/health/task-status?user_id=${uid}`)
      .then((r) => r.json())
      .then((data) => {
        const done = new Set();
        if (data.body_checkin_done) done.add("body");
        if (data.breakfast_done || data.lunch_done || data.dinner_done) done.add("meals");
        setCompletedTasks(done);
      })
      .catch(() => {});
  }, [user]);

  // Poll task_agent for dynamic task
  useEffect(() => {
    if (!user) return;
    const poll = async () => {
      try {
        const res = await fetch(`${TASK_AGENT_API}/tasks/dynamic/active?user_id=${user.user_id}`);
        const data = await res.json();
        if (data.task_id) setDynTask(data);
      } catch {}
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, [user]);

  if (loading || !user) return null;

  const dailyPts = dbDailyCompleted * PTS_PER_TASK;

  const handleDynUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !dynTask) return;
    e.target.value = "";
    setDynUploading(true);
    try {
      // Save title before clearing task
      const savedTitle = dynTask.task_content?.title || "Chase the golden hour";

      // 1. Baseline points
      const beforePts = await fetch(`${TASK_AGENT_API}/points/summary?user_id=${user.user_id}`)
        .then(r => r.json()).catch(() => ({ total_points: 0 }));

      // 2. Upload photo
      const form = new FormData();
      form.append("photo", file);
      const upRes = await fetch(
        `${TASK_AGENT_API}/tasks/dynamic/${dynTask.task_id}/upload-photo?user_id=${user.user_id}`,
        { method: "POST", body: form }
      );
      if (!upRes.ok) throw new Error("Upload failed");

      // 3. Simulate arrival using destination coords
      const dest = dynTask.task_content?.destination || dynTask.destination || {};
      const lat = dest.lat ?? 1.3526;
      const lng = dest.lng ?? 103.8352;
      const arrRes = await fetch(
        `${TASK_AGENT_API}/tasks/dynamic/${dynTask.task_id}/arrive?user_id=${user.user_id}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lat, lng }),
        }
      );
      const arrData = await arrRes.json();
      if (!arrData.passed) throw new Error("Arrival check failed");

      // 4. Fetch updated points and compute earned
      const ptsData = await fetch(`${TASK_AGENT_API}/points/summary?user_id=${user.user_id}`)
        .then(r => r.json());
      setDynEarned(ptsData.total_points - beforePts.total_points);
      setDynPoints(ptsData.total_points);
      setDynTitle(savedTitle);
      setDynCompleted(true);
      setDynTask(null);
    } catch (err) {
      setResultModal({ success: false, title: t("upload_failed") || "Upload failed", message: err.message });
    }
    setDynUploading(false);
  };

  const handleCardClick = (taskId) => {
    setExpandedId((prev) => (prev === taskId ? null : taskId));
  };

  const handleLogClick = (task) => {
    if (completedTasks.has(task.id)) return;
    setActiveTaskId(task.id);
    if (task.logType === "photo") {
      setShowPhotoModal(true);
    } else if (task.logType === "form") {
      setShowBodyModal(true);
    }
  };

  const completeTask = (taskId) => {
    setCompletedTasks((prev) => new Set([...prev, taskId]));
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    if (activeTaskId === "meals") {
      // Open mini chat with the image
      setMealImageFile(file);
      setMealChatOpen(true);
      setShowPhotoModal(false);
      setActiveTaskId(null);
    } else {
      // Non-meal photo tasks: just mark complete locally
      completeTask(activeTaskId);
      setShowPhotoModal(false);
      setActiveTaskId(null);
    }
  };

  const handleMealConfirm = () => {
    completeTask("meals");
    setMealChatOpen(false);
    setMealImageFile(null);
    // Refresh points and daily tasks
    const uid = user.user_id;
    fetch(`${API_BASE}/garden/my?user_id=${uid}`)
      .then((r) => r.json())
      .then((d) => {
        setTotalPts(d.total_points || 0);
        setPlantProgress(d.accumulated_points % 500);
      });
    fetch(`${API_BASE}/health/daily-tasks?user_id=${uid}`)
      .then((r) => r.json())
      .then((d) => setDbDailyCompleted(d.completed || 0));
  };

  const handleBodySubmit = async () => {
    try {
      const res = await fetch(`${API_BASE}/health/body-checkin`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.user_id,
          waist_cm: parseFloat(bodyForm.waist),
          weight_kg: parseFloat(bodyForm.weight),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        completeTask(activeTaskId);
        // Refresh points
        fetch(`${API_BASE}/garden/my?user_id=${user.user_id}`)
          .then((r) => r.json())
          .then((d) => {
            setTotalPts(d.total_points || 0);
            setPlantProgress(d.accumulated_points % 500);
          });
        // Refresh daily task count
        fetch(`${API_BASE}/health/daily-tasks?user_id=${user.user_id}`)
          .then((r) => r.json())
          .then((d) => setDbDailyCompleted(d.completed || 0));
      }
      if (data.already_done) {
        setResultModal({
          success: false,
          title: t("body_already_done") || "Already Done",
          message: t("body_already_done_msg") || "You already completed this check-in this week.",
        });
      }
    } catch (e) {
      console.error("Body check-in failed:", e);
    }
    setShowBodyModal(false);
    setActiveTaskId(null);
    setBodyForm({ waist: "", weight: "" });
  };

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title={t("task_title")} transparent />
      <div className="flex-1 overflow-y-auto pb-4">
        {/* Dynamic Quest Card */}
        <div className="px-4 mt-2 mb-1">
          <div className="rounded-2xl p-4" style={{ backgroundColor: "#F4BAC1" }}>
            {dynCompleted ? (
              /* Completed state */
              <>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-white font-bold italic text-lg leading-tight">
                    Chase the golden hour 🌅
                  </p>
                  <div className="w-8 h-8 rounded-full bg-white flex-shrink-0 ml-2" />
                </div>
                <div className="flex items-center gap-2">
                  <p className="text-white text-xl">🌸</p>
                  <div>
                    <p className="text-white font-bold italic text-base">{t("task_quest_complete")}</p>
                    <p className="text-white/90 text-sm">
                      {dynEarned != null ? `+${dynEarned} pts` : "+50 pts"}{" "}
                      {dynPoints != null && <span className="text-white/70">· Total: {dynPoints} pts</span>}
                    </p>
                  </div>
                </div>
              </>
            ) : dynTask?.task_content?.title ? (
              /* Active — copy ready */
              <>
                <div className="flex items-center justify-between mb-1">
                  <p className="text-white text-xs font-semibold uppercase tracking-wide opacity-80">
                    {t("task_quest_today")} ✨
                  </p>
                  <div className="w-8 h-8 rounded-full bg-white flex-shrink-0" />
                </div>
                <p className="text-white font-bold italic text-lg leading-tight">
                  {dynTask.task_content.title} 🌅
                </p>
                <p className="text-white/90 text-sm mt-2 mb-3">
                  {dynTask.task_content.body}
                </p>
                <button
                  disabled={dynUploading}
                  onClick={() => dynFileRef.current?.click()}
                  className="px-5 py-2 rounded-full text-sm font-semibold text-white flex items-center gap-2"
                  style={{ backgroundColor: dynUploading ? "#c08890" : "#e89098" }}
                >
                  {dynUploading ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                      </svg>
                      {t("task_logging")}
                    </>
                  ) : `📸 ${t("task_log_proof")}`}
                </button>
              </>
            ) : dynTask ? (
              /* Task exists but copy not ready yet */
              <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 py-1 flex-1">
                <svg className="animate-spin h-5 w-5 text-white/70 flex-shrink-0" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                <div>
                  <p className="text-white font-semibold text-sm italic">Chase the golden hour 🌅</p>
                  <p className="text-white/70 text-xs mt-0.5">{t("task_quest_personalising")}</p>
                </div>
                </div>
                <div className="w-8 h-8 rounded-full bg-white flex-shrink-0" />
              </div>
            ) : (
              /* Locked — no task yet */
              <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-white font-bold italic text-base">Chase the golden hour 🌅</p>
                <p className="text-white/80 text-sm mt-1 mb-3">
                  {t("task_quest_locked")} 🌿
                </p>
                <button
                  disabled
                  className="px-5 py-2 rounded-full text-sm font-semibold opacity-40"
                  style={{ backgroundColor: "#e89098", color: "white" }}
                >
                  📸 {t("task_log_proof")}
                </button>
              </div>
              <div className="w-8 h-8 rounded-full bg-white flex-shrink-0 mt-1" />
              </div>
            )}
          </div>
        </div>

        {/* Card Stack */}
        <div className="px-4 mt-2">
          {TASKS.map((task) => {
            const isExpanded = expandedId === task.id;
            const isCompleted = completedTasks.has(task.id);

            return (
              <div
                key={task.id}
                onClick={() => handleCardClick(task.id)}
                className="-mt-2 first:mt-0 relative cursor-pointer"
                style={{
                  backgroundColor: task.color,
                  borderRadius: 20,
                  padding: "16px 20px",
                  transition: "all 300ms ease",
                  zIndex: TASKS.indexOf(task),
                }}
              >
                {/* Header row */}
                <div className="flex items-center justify-between">
                  <h3
                    className="text-lg font-bold italic text-white"
                    style={{
                      textDecoration: isCompleted ? "line-through" : "none",
                    }}
                  >
                    {t(task.titleKey)} {task.emoji}
                  </h3>
                  {isCompleted ? (
                    <span className="text-sm font-bold italic text-[#ff6b8a]">
                      20 {t("task_pt_earned")}
                    </span>
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-white" />
                  )}
                </div>

                {/* Expanded content */}
                <div
                  style={{
                    maxHeight: isExpanded ? 120 : 0,
                    opacity: isExpanded ? 1 : 0,
                    overflow: "hidden",
                    transition: "max-height 300ms ease, opacity 300ms ease",
                  }}
                >
                  <p
                    className="text-sm text-white/90 mt-2"
                    style={{
                      textDecoration: isCompleted ? "line-through" : "none",
                    }}
                  >
                    {t(task.descKey)}
                  </p>

                  {task.extraInfo && (
                    <p className="text-sm text-white mt-2">
                      <span className="font-semibold">{task.extraInfo}</span>
                    </p>
                  )}

                  {task.logType !== "none" && (
                    <button
                      disabled={isCompleted || (uploading && task.id === "meals")}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleLogClick(task);
                      }}
                      className="mt-3 px-6 py-2 rounded-full text-sm font-semibold text-white flex items-center gap-2"
                      style={{
                        backgroundColor: isCompleted
                          ? "#8bc34a"
                          : (uploading && task.id === "meals")
                          ? "#999"
                          : task.buttonColor,
                      }}
                    >
                      {uploading && task.id === "meals" ? (
                        <>
                          <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                          {t("analysing") || "Analysing..."}
                        </>
                      ) : isCompleted ? (
                        t(task.completedKey)
                      ) : (
                        t("task_log_here")
                      )}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Mini Chat overlay for meals */}
        {mealChatOpen && (
          <div className="px-4 mt-2">
            <div className="rounded-2xl overflow-hidden" style={{ backgroundColor: "#A7CBED" }}>
              <MiniChat
                userId={user.user_id}
                imageFile={mealImageFile}
                onConfirmEaten={handleMealConfirm}
                onClose={() => {
                  setMealChatOpen(false);
                  setMealImageFile(null);
                }}
              />
            </div>
          </div>
        )}

        {/* Stats Section */}
        <div className="flex items-start px-5 mt-6">
          {/* Left: stats */}
          <div className="flex-1">
            <p className="text-sm font-semibold text-gray-800">
              {t("task_daily_completed")}
            </p>
            <p className="text-2xl font-bold text-gray-900">
              {dailyPts}{" "}
              <span className="text-sm font-normal text-gray-500">
                / {MAX_DAILY_PTS} {t("task_pts")}
              </span>
            </p>
            {/* Progress bar blue */}
            <div className="w-full h-2 bg-gray-300 rounded-full mt-1 mb-4">
              <div
                className="h-2 rounded-full"
                style={{
                  width: `${(dailyPts / MAX_DAILY_PTS) * 100}%`,
                  backgroundColor: "#b8e6e8",
                  transition: "width 300ms ease",
                }}
              />
            </div>

            <p className="text-sm font-semibold text-gray-800">
              {t("task_plant_progress")}
            </p>
            <p className="text-2xl font-bold text-gray-900">
              {plantProgress}{" "}
              <span className="text-sm font-normal text-gray-500">
                / 500 {t("task_pts")}
              </span>
            </p>
            {/* Progress bar green */}
            <div className="w-full h-2 bg-gray-300 rounded-full mt-1 mb-4">
              <div
                className="h-2 rounded-full"
                style={{
                  width: `${(plantProgress / 500) * 100}%`,
                  backgroundColor: "#c8e6a0",
                  transition: "width 300ms ease",
                }}
              />
            </div>

            <p className="text-sm font-semibold text-gray-800">{t("task_total_pts")}</p>
            <p className="text-2xl font-bold text-gray-900">
              {totalPts}
              <span className="text-sm font-normal">{t("task_pts")}</span>
            </p>
          </div>

          {/* Right: flower */}
          <img
            src="/flower.jpg"
            alt="Plant"
            className="w-[120px] h-auto object-contain ml-2"
          />
        </div>

        {/* Reset button — small icon bottom-right */}
        <div className="flex justify-end px-5 mt-2 mb-2">
          <button
            onClick={async () => {
              const form = new FormData();
              form.append("user_id", user.user_id);
              await fetch(`${API_BASE}/health/reset-tasks`, { method: "POST", body: form });
              setCompletedTasks(new Set());
              // Refresh all data
              const uid = user.user_id;
              fetch(`${API_BASE}/garden/my?user_id=${uid}`).then(r => r.json()).then(d => { setTotalPts(d.total_points || 0); setPlantProgress(d.accumulated_points % 500); });
              fetch(`${API_BASE}/health/daily-tasks?user_id=${uid}`).then(r => r.json()).then(d => setDbDailyCompleted(d.completed || 0));
            }}
            className="w-7 h-7 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center transition-colors opacity-40 hover:opacity-70"
            title="Reset tasks"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="#666" className="w-3.5 h-3.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
            </svg>
          </button>
        </div>
      </div>

      {/* Photo Modal */}
      {showPhotoModal && (
        <>
          <div
            className="fixed inset-0 bg-black/30 z-40"
            onClick={() => {
              setShowPhotoModal(false);
              setActiveTaskId(null);
            }}
          />
          <div className="fixed bottom-0 left-0 right-0 bg-white rounded-t-2xl z-50 p-4">
            <p className="text-center text-sm font-semibold mb-3">{t("upload")}</p>
            <button
              onClick={() => cameraInputRef.current?.click()}
              className="block w-full text-center py-3 text-sm border-b border-gray-200"
            >
              {t("open_camera")}
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="block w-full text-center py-3 text-sm border-b border-gray-200"
            >
              {t("open_gallery")}
            </button>
            <button
              onClick={() => {
                setShowPhotoModal(false);
                setActiveTaskId(null);
              }}
              className="block w-full text-center py-3 text-sm text-gray-500"
            >
              {t("cancel")}
            </button>
          </div>
        </>
      )}

      {/* Body Check-in Modal */}
      {showBodyModal && (
        <>
          <div
            className="fixed inset-0 bg-black/30 z-40"
            onClick={() => {
              setShowBodyModal(false);
              setActiveTaskId(null);
            }}
          />
          <div className="fixed top-1/3 left-6 right-6 bg-white rounded-2xl z-50 p-5 shadow-xl">
            <h4 className="text-lg font-bold mb-4">{t("body_checkin_title")}</h4>
            <div className="space-y-3">
              <input
                type="number"
                placeholder={t("waist_cm")}
                value={bodyForm.waist}
                onChange={(e) =>
                  setBodyForm({ ...bodyForm, waist: e.target.value })
                }
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
              <input
                type="number"
                placeholder={t("weight_kg")}
                value={bodyForm.weight}
                onChange={(e) =>
                  setBodyForm({ ...bodyForm, weight: e.target.value })
                }
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <button
              disabled={!bodyForm.waist || !bodyForm.weight}
              onClick={handleBodySubmit}
              className="mt-4 w-full py-2 rounded-full text-white font-semibold text-sm disabled:opacity-40"
              style={{ backgroundColor: "#e8a878" }}
            >
              {t("submit")}
            </button>
            <button
              onClick={() => {
                setShowBodyModal(false);
                setActiveTaskId(null);
                setBodyForm({ waist: "", weight: "" });
              }}
              className="mt-2 w-full text-center text-sm text-gray-500"
            >
              {t("cancel")}
            </button>
          </div>
        </>
      )}

      {/* Result Modal */}
      {resultModal && (
        <>
          <div
            className="fixed inset-0 bg-black/40 z-40"
            onClick={() => setResultModal(null)}
          />
          <div className="fixed top-1/3 left-6 right-6 bg-white rounded-2xl z-50 p-6 shadow-xl text-center">
            <div className="text-4xl mb-3">
              {resultModal.success ? "🎉" : "😅"}
            </div>
            <h4 className="text-lg font-bold text-gray-800 mb-2">
              {resultModal.title}
            </h4>
            <p className="text-sm text-gray-600 whitespace-pre-line mb-4">
              {resultModal.message}
            </p>
            <button
              onClick={() => setResultModal(null)}
              className="w-full py-2.5 rounded-full text-white font-semibold text-sm"
              style={{
                backgroundColor: resultModal.success ? "#7cb342" : "#e8927c",
              }}
            >
              {t("ok") || "OK"}
            </button>
          </div>
        </>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileChange}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileChange}
      />
      <input
        ref={dynFileRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleDynUpload}
      />
    </div>
  );
}
