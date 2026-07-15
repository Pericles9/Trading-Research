#!/usr/bin/env python
"""
Statistical Validator — Large-Scale Validation for AlphaMomentumHawkes v5
=========================================================================

Phase 1 — Sample events from the full event universe (or use all 20k+)
Phase 2 — PARALLEL strategy run + Permutation Test (sign-randomization)
Phase 3 — Deep Excursion Analysis via Polars (trade_analyzer.py)
Phase 4 — Generate validation_report.md + distribution plots + heatmaps
         + slippage impact comparison + duration efficiency verification

Usage
-----
    # Smoke test (10 events, no permutation)
    python tools/stat_validator.py --n-events 10 --skip-permutation

    # Full validation (all events, 8 workers)
    python tools/stat_validator.py --n-events 0 --workers 8

    # Resume from checkpoint
    python tools/stat_validator.py --resume runs/stat_validation/2025-...
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import polars as pl

from strategies.alpha_momentum_hawkes.backtest_runner import (
    run_event,
    DATA_PATH,
    DEFAULT_LIBRARY,
    _make_run_dir,
    _save_json,
)
from strategies.alpha_momentum_hawkes.parallel_runner import run_parallel_batch
from strategies.alpha_momentum_hawkes.analytics.trade_analyzer import (
    build_trade_frame,
    enrich_with_excursions,
    full_analysis,
)
from utils.polars_loader import list_events

log = logging.getLogger("stat_validator")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)

# ━━━━━━━━━━━━━━━━━━━ Directory Setup ━━━━━━━━━━━━━━━━━━━

VALIDATION_ROOT = _PROJECT_ROOT / "runs" / "stat_validation"


def _make_validation_dir() -> Path:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    d = VALIDATION_ROOT / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


# ━━━━━━━━━━━━━━━━━━━ Phase 1: Sampling ━━━━━━━━━━━━━━━━━━━

def sample_events(
    n: int = 2000,
    min_magnitude: float = 30.0,
    seed: int = 42,
    data_path: Path = DATA_PATH,
) -> List[str]:
    """
    Draw a random sample of n events from the full universe.
    Uses min_magnitude=30 to include broad spectrum, not just mega-spikes.
    """
    all_events = list_events(data_path, min_magnitude=min_magnitude)
    log.info("Universe: %d events (min_mag=%.0f)", len(all_events), min_magnitude)

    if len(all_events) <= n:
        log.warning("Requested %d but only %d available — using all", n, len(all_events))
        return all_events

    rng = np.random.default_rng(seed)
    sampled = list(rng.choice(all_events, size=n, replace=False))
    log.info("Sampled %d events (seed=%d)", len(sampled), seed)
    return sorted(sampled)


# ━━━━━━━━━━━━━━━━━━━ Phase 2: Strategy Execution ━━━━━━━━

def run_validation_batch(
    event_names: List[str],
    val_dir: Path,
    config_overrides: Optional[dict] = None,
    library_path: Path = DEFAULT_LIBRARY,
    data_path: Path = DATA_PATH,
    checkpoint_interval: int = 50,
) -> Tuple[List[dict], List[dict]]:
    """
    Run the real strategy on all events, with checkpointing.

    Returns (summaries, errors) where each summary is the full summary.json dict.
    Saves a checkpoint every `checkpoint_interval` events.
    """
    summaries: List[dict] = []
    errors: List[dict] = []
    checkpoint_path = val_dir / "checkpoint.json"

    # Resume from checkpoint if it exists
    start_idx = 0
    if checkpoint_path.exists():
        ckpt = json.loads(checkpoint_path.read_text())
        summaries = ckpt.get("summaries", [])
        errors = ckpt.get("errors", [])
        start_idx = ckpt.get("next_idx", 0)
        log.info("Resuming from checkpoint at event %d/%d", start_idx, len(event_names))

    t0 = time.time()
    for idx in range(start_idx, len(event_names)):
        name = event_names[idx]
        try:
            run_dir = run_event(
                event_name=name,
                library_path=library_path,
                config_overrides=config_overrides,
                data_path=data_path,
            )
            summary_path = run_dir / "summary.json"
            if summary_path.exists():
                summary = json.loads(summary_path.read_text())
                summaries.append(summary)
            else:
                errors.append({"event": name, "error": "No summary.json"})

            elapsed = time.time() - t0
            rate = (idx - start_idx + 1) / elapsed
            remaining = (len(event_names) - idx - 1) / max(rate, 0.01)
            log.info(
                "[%d/%d] %s — OK  (%.1f evt/min, ~%.0fm left)",
                idx + 1, len(event_names), name, rate * 60, remaining / 60,
            )

        except Exception as exc:
            log.warning("[%d/%d] %s — FAILED: %s", idx + 1, len(event_names), name, exc)
            errors.append({"event": name, "error": str(exc)})

        # Checkpoint
        if (idx + 1) % checkpoint_interval == 0:
            _save_json({
                "summaries": summaries,
                "errors": errors,
                "next_idx": idx + 1,
                "timestamp": datetime.now().isoformat(),
            }, checkpoint_path)
            log.info("Checkpoint saved at event %d", idx + 1)

    # Final save
    _save_json({
        "summaries": summaries,
        "errors": errors,
        "next_idx": len(event_names),
        "timestamp": datetime.now().isoformat(),
    }, checkpoint_path)

    elapsed_total = time.time() - t0
    log.info(
        "Batch complete: %d OK, %d errors, %.1f min total",
        len(summaries), len(errors), elapsed_total / 60,
    )
    return summaries, errors


# ━━━━━━━━━━━━━━━━━━━ Phase 2b: Permutation Test ━━━━━━━━━

def _shuffled_pnl_for_event(summary: dict, rng: np.random.Generator) -> float:
    """
    Generate one random-reshuffled PnL for a single event.

    Shuffle: keep trade durations and PnL magnitudes, but randomly reassign
    the sign of each trade's PnL. This is a sign-randomization test: under H0,
    the sign of each trade is equally likely to be + or -.

    This is equivalent to: "if entry timing were random, PnL signs would be
    random coin flips."  Much cheaper than full re-simulation.
    """
    trades = summary.get("trades", [])
    if not trades:
        return 0.0

    # Extract round-trip PnLs
    pnls = []
    for t in trades:
        if t.get("action", "").startswith("EXIT"):
            pnls.append(t.get("pnl_pct", 0.0))

    if not pnls:
        return 0.0

    pnl_arr = np.array(pnls)
    signs = rng.choice([-1, 1], size=len(pnl_arr))
    return float(np.sum(pnl_arr * signs))


def run_permutation_test(
    summaries: List[dict],
    n_permutations: int = 100,
    seed: int = 123,
) -> dict:
    """
    Monte Carlo sign-randomization test.

    H0: Entry timing has no edge — trade signs are random.
    H1: CVD-accel entries produce systematically positive trades.

    For each permutation:
        - For each event, randomly flip the sign of each trade's PnL
        - Sum across all events → one shuffled total PnL

    Real PnL vs distribution of shuffled PnLs → p-value.
    """
    rng = np.random.default_rng(seed)

    # Real aggregate PnL
    real_pnls = []
    for s in summaries:
        real_pnls.append(s.get("total_pnl_pct", 0.0))
    real_total = float(np.sum(real_pnls))
    real_mean = float(np.mean(real_pnls)) if real_pnls else 0.0

    log.info("Real aggregate PnL: %.2f%% (mean %.2f%%)", real_total, real_mean)

    # Shuffled distribution
    shuffled_totals = np.zeros(n_permutations)
    for i in range(n_permutations):
        total = 0.0
        for s in summaries:
            total += _shuffled_pnl_for_event(s, rng)
        shuffled_totals[i] = total

        if (i + 1) % 25 == 0:
            log.info("Permutation %d/%d done", i + 1, n_permutations)

    # p-value: fraction of shuffled runs ≥ real PnL (one-tailed)
    p_value = float(np.mean(shuffled_totals >= real_total))

    return {
        "real_total_pnl": real_total,
        "real_mean_pnl": real_mean,
        "n_events": len(summaries),
        "n_permutations": n_permutations,
        "shuffled_mean": float(np.mean(shuffled_totals)),
        "shuffled_std": float(np.std(shuffled_totals)),
        "shuffled_p5": float(np.percentile(shuffled_totals, 5)),
        "shuffled_p95": float(np.percentile(shuffled_totals, 95)),
        "p_value": p_value,
        "significant_at_005": p_value < 0.05,
        "significant_at_001": p_value < 0.01,
        "shuffled_distribution": shuffled_totals.tolist(),
    }


# ━━━━━━━━━━━━━━━━━━━ Phase 3: Excursion Enrichment ━━━━━━

def _collect_excursion_rows(summaries: List[dict]) -> List[dict]:
    """
    Gather per-trade excursion data from each event's run_dir.
    Each event's run_dir has a trade_excursions.csv if excursion analysis ran.
    """
    rows = []
    for s in summaries:
        run_dir = Path(s.get("run_dir", ""))
        exc_csv = run_dir / "trade_excursions.csv"
        event = s.get("event", "")
        if exc_csv.exists():
            try:
                exc_df = pl.read_csv(exc_csv)
                for r in exc_df.to_dicts():
                    r["event"] = event
                    rows.append(r)
            except Exception:
                pass
    return rows


# ━━━━━━━━━━━━━━━━━━━ Phase 4: Report Generation ━━━━━━━━━

def _generate_distribution_plot(
    real_pnl: float,
    shuffled_dist: List[float],
    val_dir: Path,
) -> Path:
    """Histogram: Real vs Shuffled PnL distribution (matplotlib)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(shuffled_dist, bins=40, alpha=0.6, color="steelblue",
                edgecolor="white", label="Shuffled PnL (H₀)")
        ax.axvline(real_pnl, color="red", linewidth=2, linestyle="--",
                   label=f"Real PnL = {real_pnl:.1f}%")
        ax.set_xlabel("Aggregate PnL (%)")
        ax.set_ylabel("Count")
        ax.set_title("Permutation Test: Real vs Random Entry Timing")
        ax.legend()
        fig.tight_layout()

        path = val_dir / "permutation_distribution.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path
    except ImportError:
        log.warning("matplotlib not installed — skipping plot")
        return val_dir / "permutation_distribution.png"


