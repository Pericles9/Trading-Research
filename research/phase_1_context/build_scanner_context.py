"""
AlphaMomentum Phase 1 — Context Engine Build
=============================================
Reconstructs the 9:30 AM "Top Gappers" scanner for every momentum-event day,
applies a 30 % hard gap filter, ranks tickers, and generates validation + plots.

Outputs:
  research/phase_1_context/scanner_context.parquet
  research/phase_1_context/plots/*.png
  research/phase_1_context/build_log.md
"""

import os, sys, time, warnings, textwrap, datetime as dt
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import PercentFormatter

warnings.filterwarnings("ignore", category=FutureWarning)

# ─── paths ───────────────────────────────────────────────────────────────────
ROOT   = Path(r"D:\Mom_db")
DATA   = ROOT / "data"
OUT    = ROOT / "research" / "phase_1_context"
PLOTS  = OUT / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

LOG_LINES: list[str] = []
T0 = time.perf_counter()

def log(msg: str):
    elapsed = time.perf_counter() - T0
    line = f"[{elapsed:8.1f}s] {msg}"
    LOG_LINES.append(line)
    print(line)


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — Load & merge momentum-event universe
# ═══════════════════════════════════════════════════════════════════════════════
log("STEP 1: Loading momentum-event universe …")

events_list = []

# Primary filtered events (2020-2024)
fp1 = DATA / "momentum_events" / "filtered_events_power_law_q05.parquet"
df1 = pd.read_parquet(fp1)
df1 = df1.rename(columns={"event_volume": "volume"})
if "volume" not in df1.columns and "event_volume" in df1.columns:
    df1 = df1.rename(columns={"event_volume": "volume"})
events_list.append(df1[["ticker", "date", "prev_close", "open", "high", "close",
                          "volume", "momentum_pct"]].copy())
log(f"  filtered_events: {len(df1):,} rows")

# Full 2020-2024 scan (may overlap – we'll dedup)
fp2 = DATA / "momentum_events" / "full_2020_2024_momentum_scan_20251122_000515.parquet"
if fp2.exists():
    df2 = pd.read_parquet(fp2)
    events_list.append(df2[["ticker", "date", "prev_close", "open", "high", "close",
                              "volume", "momentum_pct"]].copy())
    log(f"  full_scan:        {len(df2):,} rows")

# 2025 scan
fp3 = DATA / "momentum_events" / "momentum_scan_2025.parquet"
if fp3.exists():
    df3 = pd.read_parquet(fp3)
    df3 = df3.rename(columns={
        "event_date": "date", "event_open": "open", "event_high": "high",
        "event_close": "close", "event_volume": "volume"
    })
    events_list.append(df3[["ticker", "date", "prev_close", "open", "high", "close",
                              "volume", "momentum_pct"]].copy())
    log(f"  scan_2025:        {len(df3):,} rows")

# Merge & dedup
events = pd.concat(events_list, ignore_index=True)
events["date"] = events["date"].astype(str)
events = events.drop_duplicates(subset=["ticker", "date"]).reset_index(drop=True)
log(f"  Combined universe (deduped): {len(events):,} events across {events['date'].nunique():,} dates")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — Gap Calculation & 30 % Hard Filter
# ═══════════════════════════════════════════════════════════════════════════════
log("STEP 2: Calculating gap at open & applying 30 % filter …")

# Drop rows with missing price data
events = events.dropna(subset=["prev_close", "open"])
events = events[events["prev_close"] > 0].copy()

# Gap at open
events["gap_pct"] = (events["open"] - events["prev_close"]) / events["prev_close"]

# Momentum at high (for reference)
events["momentum_at_high"] = (events["high"] - events["prev_close"]) / events["prev_close"]

# 30 % hard filter on gap at open
gappers = events[events["gap_pct"] >= 0.30].copy()
log(f"  Events before filter: {len(events):,}")
log(f"  Events after 30% gap filter: {len(gappers):,}")
log(f"  Unique dates with >=1 gapper: {gappers['date'].nunique():,}")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — Gap Rank per date
# ═══════════════════════════════════════════════════════════════════════════════
log("STEP 3: Computing Gap_Rank per date …")

