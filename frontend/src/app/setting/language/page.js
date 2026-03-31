"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import TopBar from "../../../components/TopBar";
import { useAuth } from "../../../lib/useAuth";
import { getLanguage, setLanguage } from "../../../lib/users";

const LANGUAGES = [
  { code: "English", label: "English", flag: "\uD83C\uDDEC\uD83C\uDDE7" },
  { code: "Chinese", label: "\u534E\u8BED", flag: "\uD83C\uDDE8\uD83C\uDDF3" },
  { code: "Malay", label: "Bahasa Melayu", flag: "\uD83C\uDDF2\uD83C\uDDFE" },
  { code: "Tamil", label: "\u0BA4\u0BAE\u0BBF\u0BB4\u0BCD", flag: "\uD83C\uDDEE\uD83C\uDDF3" },
];

export default function LanguagePage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [selected, setSelected] = useState(() => getLanguage());

  if (loading || !user) return null;

  const handleSelect = (code) => {
    setSelected(code);
    setLanguage(code);
  };

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title="Language" transparent />

      <div className="px-6 mt-4">
        <p className="text-sm text-gray-500 mb-4">
          Choose your preferred language
        </p>

        <div className="space-y-3">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => handleSelect(lang.code)}
              className={`flex items-center w-full px-4 py-4 rounded-xl transition-all ${
                selected === lang.code
                  ? "bg-[#e8927c]/10 border-2 border-[#e8927c]"
                  : "bg-white border-2 border-transparent"
              }`}
            >
              <span className="text-2xl mr-3">{lang.flag}</span>
              <span className="text-sm font-semibold text-gray-800">{lang.label}</span>
              <span className="flex-1" />
              {selected === lang.code && (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="#e8927c" className="w-5 h-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
              )}
            </button>
          ))}
        </div>

        <p className="text-xs text-gray-400 mt-6 text-center italic">
          Language setting will be applied across the app
        </p>
      </div>
    </div>
  );
}
