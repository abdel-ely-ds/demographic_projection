"""Professional chart generation for demographic projections."""

from __future__ import annotations

from typing import Sequence

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from demoproj.model import CohortProjection

PALETTE = {
    "South Korea": "#EF4444",
    "Europe (EU)": "#3B82F6",
    "USA": "#10B981",
    "Israel": "#F59E0B",
    "Morocco": "#8B5CF6",
}

_FALLBACK_COLORS = ["#6366F1", "#EC4899", "#14B8A6", "#F97316", "#A855F7", "#0EA5E9"]

_BG = "#FAFBFC"
_GRID = "#E2E8F0"
_MUTED = "#64748B"
_REPL = "#94A3B8"


def _color_for(name: str, idx: int = 0) -> str:
    return PALETTE.get(name, _FALLBACK_COLORS[idx % len(_FALLBACK_COLORS)])


def apply_style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 10.5,
        "axes.facecolor": _BG,
        "axes.edgecolor": _GRID,
        "axes.grid": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9.5,
        "legend.framealpha": 0.95,
        "legend.edgecolor": _GRID,
        "grid.color": _GRID,
        "grid.linewidth": 0.5,
        "grid.alpha": 0.6,
        "figure.facecolor": _BG,
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.facecolor": _BG,
        "lines.linewidth": 2.2,
    })


def plot_single_country(r: CohortProjection, save_path: str | None = None) -> plt.Figure:
    """Four-panel dashboard for a single country projection."""
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(16, 10.5))
    fig.subplots_adjust(hspace=0.32, wspace=0.28)
    color = _color_for(r.name)
    yrs = r.years

    # Panel 1: age structure stacked area
    ax = axes[0, 0]
    ax.stackplot(
        yrs, r.pct_kids, r.pct_adults, r.pct_elderly,
        labels=["Children (0-14)", "Working age (15-64)", "Elderly (65+)"],
        colors=["#3B82F6", "#10B981", "#EF4444"],
        alpha=0.85,
    )
    ax.set_ylim(0, 100)
    ax.set_ylabel("Share of total population (%)")
    ax.set_title("Age Structure Evolution")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend(loc="upper right", frameon=True)

    # Panel 2: total population
    ax = axes[0, 1]
    ax.fill_between(yrs, r.total / 1e6, alpha=0.15, color=color)
    ax.plot(yrs, r.total / 1e6, color=color, lw=2.5)
    ax.set_ylabel("Population (millions)")
    ax.set_title("Total Population")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    peak_idx = int(np.argmax(r.total))
    if 0 < peak_idx < len(yrs) - 1:
        ax.plot(yrs[peak_idx], r.total[peak_idx] / 1e6, "o", color="#DC2626", ms=7, zorder=5)
        ax.annotate(
            f"Peak: {r.total[peak_idx] / 1e6:,.1f} M ({int(yrs[peak_idx])})",
            xy=(yrs[peak_idx], r.total[peak_idx] / 1e6),
            xytext=(yrs[peak_idx] + 5, r.total[peak_idx] / 1e6 * 1.03),
            fontsize=8, arrowprops=dict(arrowstyle="->", color=_MUTED, lw=0.8),
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=_GRID, alpha=0.9),
        )

    # Panel 3: dependency ratio
    ax = axes[1, 0]
    y_max = min(max(r.dependency_ratio.max() * 1.15, 1.2), 3.0)
    ax.axhspan(0, 0.55, color="#ECFDF5", alpha=0.5, zorder=0)
    ax.axhspan(0.55, 0.80, color="#FEF3C7", alpha=0.5, zorder=0)
    ax.axhspan(0.80, y_max, color="#FEE2E2", alpha=0.5, zorder=0)
    ax.plot(yrs, r.dependency_ratio, color="#7C3AED", lw=2.5, zorder=3)
    ax.axhline(1.0, color=_REPL, ls=":", lw=1.2, zorder=2)
    ax.text(yrs[-1] + 1, 1.0, "1:1", fontsize=8, va="center", color=_MUTED)
    ax.set_ylim(0, y_max)
    ax.set_ylabel("Ratio (dependents / working age)")
    ax.set_title("Total Dependency Ratio")
    ax.text(yrs[0] + 1, 0.30, "Sustainable", fontsize=8, color="#059669", alpha=0.7, weight="bold")
    ax.text(yrs[0] + 1, 0.67, "Warning", fontsize=8, color="#D97706", alpha=0.7, weight="bold")
    ax.text(yrs[0] + 1, 0.90, "Critical", fontsize=8, color="#DC2626", alpha=0.7, weight="bold")

    # Panel 4: births vs deaths
    ax = axes[1, 1]
    births = r.annual_births[:-1] / 1e6
    deaths = r.annual_deaths[:-1] / 1e6
    yr_v = yrs[:-1]
    ax.plot(yr_v, births, color="#22C55E", lw=2, label="Births")
    ax.plot(yr_v, deaths, color="#DC2626", lw=2, label="Deaths")
    ax.fill_between(yr_v, births, deaths, where=births >= deaths, interpolate=True, color="#22C55E", alpha=0.12)
    ax.fill_between(yr_v, births, deaths, where=births < deaths, interpolate=True, color="#DC2626", alpha=0.12)
    ax.set_ylabel("Millions per year")
    ax.set_title("Births vs Deaths")
    ax.legend(loc="upper right", frameon=True)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.2f}"))

    fig.suptitle(
        f"Demographic Projection - {r.name}",
        fontsize=17, fontweight="bold", y=0.98, color="#1E293B",
    )
    fig.text(
        0.5, 0.935,
        f"TFR: {r.tfr:.2f}  |  Replacement: 2.10  |  "
        f"Pop: {r.total[0] / 1e6:,.1f} M  |  {int(yrs[0])}-{int(yrs[-1])}",
        ha="center", fontsize=10, color=_MUTED,
    )
    fig.text(
        0.5, 0.005,
        "101-bucket cohort model  |  Source: UN WPP 2024  |  Constant TFR & mortality assumed",
        ha="center", fontsize=8, color=_MUTED, style="italic",
    )

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight", facecolor=_BG)
    return fig