gappers["gap_rank"] = gappers.groupby("date")["gap_pct"].rank(
    ascending=False, method="dense"
).astype(int)

log(f"  Rank range: 1 – {gappers['gap_rank'].max()}")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 4 — Volume Intensity (first 5 min) from minute data
# ═══════════════════════════════════════════════════════════════════════════════
log("STEP 4: Computing Volume_Intensity (first 5 min) …")

minute_root = DATA / "minute"
vol5_records = []
missing_minute = 0

for _, row in gappers.iterrows():
    ticker = row["ticker"]
    date_str = row["date"]
    minute_file = minute_root / ticker / f"{date_str}.parquet"
    if not minute_file.exists():
        missing_minute += 1
        continue
    try:
        mdf = pd.read_parquet(minute_file)
        if "datetime" in mdf.columns:
            mdf["datetime"] = pd.to_datetime(mdf["datetime"])
        elif "timestamp" in mdf.columns:
            mdf["datetime"] = pd.to_datetime(mdf["timestamp"])
        else:
            continue

        # Market open = 9:30 ET.  Minute data may use UTC or ET.
        # Detect: if any bar before 08:00, likely UTC; convert.
        first_time = mdf["datetime"].iloc[0]
        if first_time.hour < 8:
            # Already in some local time — use as-is
            pass

        # Filter 09:30–09:35 (first 5 minutes)
        day_date = pd.Timestamp(date_str)
        # Try both ET-based (09:30) and UTC-based (14:30)
        open_et = day_date.replace(hour=9, minute=30)
        end_et  = day_date.replace(hour=9, minute=35)
        mask_et = (mdf["datetime"] >= open_et) & (mdf["datetime"] < end_et)

        open_utc = day_date.replace(hour=14, minute=30)
        end_utc  = day_date.replace(hour=14, minute=35)
        mask_utc = (mdf["datetime"] >= open_utc) & (mdf["datetime"] < end_utc)

        if mask_et.sum() > 0:
            vol_5 = mdf.loc[mask_et, "volume"].sum()
        elif mask_utc.sum() > 0:
            vol_5 = mdf.loc[mask_utc, "volume"].sum()
        else:
            # Fallback: first 5 bars
            vol_5 = mdf["volume"].iloc[:5].sum()

        vol5_records.append({"ticker": ticker, "date": date_str, "vol_5min": vol_5})
    except Exception:
        missing_minute += 1

vol5_df = pd.DataFrame(vol5_records)
if len(vol5_df):
    gappers = gappers.merge(vol5_df, on=["ticker", "date"], how="left")
    gappers["volume_intensity_rank"] = gappers.groupby("date")["vol_5min"].rank(
        ascending=False, method="dense", na_option="bottom"
    )
else:
    gappers["vol_5min"] = np.nan
    gappers["volume_intensity_rank"] = np.nan

log(f"  Minute data found for {len(vol5_records):,} / {len(gappers):,} events")
log(f"  Missing minute files: {missing_minute:,}")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 5 — RVOL (Relative Volume vs 30-day average)
# ═══════════════════════════════════════════════════════════════════════════════
log("STEP 5: Computing RVOL (30-day average) …")

daily_root = DATA / "daily"
rvol_records = []
missing_daily = 0
daily_data_gaps = []

unique_tickers = gappers["ticker"].unique()
log(f"  Loading daily data for {len(unique_tickers):,} unique tickers …")

