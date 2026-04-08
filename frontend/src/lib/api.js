const API_URL = "http://localhost:8080/chat/message";
const STREAM_URL = "http://localhost:8080/chat/stream";

export async function sendMessage({ userId, sessionId, text, image, audio }) {
  const form = new FormData();
  form.append("user_id", userId);

  if (sessionId) form.append("session_id", sessionId);
  if (text) form.append("text", text);
  if (image) form.append("image", image);
  if (audio) form.append("audio", audio, "recording.wav");

  const res = await fetch(API_URL, { method: "POST", body: form });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}

export async function sendMessageStream({
  userId,
  sessionId,
  text,
  image,
  audio,
  mode,
  onToken,
  onDone,
  onError,
}) {
  const form = new FormData();
  form.append("user_id", userId);

  if (sessionId) form.append("session_id", sessionId);
  if (text) form.append("text", text);
  if (image) form.append("image", image);
  if (audio) form.append("audio", audio, "recording.wav");
  if (mode) form.append("mode", mode);

  try {
    const res = await fetch(STREAM_URL, { method: "POST", body: form });

    if (!res.ok) {
      onError && onError(`API error: ${res.status}`);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep the last (possibly incomplete) line in the buffer
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;
        try {
          const data = JSON.parse(raw);
          if (data.type === "token") {
            onToken && onToken(data.token);
          } else if (data.type === "done") {
            onDone && onDone(data);
          } else if (data.type === "error") {
            onError && onError(data.message);
          }
        } catch {
          // ignore malformed SSE lines
        }
      }
    }
  } catch (err) {
    onError && onError(err.message || "Stream connection failed");
  }
}
