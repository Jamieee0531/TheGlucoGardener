"use client";

import { useState, useRef } from "react";
import TopBar from "../../components/TopBar";

const TASKS = [
  {
    id: "move",
    title: "Move a little today",
    emoji: "🏃",
    color: "#A7CBED",
    description: "Moving your body helps support stable glucose.",
    logType: "none",
    completable: false,
    extraInfo: "Step count: 1234/8000",
    completedLabel: null,
  },
  {
    id: "meals",
    title: "Log your meals",
    emoji: "🍽",
    color: "#A7CBED",
    description: "Small notes today, better insights tomorrow.",
    logType: "photo",
    completable: true,
    completedLabel: "Meal Logged!",
    buttonColor: "#7bb5e0",
  },
  {
    id: "body",
    title: "Body check-in",
    emoji: "✏️",
    color: "#F5C19E",
    description: "Tracking your waist helps monitor metabolic health.",
    logType: "form",
    completable: true,
    completedLabel: "Checked In!",
    buttonColor: "#e8a878",
  },
  {
    id: "sunset",
    title: "Sunset chaser",
    emoji: "🌅",
    color: "#F4BAC1",
    description:
      "Personalized quest: Take a brisk walk at West Coast Park and capture the sunset.",
    logType: "photo",
    completable: true,
    completedLabel: "Logged!",
    buttonColor: "#e89098",
  },
];

const MOCK_BASE_PTS = 2000;
const PTS_PER_TASK = 10;
const MAX_DAILY_PTS = 40;
const MAX_PLANT_PTS = 100;

export default function TaskPage() {
  const [expandedId, setExpandedId] = useState("sunset");
  const [completedTasks, setCompletedTasks] = useState(new Set());
  const [showPhotoModal, setShowPhotoModal] = useState(false);
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [showBodyModal, setShowBodyModal] = useState(false);
  const [bodyForm, setBodyForm] = useState({ waist: "", weight: "" });

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const completedCount = TASKS.filter(
    (t) => t.completable && completedTasks.has(t.id)
  ).length;
  const dailyPts = completedCount * PTS_PER_TASK;
  const plantPts = completedCount * PTS_PER_TASK;
  const totalPts = MOCK_BASE_PTS + completedCount * PTS_PER_TASK;

  const handleCardClick = (taskId) => {
    if (taskId === "sunset") return;
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

  const handleFileChange = (e) => {
    if (e.target.files?.[0]) {
      completeTask(activeTaskId);
      setShowPhotoModal(false);
      setActiveTaskId(null);
    }
    e.target.value = "";
  };

  const handleBodySubmit = () => {
    completeTask(activeTaskId);
    setShowBodyModal(false);
    setActiveTaskId(null);
    setBodyForm({ waist: "", weight: "" });
  };

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title="Task" transparent />
      <div className="flex-1 overflow-y-auto pb-4">
        {/* Card Stack */}
        <div className="px-4 mt-2">
          {TASKS.map((task) => {
            const isExpanded =
              task.id === "sunset" || expandedId === task.id;
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
                    {task.title} {task.emoji}
                  </h3>
                  {isCompleted ? (
                    <span className="text-sm font-bold italic text-[#ff6b8a]">
                      10 pt
                      <br />
                      earned!
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
                    {task.description}
                  </p>

                  {task.extraInfo && (
                    <p className="text-sm text-white mt-2">
                      <span className="font-semibold">{task.extraInfo}</span>
                    </p>
                  )}

                  {task.logType !== "none" && (
                    <button
                      disabled={isCompleted}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleLogClick(task);
                      }}
                      className="mt-3 px-6 py-2 rounded-full text-sm font-semibold text-white"
                      style={{
                        backgroundColor: isCompleted
                          ? "#8bc34a"
                          : task.buttonColor,
                      }}
                    >
                      {isCompleted ? task.completedLabel : "Log Here"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Stats Section */}
        <div className="flex items-start px-5 mt-6">
          {/* Left: stats */}
          <div className="flex-1">
            <p className="text-sm font-semibold text-gray-800">
              Daily task completed
            </p>
            <p className="text-2xl font-bold text-gray-900">
              {dailyPts}{" "}
              <span className="text-sm font-normal text-gray-500">
                / {MAX_DAILY_PTS} pts
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
              Plant growth progress
            </p>
            <p className="text-2xl font-bold text-gray-900">
              {plantPts}{" "}
              <span className="text-sm font-normal text-gray-500">
                / {MAX_PLANT_PTS} pts
              </span>
            </p>
            {/* Progress bar green */}
            <div className="w-full h-2 bg-gray-300 rounded-full mt-1 mb-4">
              <div
                className="h-2 rounded-full"
                style={{
                  width: `${(plantPts / MAX_PLANT_PTS) * 100}%`,
                  backgroundColor: "#c8e6a0",
                  transition: "width 300ms ease",
                }}
              />
            </div>

            <p className="text-sm font-semibold text-gray-800">Total pts</p>
            <p className="text-2xl font-bold text-gray-900">
              {totalPts}
              <span className="text-sm font-normal">pts</span>
            </p>
          </div>

          {/* Right: flower */}
          <img
            src="/flower.jpg"
            alt="Plant"
            className="w-[120px] h-auto object-contain ml-2"
          />
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
            <p className="text-center text-sm font-semibold mb-3">Upload</p>
            <button
              onClick={() => cameraInputRef.current?.click()}
              className="block w-full text-center py-3 text-sm border-b border-gray-200"
            >
              Open Camera
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="block w-full text-center py-3 text-sm border-b border-gray-200"
            >
              Open Gallery
            </button>
            <button
              onClick={() => {
                setShowPhotoModal(false);
                setActiveTaskId(null);
              }}
              className="block w-full text-center py-3 text-sm text-gray-500"
            >
              Cancel
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
            <h4 className="text-lg font-bold mb-4">Body Check-in</h4>
            <div className="space-y-3">
              <input
                type="number"
                placeholder="Waist (cm)"
                value={bodyForm.waist}
                onChange={(e) =>
                  setBodyForm({ ...bodyForm, waist: e.target.value })
                }
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
              <input
                type="number"
                placeholder="Weight (kg)"
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
              Submit
            </button>
            <button
              onClick={() => {
                setShowBodyModal(false);
                setActiveTaskId(null);
                setBodyForm({ waist: "", weight: "" });
              }}
              className="mt-2 w-full text-center text-sm text-gray-500"
            >
              Cancel
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
    </div>
  );
}
