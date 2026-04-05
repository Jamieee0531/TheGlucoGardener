"use client";

/**
 * LiveSugarChart — Real-time glucose line chart for Demo Console.
 * Accumulates data points as scenario steps fire.
 * Pure SVG, no external dependencies.
 */

const W = 300;
const H = 140;
const PAD = { top: 15, right: 15, bottom: 25, left: 40 };

const Y_MIN = 2.5; // mmol/L floor
const Y_MAX = 12;  // mmol/L ceiling
const SAFE_LOW = 3.9;
const SAFE_HIGH = 10.0;

function scaleY(glucose) {
  const plotH = H - PAD.top - PAD.bottom;
  // Invert: higher glucose = lower Y
  return PAD.top + plotH * (1 - (glucose - Y_MIN) / (Y_MAX - Y_MIN));
}

function scaleX(index, total) {
  const plotW = W - PAD.left - PAD.right;
  if (total <= 1) return PAD.left + plotW / 2;
  return PAD.left + (index / (total - 1)) * plotW;
}

export default function LiveSugarChart({ dataPoints = [] }) {
  // dataPoints: [{ glucose: number, label?: string }]
  const plotLeft = PAD.left;
  const plotRight = W - PAD.right;
  const plotTop = PAD.top;
  const plotBottom = H - PAD.bottom;

  // Safe zone band
  const safeTop = scaleY(SAFE_HIGH);
  const safeBottom = scaleY(SAFE_LOW);

  // Danger threshold line
  const dangerY = scaleY(SAFE_LOW);

  // Map data to SVG coordinates
  const pts = dataPoints.map((d, i) => ({
    x: scaleX(i, dataPoints.length),
    y: scaleY(d.glucose),
    glucose: d.glucose,
    label: d.label,
  }));

  const linePath = pts
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");

  // Y-axis ticks
  const yTicks = [3, 4, 5, 6, 8, 10];

  return (
    <div className="bg-white rounded-xl p-4 shadow-sm">
      <h2 className="text-lg font-bold mb-2">Glucose Trend</h2>

      {dataPoints.length === 0 ? (
        <p className="text-sm text-gray-400 py-4 text-center">
          No glucose data yet. Play a scenario to see the chart.
        </p>
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
          {/* Safe zone band */}
          <rect
            x={plotLeft}
            y={safeTop}
            width={plotRight - plotLeft}
            height={safeBottom - safeTop}
            fill="#dcfce7"
            opacity="0.5"
          />

          {/* Danger threshold line */}
          <line
            x1={plotLeft}
            y1={dangerY}
            x2={plotRight}
            y2={dangerY}
            stroke="#ef4444"
            strokeWidth="0.8"
            strokeDasharray="4 2"
          />
          <text
            x={plotRight + 2}
            y={dangerY + 3}
            fontSize="7"
            fill="#ef4444"
          >
            3.9
          </text>

          {/* Y-axis */}
          <line
            x1={plotLeft}
            y1={plotTop}
            x2={plotLeft}
            y2={plotBottom}
            stroke="#9ca3af"
            strokeWidth="0.8"
          />

          {/* X-axis */}
          <line
            x1={plotLeft}
            y1={plotBottom}
            x2={plotRight}
            y2={plotBottom}
            stroke="#9ca3af"
            strokeWidth="0.8"
          />

          {/* Y-axis ticks */}
          {yTicks.map((val) => {
            const y = scaleY(val);
            if (y < plotTop || y > plotBottom) return null;
            return (
              <g key={val}>
                <line
                  x1={plotLeft - 3}
                  y1={y}
                  x2={plotLeft}
                  y2={y}
                  stroke="#9ca3af"
                  strokeWidth="0.5"
                />
                <text
                  x={plotLeft - 5}
                  y={y + 3}
                  fontSize="7"
                  fill="#6b7280"
                  textAnchor="end"
                >
                  {val}
                </text>
              </g>
            );
          })}

          {/* Grid lines */}
          {yTicks.map((val) => {
            const y = scaleY(val);
            if (y < plotTop || y > plotBottom) return null;
            return (
              <line
                key={`grid-${val}`}
                x1={plotLeft}
                y1={y}
                x2={plotRight}
                y2={y}
                stroke="#e5e7eb"
                strokeWidth="0.3"
              />
            );
          })}

          {/* Data line */}
          {pts.length > 1 && (
            <path
              d={linePath}
              fill="none"
              stroke="#2563eb"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Data points */}
          {pts.map((p, i) => {
            const isLast = i === pts.length - 1;
            const isDanger = p.glucose < SAFE_LOW;
            return (
              <g key={i}>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={isLast ? 5 : 3}
                  fill={isDanger ? "#ef4444" : "#2563eb"}
                  stroke="white"
                  strokeWidth="1.5"
                />
                {/* Value label on each point */}
                <text
                  x={p.x}
                  y={p.y - (isLast ? 8 : 6)}
                  fontSize={isLast ? "8" : "7"}
                  fill={isDanger ? "#ef4444" : "#374151"}
                  textAnchor="middle"
                  fontWeight={isLast ? "bold" : "normal"}
                >
                  {p.glucose}
                </text>
              </g>
            );
          })}

          {/* X-axis label */}
          <text
            x={(plotLeft + plotRight) / 2}
            y={H - 3}
            fontSize="7"
            fill="#9ca3af"
            textAnchor="middle"
          >
            Scenario Steps
          </text>

          {/* Y-axis label */}
          <text
            x="8"
            y={(plotTop + plotBottom) / 2}
            fontSize="7"
            fill="#9ca3af"
            textAnchor="middle"
            transform={`rotate(-90, 8, ${(plotTop + plotBottom) / 2})`}
          >
            mmol/L
          </text>
        </svg>
      )}
    </div>
  );
}
