"use client";

import { useState } from "react";
import Link from "next/link";

const AGENT_ICONS = {
  companion: "💞",
  expert: "🩺",
};

const NAV_ITEMS = [
  { label: "Home", href: "/" },
  { label: "Chat", href: "/chat" },
  { label: "Task", href: "/task" },
  { label: "Garden", href: "/garden" },
  { label: "Setting", href: "/setting" },
  { label: "Soft alert-Beta", href: "/soft-alert" },
  { label: "Hard alert-Beta", href: "/hard-alert" },
];

export default function TopBar({ title = "Chat", agentType, transparent = false }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const icon = agentType ? (AGENT_ICONS[agentType] || "💞") : null;

  return (
    <div className={`flex items-center justify-between px-5 pt-14 pb-3 ${transparent ? "" : "bg-cream"} relative z-40`}>
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold italic">{title}</h1>
        {icon && <span className="text-xl">{icon}</span>}
      </div>

      <button onClick={() => setMenuOpen(!menuOpen)} className="text-2xl p-1">
        ☰
      </button>

      {menuOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
          <div className="absolute right-4 top-24 bg-white rounded-xl shadow-lg z-50 py-2 min-w-[140px]">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="block w-full text-left px-4 py-2 hover:bg-gray-100 text-sm"
                onClick={() => setMenuOpen(false)}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
