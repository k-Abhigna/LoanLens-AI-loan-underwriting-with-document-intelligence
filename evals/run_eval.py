"""Evaluate the whole system against ground truth.

    python evals/run_eval.py                       # rules baseline, all applications
    python evals/run_eval.py --method gemini --limit 50 --sleep 7   # free tier: go slow

Measures:
  1. Document classification accuracy
  2. Field extraction accuracy (digital PDFs vs scanned images)
  3. Fraud detection: precision / recall per fraud type
  4. Decisions vs REAL loan outcomes (default rate per decision, AUC of risk score)
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loanlens.config import GENERATED_DIR, RESULTS_DIR  # noqa: E402
from loanlens.pipeline import METHODS, process_folder  # noqa: E402
from loanlens.schemas import ApplicationFields, BankStatementFields, PayslipFields  # noqa: E402

FIELD_SETS = {
    "application": list(ApplicationFields.model_fields),
    "payslip": list(PayslipFields.model_fields),
    "bank_statement": list(BankStatementFields.model_fields),
}
FRAUD_CHECKS = {"name_match", "payslip_arithmetic", "employer_match",
                "income_vs_application", "income_vs_bank"}


def same(pred, truth) -> bool:
    if isinstance(truth, list):
        return isinstance(pred, list) and len(pred) == len(truth) and all(
            same(p, t) for p, t in zip(pred, truth))
    if isinstance(truth, (int, float)) and not isinstance(truth, bool):
        try:
            return abs(float(pred) - float(truth)) <= max(0.01, abs(truth) * 0.001)
        except (TypeError, ValueError):
            return False
    norm = lambda v: " ".join(str(v).lower().split())  # noqa: E731
    return pred is not None and norm(pred) == norm(truth)


def auc(scores: list[float], labels: list[bool]) -> float | None:
    """Probability that a random defaulter gets a higher risk score than a random payer."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def evaluate(data_dir: Path, method: str, limit: int | None, sleep: float) -> dict:
    manifest = pd.read_csv(data_dir / "manifest.csv", dtype=str).fillna("")
    if limit:
        manifest = manifest.head(limit)

    field_hits = defaultdict(lambda: [0, 0])  # (doc, read_with, layout, field) -> [correct, total]
    cls_hits = [0, 0]
    rows = []
    for i, m in enumerate(manifest.itertuples(), 1):
        folder = data_dir / m.application_id
        truth = json.loads((folder / "truth.json").read_text())
        try:
            result = process_folder(folder, method)
        except Exception as err:  # keep going: one API failure should not stop the eval
            print(f"[{i}] {m.application_id} ERROR {err}")
            continue

        for doc in result["documents"]:
            expected = Path(doc["file"]).stem.replace("_scan", "")
            cls_hits[0] += doc["doc_type"] == expected
            cls_hits[1] += 1
            if doc["fields"] is None or doc["doc_type"] != expected:
                continue
            layout = truth["templates"].get(expected, "A")
            for field in FIELD_SETS[expected]:
                key = (expected, doc["read_with"], layout, field)
                field_hits[key][0] += same(doc["fields"].get(field), truth[expected][field])
                field_hits[key][1] += 1

        flagged = [c["name"] for c in result["checks"]
                   if c["status"] == "fail" and c["name"] in FRAUD_CHECKS]
        rows.append({
            "application_id": m.application_id,
            "fraud_type": m.fraud_type,
            "flagged": bool(flagged),
            "decision": result["decision"]["decision"],
            "risk_score": result["decision"]["risk_score"],
            "defaulted": truth["labels"]["defaulted"],
            "seconds": result["seconds"],
        })
        print(f"[{i}/{len(manifest)}] {m.application_id} {result['decision']['decision']:7}"
              f" fraud={m.fraud_type or '-':18} flagged={bool(flagged)}")
        if sleep:
            time.sleep(sleep)

    df = pd.DataFrame(rows)
    return summarize(df, field_hits, cls_hits, method)


