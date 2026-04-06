import logging
from typing import Dict, Any

from task_agent.agent.state import AgentState

logger = logging.getLogger(__name__)


async def advisor_node(state: AgentState) -> Dict[str, Any]:
    summary = state["health_summary"]

    bg = summary.get("avg_bg_last_2h")
    deficit = summary.get("calorie_deficit", 0)
    avg_cal_per_min = summary.get("avg_cal_per_min")
    history_count = summary.get("history_session_count", 0)
    recommended_duration = summary.get("recommended_duration_min", 21)
    park_distance = summary.get("selected_park_distance_m", 0)

    # Defaults
    intensity = "moderate"
    snack = None
    confidence = "medium"
    duration_min = recommended_duration
    reasoning_parts = []

    # Rule 1 & 3: BG-based intensity + snack
    if bg is not None and bg < 4.5:
        intensity = "light"
        duration_min = 20
        snack = "15g fast carbs (e.g. banana slices)"
        confidence = "medium"
        reasoning_parts.append(f"BG {bg:.1f} < 4.5: light intensity, 20 min, snack required")
    else:
        # Rule 2: elevated BG
        if bg is not None and bg > 10.0:
            reasoning_parts.append(f"BG {bg:.1f} > 10.0: moderate intensity")

        # Rule 4 & 5: duration from history
        if history_count >= 3 and avg_cal_per_min and avg_cal_per_min > 0:
            duration_min = max(15, min(60, round(deficit / avg_cal_per_min)))
            confidence = "high"
            reasoning_parts.append(f"history_count={history_count}: duration from calorie efficiency = {duration_min} min")
        else:
            duration_min = recommended_duration
            confidence = "low"
            reasoning_parts.append(f"history_count={history_count} < 3: using recommended {duration_min} min")

    # Rule 6: far park (applied after steps 1-5, capped at 60)
    if park_distance > 1500:
        duration_min = min(60, duration_min + 10)
        reasoning_parts.append(f"park distance {park_distance}m > 1500: +10 min")

    advice = {
        "exercise_type": "walking",
        "duration_min": duration_min,
        "intensity": intensity,
        "personalized_tip": None,
        "snack_before_exercise": snack,
        "confidence": confidence,
        "reasoning": "; ".join(reasoning_parts),
    }

    logger.info(f"[Advisor] rule-based advice for user={state.get('user_id')}: {advice}")
    return {"exercise_advice": advice}
