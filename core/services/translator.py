import google.generativeai as genai

from core.constants import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

TRANSLATION_MODEL = "models/gemini-flash-lite-latest"


def normalize_hindi_to_devanagari(text: str) -> str:
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
    return response.text.strip()


def translate_to_english(text: str) -> str:
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
    return response.text.strip()