def plot_comparison(results: dict[str, CohortProjection], save_path: str | None = None) -> plt.Figure:
    """Four-panel comparison of multiple country projections."""
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(16, 10.5))
    fig.subplots_adjust(hspace=0.30, wspace=0.26)

    ordered = [n for n in PALETTE if n in results]
    extra = [n for n in results if n not in PALETTE]
    order = ordered + extra

    def c(name: str) -> str:
        return _color_for(name, order.index(name))

    ax = axes[0, 0]
    for name in order:
        r = results[name]
        ax.plot(r.years, 100 * r.total / r.total[0], color=c(name), label=name)
    ax.axhline(100, color=_REPL, ls=":", lw=1, alpha=0.6)
    ax.axhline(50, color="#FCA5A5", ls=":", lw=1, alpha=0.4)
    ax.set_ylabel("Population index (2024 = 100)")
    ax.set_title("Population Trajectory")
    ax.legend(loc="best", frameon=True)

    ax = axes[0, 1]
    for name in order:
        r = results[name]
        ax.plot(r.years, r.pct_elderly, color=c(name), label=name)
    ax.axhline(33.3, color=_REPL, ls=":", lw=1)
    ax.set_ylabel("Share of population (%)")
    ax.set_title("Elderly Share (65+)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend(loc="best", frameon=True)

    ax = axes[1, 0]
    ax.axhspan(0, 0.55, color="#ECFDF5", alpha=0.4, zorder=0)
    ax.axhspan(0.55, 0.80, color="#FEF3C7", alpha=0.4, zorder=0)
    ax.axhspan(0.80, 2.0, color="#FEE2E2", alpha=0.4, zorder=0)
    for name in order:
        r = results[name]
        ax.plot(r.years, r.dependency_ratio, color=c(name), label=name)
    ax.axhline(1.0, color=_REPL, ls=":", lw=1.2)
    max_dep = max(r.dependency_ratio.max() for r in results.values())
    ax.set_ylim(0, min(max_dep * 1.15, 2.0))
    ax.set_ylabel("Dependents per worker")
    ax.set_title("Total Dependency Ratio")
    ax.legend(loc="best", frameon=True)

    ax = axes[1, 1]
    for name in order:
        r = results[name]
        ax.plot(r.years, r.pct_kids, color=c(name), label=name)
    ax.set_ylabel("Share of population (%)")
    ax.set_title("Children Share (0-14)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend(loc="best", frameon=True)

    fig.suptitle(
        "Demographic Projections - Comparison",
        fontsize=16, fontweight="bold", y=0.98, color="#1E293B",
    )
    fig.text(
        0.5, 0.935,
        "101 single-year age buckets  |  Real 2024 age pyramids (UN WPP)  |  "
        "Age-specific mortality calibrated to life expectancy",
        ha="center", fontsize=9.5, color=_MUTED,
    )
    fig.text(
        0.5, 0.005,
        "Source: UN WPP 2024 via PopulationPyramid.net  |  Constant TFR & mortality  |  Net migration included",
        ha="center", fontsize=8, color=_MUTED, style="italic",
    )

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight", facecolor=_BG)
    return fig


def plot_tfr_history(
    series: Sequence[tuple[str, list[int], list[float]]],
    save_path: str | None = None,
) -> plt.Figure:
    """Plot historical TFR time-series for one or more countries/regions."""
    apply_style()
    fig, ax = plt.subplots(figsize=(14, 7))

    for idx, (name, years, values) in enumerate(series):
        color = _color_for(name, idx)
        ax.plot(years, values, color=color, lw=2.5, label=name, zorder=3)
        ax.annotate(
            f"{values[-1]:.2f}",
            xy=(years[-1], values[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
            color=color,
            va="center",
        )

    ax.axhline(2.1, color="#DC2626", ls="--", lw=1.5, alpha=0.7, zorder=2)
    ax.text(
        ax.get_xlim()[0] + 1, 2.15,
        "Replacement rate (2.1)",
        fontsize=9, color="#DC2626", alpha=0.8, fontweight="bold",
    )

    ax.axhspan(0, 1.3, color="#FEE2E2", alpha=0.15, zorder=0)
    ax.axhspan(1.3, 2.1, color="#FEF3C7", alpha=0.15, zorder=0)
    ax.axhspan(2.1, ax.get_ylim()[1] + 1, color="#ECFDF5", alpha=0.15, zorder=0)

    ax.text(ax.get_xlim()[0] + 1, 0.9, "Very low fertility", fontsize=8, color="#DC2626", alpha=0.5, style="italic")
    ax.text(ax.get_xlim()[0] + 1, 1.6, "Below replacement", fontsize=8, color="#D97706", alpha=0.5, style="italic")

    all_vals = [v for _, _, vals in series for v in vals]
    ax.set_ylim(max(0, min(all_vals) - 0.3), max(all_vals) + 0.5)
    ax.set_ylabel("Total Fertility Rate (children per woman)")
    ax.set_xlabel("Year")
    ax.legend(loc="best", frameon=True, fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f"))

    names_str = ", ".join(n for n, _, _ in series)
    fig.suptitle(
        "Total Fertility Rate - Historical Evolution",
        fontsize=16, fontweight="bold", y=0.97, color="#1E293B",
    )
    fig.text(
        0.5, 0.92,
        names_str,
        ha="center", fontsize=11, color=_MUTED,
    )
    fig.text(
        0.5, 0.005,
        "Source: World Bank (SP.DYN.TFRT.IN)  |  Replacement rate = 2.1 children per woman",
        ha="center", fontsize=8, color=_MUTED, style="italic",
    )

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight", facecolor=_BG)
    return fig
