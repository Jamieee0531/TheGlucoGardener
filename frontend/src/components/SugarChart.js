import { useTranslation } from "../lib/i18n";

export default function SugarChart() {
  const { t } = useTranslation();
  // Simple blood sugar line on L-shaped axis
  const points = [
    [40, 75],
    [70, 60],
    [110, 50],
    [150, 55],
    [190, 40],
    [230, 48],
    [260, 35],
  ];

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
        <text x="35" y="108" fontSize="9" fill="#666">7:00am</text>
        <text x="255" y="108" fontSize="9" fill="#666" textAnchor="end">{t("now")}</text>
      </svg>
    </div>
  );
}