def summarize(df: pd.DataFrame, field_hits: dict, cls_hits: list, method: str) -> dict:
    fields = pd.DataFrame([{"doc_type": k[0], "read_with": k[1], "layout": k[2], "field": k[3],
                            "accuracy": v[0] / v[1], "n": v[1]} for k, v in field_hits.items()])
    by_doc = (fields.assign(correct=fields.accuracy * fields.n)
              .groupby(["doc_type", "layout", "read_with"])[["correct", "n"]].sum())
    by_layout = (fields.assign(correct=fields.accuracy * fields.n)
                 .groupby("layout")[["correct", "n"]].sum())
    by_doc["accuracy"] = by_doc.correct / by_doc.n

    is_fraud = df.fraud_type != ""
    tp = int((df.flagged & is_fraud).sum())
    fp = int((df.flagged & ~is_fraud).sum())
    fn = int((~df.flagged & is_fraud).sum())
    recall_by_type = df[is_fraud].groupby("fraud_type").flagged.mean().round(3).to_dict()

    # Real outcomes are only meaningful for untampered applications
    clean = df[~is_fraud]
    outcome = clean.groupby("decision").defaulted.agg(["count", "mean"]).rename(
        columns={"count": "applications", "mean": "default_rate"})

    return {
        "method": method,
        "applications": len(df),
        "classification_accuracy": round(cls_hits[0] / max(cls_hits[1], 1), 3),
        "field_accuracy_overall": round(fields.accuracy.mul(fields.n).sum() / fields.n.sum(), 3),
        "field_accuracy_by_layout": (by_layout.correct / by_layout.n).round(3).to_dict(),
        "field_accuracy_by_doc": by_doc.accuracy.round(3).reset_index().to_dict("records"),
        "worst_fields": fields.sort_values("accuracy").head(5).round(3).to_dict("records"),
        "fraud": {
            "precision": round(tp / max(tp + fp, 1), 3),
            "recall": round(tp / max(tp + fn, 1), 3),
            "false_alarms_on_clean": fp,
            "recall_by_type": recall_by_type,
        },
        "outcomes_clean_apps": {
            "baseline_default_rate": round(clean.defaulted.mean(), 3) if len(clean) else None,
            "by_decision": outcome.round(3).reset_index().to_dict("records"),
            "risk_score_auc": (round(a, 3) if (a := auc(clean.risk_score.tolist(),
                                                         clean.defaulted.tolist())) else None),
        },
        "avg_seconds_per_application": round(df.seconds.mean(), 2) if len(df) else None,
    }


def to_markdown(r: dict) -> str:
    lines = [f"# Evaluation results - `{r['method']}` extractor", "",
             f"Applications evaluated: **{r['applications']}**", "",
             "| Metric | Value |", "|---|---|",
             f"| Document classification accuracy | {r['classification_accuracy']:.1%} |",
             f"| Field extraction accuracy (all fields) | {r['field_accuracy_overall']:.1%} |",
             *[f"| Field accuracy, layout {k} {'(seen)' if k == 'A' else '(unseen)'} | {v:.1%} |"
               for k, v in r["field_accuracy_by_layout"].items()],
             f"| Fraud detection precision | {r['fraud']['precision']:.1%} |",
             f"| Fraud detection recall | {r['fraud']['recall']:.1%} |",
             f"| False fraud alarms on clean applications | {r['fraud']['false_alarms_on_clean']} |",
             f"| Risk score AUC vs real defaults | {r['outcomes_clean_apps']['risk_score_auc']} |",
             f"| Avg seconds per application | {r['avg_seconds_per_application']} |",
             "", "## Extraction accuracy by document", "",
             "| Document | Layout | Read with | Accuracy |", "|---|---|---|---|"]
    lines += [f"| {d['doc_type']} | {d['layout']} | {d['read_with']} | {d['accuracy']:.1%} |"
              for d in r["field_accuracy_by_doc"]]
    lines += ["", "## Fraud recall by type", "", "| Fraud type | Caught |", "|---|---|"]
    lines += [f"| {k} | {v:.1%} |" for k, v in r["fraud"]["recall_by_type"].items()]
    o = r["outcomes_clean_apps"]
    lines += ["", "## Decisions vs real loan outcomes (untampered applications)", "",
              f"Default rate if every application were approved: **{o['baseline_default_rate']}**",
              "", "| Decision | Applications | Real default rate |", "|---|---|---|"]
    lines += [f"| {d['decision']} | {d['applications']} | {d['default_rate']:.1%} |"
              for d in o["by_decision"]]
    lines += ["", "## Weakest fields", "", "| Document | Layout | Read with | Field | Accuracy |",
              "|---|---|---|---|---|"]
    lines += [f"| {f['doc_type']} | {f['layout']} | {f['read_with']} | {f['field']} "
              f"| {f['accuracy']:.1%} |" for f in r["worst_fields"]]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=GENERATED_DIR)
    ap.add_argument("--method", choices=METHODS, default="rules")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sleep", type=float, default=0, help="seconds between applications")
    ap.add_argument("--tag", default="", help="suffix for the results file, e.g. 'demo'")
    args = ap.parse_args()

    results = evaluate(args.data, args.method, args.limit, args.sleep)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    name = f"results_{args.method}{'_' + args.tag if args.tag else ''}"
    (RESULTS_DIR / f"{name}.json").write_text(json.dumps(results, indent=2))
    (RESULTS_DIR / f"{name}.md").write_text(to_markdown(results))
    print("\n" + to_markdown(results))
    print(f"Saved to {RESULTS_DIR / name}.md")


if __name__ == "__main__":
    main()
