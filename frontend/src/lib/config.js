// Centralized API endpoints.
// In production, set NEXT_PUBLIC_* env vars (e.g. on Vercel) to point to your ECS.
// Locally these fall back to localhost for development.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8080";

export const GATEWAY_URL =
  process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8000";

export const TASK_AGENT_API =
  process.env.NEXT_PUBLIC_TASK_AGENT_URL || "http://localhost:8001";