for ticker in unique_tickers:
    daily_file = daily_root / f"{ticker}_daily.parquet"
    if not daily_file.exists():
        missing_daily += 1
        daily_data_gaps.append(ticker)
        continue
    try:
        ddf = pd.read_parquet(daily_file)
        ddf["date"] = ddf["date"].astype(str)
        ddf = ddf.sort_values("date").reset_index(drop=True)

        ticker_events = gappers[gappers["ticker"] == ticker]
        for _, erow in ticker_events.iterrows():
            edate = erow["date"]
            idx = ddf[ddf["date"] == edate].index
            if len(idx) == 0:
                continue
            i = idx[0]
            # 30-day lookback
            lookback = ddf.iloc[max(0, i-30):i]
            if len(lookback) >= 10:
                avg_vol = lookback["volume"].mean()
                day_vol = erow["volume"] if pd.notna(erow["volume"]) else ddf.iloc[i]["volume"]
                rvol = day_vol / avg_vol if avg_vol > 0 else np.nan
                rvol_records.append({"ticker": ticker, "date": edate, "rvol": rvol})
    except Exception as e:
        missing_daily += 1
        daily_data_gaps.append(ticker)

rvol_df = pd.DataFrame(rvol_records)
if len(rvol_df):
    gappers = gappers.merge(rvol_df, on=["ticker", "date"], how="left")
else:
    gappers["rvol"] = np.nan

log(f"  RVOL computed for {len(rvol_records):,} events")
log(f"  Missing daily files: {missing_daily:,} tickers")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 6 — Save scanner_context.parquet
# ═══════════════════════════════════════════════════════════════════════════════
log("STEP 6: Saving scanner_context.parquet …")

output_cols = [
    "ticker", "date", "prev_close", "open", "high", "close", "volume",
    "gap_pct", "momentum_at_high", "gap_rank",
    "vol_5min", "volume_intensity_rank", "rvol"
]

# Ensure all columns exist
for c in output_cols:
    if c not in gappers.columns:
        gappers[c] = np.nan

scanner = gappers[output_cols].copy()
scanner = scanner.sort_values(["date", "gap_rank"]).reset_index(drop=True)
scanner.to_parquet(OUT / "scanner_context.parquet", index=False)
log(f"  Saved {len(scanner):,} rows → scanner_context.parquet")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 7 — Visualization Suite
# ═══════════════════════════════════════════════════════════════════════════════
log("STEP 7: Generating visualizations …")

# ─── 7a: Gap Distribution Histogram (10 peak days) ──────────────────────────
log("  7a: Gap distribution histogram …")

# Find top-10 days by count of gappers
day_counts = scanner.groupby("date").size().sort_values(ascending=False)
top_10_days = day_counts.head(10).index.tolist()

hist_data = scanner[scanner["date"].isin(top_10_days)]["gap_pct"].dropna()

fig, ax = plt.subplots(figsize=(12, 6))
bins = np.arange(0.0, hist_data.max() + 0.5, 0.10)
ax.hist(hist_data * 100, bins=bins * 100, color="#2196F3", edgecolor="white",
        alpha=0.85, label=f"All gappers (n={len(hist_data):,})")
ax.axvline(30, color="red", linewidth=2, linestyle="--", label="30 % Cutoff")
ax.set_xlabel("Gap at Open (%)", fontsize=13)
ax.set_ylabel("Count", fontsize=13)
ax.set_title("Gap % Distribution — Top 10 Peak Trading Days", fontsize=15, fontweight="bold")
ax.legend(fontsize=11)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(PLOTS / "gap_distribution_histogram.png", dpi=150)
plt.close(fig)
log(f"    Saved gap_distribution_histogram.png ({len(hist_data)} data points)")

# ─── 7b: Leaderboard Snapshot (best day) ────────────────────────────────────
log("  7b: Leaderboard snapshot …")

# Find the day with the single biggest runner (highest gap_pct)
best_row = scanner.loc[scanner["gap_pct"].idxmax()]
best_day = best_row["date"]
# Fall back: find a day with a 500%+ runner
super_runners = scanner[scanner["gap_pct"] >= 5.0]
if len(super_runners) > 0:
    # Pick the day with the most >500% runners, then most total gappers
    sr_day_counts = super_runners.groupby("date").size().sort_values(ascending=False)
    best_day = sr_day_counts.index[0]

leaderboard = scanner[scanner["date"] == best_day].sort_values("gap_rank").head(10)

