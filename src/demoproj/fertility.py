"""Age-specific fertility distribution."""

from __future__ import annotations

import numpy as np


def fertility_weights(peak_age: float = 31.0, spread: float = 6.5) -> np.ndarray:
    """Normalized Gaussian fertility distribution over ages 15-49.

    Returns an array of length 101 where values sum to 1.0 across the
    reproductive window.
    """
    w = np.zeros(101)
    for a in range(15, 50):
        w[a] = np.exp(-0.5 * ((a - peak_age) / spread) ** 2)
    total = w.sum()
    if total > 0:
        w /= total
    return w
