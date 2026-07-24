"""
Phase 6c A7.1 chart 04 - raw per-event evidence suite. 7 residuals + 2
controls (AMCX, AMC - primary-cohort, band-passing, highest T+0 RTH bar
count, tiebroken by smallest rel_diff). Reads filtered_trades_dev_v4
directly (dev-tier, 9 specific event keys - not a full-table pass) plus
event_minute_bars_dev_v2 and momentum_events. No reclassification, no
writes to phase_6b.

Every print, no downsampling (WebGL scattergl). Spine values shown as
labeled diagnostic reference lines only (defect-#4 standing rule) -
raw stored values always; for ACET/NUKK additionally divided by their
geometric-mean factor sqrt(r1'*r2') so a factor-scaled line is visible
alongside the raw one.
"""
import json
import os

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_6b.build_minute_bars_v2 import build_session_spine_v2

PHASE_6B_CONFIG = "config/phase_6b.json"
A61_ARTIFACT = "results/phase_6b/artifacts/a61_basis_confirmation_rerun.json"
T2_ARTIFACT = "results/phase_6c/artifacts/t2_residual_classification.json"
DB_PATH = "data/duckdb/main.duckdb"
DEV_BARS_TABLE = "event_minute_bars_dev_v2"
DEV_TRADES_TABLE = "filtered_trades_dev_v4"
OUT_DIR = "results/phase_6c/charts/residual_raw"
OUT_SUMMARY = "results/phase_6c/artifacts/a71_chart04_summary.json"

RESIDUALS = ["SCLX", "VEEE", "NEPH", "ZENA", "ACET", "NUKK", "PSIX"]
CONTROLS = ["AMCX", "AMC"]
FACTOR_SCALED_TICKERS = ["ACET", "NUKK"]
SIZE_MAX_TRADE = 200000  # escalation ceiling, checked per-file after render


