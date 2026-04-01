import json
import logging

logger = logging.getLogger(__name__)

def parse_first_json(text: str) -> dict | None:
    """
    Extract the first valid JSON object from a string that might
    contain markdown code blocks or extra leading/trailing text.
    """
    text = text.strip()
    
    # Try direct parsing first
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Find first candidate '{'
    start = text.find('{')
    if start == -1:
        return None

    # Try JSONDecoder.raw_decode from that point
    # It will stop at the end of the first valid JSON object
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass

    return None
