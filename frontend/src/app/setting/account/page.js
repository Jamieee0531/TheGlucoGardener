"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import TopBar from "../../../components/TopBar";
import { useAuth } from "../../../lib/useAuth";
import { getCurrentUserId, saveProfile, AVATARS } from "../../../lib/users";
import { useTranslation } from "../../../lib/i18n";

export default function AccountPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  const [form, setForm] = useState(null);
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);
  const [saved, setSaved] = useState(false);
  const [exercises, setExercises] = useState([]);
  const [places, setPlaces] = useState([]);
  const [contacts, setContacts] = useState([]);

  useEffect(() => {
    if (user) {
      setForm({ ...user });
      // Load lists from localStorage
      const uid = user.user_id;
      try { setExercises(JSON.parse(localStorage.getItem(`exercises_${uid}`)) || []); } catch {}
      try { setPlaces(JSON.parse(localStorage.getItem(`places_${uid}`)) || []); } catch {}
      try { setContacts(JSON.parse(localStorage.getItem(`contacts_${uid}`)) || []); } catch {}
    }
  }, [user]);

  if (loading || !user || !form) return null;

  const bmi = form.height_cm > 0
    ? (form.weight_kg / ((form.height_cm / 100) ** 2)).toFixed(1)
    : "—";

  const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
  const ACTIVITY_TYPES = ["resistance_training", "cardio", "hiit"];
  const PLACE_TYPES = ["place_home", "place_gym", "place_office"];
  const RELATIONSHIPS = ["rel_family", "rel_friend", "rel_doctor"];
  const NOTIFY_OPTIONS = ["hard_low_glucose", "hard_high_hr", "data_gap"];

  const handleSave = () => {
    const userId = getCurrentUserId();
    saveProfile(userId, form);
    localStorage.setItem(`exercises_${userId}`, JSON.stringify(exercises));
    localStorage.setItem(`places_${userId}`, JSON.stringify(places));
    localStorage.setItem(`contacts_${userId}`, JSON.stringify(contacts));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const addExercise = () => {
    setExercises([...exercises, { day_of_week: 0, start_time: "14:30", end_time: "16:00", activity_type: "cardio" }]);
  };

  const updateExercise = (i, field, value) => {
    const updated = exercises.map((e, idx) => idx === i ? { ...e, [field]: value } : e);
    setExercises(updated);
  };

  const removeExercise = (i) => {
    setExercises(exercises.filter((_, idx) => idx !== i));
  };

  const addPlace = () => {
    setPlaces([...places, { place_name: "", place_type: "home", gps_lat: "", gps_lng: "" }]);
  };

  const updatePlace = (i, field, value) => {
    const updated = places.map((p, idx) => idx === i ? { ...p, [field]: value } : p);
    setPlaces(updated);
  };

  const removePlace = (i) => {
    setPlaces(places.filter((_, idx) => idx !== i));
  };

  const addContact = () => {
    setContacts([...contacts, { contact_name: "", phone_number: "", relationship: "family", notify_on: ["hard_low_glucose"] }]);
  };

  const updateContact = (i, field, value) => {
    const updated = contacts.map((c, idx) => idx === i ? { ...c, [field]: value } : c);
    setContacts(updated);
  };

  const toggleNotify = (i, option) => {
    const c = contacts[i];
    const current = c.notify_on || [];
    const next = current.includes(option)
      ? current.filter((o) => o !== option)
      : [...current, option];
    updateContact(i, "notify_on", next);
  };

  const removeContact = (i) => {
    setContacts(contacts.filter((_, idx) => idx !== i));
  };

  const updateField = (field, value) => {
    setForm({ ...form, [field]: value });
  };

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar title={t("account")} transparent />

      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {/* Avatar */}
        <div className="flex flex-col items-center mt-2 mb-6">
          <button
            onClick={() => setShowAvatarPicker(true)}
            className="relative group"
          >
            <div className="w-[90px] h-[90px] rounded-full overflow-hidden ring-3 ring-[#e8927c]/30">
              <img src={form.avatar} alt="Avatar" className="w-full h-full object-cover" />
            </div>
            <div className="absolute inset-0 rounded-full bg-black/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="text-white text-xs font-semibold">{t("change")}</span>
            </div>
          </button>
          <p className="text-xs text-gray-400 mt-1.5">{t("tap_change_avatar")}</p>
        </div>

        {/* Avatar picker modal */}
        {showAvatarPicker && (
          <>
            <div className="fixed inset-0 bg-black/30 z-40" onClick={() => setShowAvatarPicker(false)} />
            <div className="fixed top-1/3 left-8 right-8 bg-white rounded-2xl z-50 p-5 shadow-xl">
              <h4 className="text-base font-bold mb-4 text-gray-800">{t("choose_avatar")}</h4>
              <div className="flex justify-center gap-4">
                {AVATARS.map((av) => (
                  <button
                    key={av.id}
                    onClick={() => {
                      updateField("avatar", av.src);
                      setShowAvatarPicker(false);
                    }}
                    className={`w-[70px] h-[70px] rounded-full overflow-hidden ring-3 transition-all ${
                      form.avatar === av.src ? "ring-[#e8927c] scale-110" : "ring-transparent"
                    }`}
                  >
                    <img src={av.src} alt="Avatar option" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Personal Info */}
        <div className="mb-5">
          <h3 className="text-sm font-bold text-[#e8927c] uppercase tracking-wide mb-3">
            {t("personal_info")}
          </h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500">{t("name")}</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => updateField("name", e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">{t("birth_year")}</label>
              <input
                type="number"
                value={form.birth_year}
                onChange={(e) => updateField("birth_year", parseInt(e.target.value) || "")}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">{t("gender")}</label>
              <select
                value={form.gender}
                onChange={(e) => updateField("gender", e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              >
                <option value="male">{t("male")}</option>
                <option value="female">{t("female")}</option>
                <option value="other">{t("other")}</option>
              </select>
            </div>
          </div>
        </div>

        {/* Health Info */}
        <div className="mb-5">
          <h3 className="text-sm font-bold text-[#e8927c] uppercase tracking-wide mb-3">
            {t("health_info")}
          </h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500">{t("height_cm")}</label>
              <input
                type="number"
                value={form.height_cm}
                onChange={(e) => updateField("height_cm", parseFloat(e.target.value) || "")}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">{t("weight_kg")}</label>
              <input
                type="number"
                value={form.weight_kg}
                onChange={(e) => updateField("weight_kg", parseFloat(e.target.value) || "")}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">{t("waist_cm")}</label>
              <input
                type="number"
                value={form.waist_cm}
                onChange={(e) => updateField("waist_cm", parseFloat(e.target.value) || "")}
                className="w-full mt-1 px-3 py-2 bg-white rounded-xl text-sm border border-gray-200 focus:border-[#e8927c] focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">{t("bmi_auto")}</label>
              <div className="w-full mt-1 px-3 py-2 bg-gray-100 rounded-xl text-sm text-gray-600">
                {bmi}
              </div>
            </div>
          </div>
        </div>

        {/* Weekly Exercise Plan */}
        <div className="mb-5">
          <h3 className="text-sm font-bold text-[#e8927c] uppercase tracking-wide mb-3">
            {t("weekly_exercise")}
          </h3>
          {exercises.map((ex, i) => (
            <div key={i} className="bg-white rounded-xl p-3 mb-2 border border-gray-200 space-y-2">
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-xs text-gray-500">{t("day_of_week")}</label>
                  <select
                    value={ex.day_of_week}
                    onChange={(e) => updateExercise(i, "day_of_week", parseInt(e.target.value))}
                    className="w-full mt-1 px-2 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 focus:border-[#e8927c] focus:outline-none"
                  >
                    {DAYS.map((d, idx) => (
                      <option key={d} value={idx}>{t(d)}</option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="text-xs text-gray-500">{t("activity_type")}</label>
                  <select
                    value={ex.activity_type}
                    onChange={(e) => updateExercise(i, "activity_type", e.target.value)}
                    className="w-full mt-1 px-2 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 focus:border-[#e8927c] focus:outline-none"
                  >
                    {ACTIVITY_TYPES.map((a) => (
                      <option key={a} value={a}>{t(a)}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex gap-2 items-end">
                <div className="flex-1">
                  <label className="text-xs text-gray-500">{t("start_time")}</label>
                  <input
                    type="time"
                    value={ex.start_time}
                    onChange={(e) => updateExercise(i, "start_time", e.target.value)}
                    className="w-full mt-1 px-2 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 focus:border-[#e8927c] focus:outline-none"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs text-gray-500">{t("end_time")}</label>
                  <input
                    type="time"
                    value={ex.end_time}
                    onChange={(e) => updateExercise(i, "end_time", e.target.value)}
                    className="w-full mt-1 px-2 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 focus:border-[#e8927c] focus:outline-none"
                  />
                </div>
                <button
                  onClick={() => removeExercise(i)}
                  className="text-xs text-red-400 hover:text-red-600 pb-1.5"
                >
                  {t("remove")}
                </button>
              </div>
            </div>
          ))}
          <button
            onClick={addExercise}
            className="text-sm text-[#e8927c] font-semibold hover:underline"
          >
            {t("add_schedule")}
          </button>
        </div>

        {/* Known Places */}
        <div className="mb-5">
          <h3 className="text-sm font-bold text-[#e8927c] uppercase tracking-wide mb-3">
            {t("known_places")}
          </h3>
          {places.map((pl, i) => (
            <div key={i} className="bg-white rounded-xl p-3 mb-2 border border-gray-200 space-y-2">
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-xs text-gray-500">{t("place_name")}</label>
                  <input
                    type="text"
                    value={pl.place_name}
                    onChange={(e) => updatePlace(i, "place_name", e.target.value)}
                    placeholder="e.g. Bishan Park"
                    className="w-full mt-1 px-2 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 focus:border-[#e8927c] focus:outline-none"
                  />
                </div>
                <div className="w-[100px]">
                  <label className="text-xs text-gray-500">{t("place_type")}</label>
                  <select
                    value={pl.place_type}
                    onChange={(e) => updatePlace(i, "place_type", e.target.value)}
                    className="w-full mt-1 px-2 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 focus:border-[#e8927c] focus:outline-none"
                  >
                    {PLACE_TYPES.map((p) => (
                      <option key={p} value={p.replace("place_", "")}>{t(p)}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex gap-2 items-end">
                <div className="flex-1">
                  <label className="text-xs text-gray-500">{t("gps_lat")}</label>
                  <input
                    type="number"
                    step="0.0000001"
                    value={pl.gps_lat}
                    onChange={(e) => updatePlace(i, "gps_lat", e.target.value)}
                    placeholder="e.g. 1.3521"
                    className="w-full mt-1 px-2 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 focus:border-[#e8927c] focus:outline-none"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs text-gray-500">{t("gps_lng")}</label>
                  <input
                    type="number"
                    step="0.0000001"
                    value={pl.gps_lng}
                    onChange={(e) => updatePlace(i, "gps_lng", e.target.value)}
                    placeholder="e.g. 103.8198"
                    className="w-full mt-1 px-2 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 focus:border-[#e8927c] focus:outline-none"
                  />
                </div>
                <button
                  onClick={() => removePlace(i)}
                  className="text-xs text-red-400 hover:text-red-600 pb-1.5"
                >
                  {t("remove")}
                </button>
              </div>
            </div>
          ))}
          <button
            onClick={addPlace}
            className="text-sm text-[#e8927c] font-semibold hover:underline"
          >
            {t("add_place")}
          </button>
        </div>

        {/* Emergency Contacts */}
        <div className="mb-5">
          <h3 className="text-sm font-bold text-[#e8927c] uppercase tracking-wide mb-3">
            {t("emergency_contacts")}
          </h3>
          {contacts.map((ct, i) => (
            <div key={i} className="bg-white rounded-xl p-3 mb-2 border border-gray-200 space-y-2">
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-xs text-gray-500">{t("contact_name")}</label>
                  <input
                    type="text"
                    value={ct.contact_name}
                    onChange={(e) => updateContact(i, "contact_name", e.target.value)}
                    placeholder="e.g. Linda Chen"
                    className="w-full mt-1 px-2 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 focus:border-[#e8927c] focus:outline-none"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs text-gray-500">{t("phone_number")}</label>
                  <input
                    type="tel"
                    value={ct.phone_number}
                    onChange={(e) => updateContact(i, "phone_number", e.target.value)}
                    placeholder="e.g. +65 9123 4567"
                    className="w-full mt-1 px-2 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 focus:border-[#e8927c] focus:outline-none"
                  />
                </div>
              </div>
              <div className="flex gap-2 items-end">
                <div className="flex-1">
                  <label className="text-xs text-gray-500">{t("relationship")}</label>
                  <select
                    value={ct.relationship}
                    onChange={(e) => updateContact(i, "relationship", e.target.value)}
                    className="w-full mt-1 px-2 py-1.5 bg-gray-50 rounded-lg text-xs border border-gray-200 focus:border-[#e8927c] focus:outline-none"
                  >
                    {RELATIONSHIPS.map((r) => (
                      <option key={r} value={r.replace("rel_", "")}>{t(r)}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={() => removeContact(i)}
                  className="text-xs text-red-400 hover:text-red-600 pb-1.5"
                >
                  {t("remove")}
                </button>
              </div>
              <div>
                <label className="text-xs text-gray-500">{t("notify_on")}</label>
                <div className="flex gap-2 mt-1 flex-wrap">
                  {NOTIFY_OPTIONS.map((opt) => (
                    <button
                      key={opt}
                      onClick={() => toggleNotify(i, opt)}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                        (ct.notify_on || []).includes(opt)
                          ? "bg-[#e8927c] text-white"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {t(opt)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ))}
          <button
            onClick={addContact}
            className="text-sm text-[#e8927c] font-semibold hover:underline"
          >
            {t("add_contact")}
          </button>
        </div>

        {/* Save button */}
        <button
          onClick={handleSave}
          className="w-full py-3 rounded-full text-white font-semibold text-sm transition-all"
          style={{ backgroundColor: saved ? "#7cb342" : "#e8927c" }}
        >
          {saved ? t("saved") : t("save_changes")}
        </button>
      </div>
    </div>
  );
}
