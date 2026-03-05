"""Age-specific mortality calibration using iterative Gompertz scaling."""

from __future__ import annotations

import numpy as np

_BASE_SCHEDULE = np.array(
    [0.0040]  # age 0
    + [0.0004] * 4  # 1-4
    + [0.00015] * 5  # 5-9
    + [0.00012] * 5  # 10-14
    + [0.00040] * 5  # 15-19
    + [0.00055] * 5  # 20-24
    + [0.00060] * 5  # 25-29
    + [0.00080] * 5  # 30-34
    + [0.00120] * 5  # 35-39
    + [0.00200] * 5  # 40-44
    + [0.00350] * 5  # 45-49
    + [0.00550] * 5  # 50-54
    + [0.00900] * 5  # 55-59
    + [0.01500] * 5  # 60-64
    + [0.02500] * 5  # 65-69
    + [0.04000] * 5  # 70-74
    + [0.07000] * 5  # 75-79
    + [0.12000] * 5  # 80-84
    + [0.19000] * 5  # 85-89
    + [0.30000] * 5  # 90-94
    + [0.42000] * 5  # 95-99
    + [0.55000],  # 100+
    dtype=np.float64,
)


def compute_life_expectancy(mortality: np.ndarray) -> float:
    """Period life expectancy at birth from an age-specific mortality schedule."""
    survivors = np.ones(len(mortality))
    for a in range(1, len(mortality)):
        survivors[a] = survivors[a - 1] * (1 - mortality[a - 1])
    return float(survivors.sum())


def calibrate_mortality(target_le: float, max_iter: int = 100, tol: float = 0.05) -> np.ndarray:
    """Scale the base mortality schedule to match *target_le*.

    Uses bisection-style iterative scaling of a reference schedule whose
    baseline life expectancy is ~80 years.
    """
    scale = 1.0
    for _ in range(max_iter):
        mortality = np.clip(_BASE_SCHEDULE * scale, 0.0, 0.99)
        computed = compute_life_expectancy(mortality)
        if abs(computed - target_le) < tol:
            break
        scale *= computed / target_le
    return np.clip(_BASE_SCHEDULE * scale, 0.0, 0.99)
