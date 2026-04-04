// frontend/src/lib/users.js

export const TEST_USERS = [
  {
    user_id: "user_001",
    name: "Mdm Chen",
    avatar: "/avatar_1.jpg",
    birth_year: 1958,
    gender: "female",
    height_cm: 155,
    weight_kg: 58.0,
    waist_cm: 80.0,
    language: "English",
  },
  {
    user_id: "user_002",
    name: "Marcus",
    avatar: "/avatar_2.jpg",
    birth_year: 1968,
    gender: "male",
    height_cm: 175,
    weight_kg: 82.0,
    waist_cm: 92.0,
    language: "English",
    onboarding_completed: true,
  },
  {
    user_id: "user_003",
    name: "Auntie Lin",
    avatar: "/avatar_3.jpg",
    birth_year: 1974,
    gender: "female",
    height_cm: 160,
    weight_kg: 74.5,
    waist_cm: 90.0,
    language: "English",
    onboarding_completed: true,
  },
];

export const AVATARS = [
  { id: "avatar_1.jpg", src: "/avatar_1.jpg" },
  { id: "avatar_2.jpg", src: "/avatar_2.jpg" },
  { id: "avatar_3.jpg", src: "/avatar_3.jpg" },
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

export function isOnboardingCompleted(userId) {
  if (typeof window === "undefined") return true;
  const profile = localStorage.getItem(`profile_${userId}`);
  if (!profile) return false;
  try {
    return JSON.parse(profile).onboarding_completed === true;
  } catch {
    return false;
  }
}

export function completeOnboarding(userId, formData) {
  const profile = {
    ...formData,
    user_id: userId,
    onboarding_completed: true,
  };
  localStorage.setItem(`profile_${userId}`, JSON.stringify(profile));
}
