"""Core cohort projection engine — 101 single-year age buckets."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from demoproj.fertility import fertility_weights
from demoproj.mortality import calibrate_mortality


@dataclass(frozen=True)
class ProjectionParams:
    """Immutable parameter set for a single country projection."""

    name: str
    initial_pop: np.ndarray
    tfr: float
    life_expectancy: float
    net_migration_rate: float = 0.0
    fertility_peak: float = 31.0
    fertility_spread: float = 6.5
    female_ratio: float = 0.49


@dataclass
class CohortProjection:
    """Full results of a cohort projection."""

    name: str
    tfr: float
    years: np.ndarray
    pop_by_age: np.ndarray  # (n_years, 101)
    total: np.ndarray
    pct_kids: np.ndarray  # 0-14
    pct_adults: np.ndarray  # 15-64
    pct_elderly: np.ndarray  # 65+
    dependency_ratio: np.ndarray
    annual_births: np.ndarray
    annual_deaths: np.ndarray


def project(params: ProjectionParams, horizon: int = 100, start_year: int = 2024) -> CohortProjection:
    """Run a single-year cohort-component projection.

    Each year the population vector is aged by one year, with births
    entering age 0, age-specific mortality applied, and net migration
    distributed across working ages 18-45.
    """
    mortality = calibrate_mortality(params.life_expectancy)
    fw = fertility_weights(params.fertility_peak, params.fertility_spread)

    n = horizon + 1
    pop_history = np.zeros((n, 101))
    totals = np.zeros(n)
    pct_k = np.zeros(n)
    pct_a = np.zeros(n)
    pct_e = np.zeros(n)
    dep = np.zeros(n)
    births_arr = np.zeros(n)
    deaths_arr = np.zeros(n)

    pop = params.initial_pop.copy().astype(np.float64)

    # Pre-compute migration age distribution (bell around age 30)
    mig_weights = np.zeros(101)
    for a in range(18, 46):
        mig_weights[a] = np.exp(-0.5 * ((a - 30) / 8) ** 2)
    mig_sum = mig_weights.sum()
    if mig_sum > 0:
        mig_weights /= mig_sum

    for y in range(n):
        total = pop.sum()
        kids = pop[:15].sum()
        adults = pop[15:65].sum()
        elderly = pop[65:].sum()

        pop_history[y] = pop
        totals[y] = total
        pct_k[y] = 100.0 * kids / total if total > 0 else 0.0
        pct_a[y] = 100.0 * adults / total if total > 0 else 0.0
        pct_e[y] = 100.0 * elderly / total if total > 0 else 0.0
        dep[y] = (kids + elderly) / adults if adults > 0 else float("inf")

        if y == horizon:
            break

        women = pop * params.female_ratio
        annual_births = params.tfr * float(np.sum(women * fw))
        births_arr[y] = annual_births

        deaths = np.minimum(pop * mortality, pop)
        deaths_arr[y] = deaths.sum()

        new_pop = np.zeros(101)
        new_pop[0] = annual_births
        for a in range(1, 100):
            new_pop[a] = pop[a - 1] - deaths[a - 1]
        new_pop[100] = (pop[99] - deaths[99]) + (pop[100] - deaths[100])

        if params.net_migration_rate != 0:
            new_pop += total * params.net_migration_rate * mig_weights

        np.maximum(new_pop, 0.0, out=new_pop)
        pop = new_pop

    return CohortProjection(
        name=params.name,
        tfr=params.tfr,
        years=np.arange(start_year, start_year + n),
        pop_by_age=pop_history,
        total=totals,
        pct_kids=pct_k,
        pct_adults=pct_a,
        pct_elderly=pct_e,
        dependency_ratio=dep,
        annual_births=births_arr,
        annual_deaths=deaths_arr,
    )
