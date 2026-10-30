"""Loan officer review screen.

    streamlit run app/streamlit_app.py
"""

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loanlens.audit import log_decision, read_log  # noqa: E402
from loanlens.config import GENERATED_DIR, RESULTS_DIR  # noqa: E402
from loanlens.pipeline import METHODS, document_files, process_documents  # noqa: E402

st.set_page_config(page_title="LoanLens", page_icon="🏦", layout="wide")
COLORS = {"APPROVE": "green", "REVIEW": "orange", "REJECT": "red"}
ICONS = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
AUTHOR = "Abhigna Komaravolu"

# Faint diagonal watermark behind the page + a fixed credit in the corner.
# pointer-events: none keeps both from blocking clicks.
st.markdown(f"""
<style>
.ll-watermark {{
    position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-30deg);
    font-size: 6vw; font-weight: 700; white-space: nowrap; color: rgba(128, 128, 128, 0.08);
    pointer-events: none; user-select: none; z-index: 999;
}}
.ll-credit {{
    position: fixed; bottom: 8px; right: 16px; font-size: 13px; color: rgba(128, 128, 128, 0.9);
    pointer-events: none; z-index: 999;
}}
</style>
<div class="ll-watermark">{AUTHOR}</div>
<div class="ll-credit">LoanLens · built by {AUTHOR}</div>
""", unsafe_allow_html=True)


def preview(path: Path):
    if path.suffix.lower() == ".pdf":
        pdf = pdfium.PdfDocument(str(path))
        image = pdf[0].render(scale=1.3).to_pil()
        pdf.close()
        return image
    return str(path)


def show_result(result: dict, files: list[Path], app_id: str, truth: dict | None):
    d = result["decision"]
    st.markdown(f"## :{COLORS[d['decision']]}[{d['decision']}]")
    st.caption(f"Risk {d['risk_score']}/100 · confidence {d['confidence']} · "
               f"{result['seconds']}s · extractor `{result['method']}`")
    for reason in d["reasons"]:
        st.markdown("- " + reason.replace("$", "\\$"))

    m = d["metrics"]
    if m:
        cols = st.columns(4)
        cols[0].metric("Verified monthly income", f"${m['verified_monthly_income']:,.0f}",
                       help=m["income_source"])
        cols[1].metric("DTI after loan", f"{m['dti_after_loan_pct']}%")
        cols[2].metric("Loan / annual income", f"{m['loan_to_income']:.0%}")
        cols[3].metric("Years employed", m["years_employed"])

    st.subheader("Cross-document checks")
    st.dataframe(pd.DataFrame([{"": ICONS[c["status"]], "check": c["name"], "detail": c["detail"]}
                               for c in result["checks"]]),
                 hide_index=True, use_container_width=True)

    st.subheader("Documents")
    by_name = {p.name: p for p in files}
    for doc in result["documents"]:
        with st.expander(f"{doc['file']} → {doc['doc_type']} "
                         f"(read with {doc['read_with']}, type confidence {doc['type_confidence']})"):
            left, right = st.columns([3, 2])
            left.image(preview(by_name[doc["file"]]), use_container_width=True)
            right.json(doc["fields"] or {})

    if truth:
        with st.expander("Answer key (generated data only)"):
            st.write(f"Injected fraud: **{truth['labels']['fraud_type'] or 'none'}** · "
                     f"Real loan outcome: **{truth['labels']['loan_status']}**")

    st.subheader("Officer decision")
    with st.form(f"officer_{app_id}"):
        choice = st.radio("Your decision", ["APPROVE", "REVIEW", "REJECT"],
                          index=["APPROVE", "REVIEW", "REJECT"].index(d["decision"]),
                          horizontal=True)
        note = st.text_input("Note (required if you override the AI)")
        if st.form_submit_button("Record decision"):
            if choice != d["decision"] and not note.strip():
                st.error("Please explain why you are overriding the AI recommendation.")
            else:
                entry = log_decision(app_id, result, choice, note)
                st.success("Saved to audit log" + (" (override)" if entry["overridden"] else ""))


st.title("🏦 LoanLens: loan document review")
method = st.sidebar.selectbox("Extractor", METHODS,
                              help="rules = offline regex baseline; gemini/ollama = free LLMs")
tab_review, tab_audit, tab_eval = st.tabs(["Review application", "Audit log", "Evaluation"])

with tab_review:
    source = st.radio("Documents", ["Sample application", "Upload my own"], horizontal=True)
    files, app_id, truth = [], None, None
    if source == "Sample application":
        manifest = GENERATED_DIR / "manifest.csv"
        if not manifest.exists():
            st.info("No generated applications yet. See README → Quick start.")
        else:
            rows = pd.read_csv(manifest, dtype=str).fillna("")
            app_id = st.selectbox("Application", rows.application_id)
            folder = GENERATED_DIR / app_id
            files = document_files(folder)
            truth = json.loads((folder / "truth.json").read_text())
    else:
        uploads = st.file_uploader("Application form, payslip and bank statement",
                                   type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)
        if uploads:
            tmp = Path(tempfile.mkdtemp())
            for up in uploads:
                (tmp / up.name).write_bytes(up.getvalue())
            files = sorted(tmp.iterdir())
            app_id = f"upload-{tmp.name}"

    if files and st.button("Run underwriting", type="primary"):
        with st.spinner("Reading documents..."):
            try:
                st.session_state["result"] = (app_id, process_documents(files, method))
            except Exception as err:
                st.error(f"{type(err).__name__}: {err}")
    if "result" in st.session_state and st.session_state["result"][0] == app_id:
        show_result(st.session_state["result"][1], files, app_id, truth)

with tab_audit:
    log = read_log()
    if log:
        st.dataframe(pd.DataFrame(log), hide_index=True, use_container_width=True)
    else:
        st.info("No decisions recorded yet.")

with tab_eval:
    reports = sorted(RESULTS_DIR.glob("results_*.md"))
    if not reports:
        st.info("Run `python evals/run_eval.py` to create evaluation results.")
    for report in reports:
        with st.expander(report.stem, expanded=len(reports) == 1):
            st.markdown(report.read_text())
