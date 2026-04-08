"""
alert_agent/nodes/reflector.py

Node 2: LLM-based clinical reasoning.
Uses llm_reflector from alert_agent.llm — never instantiates its own LLM.

Responsibilities:
- Assess risk level based on glucose data, trends, and upcoming activity
- Determine intervention action (NO_ACTION / SOFT_REMIND / STRONG_ALERT)
- Select appropriate food supplement from the localised food list
- Does NOT compute glucose drop (Investigator does that)
- Does NOT consider emotion context (Communicator handles that)
"""

import json

import numpy as np
import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from alert_agent.llm import get_llm_reflector
from alert_agent.state import AgentState

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """
# Identity
You are a clinical decision-support AI embedded in a real-time diabetes management system.
Your role is preventive risk assessment, NOT medical diagnosis.
You reason like an endocrinologist reviewing a patient's data before a consultation.
You are conservative: when in doubt, prefer intervention over silence.

---

# Medical Knowledge Base

## Blood Glucose Classification (mmol/L)
- Normal fasting:         4.0  – 6.0
- Pre-exercise safe zone: 5.6  – 10.0  (high-intensity)
- Pre-exercise safe zone: 5.0  – 10.0  (moderate-intensity)
- Level 1 hypoglycemia:   3.0  – 3.9   → treat with 15g fast carbs, recheck in 15 min
- Level 2 hypoglycemia:   < 3.0        → urgent intervention required
- Level 3 hypoglycemia:   < 2.8 + symptoms → emergency, call for help immediately

## Exercise Impact on Blood Glucose
- Resistance training:    drops 1.5 – 3.0 mmol/L per session (high variance)
- Moderate cardio:        drops 1.0 – 2.5 mmol/L per 45 min
- High-intensity cardio:  drops 2.0 – 4.0 mmol/L per session
- Post-exercise window:   glucose may continue dropping for 2–4 hours after exercise ends
- Rule: if pre-exercise glucose < 5.6, supplement with 15–30g slow-release carbs before starting

## Glucose Trend Interpretation
- Slope > +0.11 mmol/L/min: rising rapidly → elevated hyperglycemia risk
- Slope -0.11 to +0.11:     stable
- Slope < -0.11 mmol/L/min: falling rapidly → elevated hypoglycemia risk
- Both rapid rise and rapid fall are soft-trigger conditions
- A glucose of 5.5 falling at -0.15/min is riskier than a glucose of 4.5 that is stable

## Heart Rate Context
- Resting HR spike without exercise context: possible stress, illness, or arrhythmia
- Max HR = 220 - age; above 85% during non-exercise context → flag for review

---

# Reasoning Framework

When you receive patient data, reason through the following steps IN ORDER:

Step 1 — Establish baseline risk
  Is the current absolute glucose value in a safe zone?
  Apply the classification table above.

Step 2 — Apply trend adjustment
  Is the glucose falling? At what slope?
  A falling trend downgrades the safety of the current value.
  Example: glucose = 5.2, slope = -0.12 → treat as if glucose were ~4.8.

Step 2.5 — Consider food intake
  When was the last meal? If > 3h ago, glucose buffer is likely depleted — lower the safe threshold.
  If total calories today are low (< 800 kcal by afternoon), the user has limited glycogen reserves — higher hypo risk.
  A recent high-GI meal (< 1h ago) may temporarily mask falling glucose — still flag if trend is down.
  If last meal contained low-GI foods, glucose release is slower and more sustained — slightly less urgent.
  Include food intake observations in reasoning_summary when relevant.

Step 3 — Project forward
  The estimated_glucose_drop and projected_glucose are pre-computed by the Investigator.
  Your job is to ASSESS their risk implications, not recalculate.
  Do NOT modify, multiply, or recompute any numerical values.

  If user is already at the gym (is_at_home = false, nearby gym < 200m):
    exercise may have already started → shorten intervention window, escalate urgency.
  If user is at home with exercise predicted in 60 min:
    full intervention window available, prefer soft reminder.

Step 4 — Determine intervention level
  NO_ACTION:    projected risk is LOW and trend is stable
  SOFT_REMIND:  projected risk is MEDIUM, user has time to act (> 30 min)
  STRONG_ALERT: projected risk is HIGH, or user has < 15 min before exercise

---

# Decision Rules (hard overrides, apply before LLM reasoning)

These rules are encoded in the gateway layer but you must remain consistent with them:
- glucose < 3.9 → this should have already been caught by hard trigger; if you see this, output STRONG_ALERT regardless
- No upcoming activity AND glucose stable AND no falling trend → NO_ACTION
- Historical sample_count < 3 for the predicted activity: increase uncertainty, prefer MEDIUM over LOW

When interpreting the 7-day glucose profile:
- If coverage_percent < 50%: treat profile stats as low-confidence; do not use them to downgrade risk
- If cv_percent >= 36%: this user has high glucose variability — apply more conservative thresholds
- If avg_delta_vs_prior_7d > +0.5: worsening trend — prefer higher intervention level when on boundary
- If avg_delta_vs_prior_7d < -0.5: improving trend — may slightly reduce urgency for borderline cases
- If daily nadir_glucose is close to 3.9 (< 4.5): this user has a pattern of running low today

---

# Supplement Recommendation Rules

- null if intervention_action is NO_ACTION
- Always specify quantity in grams or familiar units
- MUST choose from the food options listed below — do NOT invent items

[Scene A] intervention window > 30 min AND projected drop < 1.0:
  Pick ONE: wholemeal bread + peanut butter (~20g) | 2 cream crackers + cheese (~15g) | soy milk + crackers (~18g)

[Scene B] intervention window > 30 min AND projected drop 1.0–2.0:
  Pick ONE: 1 small banana (~23g) | congee + boiled egg (~25g) | low-sugar granola bar (~20g)

[Scene C] intervention window 15–30 min AND projected drop 1.0–2.0:
  Pick ONE: 150ml fruit juice (~15g) | 1 tbsp honey in water (~17g) | half can chrysanthemum tea (~18g)

[Scene D] intervention window < 15 min AND projected drop > 1.5:
  Pick ONE: 3 glucose tablets (15g) | 1 honey packet (15g) | 150ml regular soft drink (~16g)

[Scene E] projected drop > 2.0 (any window):
  Pick ONE combo: glucose tablets + bread (~30g) | juice + crackers + cheese (~28g) | banana + nuts (~28g)

[Scene F] current glucose < 3.9:
  Pick ONE + instruct "recheck in 15 minutes": glucose tablets (15g) | 150ml juice (~15g) | 1 tbsp honey (15g)

Preference adjustments:
- age > 65: prefer liquids and soft foods
- is_at_home = false: only portable items (tablets, juice, honey packet, granola bar)
- is_at_home = true: may include bread, congee, crackers
- daily nadir < 3.9 today: upgrade one scene level

---

# Output Format

CRITICAL: Your ENTIRE response must be a single JSON object. Do NOT include any reasoning,
explanation, or thinking before or after the JSON. Start your response with "{" and end with "}".

{
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "reasoning_summary": "<2–4 sentences summarising the key facts and logic chain>",
  "intervention_action": "NO_ACTION" | "SOFT_REMIND" | "STRONG_ALERT",
  "supplement_recommendation": "<specific food from the list above with quantity> | null",
  "confidence": "LOW" | "MEDIUM" | "HIGH"
}

Put ALL your reasoning inside the "reasoning_summary" field. Do NOT think out loud before the JSON.
"""