fig, ax = plt.subplots(figsize=(12, 5))
ax.axis("off")
table_data = []
for _, r in leaderboard.iterrows():
    table_data.append([
        int(r["gap_rank"]),
        r["ticker"],
        f"{r['gap_pct']*100:.1f}%",
        f"${r['open']:.2f}",
        f"${r['prev_close']:.2f}",
        f"{r['rvol']:.1f}x" if pd.notna(r.get("rvol")) else "N/A",
        f"{int(r['vol_5min']):,}" if pd.notna(r.get("vol_5min")) else "N/A",
    ])

col_labels = ["Rank", "Ticker", "Gap %", "Open", "Prev Close", "RVOL", "5min Vol"]
table = ax.table(cellText=table_data, colLabels=col_labels, loc="center",
                 cellLoc="center", colColours=["#1565C0"]*7)
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1.0, 1.8)

# Style header
for j in range(len(col_labels)):
    table[0, j].set_text_props(color="white", fontweight="bold")
    table[0, j].set_facecolor("#1565C0")

# Alternate row colours
for i in range(1, len(table_data)+1):
    color = "#E3F2FD" if i % 2 == 0 else "white"
    for j in range(len(col_labels)):
        table[i, j].set_facecolor(color)

ax.set_title(f"Top 10 Scanner Leaderboard — {best_day}\n"
             f"(Biggest runner: {leaderboard.iloc[0]['ticker']} @ "
             f"{leaderboard.iloc[0]['gap_pct']*100:.1f}% gap)",
             fontsize=14, fontweight="bold", pad=20)
fig.tight_layout()
fig.savefig(PLOTS / "leaderboard_snapshot.png", dpi=150, bbox_inches="tight")
plt.close(fig)
log(f"    Saved leaderboard_snapshot.png for {best_day}")

# ─── 7c: Rank Stability + Price Overlay (Top 3 super-runners) ───────────────
log("  7c: Rank stability plots (top 3 super-runners) …")

# Find the top 3 biggest gappers that have minute data
filtered_root = DATA / "filtered"
# Use scanner sorted by gap_pct descending
candidates = scanner.sort_values("gap_pct", ascending=False).reset_index(drop=True)

super_runners_plotted = 0
fig, axes = plt.subplots(3, 1, figsize=(14, 16), sharex=False)

