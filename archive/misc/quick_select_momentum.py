"""
Quick High-Momentum Event Selection (Folder Name Heuristic)
============================================================

Uses folder naming pattern (SYMBOL_DATE_NUMBER) where NUMBER appears to
correlate with event magnitude/momentum. Selects top N by this metric.

Much faster than computing momentum from raw data.
"""
from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path
from typing import List, Tuple

log = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "filtered"


def parse_folder_magnitude(folder_name: str) -> float:
    """
    Extract magnitude from folder name like 'AACG_2021-02-04_1352.21'
    Returns the trailing number (1352.21).
    """
    match = re.search(r'_([0-9]+\.[0-9]+)$', folder_name)
    if match:
        return float(match.group(1))
    return 0.0


def select_high_magnitude_events(
    data_path: Path = DATA_PATH,
    min_magnitude: float = 150.0,
    max_events: int = 50,
) -> List[str]:
    """
    Quick selection based on folder name magnitude (heuristic for momentum).
    """
    all_dirs = [
        d for d in data_path.iterdir()
        if d.is_dir() and (d / "trades.parquet").exists()
    ]
    
    log.info("Scanning %d event folders by magnitude heuristic...", len(all_dirs))
    
    # Parse magnitudes
    events_with_mag: List[Tuple[str, float]] = []
    for d in all_dirs:
        mag = parse_folder_magnitude(d.name)
        if mag >= min_magnitude:
            events_with_mag.append((d.name, mag))
    
    # Sort by magnitude descending
    events_with_mag.sort(key=lambda x: x[1], reverse=True)
    
    # Take top N
    selected = events_with_mag[:max_events]
    
    log.info("Found %d events with magnitude >%.1f", len(events_with_mag), min_magnitude)
    
    if selected:
        log.info("Top 10:")
        for name, mag in selected[:10]:
            log.info("  %s: %.2f", name, mag)
    
    return [name for name, _ in selected]


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
    )
    
    parser = argparse.ArgumentParser(
        description="Quick high-momentum event selection (folder name heuristic)"
    )
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument("--min-magnitude", type=float, default=150.0)
    parser.add_argument("--max-events", type=int, default=50)
    parser.add_argument("--output", default="high_momentum_events.txt")
    
    args = parser.parse_args()
    
    selected = select_high_magnitude_events(
        data_path=Path(args.data),
        min_magnitude=args.min_magnitude,
        max_events=args.max_events,
    )
    
    output_path = Path(args.output)
    output_path.write_text("\n".join(selected))
    
    print(f"\n{'='*60}")
    print(f"Selected {len(selected)} events (magnitude >={args.min_magnitude})")
    print(f"Output: {output_path}")
    print(f"{'='*60}\n")
    
    if selected:
        print("Event list:")
        for i, name in enumerate(selected[:10], 1):
            print(f"  {i:2d}. {name}")
        if len(selected) > 10:
            print(f"  ... ({len(selected) - 10} more)")
        
        print(f"\nTo run batch validation:")
        print(f"  python -m strategies.bivariate_momentum_hawkes.archetype_backtest_runner batch \\")
        print(f"    --library strategies/bivariate_momentum_hawkes/archetype_library.json \\")
        print(f"    --events @{output_path.name}")


if __name__ == "__main__":
    main()
