"""Phase 10c -- S6 check 2 for Stage 0b (A1.9 per-stage protocol, A2.11 register)."""
import hashlib, json, os, sys
CFG = "config/phase_10c.json"
c = json.load(open(CFG, encoding="utf-8"))
h = hashlib.sha256(open(CFG, "rb").read()).hexdigest()[:8]
E = c["cooper_values"]["_class_E_fill_before_stage_0"]
missing = sorted(k for k, v in E.items() if v is None)
out = {
    "phase": "10c", "task": "S6 satisfiability audit", "stage_evaluated": "0b",
    "config": CFG, "config_hash": h,
    "protocol": "A1.9 check 2 per stage; A2.11 register; Stage 0b requires class_E only",
    "class_E": E, "n_required": len(E), "n_present": len(E) - len(missing),
    "missing": missing,
    "check_2_verdict": "PASS" if not missing else "FAIL",
    "why_it_blocks": None if not missing else (
        "D16_min_median_void gates T0b.6 and its statistic is PRODUCED BY T0b.2. Running "
        "T0b.1-T0b.5 first and setting D16 afterwards would set the threshold after seeing the "
        "void distribution it judges, which is the pre-registration failure A1.1's locking rule "
        "exists to prevent. A2.3 states it plainly: 'set before Stage 0b runs.'"),
    "no_pipeline_code_executed": True,
    "action": "HALT AND ESCALATE. Stage 0b not started." if missing else "clear",
    "source": "research/phase_10c/s6_audit_0b.py",
}
os.makedirs("results/phase_10c/artifacts", exist_ok=True)
json.dump(out, open("results/phase_10c/artifacts/s6_satisfiability_audit_stage0b.json", "w",
                    encoding="utf-8"), indent=2)
print(f"Stage 0b check 2: {out['check_2_verdict']}  (config {h})")
for k, v in E.items():
    print(f"   {k:28s} {'null  <-- MISSING' if v is None else v}")
print(f"\n{out['action']}")
