import json
import os

from google import genai

# Client (new SDK)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "models/gemini-flash-lite-latest"


SYSTEM_INSTRUCTIONS = """
You convert insights into behavioral triggers.

STRICT RULES:
- Output ONLY valid JSON
- JSON must be an array of strings
- Max 5 items
- Each item format:
  "WHEN <condition>, DO <action>."
- Each item <= 12 words
- Concrete actions only
- No explanation, no extra text
- English only
"""


def extract_triggers_gemini(text: str) -> list[str]:
    prompt = f"""
{SYSTEM_INSTRUCTIONS}

Insight:
{text}

JSON:
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    raw = response.text.strip()

    try:
        data = json.loads(raw)
    except Exception:
        return []

    # Hard validation (never trust LLM output)
    valid = []
    for t in data:
        if (
            isinstance(t, str)
            and t.upper().startswith("WHEN ")
            and ", DO " in t
            and len(t.split()) <= 12
        ):
            valid.append(t)

    return valid[:5]
