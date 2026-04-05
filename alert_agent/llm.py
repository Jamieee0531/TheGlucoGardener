"""
alert_agent/llm.py

Centralised LLM instances for the agent layer.
No other file should instantiate an LLM directly.

Reflector and Communicator use SEA-LION (OpenAI-compatible API).
"""

from langchain_openai import ChatOpenAI

from config import settings

# SEA-LION models
_REASONING_MODEL = "aisingapore/Llama-SEA-LION-v3.5-70B-R"  # Reflector: clinical reasoning
_INSTRUCT_MODEL = "aisingapore/Qwen-SEA-LION-v4-32B-IT"     # Communicator: patient-facing messages


def get_llm_reflector() -> ChatOpenAI:
    """For clinical reasoning: deterministic, conservative output."""
    return ChatOpenAI(
        model=_REASONING_MODEL,
        temperature=0.1,
        max_tokens=2048,
        api_key=settings.sealion_api_key,
        base_url=settings.sealion_base_url,
    )


def get_llm_communicator() -> ChatOpenAI:
    """For message generation: natural, warm tone with slight creative variation."""
    return ChatOpenAI(
        model=_INSTRUCT_MODEL,
        temperature=0.7,
        max_tokens=256,
        api_key=settings.sealion_api_key,
        base_url=settings.sealion_base_url,
    )