def _generate_duration_heatmap_plot(
    duration_data: List[dict],
    val_dir: Path,
) -> Path:
    """Bar chart: WR and PnL by duration bucket."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if not duration_data:
            return val_dir / "duration_heatmap.png"

        buckets = [d["duration_bucket"] for d in duration_data]
        wr = [d["win_rate_pct"] for d in duration_data]
        pnl = [d["avg_pnl"] for d in duration_data]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        bars1 = ax1.bar(buckets, wr, color="seagreen", edgecolor="white")
        ax1.set_ylabel("Win Rate (%)")
        ax1.set_title("Win Rate by Trade Duration")
        ax1.set_ylim(0, 100)
        for b, v in zip(bars1, wr):
            ax1.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.0f}%",
                     ha="center", fontsize=9)

        colors = ["green" if p > 0 else "red" for p in pnl]
        bars2 = ax2.bar(buckets, pnl, color=colors, edgecolor="white")
        ax2.set_ylabel("Avg PnL (%)")
        ax2.set_title("Avg PnL by Trade Duration")
        ax2.axhline(0, color="gray", linewidth=0.5)
        for b, v in zip(bars2, pnl):
            ax2.text(b.get_x() + b.get_width() / 2,
                     v + (0.1 if v >= 0 else -0.3),
                     f"{v:.2f}%", ha="center", fontsize=9)

        fig.tight_layout()
        path = val_dir / "duration_heatmap.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path
    except ImportError:
        return val_dir / "duration_heatmap.png"


def generate_report(
    val_dir: Path,
    event_names: List[str],
    summaries: List[dict],
    errors: List[dict],
    analysis: dict,
    permutation: Optional[dict],
    elapsed_sec: float,
) -> Path:
    """Generate validation_report.md with all results."""

    sr = analysis.get("statistical_robustness", {})
    ep = analysis.get("excursion_profile", {})
    em = analysis.get("efficiency_metrics", {})
    dur = analysis.get("duration_heatmap", [])
    arch = analysis.get("archetype_heatmap", [])
    fails = analysis.get("top_10_failures", [])

    # ── Build the markdown ──
    lines = []
    lines.append("# AlphaMomentumHawkes v5 — Statistical Validation Report")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Events Sampled:** {len(event_names)}")
    lines.append(f"**Events Completed:** {len(summaries)}")
    lines.append(f"**Events Failed:** {len(errors)}")
    lines.append(f"**Total Runtime:** {elapsed_sec / 60:.1f} minutes")
    lines.append("")

    # ── Statistical Robustness ──
    lines.append("## 1. Statistical Robustness")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Trades | {sr.get('n_trades', 0):,} |")
    lines.append(f"| Winners / Losers | {sr.get('n_winners', 0)} / {sr.get('n_losers', 0)} |")
    lines.append(f"| Win Rate | {sr.get('win_rate_pct', 0):.1f}% |")
    lines.append(f"| Avg Winner | +{sr.get('avg_winner_pct', 0):.2f}% |")
    lines.append(f"| Avg Loser | -{sr.get('avg_loser_pct', 0):.2f}% |")
    lines.append(f"| **Expectancy** | **{sr.get('expectancy', 0):.4f}%** |")
    lines.append(f"| **Profit Factor** | **{sr.get('profit_factor', 0):.2f}** |")
    lines.append(f"| **SQN** | **{sr.get('sqn', 0):.2f}** |")
    lines.append(f"| Total PnL | {sr.get('total_pnl', 0):.1f}% |")
    lines.append(f"| Mean PnL / Trade | {sr.get('mean_pnl', 0):.3f}% |")
    lines.append(f"| Std PnL | {sr.get('std_pnl', 0):.3f}% |")
    lines.append(f"| Gross Profit | {sr.get('gross_profit', 0):.1f}% |")
    lines.append(f"| Gross Loss | {sr.get('gross_loss', 0):.1f}% |")
    lines.append("")

    # ── Permutation Test ──
    if permutation:
        lines.append("## 2. Permutation Test (Sign Randomization)")
        lines.append("")
        lines.append(f"**H₀:** Entry timing has no edge — trade signs are random coin flips.")
        lines.append(f"**H₁:** CVD-accel entries produce systematically positive trades.")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Real Aggregate PnL | {permutation['real_total_pnl']:.1f}% |")
        lines.append(f"| Shuffled Mean | {permutation['shuffled_mean']:.1f}% |")
        lines.append(f"| Shuffled Std | {permutation['shuffled_std']:.1f}% |")
        lines.append(f"| Shuffled 5th pctl | {permutation['shuffled_p5']:.1f}% |")
        lines.append(f"| Shuffled 95th pctl | {permutation['shuffled_p95']:.1f}% |")
        lines.append(f"| **p-value** | **{permutation['p_value']:.4f}** |")
        sig = "YES ✓" if permutation["significant_at_005"] else "NO ✗"
        lines.append(f"| Significant (α=0.05) | {sig} |")
        sig01 = "YES ✓" if permutation["significant_at_001"] else "NO ✗"
        lines.append(f"| Significant (α=0.01) | {sig01} |")
        lines.append(f"| N Permutations | {permutation['n_permutations']} |")
        lines.append("")

        if permutation["significant_at_005"]:
            lines.append("> **CONCLUSION:** The CVD-acceleration entry signal produces")
            lines.append(f"> statistically significant positive PnL (p={permutation['p_value']:.4f}).")
            lines.append("> The edge is NOT due to random chance.")
        else:
            lines.append("> **CAUTION:** The permutation test failed to reject H₀.")
            lines.append("> The observed PnL may be consistent with random entry timing.")
        lines.append("")

        lines.append("![Permutation Distribution](permutation_distribution.png)")
        lines.append("")

    # ── Excursion Profile ──
    lines.append("## 3. Excursion Profile")
    lines.append("")
    lines.append("| Metric | Value | Target |")
    lines.append("|--------|-------|--------|")
    lines.append(f"| Avg MFE | {ep.get('avg_mfe', 0):.2f}% | > 1% |")
    lines.append(f"| Avg MAE | {ep.get('avg_mae', 0):.2f}% | > -2% |")
    lines.append(f"| Median MFE | {ep.get('median_mfe', 0):.2f}% | |")
    lines.append(f"| Median MAE | {ep.get('median_mae', 0):.2f}% | |")
    lines.append(f"| P90 MFE | {ep.get('p90_mfe', 0):.2f}% | |")
    lines.append(f"| P10 MAE | {ep.get('p10_mae', 0):.2f}% | |")
    mae_mfe = ep.get("mae_mfe_ratio", 0)
    target_met = "✓" if mae_mfe < 0.5 else "✗"
    lines.append(f"| **MAE/MFE Ratio** | **{mae_mfe:.3f}** | < 0.5 {target_met} |")
    rf = ep.get("recovery_factor", 0)
    lines.append(f"| **Recovery Factor** | **{rf:.1%}** | > 50% |")
    lines.append(f"| Deep MAE Trades (>1%) | {ep.get('n_deep_mae', 0)} | |")
    lines.append(f"| Recovered | {ep.get('n_recovered', 0)} | |")
    lines.append("")

    # ── Efficiency Metrics ──
    lines.append("## 4. Time & Profit Efficiency")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Avg TTP (seconds) | {em.get('avg_ttp_sec', 0):.1f}s |")
    lines.append(f"| Median TTP | {em.get('median_ttp_sec', 0):.1f}s |")
    lines.append(f"| Avg Hold Time | {em.get('avg_hold_sec', 0):.1f}s |")
    lines.append(f"| Median Hold Time | {em.get('median_hold_sec', 0):.1f}s |")
    lines.append(f"| Avg Profit Velocity | {em.get('avg_profit_velocity', 0):.4f} %/s |")
    lines.append(f"| Capital Cloggers (>120s, <0.5%) | {em.get('n_capital_cloggers', 0)} ({em.get('capital_clogger_pct', 0):.1f}%) |")
    lines.append("")

    # ── Duration Heatmap ──
    lines.append("## 5. Duration Heatmap")
    lines.append("")
    if dur:
        lines.append("| Bucket | Trades | Win Rate | Avg PnL | Avg MFE | Avg MAE | Total PnL |")
        lines.append("|--------|--------|----------|---------|---------|---------|-----------|")
        for d in dur:
            lines.append(
                f"| {d['duration_bucket']} | {d['n_trades']} | "
                f"{d['win_rate_pct']:.0f}% | {d['avg_pnl']:.2f}% | "
                f"{d['avg_mfe']:.2f}% | {d['avg_mae']:.2f}% | "
                f"{d['total_pnl']:.1f}% |"
            )
        lines.append("")
        lines.append("![Duration Heatmap](duration_heatmap.png)")
        lines.append("")
    else:
        lines.append("*No duration data available.*")
        lines.append("")

    # ── Archetype Breakdown ──
    lines.append("## 6. Archetype Breakdown")
    lines.append("")
    if arch:
        lines.append("| Archetype | Events/Trades | Avg PnL | Win Rate | Total PnL | Avg Hold |")
        lines.append("|-----------|-------------|---------|----------|-----------|----------|")
        for a in arch:
            lines.append(
                f"| {a['archetype']} | {a['n_trades']} | "
                f"{a['avg_pnl']:.2f}% | {a['win_rate_pct']:.0f}% | "
                f"{a['total_pnl']:.1f}% | {a['avg_hold_sec']:.0f}s |"
            )
        lines.append("")

    # ── Failure Analysis ──
    lines.append("## 7. Top 10 Stop-Out Failures")
    lines.append("")
    if fails:
        lines.append(
            "| Event | Entry | Exit | PnL | MAE | MFE | "
            "Hold | α Entry | α Exit | CVD σ | Decay% |"
        )
        lines.append("|" + "---|" * 11)
        for f in fails:
            lines.append(
                f"| {f.get('event', '')} | {f.get('entry_type', '')} | "
                f"{f.get('exit_trigger', '')} | {f.get('pnl_pct', 0):.2f}% | "
                f"{f.get('mae_pct', 0):.2f}% | {f.get('mfe_pct', 0):.2f}% | "
                f"{f.get('elapsed_sec', 0):.0f}s | {f.get('alpha_at_entry', 0):.2f} | "
                f"{f.get('alpha_at_exit', 0):.2f} | {f.get('cvd_vel_sigma', 0):.1f}σ | "
                f"{f.get('decay_pct', 0):.0f}% |"
            )
        lines.append("")
    else:
        lines.append("*No failure data available.*")
        lines.append("")

    # ── Errors ──
    if errors:
        lines.append("## 8. Event Errors")
        lines.append("")
        lines.append(f"**{len(errors)}** events failed during processing:")
        lines.append("")
        # Show first 20 errors max
        for e in errors[:20]:
            lines.append(f"- `{e['event']}`: {e.get('error', 'Unknown error')}")
        if len(errors) > 20:
            lines.append(f"- ... and {len(errors) - 20} more")
        lines.append("")

    # ── Footer ──
    lines.append("---")
    lines.append(f"*Report generated by `tools/stat_validator.py` on {datetime.now().isoformat()}*")

    report_path = val_dir / "validation_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Report saved: %s", report_path)
    return report_path


# ━━━━━━━━━━━━━━━━━━━ Parallel → Summary Bridge ━━━━━━━━━━


def _load_summaries_from_batch(batch_dir: Path) -> Tuple[List[dict], List[dict]]:
    """
    Load full summary.json dicts from a parallel batch's individual run_dirs.
    Returns (summaries, errors) matching the old sequential interface.
    """
    summaries: List[dict] = []
    errors: List[dict] = []

    # Read the final batch results file
    final_path = None
    for f in sorted(batch_dir.glob("batch_results_*.json")):
        final_path = f

    if final_path is None:
        log.warning("No batch_results file found in %s", batch_dir)
        return summaries, errors

    batch_data = json.loads(final_path.read_text())
    results = batch_data.get("results", [])

    for r in results:
        if r.get("status") == "ERROR":
            errors.append({"event": r.get("event", ""), "error": r.get("error", "")})
            continue

        run_dir = r.get("run_dir", "")
        if not run_dir:
            continue

        summary_path = Path(run_dir) / "summary.json"
        if summary_path.exists():
            try:
                summary = json.loads(summary_path.read_text())
                summaries.append(summary)
            except Exception as exc:
                errors.append({"event": r.get("event", ""), "error": f"JSON parse: {exc}"})
        else:
            errors.append({"event": r.get("event", ""), "error": "No summary.json"})

    return summaries, errors


# ━━━━━━━━━━━━━━━━━━━ Main Orchestrator ━━━━━━━━━━━━━━━━━━━

def run_validation(
    n_events: int = 2000,
    n_permutations: int = 100,
    min_magnitude: float = 30.0,
    skip_permutation: bool = False,
    config_overrides: Optional[dict] = None,
    resume_dir: Optional[str] = None,
    seed: int = 42,
    n_workers: Optional[int] = None,
) -> Path:
    """
    Full statistical validation pipeline (v5 — parallel).

    Returns path to the validation directory.
    """
    t_start = time.time()

    # ── Directory ──
    if resume_dir:
        val_dir = Path(resume_dir)
        assert val_dir.exists(), f"Resume dir not found: {val_dir}"
        log.info("Resuming validation from %s", val_dir)
    else:
        val_dir = _make_validation_dir()
    log.info("Validation dir: %s", val_dir)

    # ── Phase 1: Sample events ──
    event_list_path = val_dir / "event_list.json"
    if event_list_path.exists():
        event_names = json.loads(event_list_path.read_text())
        log.info("Loaded %d events from existing event_list.json", len(event_names))
    else:
        if n_events <= 0:
            # Use ALL events
            event_names = list_events(DATA_PATH, min_magnitude=min_magnitude)
            log.info("Using ALL %d events (min_mag=%.0f)", len(event_names), min_magnitude)
        else:
            event_names = sample_events(n=n_events, min_magnitude=min_magnitude, seed=seed)
        _save_json(event_names, event_list_path)

    # ── Phase 2a: Run real strategy (PARALLEL via ProcessPoolExecutor) ──
    log.info("=" * 60)
    log.info("PHASE 2a: Running v5 strategy on %d events (PARALLEL)", len(event_names))
    log.info("=" * 60)

    batch_dir = run_parallel_batch(
        event_names=event_names,
        n_workers=n_workers,
        config_overrides=config_overrides,
        batch_dir=val_dir / "parallel_batch",
    )

    # Load summaries from the parallel batch run_dirs
    summaries, errors = _load_summaries_from_batch(batch_dir)
    log.info("Loaded %d summaries, %d errors from parallel batch", len(summaries), len(errors))

    # Save raw summaries (without full trades — too large for a single JSON)
    compact_summaries = []
    for s in summaries:
        compact_summaries.append({
            "event": s.get("event", ""),
            "entries": s.get("entries", 0),
            "total_pnl_pct": s.get("total_pnl_pct", 0),
            "win_rate_pct": s.get("win_rate_pct", 0),
            "avg_pnl_pct": s.get("avg_pnl_pct", 0),
            "archetype": s.get("archetype", {}),
            "diagnostics": s.get("diagnostics", {}),
            "run_dir": s.get("run_dir", ""),
        })
    _save_json({
        "n_events": len(event_names),
        "n_completed": len(summaries),
        "n_errors": len(errors),
        "results": compact_summaries,
        "errors": errors,
    }, val_dir / "real_results.json")

    # ── Phase 2b: Permutation test ──
    permutation_result = None
    if not skip_permutation and summaries:
        log.info("=" * 60)
        log.info("PHASE 2b: Permutation test (%d permutations)", n_permutations)
        log.info("=" * 60)

        permutation_result = run_permutation_test(
            summaries, n_permutations=n_permutations, seed=seed + 1,
        )
        _save_json(permutation_result, val_dir / "permutation_test.json")

        # Plot
        _generate_distribution_plot(
            permutation_result["real_total_pnl"],
            permutation_result["shuffled_distribution"],
            val_dir,
        )

    # ── Phase 3: Deep excursion analysis ──
    log.info("=" * 60)
    log.info("PHASE 3: Deep excursion analysis via Polars")
    log.info("=" * 60)

    # Build the master trade frame from summaries
    trade_df = build_trade_frame(summaries)

    # Enrich with excursion data from CSVs
    exc_rows = _collect_excursion_rows(summaries)
    if exc_rows:
        trade_df = enrich_with_excursions(trade_df, exc_rows)

    if not trade_df.is_empty():
        analysis = full_analysis(trade_df)
        _save_json(analysis, val_dir / "deep_analysis.json")

        # Save trade-level Polars frame as parquet for future analysis
        trade_df.write_parquet(val_dir / "all_trades.parquet")
        log.info("Trade frame: %d trades from %d events", trade_df.height, len(summaries))
    else:
        analysis = {}
        log.warning("No trades — skipping deep analysis")

    # Duration heatmap plot
    _generate_duration_heatmap_plot(
        analysis.get("duration_heatmap", []), val_dir,
    )

    # ── Phase 4: Generate report ──
    elapsed = time.time() - t_start
    report_path = generate_report(
        val_dir, event_names, summaries, errors,
        analysis, permutation_result, elapsed,
    )

    # Final summary
    sr = analysis.get("statistical_robustness", {})
    log.info("=" * 60)
    log.info("VALIDATION COMPLETE")
    log.info("  Events:       %d completed, %d failed", len(summaries), len(errors))
    log.info("  Total Trades: %d", sr.get("n_trades", 0))
    log.info("  Win Rate:     %.1f%%", sr.get("win_rate_pct", 0))
    log.info("  Expectancy:   %.4f%%", sr.get("expectancy", 0))
    log.info("  Profit Factor:%.2f", sr.get("profit_factor", 0))
    log.info("  SQN:          %.2f", sr.get("sqn", 0))
    if permutation_result:
        log.info("  p-value:      %.4f %s",
                 permutation_result["p_value"],
                 "✓" if permutation_result["significant_at_005"] else "✗")
    log.info("  Runtime:      %.1f min", elapsed / 60)
    log.info("  Report:       %s", report_path)
    log.info("=" * 60)

    return val_dir


# ━━━━━━━━━━━━━━━━━━━ CLI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    parser = argparse.ArgumentParser(
        description="AlphaMomentumHawkes v5 — Statistical Validator (Parallel)"
    )
    parser.add_argument(
        "--n-events", type=int, default=0,
        help="Number of events to sample (0 = ALL events, default: 0)",
    )
    parser.add_argument(
        "--n-permutations", type=int, default=100,
        help="Number of permutation shuffles (default: 100)",
    )
    parser.add_argument(
        "--min-magnitude", type=float, default=30.0,
        help="Min magnitude for event sampling (default: 30.0)",
    )
    parser.add_argument(
        "--skip-permutation", action="store_true",
        help="Skip the permutation test",
    )
    parser.add_argument(
        "--workers", type=int, default=None,
        help="Number of parallel workers (default: auto)",
    )
    parser.add_argument(
        "--resume", type=str, default=None,
        help="Path to validation dir to resume from checkpoint",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42)",
    )
    args = parser.parse_args()

    run_validation(
        n_events=args.n_events,
        n_permutations=args.n_permutations,
        min_magnitude=args.min_magnitude,
        skip_permutation=args.skip_permutation,
        resume_dir=args.resume,
        seed=args.seed,
        n_workers=args.workers,
    )


if __name__ == "__main__":
    main()
