export const TEST_USERS = [
  { user_id: "user_001", name: "Alice Tan", avatar: "/avatar.jpg" },
  { user_id: "user_002", name: "Bob Lee", avatar: "/avatar3.jpg" },
  { user_id: "user_003", name: "Charlie Wong", avatar: "/avatar1.jpg" },
];

export function loginUser(userId) {
  localStorage.setItem("user_id", userId);
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
  return TEST_USERS.find((u) => u.user_id === userId) || null;
}
