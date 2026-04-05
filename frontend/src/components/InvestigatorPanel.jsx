"use client";

/**
 * InvestigatorPanel — Shows Investigator Node output in Demo Console.
 * Data is hardcoded for demo stability. Appears after scenario starts playing.
 */

const INVESTIGATOR_DATA = {
  marcus_soft_pre_exercise: {
    user_profile: { age: 27, bmi: 22.3, gender: "male", waist_cm: 78 },
    location: "Near ActiveSG Gym (gym, 50m away)",
    upcoming_activity: { type: "resistance_training", start: "14:00", duration: "90 min" },
    exercise_history: [
      { session: 1, glucose_drop: 0.90 },
      { session: 2, glucose_drop: 0.80 },
      { session: 3, glucose_drop: 0.88 },
    ],
    estimated_glucose_drop: 0.86,
    projected_glucose: 4.04,
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

export default function InvestigatorPanel({ visible = false, scenarioId = "" }) {
  const data = INVESTIGATOR_DATA[scenarioId];

  return (
    <div className="bg-white rounded-xl p-4 shadow-sm">
      <h2 className="text-lg font-bold mb-3">Investigator Node</h2>

      {!visible || !data ? (
        <p className="text-sm text-gray-400">
          Play a scenario to see the data collected by Investigator.
        </p>
      ) : (
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
      )}
    </div>
  );
}