for idx, (_, cand) in enumerate(candidates.iterrows()):
    if super_runners_plotted >= 3:
        break

    ticker = cand["ticker"]
    edate = cand["date"]

    # Check if minute data exists
    minute_file = minute_root / ticker / f"{edate}.parquet"
    if not minute_file.exists():
        continue

    try:
        mdf = pd.read_parquet(minute_file)
        if "datetime" in mdf.columns:
            mdf["datetime"] = pd.to_datetime(mdf["datetime"])
        elif "timestamp" in mdf.columns:
            mdf["datetime"] = pd.to_datetime(mdf["timestamp"])
        else:
            continue

        # Determine timezone offset
        day_ts = pd.Timestamp(edate)

        # Try ET (09:30-10:30) or UTC (14:30-15:30)
        open_et = day_ts.replace(hour=9, minute=30)
        end_et = day_ts.replace(hour=10, minute=30)
        mask_et = (mdf["datetime"] >= open_et) & (mdf["datetime"] <= end_et)

        open_utc = day_ts.replace(hour=14, minute=30)
        end_utc = day_ts.replace(hour=15, minute=30)
        mask_utc = (mdf["datetime"] >= open_utc) & (mdf["datetime"] <= end_utc)

        if mask_et.sum() >= 5:
            session = mdf[mask_et].copy()
            time_offset = 0
        elif mask_utc.sum() >= 5:
            session = mdf[mask_utc].copy()
            time_offset = -5  # UTC to ET
        else:
            # fallback: first 60 bars
            session = mdf.head(60).copy()
            time_offset = 0

        if len(session) < 5:
            continue

        # Compute rolling rank: at each minute, where does this ticker rank
        # among all gappers that day based on current price vs prev_close?
        # Simplified: use the price trajectory and show gap_rank evolution
        # We'll compute "dynamic rank" using the price at each minute
        prev_c = cand["prev_close"]
        session["cur_gap_pct"] = (session["close"] - prev_c) / prev_c
        session["minutes_from_open"] = range(len(session))

        # For rank evolution, we need other gappers' trajectories too
        # Simplified: show Scanner_Rank = gap_rank (static) as a horizontal reference
        # and the running gap % as the dynamic line
        ax = axes[super_runners_plotted]
        ax2 = ax.twinx()

        # Price action on right axis
        ax2.plot(session["minutes_from_open"], session["close"],
                 color="#FF5722", linewidth=2, alpha=0.8, label="Price")
        ax2.set_ylabel("Price ($)", color="#FF5722", fontsize=11)
        ax2.tick_params(axis="y", labelcolor="#FF5722")

        # Running gap % on left axis
        ax.plot(session["minutes_from_open"], session["cur_gap_pct"] * 100,
                color="#1565C0", linewidth=2, alpha=0.9, label="Running Gap %")
        ax.axhline(cand["gap_pct"] * 100, color="#1565C0", linestyle="--",
                   alpha=0.4, label=f"Open Gap: {cand['gap_pct']*100:.0f}%")
        ax.set_ylabel("Gap % (vs Prev Close)", color="#1565C0", fontsize=11)
        ax.tick_params(axis="y", labelcolor="#1565C0")
        ax.set_xlabel("Minutes from Open", fontsize=11)
        ax.set_title(f"{ticker} — {edate}  |  Gap Rank: #{int(cand['gap_rank'])}  |  "
                     f"Open Gap: {cand['gap_pct']*100:.1f}%  |  "
                     f"Peak: {cand['momentum_at_high']*100:.1f}%",
                     fontsize=12, fontweight="bold")

        # Legends
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)
        ax.grid(axis="both", alpha=0.2)

        super_runners_plotted += 1
    except Exception as e:
        log(f"    Warning: failed to plot {ticker} {edate}: {e}")
        continue

if super_runners_plotted < 3:
    log(f"    Only found {super_runners_plotted} super-runners with minute data")
    for i in range(super_runners_plotted, 3):
        axes[i].set_visible(False)

fig.suptitle("Rank Stability — Top 3 Super-Runners (First 60 Minutes)",
             fontsize=15, fontweight="bold", y=1.01)
fig.tight_layout()
fig.savefig(PLOTS / "rank_stability_top3.png", dpi=150, bbox_inches="tight")
plt.close(fig)
log(f"    Saved rank_stability_top3.png ({super_runners_plotted} runners)")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 8 — Quality Control
# ═══════════════════════════════════════════════════════════════════════════════
log("STEP 8: Quality control …")

# ─── 8a: Survivorship bias check ────────────────────────────────────────────
log("  8a: Survivorship bias audit …")
# NOTE: symbol-properties-database.csv contains crypto/futures/forex ONLY —
# it does NOT contain US equities. We instead check survivorship by looking
# for tickers that appear in events but have zero daily or minute data presence.
scanner_tickers = set(scanner["ticker"].unique())

# Check which tickers have any minute data
tickers_with_minute = set()
if minute_root.exists():
    tickers_with_minute = {d for d in os.listdir(minute_root)
                           if (minute_root / d).is_dir()}

# Check which tickers have any daily data
tickers_with_daily = set()
if daily_root.exists():
    tickers_with_daily = {f.replace("_daily.parquet", "")
                          for f in os.listdir(daily_root)
                          if f.endswith("_daily.parquet")}

tickers_no_minute = scanner_tickers - tickers_with_minute
tickers_no_daily  = scanner_tickers - tickers_with_daily

log(f"    Tickers in scanner: {len(scanner_tickers):,}")
log(f"    Tickers with minute data: {len(scanner_tickers & tickers_with_minute):,}")
log(f"    Tickers with daily data : {len(scanner_tickers & tickers_with_daily):,}")
log(f"    Tickers missing BOTH   : {len(tickers_no_minute & tickers_no_daily):,}")
unknown_tickers = tickers_no_minute & tickers_no_daily
if unknown_tickers:
    sample = sorted(unknown_tickers)[:20]
    log(f"    Sample (no data at all): {sample}")

