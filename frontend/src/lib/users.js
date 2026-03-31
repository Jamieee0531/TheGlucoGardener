// frontend/src/lib/users.js

export const TEST_USERS = [
  {
    user_id: "user_001",
    name: "Alice Tan",
    avatar: "/avatar.jpg",
    birth_year: 1975,
    gender: "female",
    height_cm: 158,
    weight_kg: 62.5,
    waist_cm: 82.0,
    language: "English",
  },
  {
    user_id: "user_002",
    name: "Bob Lee",
    avatar: "/avatar3.jpg",
    birth_year: 1968,
    gender: "male",
    height_cm: 172,
    weight_kg: 78.0,
    waist_cm: 94.5,
    language: "Chinese",
  },
  {
    user_id: "user_003",
    name: "Charlie Wong",
    avatar: "/avatar1.jpg",
    birth_year: 1980,
    gender: "male",
    height_cm: 165,
    weight_kg: 70.0,
    waist_cm: 88.0,
    language: "English",
  },
];

export const AVATARS = [
  { id: "avatar.jpg", src: "/avatar.jpg" },
  { id: "avatar1.jpg", src: "/avatar1.jpg" },
  { id: "avatar3.jpg", src: "/avatar3.jpg" },
];

export function loginUser(userId) {
  localStorage.setItem("user_id", userId);
  // Initialize profile from TEST_USERS on first login
  const existing = localStorage.getItem(`profile_${userId}`);
  if (!existing) {
    const user = TEST_USERS.find((u) => u.user_id === userId);
    if (user) {
      localStorage.setItem(`profile_${userId}`, JSON.stringify(user));
    }
  }
}

export function logoutUser() {
  localStorage.removeItem("user_id");
}

export function getCurrentUserId() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("user_id");
}

export function getCurrentUser() {
  const userId = getCurrentUserId();
  if (!userId) return null;
  // Try localStorage profile first (may have been edited), fall back to TEST_USERS
  const stored = localStorage.getItem(`profile_${userId}`);
  if (stored) {
    try { return JSON.parse(stored); } catch {}
  }
  return TEST_USERS.find((u) => u.user_id === userId) || null;
}

export function saveProfile(userId, profile) {
  localStorage.setItem(`profile_${userId}`, JSON.stringify(profile));
}

export function getLanguage() {
  if (typeof window === "undefined") return "English";
  return localStorage.getItem("app_language") || "English";
}

export function setLanguage(lang) {
  localStorage.setItem("app_language", lang);
}
