import json
import re
import logging
from typing import Dict, Any

from task_agent.agent.state import AgentState

logger = logging.getLogger(__name__)

def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("Empty response text from LLM")

    text = re.sub(r'^```[a-zA-Z]*\n?', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'```$', '', text.strip(), flags=re.MULTILINE)

    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as jde:
            raise ValueError(f"JSON decode error: {jde}. Raw snippet: {json_str[:100]}")

    raise ValueError(f"No JSON object found in writer output: {text[:200]}")

WRITER_SYSTEM_PROMPT = """You are a warm, friendly health companion writing a mobile push notification
for a diabetic user. You will receive:
- The user's name
- A clinical exercise recommendation (from our advisor system)
- The destination park name and distance
- The output language (users.language_pref)

Writing rules:
1. Write ONLY in the language specified by language_pref.
   Supported: en, zh-CN, zh-TW, ms, id, th.
2. Tone: warm and conversational, like a message from a caring friend.
   Not clinical. Not commanding.
3. Always include: the park name, the recommended duration.
4. If snack_before_exercise is present, weave it in naturally.
   Example: "...maybe grab a small banana before you head out."
5. Based on the user's bg_status and snack suggestion, craft ONE short personalized tip (under 15 words). Examples: "Your glucose is a bit high — a gentle walk will help bring it down." or "Have a small snack before you head out."
6. Keep the entire message under 60 words.
7. End with one short encouraging phrase (under 8 words).

Return ONLY a JSON object with these exact keys:
{
  "title": "<short notification title, under 8 words>",
  "body":  "<the full message>",
  "cta":   "I have arrived"
}

No markdown. No explanation. Only valid JSON."""

async def writer_node(state: AgentState) -> Dict[str, Any]:
    from task_agent.agent.llm import llm_writer
    import time as _time
    _t0 = _time.time()
    print(f"[{_time.strftime('%H:%M:%S')}] [Writer] ENTER user={state.get('user_id')}")

    advice  = state["exercise_advice"]
    summary = state["health_summary"]

    user_prompt = f"""User name:       {summary["user_name"]}
Language:        {summary["language_pref"]}
Park:            {summary["selected_park_name"]} ({summary["selected_park_distance_m"]}m away)
Duration:        {advice["duration_min"]} minutes
Intensity:       {advice["intensity"]}
BG status:       {summary["bg_status"]}
Snack needed:    {advice["snack_before_exercise"] or "none"}"""

    try:
        response = await llm_writer.acomplete(
            system=WRITER_SYSTEM_PROMPT,
            user=user_prompt,
        )
        task_content = _extract_json(response.text)
        assert "title" in task_content and "body" in task_content
        print(f"[{_time.strftime('%H:%M:%S')}] [Writer] OK elapsed={_time.time()-_t0:.1f}s")
        return {"task_content": task_content}

    except Exception as e:
        err_reason = str(e)
        logger.error(f"writer_node error: {err_reason}")
        print(f"[{_time.strftime('%H:%M:%S')}] [Writer] FALLBACK reason={err_reason[:80]}")
        snack_note = f" Have {advice['snack_before_exercise']} before you go." if advice.get("snack_before_exercise") else ""
        return {"task_content": {
            "title": f"Time for a walk, {summary['user_name']}!",
            "body":  (f"Head to {summary['selected_park_name']} for a "
                      f"{advice['duration_min']}-minute {advice['intensity']} walk.{snack_note}"),
            "cta":   "I have arrived",
            "_fallback_reason": err_reason[:120],
        }}
