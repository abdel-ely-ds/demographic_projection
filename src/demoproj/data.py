"""Data loading — resolves country configs from cache or built-in defaults."""

from __future__ import annotations

from typing import Any

import numpy as np

from demoproj.fetch import get_or_fetch


def expand_5yr_to_single(groups: list[tuple[int, int, int] | list]) -> np.ndarray:
    """Distribute 5-year age groups uniformly into 101 single-year buckets."""
    pop = np.zeros(101, dtype=np.float64)
    for item in groups:
        low, high, count = int(item[0]), int(item[1]), int(item[2])
        if high >= 100:
            pop[100] += count
        else:
            span = high - low + 1
            per_year = count / span
            for a in range(low, min(high + 1, 101)):
                pop[a] = per_year
    return pop


def load_params(query: str) -> dict[str, Any]:
    """Load country data (from cache or API) ready for projection."""
    return get_or_fetch(query)
