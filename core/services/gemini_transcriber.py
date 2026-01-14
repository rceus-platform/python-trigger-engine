import base64
import os

from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "models/gemini-flash-lite-latest"


def gemini_transcribe(audio_path: str) -> dict:
    """
    Returns:
    {
      "language": "hi" | "mr" | "en",
      "transcript_devanagari": "...",
      "transcript_english": "..."
    }
    """

    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()

    prompt = """
You are a speech-to-text engine.

Rules:
- Detect the spoken language (Hindi, Marathi, or English)
- If Hindi or Marathi:
  - Output transcript in DEVANAGARI script only
  - Do NOT use Urdu or Roman script
- Preserve English words if spoken
- Also provide a clean English translation
- Do NOT explain anything

Output STRICT JSON only in this format:

{
  "language": "hi|mr|en",
  "transcript_native": "...",
  "transcript_english": "..."
}
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "audio/wav",
                            "data": audio_b64,
                        }
                    },
                    {"text": prompt},
                ],
            }
        ],
    )

    import json

    return json.loads(response.text.strip())