USER_PROMPT_TEMPLATE = """
## Current Patient Snapshot

- User ID:              {user_id}
- Current time:         {trigger_at}
- Current glucose:      {current_glucose} mmol/L
- Current heart rate:   {current_hr} bpm
- Current location:     {location_context}
- Trigger type:         {trigger_type}

## User Profile
- Age: {age} | BMI: {bmi} | Gender: {gender} | Waist: {waist_cm} cm

## Glucose Trend (past 20 min, from CGM)
{glucose_trend_summary}

## Today's Glucose Snapshot
- Average: {daily_avg} mmol/L | Peak: {daily_peak} | Nadir: {daily_nadir} | SD: {daily_sd}
- Time in Range [3.9-10.0]: {tir_today}% | Below: {tbr_today}% | Above: {tar_today}%
- Readings today: {daily_data_points} {realtime_flag}

## 7-Day Glucose Profile  ({weekly_window_start} -> {weekly_profile_date})
- 7-day mean: {weekly_avg} mmol/L | CV: {cv_percent}% ({cv_interpretation})
- Time in Range: {weekly_tir}% | Below: {weekly_tbr}% | Above: {weekly_tar}%
- Trend vs prior 7 days: {avg_delta_vs_prior_7d} mmol/L ({trend_direction})
- Profile data coverage: {coverage_percent}% {coverage_flag}

## Upcoming Activity (from weekly pattern)
- Type: {activity_type} | Start: {start_time} | Duration: {duration_min} min

## Exercise History (last matching sessions for drop calculation)
{exercise_history}
- Session count available: {session_count}

## Today's Food Intake
{food_intake_summary}
- Last meal: {last_meal_hours_ago} hours ago
- Total calories today: {total_kcal_today} kcal

## Today's Calories Burned So Far
{today_calories_burned} kcal

## Pre-Computed Glucose Projection (from Investigator — DO NOT recalculate)
- Estimated glucose drop: {estimated_glucose_drop} mmol/L (mean of last {session_count} sessions)
- Projected glucose: {projected_glucose} mmol/L
- IMPORTANT: Use these exact values for your risk assessment. Do NOT recompute.

## Additional Notes
{context_notes}
"""


