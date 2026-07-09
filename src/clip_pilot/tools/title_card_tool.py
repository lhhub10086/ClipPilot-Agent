from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_title_cards(clips: list[dict[str, Any]], output_dir: str) -> dict[str, Any]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return {"success": True, "backend": "skipped_title_cards", "data": {"cards": [], "segment_count": len(clips)}, "metadata": {"note": "Title cards are optional assets; final_review uses selected segments only."}}