def main():
    with open(PHASE_6B_CONFIG) as f:
        cfg = json.load(f)
    with open(A61_ARTIFACT) as f:
        a61 = json.load(f)
    with open(T2_ARTIFACT) as f:
        t2 = json.load(f)

    full = pd.DataFrame(a61["full_table"])
    full["event_date_canonical"] = pd.to_datetime(full["event_date_canonical"])
    class_by_ticker = {c["ticker"]: c["classification"] for c in t2["classifications"]}
    factor_by_ticker = {c["ticker"]: np.sqrt(c["r1p"] * c["r2p"]) for c in t2["classifications"]}

    targets = RESIDUALS + CONTROLS
    events = full[full["ticker"].isin(targets)][["ticker", "event_date_canonical", "momentum_pct", "dev_cohort"]].copy()

    os.makedirs(OUT_DIR, exist_ok=True)

    con = duckdb.connect(DB_PATH, read_only=True)
    con.execute("INSTALL icu"); con.execute("LOAD icu")

    spine_prices = con.execute("""
        SELECT ticker, COALESCE(date, event_date) AS event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp,
               prev_close, high, open, close, event_high, event_open, event_close, event_volume
        FROM momentum_events
    """).fetchdf()
    spine_prices["event_date_canonical"] = pd.to_datetime(spine_prices["event_date_canonical"])

    spine = build_session_spine_v2(events, cfg)
    spine01 = spine[spine["session_offset"].isin([-1, 0])].copy()

    index_rows = []
    file_sizes = []

    for row in events.itertuples(index=False):
        ticker, d, mom = row.ticker, row.event_date_canonical, row.momentum_pct
        is_control = ticker in CONTROLS
        ev_spine = spine01[(spine01["ticker"] == ticker) & (spine01["event_date_canonical"] == d)]
        bars = con.execute(f"""
            SELECT session_offset, segment, minute_index, n_trades, volume, vwap, high, low, first_price, last_price
            FROM {DEV_BARS_TABLE}
            WHERE ticker=? AND event_date_canonical=? AND ROUND(momentum_pct,2)=ROUND(?,2) AND session_offset IN (-1,0)
            ORDER BY session_offset, minute_index
        """, [ticker, d.date(), mom]).fetchdf()

        # clock time per bar = premarket_start_et(offset) + minute_index minutes
        pm_start = ev_spine.set_index("session_offset")["premarket_start_et"]
        bars["clock_time"] = bars.apply(lambda r: pm_start[r["session_offset"]] + pd.Timedelta(minutes=r["minute_index"]), axis=1)

        trades = con.execute(f"""
            SELECT ticker, sip_timestamp, price, size,
                   TO_TIMESTAMP(sip_timestamp/1e9) AT TIME ZONE 'America/New_York' AS et_ts
            FROM {DEV_TRADES_TABLE}
            WHERE ticker=? AND ROUND(momentum_pct,2)=ROUND(?,2)
              AND CAST(TO_TIMESTAMP(sip_timestamp/1e9) AT TIME ZONE 'America/New_York' AS DATE) IN (
                  SELECT session_date FROM (VALUES {','.join(f"(DATE '{r.session_date}')" for r in ev_spine.itertuples())}) v(session_date)
              )
        """, [ticker, mom]).fetchdf()
        ev_spine_small = ev_spine[["session_date", "premarket_start_et", "rth_open_et", "rth_close_et", "post_end_et"]].copy()
        trades["et_date"] = trades["et_ts"].dt.date
        trades = trades.merge(ev_spine_small, left_on="et_date", right_on="session_date", how="inner")
        trades["segment"] = np.select(
            [trades["et_ts"] < trades["rth_open_et"], trades["et_ts"] < trades["rth_close_et"]],
            ["premarket", "rth"], default="post")
        trades = trades[(trades["et_ts"] >= trades["premarket_start_et"]) & (trades["et_ts"] < trades["post_end_et"])]

        sp = spine_prices[(spine_prices["ticker"] == ticker) & (spine_prices["event_date_canonical"] == d) &
                           (abs(spine_prices["mom_2dp"] - mom) < 1e-6)]
        sp_row = sp.iloc[0] if len(sp) else None
        spine_high = sp_row["high"] if sp_row is not None and pd.notna(sp_row["high"]) else (sp_row["event_high"] if sp_row is not None else None)
        spine_open = sp_row["open"] if sp_row is not None and pd.notna(sp_row["open"]) else (sp_row["event_open"] if sp_row is not None else None)
        spine_close = sp_row["close"] if sp_row is not None and pd.notna(sp_row["close"]) else (sp_row["event_close"] if sp_row is not None else None)
        spine_prev_close = sp_row["prev_close"] if sp_row is not None else None
        event_volume = sp_row["event_volume"] if sp_row is not None else None

        t0_date = ev_spine[ev_spine["session_offset"] == 0]["session_date"].iloc[0] if (ev_spine["session_offset"] == 0).any() else None
        t0_volume_ours = int(trades[trades["et_date"] == t0_date]["size"].sum()) if t0_date is not None else None
        volume_ratio = (t0_volume_ours / event_volume) if (event_volume and t0_volume_ours is not None and event_volume > 0) else None

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.3, 0.2], vertical_spacing=0.03,
                             subplot_titles=("1-min candlesticks (dev v2 bars)", "raw trade scatter - every print", "per-minute volume"))

        for off in (-1, 0):
            b = bars[bars["session_offset"] == off]
            if len(b) == 0:
                continue
            fig.add_trace(go.Candlestick(x=b["clock_time"], open=b["first_price"], high=b["high"], low=b["low"], close=b["last_price"],
                                          name=f"T{off:+d}" if off != 0 else "T+0", showlegend=False), row=1, col=1)
            fig.add_trace(go.Bar(x=b["clock_time"], y=b["volume"], marker_color="rgb(100,100,150)", showlegend=False), row=3, col=1)

        for seg, color in [("premarket", "rgb(255,165,0)"), ("rth", "rgb(31,119,180)"), ("post", "rgb(150,0,150)")]:
            sub = trades[trades["segment"] == seg]
            if len(sub) == 0:
                continue
            fig.add_trace(go.Scattergl(x=sub["et_ts"], y=sub["price"], mode="markers",
                                        marker=dict(size=np.clip(np.sqrt(sub["size"]) / 3, 2, 14), color=color, opacity=0.5),
                                        name=seg, hovertemplate="%{x}<br>price=%{y}"), row=2, col=1)

        for off in (-1, 0):
            r = ev_spine[ev_spine["session_offset"] == off]
            if len(r) == 0:
                continue
            r = r.iloc[0]
            for rr in (1, 2):
                fig.add_vrect(x0=r["rth_open_et"], x1=r["rth_close_et"], fillcolor="rgba(31,119,180,0.06)", line_width=0, row=rr, col=1)
                fig.add_vline(x=r["rth_open_et"], line=dict(color="gray", dash="dot", width=1), row=rr, col=1)
                fig.add_vline(x=r["rth_close_et"], line=dict(color="gray", dash="dot", width=1), row=rr, col=1)

        ref_lines = [("prev_close", spine_prev_close, "black"), ("high", spine_high, "red"),
                     ("open", spine_open, "green"), ("close", spine_close, "purple")]
        for label, val, color in ref_lines:
            if val is None or pd.isna(val):
                continue
            fig.add_hline(y=val, line=dict(color=color, dash="dash", width=1),
                          annotation_text=f"spine {label}={val:.4g}", annotation_position="right",
                          annotation_font=dict(size=9), row=1, col=1)
            fig.add_hline(y=val, line=dict(color=color, dash="dash", width=1), row=2, col=1)
        if ticker in FACTOR_SCALED_TICKERS and ticker in factor_by_ticker:
            factor = factor_by_ticker[ticker]
            for label, val, color in ref_lines:
                if val is None or pd.isna(val) or factor in (0, None):
                    continue
                scaled = val / factor
                fig.add_hline(y=scaled, line=dict(color=color, dash="dot", width=1),
                              annotation_text=f"{label}/{factor:.2f}={scaled:.4g}", annotation_position="left",
                              annotation_font=dict(size=9), row=1, col=1)
                fig.add_hline(y=scaled, line=dict(color=color, dash="dot", width=1), row=2, col=1)

        # no-print minutes shaded in panel 1 - identify gaps
        for off in (-1, 0):
            b = bars[bars["session_offset"] == off].sort_values("minute_index")
            if len(b) < 2:
                continue
            mi = b["minute_index"].to_numpy()
            ct = b["clock_time"].to_numpy()
            gaps = np.where(np.diff(mi) > 1)[0]
            for gi in gaps:
                fig.add_vrect(x0=ct[gi], x1=ct[gi + 1], fillcolor="rgba(255,0,0,0.08)", line_width=0, row=1, col=1)

        is_ctrl_tag = " (CONTROL)" if is_control else ""
        cls_tag = class_by_ticker.get(ticker, "control" if is_control else "n/a")
        title = f"{ticker} {d.date()} mom={mom:.2f}{is_ctrl_tag} - T2 class: {cls_tag}"
        fig.update_layout(height=900, width=1400, title=title, xaxis3_title="ET clock time",
                           legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0.3),
                           annotations=list(fig.layout.annotations) + [dict(
                               text=f"T+0 our trade volume={t0_volume_ours:,} vs spine event_volume={event_volume}"
                                    + (f", ratio={volume_ratio:.3f}" if volume_ratio is not None else "") +
                                    f" | longest intra-RTH gap and bar-count evidence in t2_residual_classification.json",
                               xref="paper", yref="paper", x=0, y=-0.06, showarrow=False, font=dict(size=10, color="gray"))])
        x_lo = ev_spine["premarket_start_et"].min() - pd.Timedelta(minutes=15)
        x_hi = ev_spine["post_end_et"].max() + pd.Timedelta(minutes=15)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.update_xaxes(range=[x_lo, x_hi])

        out_path = f"{OUT_DIR}/{ticker}_{d.date()}.html"
        fig.write_html(out_path)
        if len(trades) <= 100000:
            fig.write_image(out_path.replace(".html", ".png"), scale=1.2)
        size_mb = os.path.getsize(out_path) / 1e6
        file_sizes.append({"ticker": ticker, "file": out_path, "size_mb": round(size_mb, 2), "n_trades": len(trades)})
        print(f"{ticker} {d.date()}: {out_path} ({size_mb:.1f} MB, {len(trades)} trades)")
        if size_mb > 150:
            raise SystemExit(f"*** ESCALATION: {out_path} is {size_mb:.1f}MB > 150MB cap - stopping per instruction, not thinning data ***")

        index_rows.append({
            "ticker": ticker, "event_date": str(d.date()), "momentum_pct": mom,
            "cohort": "control" if is_control else ("sidecar" if row.dev_cohort == "flagged_sidecar" else "primary"),
            "t2_class": cls_tag, "file": os.path.basename(out_path),
            "t0_volume_ours": t0_volume_ours, "spine_event_volume": event_volume, "volume_ratio": volume_ratio,
        })

    con.close()

    index_html = ["<!doctype html><html><head><meta charset='utf-8'><title>Phase 6c residual raw suite</title>",
                  "<style>body{font-family:sans-serif;margin:20px} table{border-collapse:collapse} td,th{padding:6px 12px;border-bottom:1px solid #ddd;text-align:left}</style>",
                  "</head><body><h2>Phase 6c A7.1 - raw evidence suite (7 residuals + 2 controls)</h2><table>",
                  "<tr><th>Ticker</th><th>Date</th><th>Cohort</th><th>T2 class</th><th>Volume check (ours/spine)</th><th>File</th></tr>"]
    for r in index_rows:
        vr = f"{r['t0_volume_ours']:,} / {r['spine_event_volume']} (ratio {r['volume_ratio']:.3f})" if r["volume_ratio"] is not None else "n/a"
        index_html.append(f"<tr><td>{r['ticker']}</td><td>{r['event_date']}</td><td>{r['cohort']}</td><td>{r['t2_class']}</td>"
                           f"<td>{vr}</td><td><a href='{r['file']}'>{r['file']}</a></td></tr>")
    index_html.append("</table></body></html>")
    with open(f"{OUT_DIR}/index.html", "w", encoding="utf-8") as f:
        f.write("\n".join(index_html))

    summary = {"phase": "6c", "task": "A7.1_chart04", "events": index_rows, "file_sizes": file_sizes,
               "source": "research/phase_6c/a71_chart_04_raw.py:main"}
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(index_rows, indent=2, default=str))


if __name__ == "__main__":
    main()
