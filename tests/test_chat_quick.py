"""
tests/test_chat_quick.py
Minimal conversation test — runs one graph turn to verify SEA-LION connectivity and memory injection.

How to run:
    python -m tests.test_chat_quick
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
os.environ["DEMO_MODE"] = "false"

USER_ID     = "user_001"
TEST_INPUT  = "Good morning! How should I plan my breakfast today?"

from chatbot.graph.builder import app
from chatbot.utils.memory import get_user_profile

config = {"configurable": {"thread_id": f"quick_{int(time.time())}"}}
state  = {
    "user_id":      USER_ID,
    "user_input":   TEST_INPUT,
    "input_mode":   "text",
    "chat_mode":    "personal",
    "history":      [],
    "user_profile": get_user_profile(USER_ID),
    "audio_path":   None,
    "image_paths":  None,
}

print(f"Input: {TEST_INPUT}\n")
t0     = time.time()
result = app.invoke(state, config=config)
elapsed = round(time.time() - t0, 1)

print(f"\nIntent : {result.get('intent')}")
print(f"Emotion: {result.get('emotion_label')} ({result.get('emotion_intensity')})")
print(f"Elapsed: {elapsed}s")
print(f"\nResponse:\n{result.get('response', '')}")
