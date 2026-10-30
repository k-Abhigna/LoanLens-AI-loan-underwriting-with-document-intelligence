"""Build the document dataset: one folder of documents per real borrower.

Usage:
    python -m loanlens.generate.build_dataset --input data/processed/borrowers.csv --limit 300
"""

import argparse
import json
import random
import shutil
from pathlib import Path

import pandas as pd

from loanlens.config import GENERATED_DIR
from loanlens.generate.pdfs import RENDERERS
from loanlens.generate.profile import FRAUD_TYPES, TEMPLATES, build_case
from loanlens.generate.scan import pdf_to_scan


def build(input_csv: Path, out_dir: Path, limit: int, fraud_rate: float, scan_rate: float,
          new_layout_rate: float, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    borrowers = pd.read_csv(input_csv).head(limit)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    manifest = []
    for row in borrowers.to_dict("records"):
        fraud = rng.choice(FRAUD_TYPES) if rng.random() < fraud_rate else None
        templates = {d: TEMPLATES[1] if rng.random() < new_layout_rate else TEMPLATES[0]
                     for d in ("payslip", "bank_statement")}
        case = build_case(row, fraud, templates)
        folder = out_dir / case["application_id"]
        folder.mkdir()

        files = {}
        for doc_type, render in RENDERERS.items():
            pdf_path = folder / f"{doc_type}.pdf"
            render(case, pdf_path, case["templates"].get(doc_type, "A"))
            # Some payslips arrive as photos/scans instead of clean PDFs
            if doc_type == "payslip" and rng.random() < scan_rate:
                img_path = folder / "payslip_scan.jpg"
                pdf_to_scan(pdf_path, img_path, seed=rng.randint(0, 10**6))
                pdf_path.unlink()
                files[doc_type] = img_path.name
            else:
                files[doc_type] = pdf_path.name

        (folder / "truth.json").write_text(json.dumps(case, indent=2))
        manifest.append({
            "application_id": case["application_id"],
            "fraud_type": fraud or "",
            "loan_status": case["labels"]["loan_status"],
            "payslip_file": files["payslip"],
            "payslip_layout": templates["payslip"],
            "bank_layout": templates["bank_statement"],
        })
        print(f"  {case['application_id']}  fraud={fraud or '-':18}  payslip={files['payslip']:17}"
              f" layouts={templates['payslip']}/{templates['bank_statement']}")

    df = pd.DataFrame(manifest)
    df.to_csv(out_dir / "manifest.csv", index=False)
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=Path("data/processed/borrowers.csv"))
    ap.add_argument("--out", type=Path, default=GENERATED_DIR)
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--fraud-rate", type=float, default=0.20)
    ap.add_argument("--scan-rate", type=float, default=0.25)
    ap.add_argument("--new-layout-rate", type=float, default=0.30,
                    help="share of payslips/bank statements using the unseen layout B")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    df = build(args.input, args.out, args.limit, args.fraud_rate, args.scan_rate,
               args.new_layout_rate, args.seed)
    print(f"\nBuilt {len(df)} applications in {args.out}")
    print(df["fraud_type"].replace("", "none").value_counts().to_string())


if __name__ == "__main__":
    main()
