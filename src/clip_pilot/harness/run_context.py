from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RunContext:
    video_path: str
    subtitle_path: str
    intent: str
    out_dir: str
    run_id: str = "workflow_run"
    clip_count: int | None = None
    config: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)

    @property
    def root(self) -> Path:
        return Path(self.out_dir)

    @property
    def selected_segments_dir(self) -> Path:
        return self.root / "assets" / "selected_segments"

    @property
    def title_cards_dir(self) -> Path:
        return self.root / "assets" / "title_cards"

    @property
    def temp_chunks_dir(self) -> Path:
        return self.root / "assets" / "temp_chunks"

    def prepare_dirs(self) -> None:
        for path in [self.root, self.selected_segments_dir, self.title_cards_dir, self.temp_chunks_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def output_path(self, name: str) -> Path:
        return self.root / name