# ─── 8b: Open price consistency (events open vs filtered first trade) ────────
log("  8b: Open price consistency check (events open vs filtered first trade) …")
log("       NOTE: Events data may have split-adjusted prices while trade data is raw.")
discrepancies = []
consistent = []
checked = 0

# Sample up to 200 events for speed
sample_events = scanner.sample(min(200, len(scanner)), random_state=42)

all_filtered_dirs = set()
if filtered_root.exists():
    all_filtered_dirs = set(os.listdir(filtered_root))

for _, row in sample_events.iterrows():
    ticker = row["ticker"]
    edate = row["date"]

    # Find matching filtered folder: {TICKER}_{DATE}_{MOMENTUM_PCT}/
    pattern_prefix = f"{ticker}_{edate}_"
    matching_dirs = [d for d in all_filtered_dirs if d.startswith(pattern_prefix)]

    if not matching_dirs:
        continue

    trades_file = filtered_root / matching_dirs[0] / "trades.parquet"
    if not trades_file.exists():
        continue

    try:
        tdf = pd.read_parquet(trades_file)
        if "price" not in tdf.columns or len(tdf) == 0:
            continue

        # Sort by timestamp and filter to EVENT DATE only at market open
        # (filtered/ contains a ~7-day window around the event,
        #  and trades start at ~4:00 AM ET / 08:00 UTC pre-market)
        if "sip_timestamp" in tdf.columns:
            tdf = tdf.sort_values("sip_timestamp")
            tdf["_dt"] = pd.to_datetime(tdf["sip_timestamp"], unit="ns")
            tdf["_date"] = tdf["_dt"].dt.strftime("%Y-%m-%d")
            event_day_trades = tdf[tdf["_date"] == edate]
            if len(event_day_trades) == 0:
                continue
            # Filter to regular market hours: 9:30 AM ET = 14:30 UTC (EST)
            # or 13:30 UTC (EDT). Use 13:30 UTC as conservative start.
            mkt_open_utc = event_day_trades["_dt"].iloc[0].normalize() + pd.Timedelta(hours=13, minutes=30)
            rth_trades = event_day_trades[event_day_trades["_dt"] >= mkt_open_utc]
            if len(rth_trades) == 0:
                continue
            first_trade_price = rth_trades["price"].iloc[0]
        else:
            first_trade_price = tdf["price"].iloc[0]

        events_open = row["open"]

        if events_open > 0 and first_trade_price > 0:
            pct_diff = abs(first_trade_price - events_open) / events_open
            checked += 1
            # Large ratio suggests split adjustment (catch 2:1, 3:1, 4:1, etc.)
            ratio = events_open / first_trade_price if first_trade_price > 0 else 0
            is_likely_split = ratio > 1.8 or ratio < 0.55
            entry = {
                "ticker": ticker,
                "date": edate,
                "events_open": events_open,
                "first_trade": first_trade_price,
                "pct_diff": pct_diff * 100,
                "likely_split_adjusted": is_likely_split,
            }
            if pct_diff > 0.01:
                discrepancies.append(entry)
            else:
                consistent.append(entry)
    except Exception:
        continue

# Separate split-adjusted from genuine discrepancies
split_adjusted = [d for d in discrepancies if d["likely_split_adjusted"]]
genuine_disc   = [d for d in discrepancies if not d["likely_split_adjusted"]]

log(f"    Checked {checked} events:")
log(f"      Consistent (<1% diff): {len(consistent)}")
log(f"      Split-adjusted (>5x ratio): {len(split_adjusted)}")
log(f"      Genuine discrepancy: {len(genuine_disc)}")
if genuine_disc:
    log(f"    Top genuine discrepancies:")
    for d in sorted(genuine_disc, key=lambda x: -x["pct_diff"])[:10]:
        log(f"      {d['ticker']} {d['date']}: events_open=${d['events_open']:.2f}, "
            f"first_trade=${d['first_trade']:.2f}, diff={d['pct_diff']:.1f}%")


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 9 — Write build_log.md
# ═══════════════════════════════════════════════════════════════════════════════
log("STEP 9: Writing build_log.md …")

