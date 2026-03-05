"""Demographic projection model using single-year age cohorts."""

from demoproj.data import expand_5yr_to_single, load_params
from demoproj.fertility import fertility_weights
from demoproj.model import CohortProjection, ProjectionParams, project
from demoproj.mortality import calibrate_mortality
from demoproj.plotting import plot_comparison, plot_single_country

__all__ = [
    "CohortProjection",
    "ProjectionParams",
    "calibrate_mortality",
    "expand_5yr_to_single",
    "fertility_weights",
    "load_params",
    "plot_comparison",
    "plot_single_country",
    "project",
]
