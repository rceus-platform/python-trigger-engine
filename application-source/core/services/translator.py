"""Translation helpers backed by Gemini."""

from google import genai

from core.constants import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

TRANSLATION_MODEL = "models/gemini-flash-lite-latest"


def normalize_hindi_to_devanagari(text: str) -> str:
    """Convert spoken Hindi text into pure Devanagari script."""
    prompt = f"""
The following text represents SPOKEN HINDI.
It may be written in Urdu script, Roman Hindi, or mixed scripts.

Rewrite it in PURE DEVANAGARI HINDI (हिंदी).
Do NOT use Urdu script.
Do NOT translate to English.
Do NOT explain.
Output ONLY Devanagari Hindi.

Text:
{text}
"""
    response = client.models.generate_content(
        model=TRANSLATION_MODEL,
        contents=prompt,
    )
    response_text = response.text
    if not response_text:
        raise RuntimeError("Gemini returned empty text for Hindi normalization.")
    return response_text.strip()


def translate_to_english(text: str) -> str:
    """Translate spoken text into natural, idiomatic English."""
    prompt = f"""
Translate the following spoken text into clear, natural English.
Focus on meaning, not literal translation.
Do NOT explain.

Text:
{text}
"""
    response = client.models.generate_content(
        model=TRANSLATION_MODEL,
        contents=prompt,
    )
    response_text = response.text
    if not response_text:
        raise RuntimeError("Gemini returned empty text for translation.")
    return response_text.strip()
