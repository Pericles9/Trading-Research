"""
Phase 1 T6 - build the three Chart Contract charts.
Plotly, standalone HTML, one file each, log axes, outliers shown (never
clipped), n annotated, distributions not just centers, caption states
sample/filters/config hash.
"""
import hashlib
import json

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import statsmodels.formula.api as smf

CONFIG_PATH = "config/phase_1.json"
DB_PATH = "data/duckdb/main.duckdb"
CHARTS_DIR = "results/phase_1/charts"

# Palette (validated: see references/palette.md, checks run via validate_palette.js)
BLUE = "#2a78d6"
GREEN = "#008300"
MAGENTA = "#e87ba4"
RED = "#e34948"
GRAY = "#898781"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

TEMPLATE_LAYOUT = dict(
    paper_bgcolor="#fcfcfb",
    plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=13),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor="#c3c2b7"),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor="#c3c2b7"),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=70, b=60, l=70, r=30),
)


def config_hash():
    with open(CONFIG_PATH, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def ecdf(values):
    v = np.sort(np.asarray(values, dtype=float))
    y = np.arange(1, len(v) + 1) / len(v)
    return v, y


def chart_01():
    con = duckdb.connect(database=DB_PATH, read_only=True)
    df = con.execute("SELECT momentum_pct, date IS NULL AS null_date FROM momentum_events").fetchdf()
    con.close()

    null_vals = df.loc[df["null_date"], "momentum_pct"].values
    dated_vals = df.loc[~df["null_date"], "momentum_pct"].values
    n_null, n_dated = len(null_vals), len(dated_vals)

    fig = go.Figure()
    fig = go.Figure(
        layout=dict(
            **TEMPLATE_LAYOUT,
            grid=dict(rows=2, columns=1, pattern="independent", roworder="top to bottom"),
            height=640,
            title=dict(
                text="Are NULL-date events a random draw from the dated events' momentum_pct distribution?",
                x=0.02, xanchor="left",
            ),
        )
    )

    for vals, name, color in [(dated_vals, f"dated (n={n_dated:,})", BLUE), (null_vals, f"NULL date (n={n_null:,})", GREEN)]:
        x, y = ecdf(vals)
        fig.add_trace(
            go.Scatter(
                x=x, y=y, mode="lines", name=name, line=dict(color=color, width=2),
                xaxis="x1", yaxis="y1",
            )
        )

    rng = np.random.default_rng(42)
    for vals, name, color, y0 in [(dated_vals, "dated", BLUE, 0.6), (null_vals, "NULL date", GREEN, 0.2)]:
        sample = vals if len(vals) <= 4000 else rng.choice(vals, 4000, replace=False)
        fig.add_trace(
            go.Scatter(
                x=sample, y=np.full(len(sample), y0) + rng.uniform(-0.15, 0.15, len(sample)),
                mode="markers", marker=dict(color=color, size=3, opacity=0.25),
                name=name, showlegend=False, xaxis="x2", yaxis="y2",
            )
        )

    fig.update_layout(
        xaxis=dict(type="log", title="momentum_pct (log)", domain=[0, 1], anchor="y1", matches="x2"),
        yaxis=dict(title="ECDF", domain=[0.42, 1], anchor="x1"),
        xaxis2=dict(type="log", title="momentum_pct (log) - strip (jittered, ≤4,000/group subsample)", domain=[0, 1], anchor="y2"),
        yaxis2=dict(domain=[0, 0.32], anchor="x2", showticklabels=False, range=[-0.3, 1.0]),
        annotations=[
            dict(
                text=(f"n_dated={n_dated:,}, n_null_date={n_null:,} | source: momentum_events | "
                      f"strip subsampled to ≤4,000/group, seed=42 | config_hash={config_hash()}"),
                xref="paper", yref="paper", x=0.02, y=-0.08, showarrow=False,
                font=dict(size=11, color=INK_SEC), xanchor="left",
            )
        ],
    )
    fig.write_html(f"{CHARTS_DIR}/01_momentum_pct_by_date_status.html", include_plotlyjs="inline")
    print("chart 01 written:", n_dated, n_null)


def chart_02():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    file1, file2 = cfg["candidate_scan_inputs"]

    df1 = pd.read_parquet(file1)
    if "volume" in df1.columns:
        df1 = df1.rename(columns={"volume": "event_volume"})
    df2 = pd.read_parquet(file2)
    full_df = pd.concat([df1, df2], ignore_index=True)

    calc_df = full_df.dropna(subset=["momentum_pct", "event_volume"])
    calc_df = calc_df[(calc_df["event_volume"] > 0) & (calc_df["momentum_pct"] > 0)].copy()
    calc_df["log_mom"] = np.log10(calc_df["momentum_pct"])
    calc_df["log_vol"] = np.log10(calc_df["event_volume"])

    upper_bound = calc_df["momentum_pct"].quantile(0.995)
    train_df = calc_df[calc_df["momentum_pct"] <= upper_bound]
    res = smf.quantreg("log_vol ~ log_mom", train_df).fit(q=0.05)

    calc_df["log_vol_threshold"] = res.predict(calc_df[["log_mom"]])
    calc_df["kept"] = calc_df["log_vol"] > calc_df["log_vol_threshold"]

    n_total = len(calc_df)
    cap = cfg["chart_subsample_cap"]
    rng = np.random.default_rng(cfg["seed"])
    if n_total > cap:
        idx = rng.choice(calc_df.index, cap, replace=False)
        plot_df = calc_df.loc[idx]
        subsample_note = f"seeded subsample {cap:,} of {n_total:,} (seed={cfg['seed']})"
    else:
        plot_df = calc_df
        subsample_note = f"all {n_total:,} rows shown (under the {cap:,} cap, no subsampling needed)"

    n_kept = int(calc_df["kept"].sum())

    fig = go.Figure(layout=dict(**TEMPLATE_LAYOUT, height=620, title=dict(
        text="Does the fitted q=0.05 boundary cleanly separate kept from dropped in the scan inputs?", x=0.02, xanchor="left")))

    dropped = plot_df[~plot_df["kept"]]
    kept = plot_df[plot_df["kept"]]
    fig.add_trace(go.Scattergl(
        x=dropped["momentum_pct"], y=dropped["event_volume"], mode="markers",
        marker=dict(color=GRAY, size=4, opacity=0.35), name=f"dropped (n={len(dropped):,} shown)",
    ))
    fig.add_trace(go.Scattergl(
        x=kept["momentum_pct"], y=kept["event_volume"], mode="markers",
        marker=dict(color=BLUE, size=4, opacity=0.45), name=f"kept (n={len(kept):,} shown / {n_kept:,} total)",
    ))

    line_mom = np.logspace(np.log10(calc_df["momentum_pct"].min()), np.log10(calc_df["momentum_pct"].max()), 200)
    line_log_vol = res.params["Intercept"] + res.params["log_mom"] * np.log10(line_mom)
    fig.add_trace(go.Scatter(
        x=line_mom, y=10 ** line_log_vol, mode="lines",
        line=dict(color=RED, width=2, dash="dash"), name="fitted q=0.05 boundary",
    ))

    fig.update_layout(
        xaxis=dict(type="log", title="momentum_pct (log) - regressor, T1b"),
        yaxis=dict(type="log", title="event_volume (log) - dependent variable, T1b"),
        annotations=[
            dict(
                text=(f"total cleaned rows n={n_total:,} | {subsample_note} | kept (full) n={n_kept:,} | "
                      f"source: {file1.split('/')[-1]} + {file2.split('/')[-1]} | config_hash={config_hash()} | "
                      f"note: axes are (momentum_pct, event_volume) per the actual fit direction in T1b "
                      f"(log_vol ~ log_mom) - the contract's 'y=momentum measure' is read as the fitted "
                      f"dependent variable, volume, not a second momentum axis"),
                xref="paper", yref="paper", x=0.02, y=-0.14, showarrow=False,
                font=dict(size=10.5, color=INK_SEC), xanchor="left",
            )
        ],
    )
    fig.write_html(f"{CHARTS_DIR}/02_q05_boundary.html", include_plotlyjs="inline")
    print("chart 02 written:", n_total, n_kept)


def chart_03():
    fi = pd.read_parquet("results/phase_0c/artifacts/folder_inventory.parquet")
    with open("results/phase_0c/artifacts/join_reconciliation_detail.json") as f:
        t2c = pd.DataFrame(json.load(f)["t2c_results"])
    merged = fi.rename(columns={"class": "files_class"}).merge(t2c, on="folder_name", how="inner")
    matched = merged[merged["class"] == "matched"]["momentum_str"].astype(float).values

    orph = pd.read_parquet("results/phase_1/artifacts/orphan_classification.parquet")
    false_orphan = orph.loc[orph["is_false_orphan_date_bug"], "momentum_pct_parsed"].values
    genuine_orphan = orph.loc[orph["is_genuine_orphan"], "momentum_pct_parsed"].values

    with open("results/phase_1/artifacts/orphan_summary.json") as f:
        orphan_summary = json.load(f)
    min_kept_mom = orphan_summary["momentum_only_test_all_orphans"]["min_kept_momentum_pct"]

    fig = go.Figure(layout=dict(**TEMPLATE_LAYOUT, height=600, title=dict(
        text="Do the 7,252 orphan folders look like the residue of an earlier, looser filter run?", x=0.02, xanchor="left")))

    for vals, name, color in [
        (matched, f"matched folders (n={len(matched):,})", BLUE),
        (false_orphan, f"'orphan' but actually in momentum_events - date bug (n={len(false_orphan):,})", GREEN),
        (genuine_orphan, f"genuine orphan (n={len(genuine_orphan):,})", MAGENTA),
    ]:
        x, y = ecdf(vals)
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name, line=dict(color=color, width=2)))

    fig.add_vline(
        x=min_kept_mom, line=dict(color=RED, width=2, dash="dash"),
        annotation_text=f"min kept momentum_pct = {min_kept_mom:g}", annotation_position="top right",
    )

    fig.update_layout(
        xaxis=dict(type="log", title="momentum_pct parsed from folder name (log)"),
        yaxis=dict(title="ECDF"),
        annotations=[
            dict(
                text=(f"n_matched={len(matched):,}, n_false_orphan(date-bug)={len(false_orphan):,}, "
                      f"n_genuine_orphan={len(genuine_orphan):,} | reference line = minimum momentum_pct "
                      f"among the 23,268 kept momentum_events rows | source: folder_inventory.parquet (0c), "
                      f"orphan_classification.parquet (T4) | config_hash={config_hash()}"),
                xref="paper", yref="paper", x=0.02, y=-0.12, showarrow=False,
                font=dict(size=10.5, color=INK_SEC), xanchor="left",
            )
        ],
    )
    fig.write_html(f"{CHARTS_DIR}/03_orphans_vs_boundary.html", include_plotlyjs="inline")
    print("chart 03 written:", len(matched), len(false_orphan), len(genuine_orphan))


if __name__ == "__main__":
    chart_01()
    chart_02()
    chart_03()