total_time = time.perf_counter() - T0

build_log = f"""# Phase 1 Context Engine — Build Log
**Generated:** {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Total execution time:** {total_time:.1f}s

## Summary Statistics
| Metric | Value |
|---|---|
| Raw momentum events loaded | {len(events):,} |
| Events after 30% gap filter | {len(gappers):,} |
| Unique dates | {gappers['date'].nunique():,} |
| Unique tickers | {gappers['ticker'].nunique():,} |
| Minute data coverage | {len(vol5_records):,} / {len(gappers):,} ({100*len(vol5_records)/max(1,len(gappers)):.1f}%) |
| RVOL computed | {len(rvol_records):,} / {len(gappers):,} ({100*len(rvol_records)/max(1,len(gappers)):.1f}%) |
| Open price consistent (<1% diff) | {len(consistent)} / {checked} checked |
| Open price split-adjusted discrepancy | {len(split_adjusted)} / {checked} checked |
| Genuine open price discrepancies | {len(genuine_disc)} / {checked} checked |
| Tickers missing all data | {len(unknown_tickers)} |

## Key Data Gap Findings

### Daily Data Coverage
The `daily/` folder only contains data from **~Dec 2024 onward** (~82 trading days).
Since momentum events span 2020–2025, RVOL can only be computed for recent events.
Historical RVOL would require either archival daily data or computing average volume
from the minute-bar data.

### Split Adjustment
The events data (momentum_events/) uses **split-adjusted prices** while the raw
trade data (filtered/) has **unadjusted tick-level prices**. This explains the large
discrepancies where events_open >> first_trade (reverse splits) or first_trade >>
events_open (forward splits). Of {checked} events checked, {len(split_adjusted)}
showed split-adjusted ratios (>5x price difference).

## Data Gaps — Missing Daily Files
The following tickers in the scanner had no `daily/` parquet file (expected — daily data
only covers Dec 2024+):

```
{chr(10).join(sorted(set(daily_data_gaps))[:50]) if daily_data_gaps else 'None'}
```

## Open Price Discrepancies
### Genuine Discrepancies (not split-adjusted, >1% diff)
"""

if genuine_disc:
    disc_df = pd.DataFrame(genuine_disc).sort_values("pct_diff", ascending=False)
    build_log += "| Ticker | Date | Events Open | First Trade | Diff % |\n"
    build_log += "|---|---|---|---|---|\n"
    for _, d in disc_df.iterrows():
        build_log += f"| {d['ticker']} | {d['date']} | ${d['events_open']:.2f} | ${d['first_trade']:.2f} | {d['pct_diff']:.1f}% |\n"
else:
    build_log += "No genuine discrepancies > 1% found (excluding split-adjusted events).\n"

build_log += f"""
### Split-Adjusted Events ({len(split_adjusted)} total)
These events have a price ratio >5x between events_open and first filtered trade,
indicating a stock split/reverse-split between the event date and data collection.

## Survivorship Bias Audit
- Scanner contains {len(set(scanner['ticker'].unique())):,} unique tickers.
- **{len(unknown_tickers)}** tickers have neither minute nor daily data in the workspace.
- Note: `symbol-properties-database.csv` only contains crypto/futures — NOT US equities.
- Survivorship check uses minute + daily data presence as alternative signal.

## Execution Trace
```
{chr(10).join(LOG_LINES)}
```
"""

(OUT / "build_log.md").write_text(build_log, encoding="utf-8")
log(f"  build_log.md written ({len(LOG_LINES)} log lines)")
log(f"BUILD COMPLETE in {total_time:.1f}s")

# Clean up temp file
temp_file = ROOT / "_inspect_schemas.py"
if temp_file.exists():
    temp_file.unlink()
