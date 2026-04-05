"""
alert_agent/nodes/communicator.py

Node 3: Generate personalised push notification using LLM and send via NotificationService.
Uses llm_communicator from alert_agent.llm — never instantiates its own LLM.
"""

import json
from datetime import datetime

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.exc import SQLAlchemyError

from alert_agent.llm import get_llm_communicator
from alert_agent.state import AgentState
from alert_db.models import InterventionLog
from alert_db.session import AsyncSessionLocal
from gateway.services.notification import NotificationService

logger = structlog.get_logger(__name__)

COMMUNICATOR_PROMPT = """
You are the user's personal health companion in a diabetes management app.
Write a single mobile push notification based on the clinical analysis provided.

You will receive:
- current_glucose: current blood glucose in mmol/L
- estimated_glucose_drop: how much glucose is expected to drop during exercise (mmol/L)
- projected_glucose: predicted glucose after exercise (mmol/L)
- risk_level: LOW / MEDIUM / HIGH
- intervention_action: SOFT_REMIND / STRONG_ALERT
- reflector_confidence: LOW / MEDIUM / HIGH
- reasoning_summary: clinical reasoning (use as context, do NOT copy verbatim)
- supplement_recommendation: food suggestion with quantity (if any)
- upcoming_activity: exercise details (type, time, duration)
- emotion_summary: user's recent emotional state (if available)

---

## Tone Matrix (MUST follow)

Match your tone to the combination of intervention_action and confidence:

| intervention_action | confidence | Tone & Style |
|---------------------|-----------|--------------|
| SOFT_REMIND | HIGH | Casual, friendly nudge. "Just a heads up..." |
| SOFT_REMIND | MEDIUM | Gentle but include the numbers. "Your blood sugar is X, and it might drop by Y..." |
| SOFT_REMIND | LOW | Honest about uncertainty. "Not 100% sure, but it might be worth having a snack..." |
| STRONG_ALERT | HIGH | Direct and clear, not alarming. "Important — your blood sugar is X..." |
| STRONG_ALERT | MEDIUM | Urgent, acknowledge uncertainty. "Better safe than sorry — please grab a snack..." |
| STRONG_ALERT | LOW | Cautious urgency. "Something looks off — please check and grab a snack just in case." |

## Emotion-Aware Tone Adjustment

If emotion_summary indicates a specific emotional state, adjust your wording accordingly.
This does NOT change the intervention level or clinical content — only the WAY you say it.

| Emotion | Adjustment |
|---------|-----------|
| anxious / stressed | Use calming, reassuring language. Avoid alarming words ("danger", "warning"). Add a phrase like "no need to worry" or "just a small step". |
| sad / low mood | Use warmer, more encouraging tone. Emphasise the positive action they can take. |
| suicidal_ideation | Use gentle, caring tone. Do NOT mention the emotion directly. Add "you're doing great by staying on top of this" or similar affirmation. |
| unknown / null | No adjustment — use default tone from Tone Matrix. |

---

## Writing Rules

1. Always mention the current glucose value
2. If estimated_glucose_drop is available, say something like
   "your blood sugar could drop by about X during your workout"
3. If projected_glucose is available, mention it:
   "that could put you around X by mid-session"
4. If supplement_recommendation is present, weave it naturally —
   do NOT use bullet points or clinical formatting
5. Keep the message under 50 words for SOFT_REMIND, under 60 words for STRONG_ALERT
6. End with one short encouraging phrase (under 8 words)
7. Never use medical jargon — say "blood sugar" not "glucose",
   "on the low side" not "hypoglycemia", no units like "mmol/L"
8. Never mention the user's emotional state explicitly (e.g. do NOT say "I know you're feeling anxious")
"""


async def communicator_node(state: AgentState) -> dict:
    """Generate personalised push notification and send to user."""
    task = state["task"]
    user_id = state["user_id"]

    # Silent logging for NO_ACTION decisions
    if state.get("intervention_action") == "NO_ACTION":
        logger.info("communicator_silent_log", user_id=user_id, decision="NO_ACTION")
        await _log_intervention(user_id, state, message="No notification needed due to safe projections.")
        return {
            "message_to_user": None,
            "notification_sent": False,
        }

    user_prompt = (
        f"current_glucose:           {task.get('current_glucose')}\n"
        f"estimated_glucose_drop:    {state.get('estimated_glucose_drop')}\n"
        f"projected_glucose:         {state.get('projected_glucose')}\n"
        f"risk_level:                {state.get('risk_level')}\n"
        f"intervention_action:       {state.get('intervention_action')}\n"
        f"reflector_confidence:      {state.get('reflector_confidence')}\n"
        f"reasoning_summary:         {state.get('reasoning_summary')}\n"
        f"supplement_recommendation: {state.get('supplement_recommendation')}\n"
        f"upcoming_activity:         {state.get('upcoming_activity')}\n"
        f"emotion_summary:           {state.get('emotion_summary', 'No recent emotion data')}\n"
    )

    messages = [
        SystemMessage(content=COMMUNICATOR_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    try:
        llm = get_llm_communicator()
        response = await llm.ainvoke(messages)
        message = response.content.strip()
    except Exception as e:
        logger.error("communicator_llm_failed", user_id=user_id, error=str(e))
        message = (
            f"Your glucose is at {task.get('current_glucose')} mmol/L. "
            "Please consider having a snack before your next activity. Stay safe!"
        )

    # Send push notification
    await NotificationService.send_push(user_id, message, state)

    # Write to intervention_log
    await _log_intervention(user_id, state, message)

    logger.info("communicator_sent", user_id=user_id, message_length=len(message))

    return {
        "message_to_user": message,
        "notification_sent": True,
    }


async def _log_intervention(
    user_id: str,
    state: AgentState,
    message: str,
) -> None:
    """Write soft trigger intervention to intervention_log."""
    task = state["task"]

    # Build agent_decision JSON from Reflector output
    agent_decision = json.dumps({
        "estimated_glucose_drop": state.get("estimated_glucose_drop"),
        "risk_level": state.get("risk_level"),
        "reasoning_summary": state.get("reasoning_summary"),
        "projected_glucose": state.get("projected_glucose"),
        "intervention_action": state.get("intervention_action"),
        "supplement_recommendation": state.get("supplement_recommendation"),
        "confidence": state.get("reflector_confidence"),
    })

    try:
        async with AsyncSessionLocal() as session:
            record = InterventionLog(
                user_id=user_id,
                triggered_at=datetime.now(),
                trigger_type=task.get("trigger_type"),
                display_label=None,  # soft triggers have no display_label
                agent_decision=agent_decision,
                message_sent=message,
            )
            session.add(record)
            await session.commit()
    except SQLAlchemyError as e:
        logger.error("intervention_log_failed", user_id=user_id, error=str(e))