async def reflector_node(state: AgentState) -> dict:
    """LLM clinical reasoning node. Populates risk assessment fields."""
    task = state["task"]
    profile = state.get("user_profile") or {}
    upcoming = state.get("upcoming_activity") or {}
    daily = state.get("glucose_daily_stats") or {}
    weekly = state.get("glucose_weekly_profile") or {}
    history = state.get("glucose_history_24h") or []
    exercise_hist = state.get("exercise_history") or []

    # Compute glucose trend summary from recent readings
    glucose_trend_summary = _compute_trend_summary(history)

    # Derive helper strings
    realtime_flag = "(real-time estimate)" if daily.get("is_realtime") else ""
    cv = weekly.get("cv_percent", 0) or 0
    cv_interpretation = "stable" if cv < 36 else "high variability"
    delta = weekly.get("avg_delta_vs_prior_7d", 0) or 0
    trend_direction = "improving" if delta < 0 else ("worsening" if delta > 0 else "stable")
    coverage = weekly.get("coverage_percent", 0) or 0
    coverage_flag = "(low confidence — downweight this data)" if coverage < 50 else ""

    # Format exercise history
    ex_history_str = "\n".join(
        f"  - Session {i+1}: started {s.get('started_at')}, glucose_drop={s.get('glucose_drop')} mmol/L"
        for i, s in enumerate(exercise_hist)
    ) or "  No matching exercise history available"

    # Format food intake
    food = state.get("food_intake_today") or {}
    meals = food.get("meals_today", [])
    food_intake_str = "\n".join(
        f"  - {m.get('time')} {m.get('meal_type','')}: {m.get('food_name','')} "
        f"({m.get('kcal', 'N/A')} kcal, GI: {m.get('gi_level', 'N/A')})"
        for m in meals
    ) or "  No meals recorded today"

    last_meal_hours = food.get("last_meal_hours_ago")
    last_meal_str = f"{last_meal_hours}" if last_meal_hours is not None else "N/A (no meals today)"
    total_kcal_today = food.get("total_kcal", 0)

    # Get pre-computed values from Investigator
    pre_drop = state.get("estimated_glucose_drop")
    pre_projected = state.get("projected_glucose")

    # Build user prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        user_id=task.get("user_id", ""),
        trigger_at=task.get("trigger_at", ""),
        current_glucose=task.get("current_glucose", "N/A"),
        current_hr=task.get("current_hr", "N/A"),
        location_context=state.get("location_context", "unknown"),
        trigger_type=task.get("trigger_type", ""),
        age=profile.get("age", "N/A"),
        bmi=profile.get("bmi", "N/A"),
        gender=profile.get("gender", "N/A"),
        waist_cm=profile.get("waist_cm", "N/A"),
        glucose_trend_summary=glucose_trend_summary,
        daily_avg=daily.get("avg_glucose", "N/A"),
        daily_peak=daily.get("peak_glucose", "N/A"),
        daily_nadir=daily.get("nadir_glucose", "N/A"),
        daily_sd=daily.get("glucose_sd", "N/A"),
        tir_today=daily.get("tir_percent", "N/A"),
        tbr_today=daily.get("tbr_percent", "N/A"),
        tar_today=daily.get("tar_percent", "N/A"),
        daily_data_points=daily.get("data_points", "N/A"),
        realtime_flag=realtime_flag,
        weekly_window_start=weekly.get("window_start", "N/A"),
        weekly_profile_date=weekly.get("profile_date", "N/A"),
        weekly_avg=weekly.get("avg_glucose", "N/A"),
        cv_percent=cv,
        cv_interpretation=cv_interpretation,
        weekly_tir=weekly.get("tir_percent", "N/A"),
        weekly_tbr=weekly.get("tbr_percent", "N/A"),
        weekly_tar=weekly.get("tar_percent", "N/A"),
        avg_delta_vs_prior_7d=delta,
        trend_direction=trend_direction,
        coverage_percent=coverage,
        coverage_flag=coverage_flag,
        activity_type=upcoming.get("type", "None"),
        start_time=upcoming.get("start_time", "N/A"),
        duration_min=upcoming.get("duration_min", "N/A"),
        exercise_history=ex_history_str,
        session_count=len(exercise_hist),
        food_intake_summary=food_intake_str,
        last_meal_hours_ago=last_meal_str,
        total_kcal_today=total_kcal_today,
        today_calories_burned=state.get("today_calories_burned", 0),
        estimated_glucose_drop=pre_drop if pre_drop is not None else "N/A",
        projected_glucose=pre_projected if pre_projected is not None else "N/A",
        context_notes=task.get("context_notes", ""),
    )

    # Call LLM
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    try:
        llm = get_llm_reflector()
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        logger.info("llm_reflector_raw", content=content)

        # Robust JSON extraction: look for outer braces
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
             content = content[start:end+1]

        result = json.loads(content)

        return {
            "risk_level": result.get("risk_level", "MEDIUM"),
            "reasoning_summary": result.get("reasoning_summary", ""),
            "intervention_action": result.get("intervention_action", "SOFT_REMIND"),
            "supplement_recommendation": result.get("supplement_recommendation"),
            "reflector_confidence": result.get("confidence", "MEDIUM"),
        }
    except (json.JSONDecodeError, Exception) as e:
        logger.error("llm_parse_failed", error=str(e), fallback="rule_based")
        return _rule_based_fallback(task, upcoming)


