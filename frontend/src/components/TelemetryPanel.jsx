"use client";

/**
 * TelemetryPanel — Live vitals display for Demo Console.
 * Shows current glucose, heart rate, and GPS location.
 */

const KNOWN_PLACES = [
  { name: "ActiveSG Gym", lat: 1.32, lng: 103.84 },
  { name: "Home", lat: 1.3521, lng: 103.8198 },
  { name: "Warehouse", lat: 1.28, lng: 103.85 },
];

function glucoseColor(g) {
  if (g == null) return "text-gray-400";
  if (g < 3.9) return "text-red-600";
  if (g <= 5.6) return "text-yellow-600";
  return "text-green-600";
}

function glucoseLabel(g) {
  if (g == null) return "";
  if (g < 3.9) return "LOW";
  if (g <= 5.6) return "BORDERLINE";
  return "NORMAL";
}

function hrColor(hr) {
  if (hr == null) return "text-gray-400";
  if (hr > 145) return "text-red-600";
  if (hr > 120) return "text-yellow-600";
  return "text-green-600";
}

function resolvePlaceName(gps) {
  if (!gps) return "--";
  for (const place of KNOWN_PLACES) {
    const dist = Math.sqrt((gps.lat - place.lat) ** 2 + (gps.lng - place.lng) ** 2);
    if (dist < 0.01) return place.name;
  }
  return `${gps.lat.toFixed(4)}, ${gps.lng.toFixed(4)}`;
}

export default function TelemetryPanel({ glucose, heartRate, gps, lastUpdate }) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm">
      <h2 className="text-lg font-bold mb-3">Live Telemetry</h2>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-500">Glucose</span>
          <p className={`text-xl font-bold ${glucoseColor(glucose)}`}>
            {glucose != null ? `${glucose} mmol/L` : "--"}
          </p>
          {glucose != null && (
            <span className={`text-xs font-semibold ${glucoseColor(glucose)}`}>
              {glucoseLabel(glucose)}
            </span>
          )}
        </div>
        <div>
          <span className="text-gray-500">Heart Rate</span>
          <p className={`text-xl font-bold ${hrColor(heartRate)}`}>
            {heartRate != null ? `${heartRate} bpm` : "--"}
          </p>
        </div>
        <div className="col-span-2">
          <span className="text-gray-500">Location</span>
          <p className="text-base font-medium text-gray-800">
            {resolvePlaceName(gps)}
          </p>
        </div>
        {lastUpdate && (
          <div className="col-span-2 text-xs text-gray-400">
            Last update: {lastUpdate}
          </div>
        )}
      </div>
    </div>
  );
}
