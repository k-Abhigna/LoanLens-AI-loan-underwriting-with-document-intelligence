"""LLM extractor using FREE options: Google Gemini (free tier) or a local Ollama model.

Setup (pick one):
  Gemini: get a free key at https://aistudio.google.com/apikey and put
          GEMINI_API_KEY=... in a .env file in the project root.
  Ollama: install from https://ollama.com, run `ollama pull qwen2.5:3b`.
"""

import json
import os

import requests
from dotenv import load_dotenv
from pydantic import ValidationError

from loanlens.config import ROOT
from loanlens.schemas import ApplicationFields, BankStatementFields, PayslipFields

load_dotenv(ROOT / ".env")

SCHEMAS = {
    "application": ApplicationFields,
    "payslip": PayslipFields,
    "bank_statement": BankStatementFields,
}

PROMPT = """You extract fields from a {doc_type} used in a loan application.
Return ONLY a JSON object matching this JSON schema:
{schema}

Rules:
- Copy values exactly as printed. Do not guess or calculate missing values; use null.
- Money values are plain numbers without $ or commas, e.g. 4250.5. Debits are not needed.
- For a payslip, "employer" is the company name in the letterhead.
- For a bank statement, "salary_credits" is the list of payroll deposit amounts and
  "salary_payer" is the description text of the payroll deposit line.

Document text:
\"\"\"
{text}
\"\"\"
"""


def _call_gemini(prompt: str) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to the .env file.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }
    resp = requests.post(url, json=body, headers={"x-goog-api-key": key}, timeout=60)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _call_ollama(prompt: str) -> str:
    url = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/chat"
    body = {
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0},
    }
    resp = requests.post(url, json=body, timeout=180)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


PROVIDERS = {"gemini": _call_gemini, "ollama": _call_ollama}


def extract(doc_type: str, text: str, provider: str = "gemini"):
    """Ask the LLM for JSON, validate it; if invalid, retry once showing the error."""
    model_cls = SCHEMAS[doc_type]
    prompt = PROMPT.format(doc_type=doc_type.replace("_", " "),
                           schema=json.dumps(model_cls.model_json_schema()), text=text[:12000])
    call = PROVIDERS[provider]
    raw = call(prompt)
    try:
        return model_cls.model_validate_json(raw)
    except ValidationError as err:
        retry = f"{prompt}\n\nYour previous answer was invalid:\n{raw}\nError: {err}\nFix it."
        return model_cls.model_validate_json(call(retry))
