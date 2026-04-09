import { GATEWAY_URL } from "./config";

/**
 * POST /telemetry/cgm — send glucose reading
 * Returns { status, hard_fired, trigger_type }
 */
export async function postCGM(user_id, glucose, recorded_at) {
  const body = {
    user_id,
    glucose,
    recorded_at: recorded_at || new Date().toISOString(),
  };
  const res = await fetch(`${GATEWAY_URL}/telemetry/cgm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Gateway CGM error: ${res.status}`);
  return res.json();
}

/**
 * POST /telemetry/hr — send heart rate + GPS
 * Returns { status }
 */
export async function postHR(user_id, heart_rate, gps_lat, gps_lng, recorded_at) {
  const body = {
    user_id,
    heart_rate,
    gps_lat: gps_lat ?? null,
    gps_lng: gps_lng ?? null,
    recorded_at: recorded_at || new Date().toISOString(),
  };
  const res = await fetch(`${GATEWAY_URL}/telemetry/hr`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Gateway HR error: ${res.status}`);
  return res.json();
}

/**
 * POST /test/reset-today — clear today's data for a user
 */
export async function resetToday(user_id) {
  const res = await fetch(`${GATEWAY_URL}/test/reset-today`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id }),
  });
  if (!res.ok) throw new Error(`Gateway reset error: ${res.status}`);
  return res.json();
}

/**
 * GET /users/{user_id}/intervention-log — fetch intervention records
 */
export async function fetchInterventions(user_id, todayOnly = true) {
  const params = new URLSearchParams({ today_only: todayOnly });
  const res = await fetch(
    `${GATEWAY_URL}/users/${user_id}/intervention-log?${params}`
  );
  if (!res.ok) throw new Error(`Gateway interventions error: ${res.status}`);
  return res.json();
}
