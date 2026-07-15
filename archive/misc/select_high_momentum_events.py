"""
Select High-Momentum Events
============================

Scans filtered event folders and identifies events with momentum >150%,
then returns a list suitable for batch validation.

Momentum is calculated as: (high_price - open_price) / open_price * 100
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd

# ── Ensure project root is on sys.path ──
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from strategies.bivariate_momentum_hawkes.data_loader import load_and_classify

log = logging.getLogger(__name__)

DATA_PATH = _PROJECT_ROOT / "data" / "filtered"


def compute_event_momentum(event_dir: Path) -> Tuple[str, float, int]:
    """
    Compute momentum % for a single event.
    
    Returns (event_name, momentum_pct, n_trades)
    """
    try:
        merged, meta = load_and_classify(DATA_PATH, event_dir.name)
        if merged is None or len(merged) < 100:
            return (event_dir.name, 0.0, 0)
        
        prices = merged["price"].values
        open_price = float(prices[0])
        high_price = float(prices.max())
        
        if open_price <= 0:
            return (event_dir.name, 0.0, len(merged))
        
        momentum_pct = (high_price - open_price) / open_price * 100.0
        return (event_dir.name, momentum_pct, len(merged))
    
    except Exception as exc:
        log.warning("Error processing %s: %s", event_dir.name, exc)
        return (event_dir.name, 0.0, 0)


def select_high_momentum_events(
    data_path: Path = DATA_PATH,
    min_momentum_pct: float = 150.0,
    max_events: int = 50,
    min_trades: int = 500,
) -> List[str]:
    """
    Scan all events, compute momentum, return top N events above threshold.
    """
    all_dirs = sorted([
        d for d in data_path.iterdir()
        if d.is_dir() and (d / "trades.parquet").exists()
    ])
    
    log.info("Scanning %d event folders for momentum >%.1f%%...", len(all_dirs), min_momentum_pct)
    
    results: List[Tuple[str, float, int]] = []
    
    for idx, event_dir in enumerate(all_dirs):
        if (idx + 1) % 100 == 0:
            log.info("Processed %d / %d events", idx + 1, len(all_dirs))
        
        name, momentum, n_trades = compute_event_momentum(event_dir)
        
        if momentum >= min_momentum_pct and n_trades >= min_trades:
            results.append((name, momentum, n_trades))
    
    # Sort by momentum descending
    results.sort(key=lambda x: x[1], reverse=True)
    
    # Take top max_events
    selected = results[:max_events]
    
    log.info("Found %d events with momentum >%.1f%% (%.1f%% of total)",
             len(results), min_momentum_pct, len(results) / max(len(all_dirs), 1) * 100)
    
    if selected:
        log.info("Top 10 by momentum:")
        for name, mom, n in selected[:10]:
            log.info("  %s: %.1f%% (%d trades)", name, mom, n)
    
    return [name for name, _, _ in selected]


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
    )
    
    parser = argparse.ArgumentParser(
        description="Select high-momentum events for batch testing"
    )
    parser.add_argument(
        "--data", default=str(DATA_PATH), help="Path to filtered data"
    )
    parser.add_argument(
        "--min-momentum", type=float, default=150.0,
        help="Minimum momentum percentage"
    )
    parser.add_argument(
        "--max-events", type=int, default=50,
        help="Maximum number of events to select"
    )
    parser.add_argument(
        "--min-trades", type=int, default=500,
        help="Minimum trades per event"
    )
    parser.add_argument(
        "--output", default="high_momentum_events.txt",
        help="Output file (event names, one per line)"
    )
    
    args = parser.parse_args()
    
    selected = select_high_momentum_events(
        data_path=Path(args.data),
        min_momentum_pct=args.min_momentum,
        max_events=args.max_events,
        min_trades=args.min_trades,
    )
    
    # Save to file
    output_path = Path(args.output)
    output_path.write_text("\n".join(selected))
    
    print(f"\n{'='*60}")
    print(f"Selected {len(selected)} high-momentum events (>={args.min_momentum}%)")
    print(f"Output: {output_path}")
    print(f"{'='*60}\n")
    
    if selected:
        print("To run batch validation:")
        print(f"  python -m strategies.bivariate_momentum_hawkes.archetype_backtest_runner batch \\")
        print(f"    --library strategies/bivariate_momentum_hawkes/archetype_library.json \\")
        print(f"    --events $(<{output_path.name})")


if __name__ == "__main__":
    main()
