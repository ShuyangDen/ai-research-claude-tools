"""Shared conservative token estimates for frontier-review planning and validation."""

from __future__ import annotations

import math
import re


def estimate_tokens(value: str) -> int:
    """Return a conservative, model-agnostic estimate for mixed-language text."""

    text = str(value or "")
    chinese = len(re.findall(r"[\u3400-\u9fff]", text))
    return max(1, math.ceil(len(text.encode("utf-8")) / 4), chinese)
