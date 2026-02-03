def extract_triggers(text: str) -> list[str]:
    """
    Convert insight text into behavioral triggers.
    Deterministic v1 (rule-based).
    """

    triggers = []

    lower = text.lower()

    if "sleep" in lower and "goal" in lower:
        triggers.append("When choosing rest vs goal work, choose goal work.")

    if "dream" in lower:
        triggers.append("When tempted to only plan, take immediate action.")

    # Hard cap
    return triggers[:5]
