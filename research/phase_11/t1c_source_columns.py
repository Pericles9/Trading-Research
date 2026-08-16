"""Phase 11 T1c - the dropped columns, and whether they are usable.

Reads the source quotes.parquet for the 50 primary dev events READ-ONLY.
No re-ingest, no write to the data root, no change to src/ (escalation row 14).

T1c-v is the storage-order census and is the sole task exempt from escalation
row 19 (exempted by name in row 19a): measuring storage order necessarily
depends on storage order, and its output feeds nothing.

Outputs
  results/phase_11/artifacts/t1c_indicators.parquet
  results/phase_11/artifacts/t1c_conditions_codes.parquet
  results/phase_11/artifacts/t1c_conditions_combos.parquet
  results/phase_11/artifacts/t1c_by_day_offset.parquet
  results/phase_11/artifacts/t1c_storage_order.parquet
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import pandas as pd
from common import ARTIFACTS, connect, primary_events


def era_of(d) -> str:
    return "era_2020_2021" if pd.Timestamp(d).year <= 2021 else "era_2022_2024"


def main() -> None:
    con = connect()
    ev = primary_events(con)
    ev["era"] = ev["event_date"].map(era_of)
    files = {
        r.folder + "\\quotes.parquet": (r.ticker, r.event_date, r.era)
        for r in ev.itertuples()
    }
    meta = pd.DataFrame(
        [{"path": p, "ticker": t, "event_date": d, "era": e} for p, (t, d, e) in files.items()]
    )
    con.register("meta_df", meta)
    con.execute("CREATE TABLE meta AS SELECT * FROM meta_df")

    paths = "[" + ", ".join("'" + p.replace("\\", "/") + "'" for p in files) + "]"
    con.execute(
        f"""
        CREATE TABLE src AS
        SELECT
          m.ticker, m.event_date, m.era,
          s.conditions, s.indicators,
          s.sip_timestamp, s.participant_timestamp, s.sequence_number,
          s.file_row_number,
          (make_timestamp_ns(s.sip_timestamp) AT TIME ZONE 'UTC'
             AT TIME ZONE 'America/New_York')::DATE AS session_date
        FROM read_parquet({paths}, filename = true, file_row_number = true) s
        JOIN meta m ON replace(m.path, '\\', '/') = s.filename
        """
    )
    n = con.execute("SELECT COUNT(*) FROM src").fetchone()[0]
    print(f"source rows read: {n:,}")

    # Day offset relative to the event day, in trading-session terms within the file.
    con.execute(
        """
        CREATE TABLE src2 AS
        SELECT *, CASE WHEN session_date = event_date THEN 0
                       WHEN session_date <  event_date THEN -DENSE_RANK() OVER (
                            PARTITION BY ticker, event_date
                            ORDER BY CASE WHEN session_date < event_date
                                          THEN session_date END DESC)
                       ELSE DENSE_RANK() OVER (
                            PARTITION BY ticker, event_date
                            ORDER BY CASE WHEN session_date > event_date
                                          THEN session_date END ASC)
                  END AS day_offset
        FROM src
        """
    )

    # --- T1c-i  indicators -------------------------------------------------
    con.execute(
        """
        CREATE TABLE t1c_ind AS
        SELECT ticker, event_date, era,
               COUNT(*) AS n_rows,
               COUNT(*) FILTER (WHERE indicators IS NULL) AS n_null,
               COUNT(*) FILTER (WHERE indicators IS NOT NULL
                                  AND len(indicators) = 0)  AS n_empty_list,
               COUNT(*) FILTER (WHERE indicators IS NOT NULL
                                  AND len(indicators) > 0)  AS n_populated
        FROM src2 GROUP BY 1, 2, 3
        """
    )
    ind_vals = con.execute(
        """
        SELECT v AS indicator_code, COUNT(*) n
        FROM (SELECT unnest(indicators) v FROM src2 WHERE indicators IS NOT NULL)
        GROUP BY 1 ORDER BY 2 DESC
        """
    ).df()

    # --- T1c-ii  conditions: individual codes and observed combinations -----
    codes = con.execute(
        """
        SELECT v AS condition_code, COUNT(*) n_rows,
               COUNT(DISTINCT (ticker, event_date)) n_events
        FROM (SELECT ticker, event_date, unnest(conditions) v
              FROM src2 WHERE conditions IS NOT NULL)
        GROUP BY 1 ORDER BY 2 DESC
        """
    ).df()
    combos = con.execute(
        """
        SELECT combo, COUNT(*) n_rows, COUNT(DISTINCT (ticker, event_date)) n_events
        FROM (SELECT ticker, event_date,
                     CASE WHEN conditions IS NULL THEN 'NULL'
                          ELSE list_aggregate(list_sort(conditions), 'string_agg', ',')
                     END AS combo
              FROM src2)
        GROUP BY 1 ORDER BY 2 DESC
        """
    ).df()

    # --- T1c-iv  pattern by day offset and era -----------------------------
    by_off = con.execute(
        """
        SELECT era, day_offset,
               COUNT(*) n_rows,
               COUNT(DISTINCT (ticker, event_date)) n_events,
               AVG(CASE WHEN indicators IS NULL THEN 1.0 ELSE 0.0 END) share_ind_null,
               AVG(CASE WHEN conditions IS NULL THEN 1.0 ELSE 0.0 END) share_cond_null
        FROM src2 GROUP BY 1, 2 ORDER BY 1, 2
        """
    ).df()

    # --- T1c-v  storage-order census (row 19a exemption) -------------------
    storage = con.execute(
        """
        SELECT ticker, event_date, era, COUNT(*) n_pairs,
          AVG(CASE WHEN d_sip < 0 THEN 1.0 ELSE 0.0 END) share_sip_decreases,
          AVG(CASE WHEN d_par < 0 THEN 1.0 ELSE 0.0 END) share_par_decreases,
          AVG(CASE WHEN d_seq < 0 THEN 1.0 ELSE 0.0 END) share_seq_decreases,
          AVG(CASE WHEN (d_sip < 0) = (d_seq < 0) THEN 1.0 ELSE 0.0 END) share_sip_seq_agree,
          COUNT(*) FILTER (WHERE d_session <> 0) n_session_boundary_pairs
        FROM (
          SELECT ticker, event_date, era,
            sip_timestamp - LAG(sip_timestamp) OVER w AS d_sip,
            participant_timestamp - LAG(participant_timestamp) OVER w AS d_par,
            sequence_number - LAG(sequence_number) OVER w AS d_seq,
            CASE WHEN session_date = LAG(session_date) OVER w THEN 0 ELSE 1 END AS d_session
          FROM src2
          WINDOW w AS (PARTITION BY ticker, event_date ORDER BY file_row_number)
        ) g
        WHERE d_sip IS NOT NULL
        GROUP BY 1, 2, 3 ORDER BY 1, 2
        """
    ).df()

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    for name, df in [
        ("t1c_indicators", con.execute("SELECT * FROM t1c_ind ORDER BY ticker, event_date").df()),
        ("t1c_indicator_values", ind_vals),
        ("t1c_conditions_codes", codes),
        ("t1c_conditions_combos", combos),
        ("t1c_by_day_offset", by_off),
        ("t1c_storage_order", storage),
    ]:
        df.to_parquet(ARTIFACTS / f"{name}.parquet", index=False)
        print(f"{name:26s} rows={len(df):>7,}")

    print("\n--- T1c-i indicators ---")
    ind = con.execute("SELECT * FROM t1c_ind").df()
    print(f"  total rows {ind.n_rows.sum():,} | null {ind.n_null.sum():,} "
          f"| empty-list {ind.n_empty_list.sum():,} | populated {ind.n_populated.sum():,}")
    print(f"  events with 100% null indicators: {(ind.n_null == ind.n_rows).sum()} / {len(ind)}")
    print(f"  distinct indicator codes observed: {len(ind_vals)}")

    print("\n--- T1c-ii conditions: top individual codes (opaque integers) ---")
    print(codes.head(10).to_string(index=False))
    print("\n--- T1c-ii conditions: top combinations (opaque) ---")
    print(combos.head(10).to_string(index=False))

    print("\n--- T1c-v storage order ---")
    for c in ["share_sip_decreases", "share_par_decreases", "share_seq_decreases"]:
        q = storage[c].quantile([0, 0.5, 1]).values
        print(f"  {c:22s} min={q[0]:.6%} median={q[1]:.6%} max={q[2]:.6%}")
    print(f"  events with ANY sip decrease in file order: "
          f"{(storage.share_sip_decreases > 0).sum()} / {len(storage)}")


if __name__ == "__main__":
    main()
