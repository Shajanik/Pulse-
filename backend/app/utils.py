import secrets


def generate_room_code() -> str:
    """Random 6-digit numeric code, e.g. '042817'. Uniqueness is enforced by
    the unique index on polls.code (callers retry on collision)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def crowd_pulse_message(option_texts: list[str], votes: list[int]) -> str:
    """Deterministic live commentary derived from vote percentages. No AI
    involved: simple rules over the current standings."""
    total = sum(votes)
    if total == 0:
        return "Waiting for the first vote..."

    stats = sorted(
        ((text, v / total * 100) for text, v in zip(option_texts, votes)),
        key=lambda s: s[1],
        reverse=True,
    )
    pcts = [p for _, p in stats]
    spread = max(pcts) - min(pcts)

    if len(stats) == 1:
        return f"{stats[0][0]} is dominating!"

    gap = pcts[0] - pcts[1]
    if gap >= 25:
        return f"{stats[0][0]} is dominating!"
    if spread <= 15:
        return "The crowd is divided!"
    return "It's getting competitive!"
