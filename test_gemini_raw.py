"""
Direct Gemini API test - no system prompt, see what it actually identifies.
Usage:
    python test_gemini_raw.py <image_path>
    python test_gemini_raw.py  (uses a built-in test URL if no path given)
"""
import sys
import os
import base64
import json
import httpx

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    # Try loading from .env manually
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if not API_KEY:
    print("ERROR: GEMINI_API_KEY not found in environment or .env file")
    sys.exit(1)

MODEL = "gemini-2.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

if len(sys.argv) >= 3:
    API_KEY = sys.argv[1]
    image_path = sys.argv[2]
elif len(sys.argv) == 2:
    image_path = sys.argv[1]
else:
    image_path = None

if not API_KEY:
    print("ERROR: GEMINI_API_KEY not found. Pass it as first argument:")
    print("  python test_gemini_raw.py <api_key> <image_path>")
    sys.exit(1)

if not image_path or not os.path.exists(image_path):
    print(f"ERROR: provide a valid image path as argument")
    print(f"  e.g. python test_gemini_raw.py C:\\path\\to\\food.jpg")
    sys.exit(1)

with open(image_path, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

# ── Test 1: completely raw, no prompt ──────────────────────────────────────
print("=" * 60)
print("TEST 1: Raw prompt - 'What food is in this image?'")
print("=" * 60)

payload = {
    "contents": [{
        "parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
            {"text": "What food is in this image? Describe exactly what you see - the type of noodles/rice, cooking method, and toppings."},
        ]
    }],
    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 1024},
}

resp = httpx.post(URL, json=payload, timeout=60)
resp.raise_for_status()
data = resp.json()
text1 = data["candidates"][0]["content"]["parts"][0]["text"]
print(text1)

# ── Test 2: with our current food prompt ──────────────────────────────────
print("\n" + "=" * 60)
print("TEST 2: With FOOD_PROMPT from food.py")
print("=" * 60)

sys.path.insert(0, os.path.dirname(__file__))
from src.vision_agent.prompts.food import FOOD_PROMPT

print(f"[Prompt first 200 chars]: {FOOD_PROMPT[:200]}")
print()

payload2 = {
    "contents": [{
        "parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
            {"text": FOOD_PROMPT},
        ]
    }],
    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 2048},
}

resp2 = httpx.post(URL, json=payload2, timeout=60)
resp2.raise_for_status()
data2 = resp2.json()
text2 = data2["candidates"][0]["content"]["parts"][0]["text"]
print(text2)
