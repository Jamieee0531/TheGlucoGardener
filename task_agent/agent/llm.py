from task_agent.agent.sea_lion_client import SeaLionClient
from task_agent.config import settings

# Copywriting: higher temperature for natural, warm tone
llm_writer = SeaLionClient(
    temperature=0.6,
    max_tokens=256,
    api_key=settings.sealion_api_key,
)
