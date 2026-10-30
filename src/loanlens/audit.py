"""Audit trail: every AI recommendation and every human override is appended to a log."""

import json
from datetime import datetime, timezone

from loanlens.config import AUDIT_LOG


def log_decision(application_id: str, result: dict, officer_decision: str | None = None,
                 officer_note: str = "") -> dict:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "application_id": application_id,
        "method": result.get("method"),
        "ai_decision": result["decision"]["decision"],
        "ai_reasons": result["decision"]["reasons"],
        "risk_score": result["decision"]["risk_score"],
        "officer_decision": officer_decision,
        "overridden": officer_decision is not None
                      and officer_decision != result["decision"]["decision"],
        "officer_note": officer_note,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_log() -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    return [json.loads(line) for line in AUDIT_LOG.read_text().splitlines() if line.strip()]
