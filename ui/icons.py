import re
from functools import lru_cache
from pathlib import Path

_ICON_DIR = Path(__file__).resolve().parent.parent / "static" / "icons"


@lru_cache(maxsize=None)
def icon(name: str, size: int = 24) -> str:
    """Inline a Lucide SVG as a single line (st.markdown breaks on newlines).
    Colour comes from CSS `color`, since Lucide strokes use currentColor."""
    svg = " ".join((_ICON_DIR / f"{name}.svg").read_text(encoding="utf-8").split())
    start, end = svg.index("<svg"), svg.index(">", svg.index("<svg")) + 1
    tag = re.sub(r'\s(?:width|height|class)="[^"]*"', "", svg[start:end])
    tag = tag.replace("<svg", f'<svg class="icon" width="{size}" height="{size}"', 1)
    return svg[:start] + tag + svg[end:]