"use client";

import { useState, useEffect } from "react";
import { useTranslation } from "../lib/i18n";
import { API_BASE } from "../lib/config";

export default function SugarChart({ userId }) {
  const { t } = useTranslation();
  const [points, setPoints] = useState([]);
  const [startLabel, setStartLabel] = useState("");

  useEffect(() => {
    if (!userId) return;

    fetch(`${API_BASE}/health/glucose?user_id=${userId}&hours=24`)
      .then((res) => res.json())
      .then((data) => {
        if (!data.readings || data.readings.length === 0) return;

        const readings = data.readings;
        const xMin = 40;
        const xMax = 260;
        const yMin = 20;
        const yMax = 85;

        // Find glucose range for scaling
        const glucoseValues = readings.map((r) => r.glucose);
        const gMin = Math.min(...glucoseValues);
        const gMax = Math.max(...glucoseValues);
        const gRange = gMax - gMin || 1;

        const mapped = readings.map((r, i) => {
          const x = xMin + (i / Math.max(readings.length - 1, 1)) * (xMax - xMin);
          // Invert Y: higher glucose = lower Y value (higher on chart)
          const y = yMax - ((r.glucose - gMin) / gRange) * (yMax - yMin);
          return [Math.round(x), Math.round(y)];
        });

        setPoints(mapped);

        // Set start label from first reading
        const first = new Date(readings[0].recorded_at);
        const hours = first.getHours();
        const mins = first.getMinutes().toString().padStart(2, "0");
        const ampm = hours >= 12 ? "pm" : "am";
        const h12 = hours % 12 || 12;
        setStartLabel(`${h12}:${mins}${ampm}`);
      })
      .catch(() => {
        // Keep mock points on failure
      });
  }, [userId]);

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p[0]} ${p[1]}`)
    .join(" ");

  return (
    <div className="mt-2">
      {/* Labels */}
      <div className="text-xs font-semibold text-gray-800 leading-tight mb-1">
        <div>{t("blood")}</div>
        <div>{t("sugar")}</div>
      </div>

      <svg viewBox="0 0 300 110" className="w-full h-auto">
        {/* Y-axis */}
        <line x1="30" y1="10" x2="30" y2="90" stroke="#333" strokeWidth="1.5" />
        {/* Y-axis arrow */}
        <polygon points="30,10 27,18 33,18" fill="#333" />

        {/* X-axis */}
        <line x1="30" y1="90" x2="270" y2="90" stroke="#333" strokeWidth="1.5" />
        {/* X-axis arrow */}
        <polygon points="270,90 262,87 262,93" fill="#333" />

        {/* Line */}
        <path d={linePath} fill="none" stroke="#333" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* X labels */}
        <text x="35" y="108" fontSize="9" fill="#666">{startLabel}</text>
        <text x="255" y="108" fontSize="9" fill="#666" textAnchor="end">{t("now")}</text>
      </svg>
    </div>
  );
}
