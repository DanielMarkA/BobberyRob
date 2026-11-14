"""Display-only formatting helpers. The backend owns the actual values."""


def format_time(seconds) -> str:
    """134 -> '02:14' (leaderboard)."""
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def format_time_precise(seconds) -> str:
    """522.36 -> '08:42.36' (results screen, with hundredths)."""
    hundredths_total = max(0, int(round(float(seconds) * 100)))
    minutes, rest = divmod(hundredths_total, 6000)
    secs, hundredths = divmod(rest, 100)
    return f"{minutes:02d}:{secs:02d}.{hundredths:02d}"


def format_penalty(seconds) -> str:
    """30 -> '+00:30'."""
    minutes, secs = divmod(int(seconds), 60)
    return f"+{minutes:02d}:{secs:02d}"