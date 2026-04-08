"use client";

/**
 * InvestigatorPanel — Shows Investigator Node output in Demo Console.
 * Data is hardcoded for demo stability. Appears after scenario starts playing.
 */

const INVESTIGATOR_DATA = {
  marcus_soft_pre_exercise: {
    user_profile: { age: 27, bmi: 22.3, gender: "male", waist_cm: 78 },
    location: "Near ActiveSG Gym (gym, 50m away)",
    upcoming_activity: { type: "hiit", start: "14:00", duration: "45 min" },
    exercise_history: [
      { session: 1, glucose_drop: 1.05 },
      { session: 2, glucose_drop: 0.95 },
      { session: 3, glucose_drop: 1.10 },
    ],
    estimated_glucose_drop: 1.03,
    projected_glucose: 3.87,
    food_intake: {
      meals: [
        { time: "06:30", meal_type: "breakfast", food_name: "Kaya Toast + Kopi", kcal: 320, gi: "medium" },
        { time: "11:30", meal_type: "lunch", food_name: "Chicken Sandwich", kcal: 350, gi: "medium" },
      ],
      total_kcal: 670,
      last_meal_hours_ago: 2.0,
    },
    emotion: "No recent emotion data",
  },
};

function DataRow({ label, value, highlight }) {
  return (
    <div className="flex justify-between text-xs py-0.5">
      <span className="text-gray-500">{label}</span>
      <span className={`font-mono ${highlight ? "font-bold text-orange-600" : "text-gray-700"}`}>
        {value}
      </span>
    </div>
  );
}

/**
 * Content-only version used inside the Agent Pipeline wrapper on demo page.
 */
export function InvestigatorPanelContent({ visible = false, scenarioId = "" }) {
  const data = INVESTIGATOR_DATA[scenarioId];

  if (!visible || !data) {
    return (
      <p className="text-sm text-gray-400">
        Play a scenario to see the data collected by Investigator.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {/* User Profile */}
      <div>
        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">
          User Profile
        </h4>
        <div className="bg-gray-50 rounded p-2">
          <DataRow label="Age" value={data.user_profile.age} />
          <DataRow label="BMI" value={data.user_profile.bmi} />
          <DataRow label="Gender" value={data.user_profile.gender} />
          <DataRow label="Waist" value={`${data.user_profile.waist_cm} cm`} />
        </div>
      </div>

      {/* Location */}
      <div>
        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">
          Location
        </h4>
        <div className="bg-gray-50 rounded p-2">
          <p className="text-xs text-gray-700">{data.location}</p>
        </div>
      </div>

      {/* Upcoming Activity */}
      <div>
        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">
          Upcoming Activity
        </h4>
        <div className="bg-gray-50 rounded p-2">
          <DataRow label="Type" value={data.upcoming_activity.type} />
          <DataRow label="Start" value={data.upcoming_activity.start} />
          <DataRow label="Duration" value={data.upcoming_activity.duration} />
        </div>
      </div>

      {/* Exercise History */}
      <div>
        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">
          Exercise History (last 3 sessions)
        </h4>
        <div className="bg-gray-50 rounded p-2">
          {data.exercise_history.map((s) => (
            <DataRow
              key={s.session}
              label={`Session ${s.session}`}
              value={`-${s.glucose_drop} mmol/L`}
            />
          ))}
        </div>
      </div>

      {/* Computed Values */}
      <div>
        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">
          Glucose Projection (deterministic)
        </h4>
        <div className="bg-orange-50 rounded p-2 border border-orange-200">
          <DataRow
            label="Estimated drop"
            value={`${data.estimated_glucose_drop} mmol/L`}
            highlight
          />
          <DataRow
            label="Projected glucose"
            value={`${data.projected_glucose} mmol/L`}
            highlight
          />
        </div>
      </div>

      {/* Food Intake */}
      <div>
        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">
          Today&apos;s Food Intake
        </h4>
        <div className="bg-gray-50 rounded p-2">
          {data.food_intake.meals.map((m, i) => (
            <DataRow
              key={i}
              label={`${m.time} ${m.meal_type}`}
              value={`${m.food_name} (${m.kcal} kcal, GI: ${m.gi})`}
            />
          ))}
          <div className="border-t border-gray-200 mt-1 pt-1">
            <DataRow label="Total calories" value={`${data.food_intake.total_kcal} kcal`} />
            <DataRow label="Last meal" value={`${data.food_intake.last_meal_hours_ago}h ago`} />
          </div>
        </div>
      </div>

      {/* Emotion */}
      <div>
        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">
          Emotion Context
        </h4>
        <div className="bg-gray-50 rounded p-2">
          <p className="text-xs text-gray-500">{data.emotion}</p>
        </div>
      </div>
    </div>
  );
}

/**
 * Standalone card version (kept for backwards compat if used elsewhere).
 */
export default function InvestigatorPanel({ visible = false, scenarioId = "" }) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm">
      <h2 className="text-lg font-bold mb-3">Investigator Node</h2>
      <InvestigatorPanelContent visible={visible} scenarioId={scenarioId} />
    </div>
  );
}
