"""End-to-end: documents in -> classified, extracted, checked, decided.

    python -m loanlens.pipeline data/generated/<application_id>
    python -m loanlens.pipeline data/generated/<application_id> --method gemini
"""

import argparse
import json
import time
from pathlib import Path

from loanlens.checks import run_checks
from loanlens.decide import decide
from loanlens.extract import rules
from loanlens.extract.classify import classify
from loanlens.extract.text import IMAGE_EXTS, get_text

METHODS = ["rules", "gemini"]


def extract_fields(doc_type: str, text: str, method: str):
    if method == "rules":
        return rules.extract(doc_type, text)
    from loanlens.extract import llm  # only needed when an LLM is used
    return llm.extract(doc_type, text, provider=method)


def process_documents(paths: list[Path], method: str = "rules") -> dict:
    start = time.perf_counter()
    docs, fields = [], {}
    for path in paths:
        text, read_with = get_text(path)
        doc_type, conf = classify(text)
        entry = {"file": path.name, "read_with": read_with, "doc_type": doc_type,
                 "type_confidence": conf, "fields": None}
        if doc_type != "unknown" and doc_type not in fields:
            extracted = extract_fields(doc_type, text, method)
            if read_with == "ocr" and doc_type == "payslip":
                extracted = rules.clean_ocr_payslip(extracted)
            fields[doc_type] = extracted
            entry["fields"] = extracted.model_dump()
        docs.append(entry)

    app, slip, bank = (fields.get(k) for k in ("application", "payslip", "bank_statement"))
    checks, derived = run_checks(app, slip, bank)
    used_ocr = any(d["read_with"] == "ocr" for d in docs)
    decision = decide(app, checks, derived, used_ocr=used_ocr)
    return {
        "method": method,
        "documents": docs,
        "checks": [c.model_dump() for c in checks],
        "decision": decision.model_dump(),
        "seconds": round(time.perf_counter() - start, 2),
    }


def document_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir()
                  if p.suffix.lower() == ".pdf" or p.suffix.lower() in IMAGE_EXTS)


def process_folder(folder: Path, method: str = "rules") -> dict:
    result = process_documents(document_files(folder), method)
    result["application_id"] = folder.name
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--method", choices=METHODS, default="rules")
    args = ap.parse_args()
    print(json.dumps(process_folder(args.folder, args.method), indent=2))


if __name__ == "__main__":
    main()
