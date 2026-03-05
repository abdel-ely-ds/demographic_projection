"""CLI: ``demoproj fetch``, ``demoproj project``, ``demoproj compare``, ``demoproj history``."""

from __future__ import annotations

import argparse
import sys

import numpy as np

from demoproj.data import expand_5yr_to_single, load_params
from demoproj.fetch import fetch_country, fetch_tfr_history, get_or_fetch, list_cached, save_country
from demoproj.model import ProjectionParams, project
from demoproj.plotting import plot_comparison, plot_single_country, plot_tfr_history


def _to_params(cfg: dict) -> ProjectionParams:
    return ProjectionParams(
        name=cfg["name"],
        initial_pop=expand_5yr_to_single(cfg["groups"]),
        tfr=cfg["tfr"],
        life_expectancy=cfg["life_expectancy"],
        net_migration_rate=cfg["net_migration_rate"],
        fertility_peak=cfg["fertility_peak"],
        fertility_spread=cfg["fertility_spread"],
    )


def _print_table(results: dict) -> None:
    print(f"\n{'=' * 92}")
    print(
        f"  {'Country':<22s}  {'TFR':>5s}  {'Pop 2024':>10s}  {'Pop +50y':>10s}  "
        f"{'Change':>8s}  {'Elderly +50y':>12s}  {'Dep. +50y':>10s}"
    )
    print(f"{'-' * 92}")
    for name, r in results.items():
        yr50 = min(50, len(r.years) - 1)
        p0, p50 = r.total[0] / 1e6, r.total[yr50] / 1e6
        print(
            f"  {name:<22s}  {r.tfr:>5.2f}  {p0:>8.1f} M  {p50:>8.1f} M  "
            f"{100 * (p50 / p0 - 1):>+7.1f}%  {r.pct_elderly[yr50]:>10.1f} %  "
            f"{r.dependency_ratio[yr50]:>9.2f}"
        )
    print(f"{'=' * 92}")


def _print_milestones(results: dict) -> None:
    print("\n  KEY MILESTONES:")
    for name, r in results.items():
        crosses = np.where(r.dependency_ratio >= 1.0)[0]
        dep_year = str(int(r.years[crosses[0]])) if len(crosses) else "never"
        half_idx = np.where(r.total <= 0.5 * r.total[0])[0]
        half_year = str(int(r.years[half_idx[0]])) if len(half_idx) else "never"
        peak_idx = int(np.argmax(r.pct_elderly))
        print(
            f"    {name:<22s}  Dep>1.0: {dep_year:<8s}  "
            f"Pop halved: {half_year:<8s}  "
            f"Peak elderly: {r.pct_elderly[peak_idx]:.1f}% ({int(r.years[peak_idx])})"
        )
    print()


def cmd_fetch(args: argparse.Namespace) -> int:
    for q in args.countries:
        try:
            data = fetch_country(q)
            path = save_country(data)
            print(f"  -> Saved to {path}\n")
        except Exception as e:
            print(f"  ERROR fetching '{q}': {e}\n", file=sys.stderr)
            return 1

    cached = list_cached()
    if cached:
        print(f"Cached countries ({len(cached)}): {', '.join(cached)}")
    return 0


def cmd_project(args: argparse.Namespace) -> int:
    cfg = get_or_fetch(args.country)
    params = _to_params(cfg)
    result = project(params, horizon=args.horizon)

    _print_table({result.name: result})
    _print_milestones({result.name: result})

    slug = cfg["iso3"].lower()
    path = f"{args.output_dir}/{slug}_projection.png"
    plot_single_country(result, save_path=path)
    print(f"Chart saved: {path}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    queries = args.countries if args.countries else list_cached()
    if not queries:
        print("No countries specified and none cached. Run 'demoproj fetch' first.", file=sys.stderr)
        return 1

    results = {}
    for q in queries:
        cfg = get_or_fetch(q)
        params = _to_params(cfg)
        results[cfg["name"]] = project(params, horizon=args.horizon)

    _print_table(results)
    _print_milestones(results)

    path = f"{args.output_dir}/demographic_comparison.png"
    plot_comparison(results, save_path=path)
    print(f"Chart saved: {path}")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    series = []
    for q in args.countries:
        try:
            name, years, values = fetch_tfr_history(q, start=args.start, end=args.end)
            series.append((name, years, values))
            print(f"  {name}: {years[0]}-{years[-1]} ({len(years)} data points, latest TFR={values[-1]:.2f})")
        except Exception as e:
            print(f"  ERROR fetching TFR history for '{q}': {e}", file=sys.stderr)
            return 1

    path = f"{args.output_dir}/tfr_history.png"
    plot_tfr_history(series, save_path=path)
    print(f"\nChart saved: {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="demoproj",
        description="Demographic cohort projection (101 age buckets, real UN data)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="Download & cache country data")
    p_fetch.add_argument("countries", nargs="+", help="ISO3 codes or country names (e.g. KOR Japan France)")

    p_proj = sub.add_parser("project", help="Single-country projection dashboard")
    p_proj.add_argument("country", help="ISO3 code or country name")
    p_proj.add_argument("--horizon", type=int, default=100)
    p_proj.add_argument("--output-dir", type=str, default=".")

    p_comp = sub.add_parser("compare", help="Multi-country comparison")
    p_comp.add_argument("countries", nargs="*", help="ISO3 codes or names (default: all cached)")
    p_comp.add_argument("--horizon", type=int, default=100)
    p_comp.add_argument("--output-dir", type=str, default=".")

    p_hist = sub.add_parser("history", help="Historical TFR evolution chart")
    p_hist.add_argument("countries", nargs="+", help="ISO3 codes or country names")
    p_hist.add_argument("--start", type=int, default=1960, help="Start year (default: 1960)")
    p_hist.add_argument("--end", type=int, default=2023, help="End year (default: 2023)")
    p_hist.add_argument("--output-dir", type=str, default=".")

    args = parser.parse_args(argv)
    handlers = {
        "fetch": cmd_fetch,
        "project": cmd_project,
        "compare": cmd_compare,
        "history": cmd_history,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
