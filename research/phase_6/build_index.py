"""
Phase 6 T4e - sortable full-population index. Per Agent_Prompt_Standard.md
SS7's index-file pattern (adapted for an analysis, not backtest, phase):
covers every T1-eligible event, no sampling - sampling only applies to the
Chart Contract's per-event overlay (chart 05), never to this index.
"""
import pandas as pd

EVENT_INDEX = "results/phase_6/artifacts/event_index.parquet"
OUT_HTML = "results/phase_6/charts/index.html"

COLUMNS = [
    ("ticker", "Ticker"), ("event_date_canonical", "Event date"), ("momentum_pct", "Momentum %"),
    ("decile", "Decile"), ("min_window_25pct_minutes", "Min window 25% (min)"),
    ("min_window_50pct_minutes", "Min window 50% (min)"), ("min_window_75pct_minutes", "Min window 75% (min)"),
    ("minutes_to_50pct", "Minutes to 50% move"), ("open_close_abs_move", "|open->close log move|"),
]

HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Phase 6 - event index</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; margin: 20px; color:#1a1a1a; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ padding: 4px 10px; text-align: right; border-bottom: 1px solid #ddd; }}
th:first-child, td:first-child {{ text-align: left; }}
th {{ position: sticky; top: 0; background: #f4f4f4; cursor: pointer; user-select: none; }}
th.sorted-asc::after {{ content: " \\2191"; }}
th.sorted-desc::after {{ content: " \\2193"; }}
tr:hover {{ background: #f0f6ff; }}
caption {{ text-align: left; caption-side: top; font-size: 14px; margin-bottom: 8px; color: #444; }}
</style></head>
<body>
<table id="idx">
<caption>Phase 6 - full-population event index (n={n}). Eligibility: all D1 events are T=0-trades-eligible (T1). Click a column header to sort.</caption>
<thead><tr>{header}</tr></thead>
<tbody>{rows}</tbody>
</table>
<script>
const table = document.getElementById('idx');
const getCellVal = (tr, idx) => tr.children[idx].getAttribute('data-v');
const comparer = (idx, asc) => (a, b) => {{
  const v1 = getCellVal(asc ? a : b, idx), v2 = getCellVal(asc ? b : a, idx);
  const n1 = parseFloat(v1), n2 = parseFloat(v2);
  if (!isNaN(n1) && !isNaN(n2)) return n1 - n2;
  return v1.toString().localeCompare(v2);
}};
document.querySelectorAll('th').forEach((th, idx) => {{
  th.addEventListener('click', () => {{
    const tbody = table.querySelector('tbody');
    const asc = !th.classList.contains('sorted-asc');
    document.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc','sorted-desc'));
    th.classList.add(asc ? 'sorted-asc' : 'sorted-desc');
    Array.from(tbody.querySelectorAll('tr')).sort(comparer(idx, asc)).forEach(tr => tbody.appendChild(tr));
  }});
}});
</script>
</body></html>
"""


def build():
    df = pd.read_parquet(EVENT_INDEX)
    header = "".join(f"<th>{label}</th>" for _, label in COLUMNS)

    row_parts = []
    for row in df.itertuples(index=False):
        cells = []
        for col, _ in COLUMNS:
            v = getattr(row, col)
            display = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else (f"{v:.4f}" if isinstance(v, float) else v)
            cells.append(f'<td data-v="{v}">{display}</td>')
        row_parts.append("<tr>" + "".join(cells) + "</tr>")

    html = HTML_TEMPLATE.format(n=len(df), header=header, rows="".join(row_parts))
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {OUT_HTML} ({len(df)} rows)")


if __name__ == "__main__":
    build()
