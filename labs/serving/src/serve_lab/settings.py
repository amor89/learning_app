"""Settings from environment variables, checked when the app starts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Where the model is and how many answers one request may hold."""

    model_dir: Path
    max_batch: int

    @classmethod
    def from_env(cls) -> Settings:
        """Read MODEL_DIR (default `model`) and MAX_BATCH (default 100).

        Raises:
            ValueError: If MAX_BATCH is not a whole number from 1 to 1,000.
        """
        raw = os.environ.get("MAX_BATCH", "100")
        if not raw.isdigit() or not 1 <= int(raw) <= 1_000:
            raise ValueError(f"MAX_BATCH must be a whole number from 1 to 1000, got {raw!r}")
        return cls(model_dir=Path(os.environ.get("MODEL_DIR", "model")), max_batch=int(raw))