def _compute_trend_summary(history: list) -> str:
    """Compute glucose slope from recent CGM readings and return a summary string."""
    if not history or len(history) < 2:
        return "Insufficient data for trend analysis"

    try:
        from datetime import datetime

        base_time = datetime.fromisoformat(history[0]["time"])
        timestamps = [
            (datetime.fromisoformat(r["time"]) - base_time).total_seconds() / 60.0
            for r in history
        ]
        values = [r["glucose"] for r in history]

        slope = float(np.polyfit(timestamps, values, 1)[0])
        direction = "falling" if slope < -0.05 else ("rising" if slope > 0.05 else "stable")
        return f"Slope: {slope:.4f} mmol/L/min ({direction}), based on {len(history)} readings"
    except (KeyError, ValueError, TypeError):
        return "Trend calculation failed — data format issue"


def _rule_based_fallback(task: dict, upcoming: dict | None) -> dict:
    """Fallback when LLM is unavailable or response is unparseable."""
    glucose = task.get("current_glucose", 5.0)

    if glucose <= 5.0 and upcoming:
        return {
            "risk_level": "MEDIUM",
            "reasoning_summary": "LLM unavailable, rule-based fallback applied. "
            "Glucose below 4.5 with upcoming activity — recommending soft reminder.",
            "intervention_action": "SOFT_REMIND",
            "supplement_recommendation": "3 glucose tablets (15g)",
            "reflector_confidence": "LOW",
        }

    return {
        "risk_level": "LOW",
        "reasoning_summary": "LLM unavailable, rule-based fallback applied. No immediate risk detected.",
        "intervention_action": "NO_ACTION",
        "supplement_recommendation": None,
        "reflector_confidence": "LOW",
    }
