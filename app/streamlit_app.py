"""Loan officer review screen.

    streamlit run app/streamlit_app.py
"""

import html
import json
import sys
import tempfile
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loanlens.audit import log_decision, read_log  # noqa: E402
from loanlens.config import DEMO_DIR, GENERATED_DIR, POLICY, RESULTS_DIR  # noqa: E402
from loanlens.evidence import highlight  # noqa: E402
from loanlens.generate import demo  # noqa: E402
from loanlens.generate.build_dataset import build  # noqa: E402
from loanlens.pipeline import METHODS, document_files, process_documents  # noqa: E402

st.set_page_config(page_title="LoanLens", page_icon="🏦", layout="wide")
AUTHOR = "Abhigna Komaravolu"
DECISION_COLORS = {"APPROVE": "#22c55e", "REVIEW": "#f59e0b", "REJECT": "#ef4444"}
STATUS = {"pass": ("#22c55e", "✓", "Pass"), "warn": ("#f59e0b", "!", "Needs attention"),
          "fail": ("#ef4444", "✕", "Failed")}
OK, BAD, ACCENT = "#22c55e", "#ef4444", "#22d3ee"

st.markdown(f"""
<style>
.block-container {{ padding-top: 2rem; }}
.ll-credit {{ position: fixed; bottom: 8px; right: 16px; font-size: 13px;
    color: rgba(148, 163, 184, 0.9); pointer-events: none; z-index: 999; }}
.ll-sub {{ color: #94a3b8; margin-top: -0.6rem; margin-bottom: 1rem; }}
.ll-card {{ background: #131c2e; border: 1px solid #1f2a40; border-radius: 14px;
    padding: 1rem 1.2rem; height: 100%; }}
.ll-label {{ color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;
    letter-spacing: 0.06em; }}
.ll-decision {{ font-size: 2.6rem; font-weight: 800; letter-spacing: 0.02em; line-height: 1.1; }}
.ll-bar {{ background: #1f2a40; border-radius: 99px; height: 8px; margin: 0.6rem 0 0.3rem; }}
.ll-bar > div {{ height: 8px; border-radius: 99px; }}
.ll-muted {{ color: #94a3b8; font-size: 0.85rem; }}
.ll-kpi {{ font-size: 1.6rem; font-weight: 700; }}
.ll-tile {{ min-height: 150px; }}
.ll-steps {{ display: flex; gap: 0.5rem; margin: 0.4rem 0 1.2rem; flex-wrap: wrap; }}
.ll-step {{ flex: 1; min-width: 140px; display: flex; gap: 0.6rem; align-items: center;
    background: #131c2e; border: 1px solid #1f2a40; border-radius: 12px; padding: 0.6rem 0.8rem; }}
.ll-dot {{ width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center;
    justify-content: center; font-weight: 800; color: #0b1220; flex: none; }}
.ll-step b {{ display: block; font-size: 0.9rem; }}
.ll-step span {{ color: #94a3b8; font-size: 0.78rem; }}
.ll-check {{ background: #131c2e; border: 1px solid #1f2a40; border-left: 5px solid;
    border-radius: 12px; padding: 0.8rem 1rem; margin-bottom: 0.7rem; }}
.ll-check b {{ font-size: 0.95rem; }}
.ll-reason {{ padding: 0.35rem 0; border-bottom: 1px solid #1f2a40; font-size: 0.92rem; }}
.ll-reason:last-child {{ border-bottom: none; }}
.ll-chip {{ display: flex; gap: 0.6rem; align-items: center; padding: 0.4rem 0;
    border-bottom: 1px solid #1f2a40; font-size: 0.88rem; }}
.ll-num {{ width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center;
    justify-content: center; font-weight: 700; color: #0b1220; flex: none; font-size: 0.8rem; }}
</style>
<div class="ll-credit">LoanLens · built by {AUTHOR}</div>
""", unsafe_allow_html=True)


def esc(text) -> str:
    """HTML-escape and stop Streamlit from reading '$...$' as maths."""
    return html.escape(str(text)).replace("$", "&#36;")


def money(x: float | None) -> str:
    return "—" if x is None else f"${x:,.2f}"


@st.cache_resource(show_spinner="First start: generating 40 demo applications...")
def ensure_demo_data() -> None:
    """On a fresh deploy there are no documents yet, so create the demo set once."""
    if (GENERATED_DIR / "manifest.csv").exists():
        return
    demo.main()
    build(DEMO_DIR / "demo_borrowers.csv", GENERATED_DIR, limit=40, fraud_rate=0.2,
          scan_rate=0.25, new_layout_rate=0.3, seed=42)


@st.cache_data(show_spinner=False)
def cached_highlight(path: str, doc_type: str, fields_json: str):
    return highlight(Path(path), doc_type, json.loads(fields_json))


# ---------------------------------------------------------------- result sections

def step_tracker(result: dict) -> None:
    docs, checks = result["documents"], result["checks"]
    ocr = sum(d["read_with"] == "ocr" for d in docs)
    known = [d for d in docs if d["doc_type"] != "unknown"]
    counts = {s: sum(c["status"] == s for c in checks) for s in ("pass", "warn", "fail")}
    check_color = BAD if counts["fail"] else "#f59e0b" if counts["warn"] else OK
    decision = result["decision"]["decision"]
    steps = [
        ("Read", f"{len(docs)} docs" + (f" · {ocr} via OCR" if ocr else ""), OK),
        ("Classify", f"{len(known)}/{len(docs)} recognised", OK if len(known) == len(docs) else BAD),
        ("Extract", f"extractor: {result['method']}", OK),
        ("Cross-check", f"{counts['pass']} pass · {counts['warn']} warn · {counts['fail']} fail",
         check_color),
        ("Decide", decision.title(), DECISION_COLORS[decision]),
    ]
    st.markdown('<div class="ll-steps">' + "".join(
        f'<div class="ll-step"><div class="ll-dot" style="background:{c}">{i}</div>'
        f'<div><b>{esc(name)}</b><span>{esc(sub)}</span></div></div>'
        for i, (name, sub, c) in enumerate(steps, 1)) + "</div>", unsafe_allow_html=True)


def decision_hero(result: dict) -> None:
    d, m = result["decision"], result["decision"]["metrics"]
    color = DECISION_COLORS[d["decision"]]
    left, right = st.columns([5, 7], gap="medium")
    with left:
        st.markdown(f"""
<div class="ll-card" style="border-color:{color}55">
  <div class="ll-label">AI recommendation</div>
  <div class="ll-decision" style="color:{color}">{d['decision']}</div>
  <div class="ll-bar"><div style="width:{d['risk_score']}%;background:{color}"></div></div>
  <div class="ll-muted">Risk {d['risk_score']:.0f}/100 · confidence {esc(d['confidence'])} ·
    {result['seconds']}s · {esc(result['method'])}</div>
</div>""", unsafe_allow_html=True)
    with right:
        tiles = [
            ("Monthly income", money(m.get("verified_monthly_income")),
             m.get("income_source", "")),
            ("DTI after loan", f"{m['dti_after_loan_pct']}%" if m else "—",
             f"reject above {POLICY['dti_reject_above']:.0f}%"),
            ("Loan / income", f"{m['loan_to_income']:.0%}" if m else "—",
             f"review above {POLICY['loan_to_income_review_above']:.0%}"),
            ("Years employed", m.get("years_employed", "—") if m else "—",
             f"review under {POLICY['min_employment_years']}"),
        ]
        cols = st.columns(4)
        for col, (label, value, hint) in zip(cols, tiles):
            col.markdown(f'<div class="ll-card ll-tile"><div class="ll-label">{esc(label)}</div>'
                         f'<div class="ll-kpi">{esc(value)}</div>'
                         f'<div class="ll-muted">{esc(hint)}</div></div>',
                         unsafe_allow_html=True)
    st.markdown('<div class="ll-card" style="margin-top:0.8rem"><div class="ll-label">Why</div>'
                + "".join(f'<div class="ll-reason">{esc(r)}</div>' for r in d["reasons"])
                + "</div>", unsafe_allow_html=True)


def checks_view(result: dict) -> None:
    cols = st.columns(2, gap="medium")
    for i, c in enumerate(result["checks"]):
        color, icon, label = STATUS[c["status"]]
        cols[i % 2].markdown(
            f'<div class="ll-check" style="border-left-color:{color}">'
            f'<b>{icon} {esc(c["name"].replace("_", " ").capitalize())}</b> '
            f'<span class="ll-muted">· {label}</span><br>'
            f'<span class="ll-muted">{esc(c["detail"])}</span></div>',
            unsafe_allow_html=True)


def forensics_view(result: dict) -> None:
    fields = {d["doc_type"]: d["fields"] or {} for d in result["documents"]}
    slip, bank, app = (fields.get(k, {}) for k in ("payslip", "bank_statement", "application"))
    net, credits = slip.get("net_pay"), bank.get("salary_credits") or []
    if not credits:
        st.info("No salary deposits could be read from the bank statement, so there is "
                "nothing to compare. The rules extractor cannot read the unseen bank layout; "
                "try the Gemini extractor (Advanced, at the bottom of the page).")
        return

    tol, reject = POLICY["income_tolerance"], POLICY["income_reject_mismatch"]
    rows = []
    for i, amount in enumerate(credits, 1):
        gap = abs(net - amount) / amount if net else None  # same formula as checks.py
        rows.append({"deposit": f"Deposit {i}", "amount": amount,
                     "status": "matches payslip" if gap is not None and gap <= tol
                     else "does not match"})
    df = pd.DataFrame(rows)
    top = max(df.amount.max(), net or 0) * 1.2

    bars = alt.Chart(df).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=56).encode(
        x=alt.X("deposit:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("amount:Q", title="USD per month", scale=alt.Scale(domain=[0, top])),
        color=alt.Color("status:N", title=None, legend=alt.Legend(orient="bottom"),
                        scale=alt.Scale(domain=["matches payslip", "does not match"],
                                        range=[OK, BAD])),
        tooltip=[alt.Tooltip("deposit:N"), alt.Tooltip("amount:Q", format="$,.2f")])
    layers = [bars]
    if net:
        line = pd.DataFrame({"y": [net], "label": [f"Payslip says net pay {money(net)}"]})
        layers += [
            alt.Chart(line).mark_rule(color=ACCENT, strokeDash=[6, 4], size=2).encode(y="y:Q"),
            alt.Chart(line).mark_text(align="left", dx=6, dy=-8, color=ACCENT, fontSize=13)
            .encode(y="y:Q", x=alt.value(0), text="label:N"),
        ]

    left, right = st.columns([3, 2], gap="medium")
    with left:
        st.markdown("**Salary actually deposited vs what the payslip claims**")
        st.altair_chart(alt.layer(*layers).properties(height=320), width="stretch")
    with right:
        avg = sum(credits) / len(credits)
        gap = abs(net - avg) / avg if net else None
        if gap is None:
            verdict, color = "Payslip net pay could not be read", "#f59e0b"
        elif gap > reject:
            verdict, color = "Likely inflated or forged payslip", BAD
        elif gap > tol:
            verdict, color = "Mismatch: needs a human look", "#f59e0b"
        else:
            verdict, color = "Payslip confirmed by bank deposits", OK
        st.markdown(f"""
<div class="ll-card" style="border-color:{color}55">
  <div class="ll-label">Income verdict</div>
  <div class="ll-kpi" style="color:{color}">{esc(verdict)}</div>
  <div class="ll-muted" style="margin-top:0.5rem">
    Payslip net pay: <b>{esc(money(net))}</b><br>
    Average deposit: <b>{esc(money(avg))}</b><br>
    Gap: <b>{'—' if gap is None else f'{gap:.0%}'}</b>
    (review above {tol:.0%}, fail above {reject:.0%})</div>
</div>""", unsafe_allow_html=True)

        stated = app.get("stated_annual_income")
        verified = result["decision"]["metrics"].get("verified_monthly_income")
        income = pd.DataFrame([
            {"source": "Application (stated)", "monthly": stated / 12 if stated else None},
            {"source": "Payslip gross", "monthly": slip.get("gross_pay")},
            {"source": "Verified", "monthly": verified},
        ]).dropna()
        if not income.empty:
            st.markdown("**Monthly income: claimed vs verified** (verified is used for the decision)")
            st.altair_chart(
                alt.Chart(income).mark_bar(cornerRadiusEnd=6, size=22).encode(
                    y=alt.Y("source:N", title=None, sort=None, axis=alt.Axis(labelLimit=220)),
                    x=alt.X("monthly:Q", title="USD per month"),
                    color=alt.condition(alt.datum.source == "Verified",
                                        alt.value(ACCENT), alt.value("#475569")),
                    tooltip=[alt.Tooltip("monthly:Q", format="$,.2f")],
                ).properties(height=150), width="stretch")


def evidence_view(result: dict, files: list[Path]) -> None:
    st.caption("Every extracted value is boxed where it was found on the page. A value that "
               "was extracted but cannot be located should not be trusted.")
    by_name = {p.name: p for p in files}
    docs = [d for d in result["documents"] if d["fields"]]
    if not docs:
        st.info("No fields were extracted.")
        return
    for tab, doc in zip(st.tabs([f"{d['doc_type'].replace('_', ' ').title()}" for d in docs]),
                        docs):
        with tab:
            image, legend = cached_highlight(str(by_name[doc["file"]]), doc["doc_type"],
                                             json.dumps(doc["fields"]))
            left, right = st.columns([3, 2], gap="medium")
            left.image(image, width="stretch")
            rows = []
            for item in legend:
                value = item["value"]
                if isinstance(value, list):
                    value = ", ".join(money(v) for v in value) or None
                elif isinstance(value, float):
                    value = money(value)
                state = ("located on page" if item["found"] else
                         "extracted, not located" if item["extracted"] else "not extracted")
                state_color = OK if item["found"] else "#f59e0b" if item["extracted"] else BAD
                rows.append(
                    f'<div class="ll-chip"><div class="ll-num" style="background:{item["color"]}">'
                    f'{item["number"]}</div><div style="flex:1"><b>'
                    f'{esc(item["field"].replace("_", " "))}</b><br>'
                    f'<span class="ll-muted">{esc(value if value is not None else "—")}</span>'
                    f'</div><span style="color:{state_color};font-size:0.78rem">{state}</span>'
                    f'</div>')
            right.markdown(
                f'<div class="ll-card"><div class="ll-label">{esc(doc["file"])} · read with '
                f'{esc(doc["read_with"])}</div>{"".join(rows)}</div>', unsafe_allow_html=True)


def officer_form(result: dict, app_id: str) -> None:
    d = result["decision"]
    st.subheader("Officer decision")
    with st.form(f"officer_{app_id}"):
        choice = st.radio("Your decision", ["APPROVE", "REVIEW", "REJECT"],
                          index=["APPROVE", "REVIEW", "REJECT"].index(d["decision"]),
                          horizontal=True)
        note = st.text_input("Note (required if you override the AI)")
        if st.form_submit_button("Record decision", type="primary"):
            if choice != d["decision"] and not note.strip():
                st.error("Please explain why you are overriding the AI recommendation.")
            else:
                entry = log_decision(app_id, result, choice, note)
                st.success("Saved to audit log" + (" (override)" if entry["overridden"] else ""))


def show_result(result: dict, files: list[Path], app_id: str, truth: dict | None) -> None:
    step_tracker(result)
    decision_hero(result)
    st.write("")
    tab_checks, tab_fraud, tab_evidence = st.tabs(
        ["🔍 Cross-document checks", "📊 Fraud forensics", "📄 Evidence"])
    with tab_checks:
        checks_view(result)
    with tab_fraud:
        forensics_view(result)
    with tab_evidence:
        evidence_view(result, files)
    if truth:
        with st.expander("Answer key (generated data only)"):
            st.write(f"Injected fraud: **{truth['labels']['fraud_type'] or 'none'}** · "
                     f"Real loan outcome: **{truth['labels']['loan_status']}**")
    officer_form(result, app_id)


# ---------------------------------------------------------------- page

ensure_demo_data()
st.title("🏦 LoanLens")
st.markdown('<div class="ll-sub">AI loan underwriting with document intelligence: reads the '
            'application, payslip and bank statement, checks them against each other, and '
            'recommends a decision for a human loan officer.</div>', unsafe_allow_html=True)
# The extractor picker is drawn at the bottom of the page; its value is read here first
method = st.session_state.get("method", METHODS[0])
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

    with st.expander("Advanced: extraction method"):
        st.selectbox("Extractor", METHODS, key="method",
                     help="rules = offline regex baseline; gemini/ollama = free LLMs")
        st.caption(
            "The rules baseline only knows one payslip and bank-statement layout. About 30% of "
            "sample applications use a layout it has never seen, so it misreads them (e.g. "
            "'PAY SLIP' as the employer) and wrongly flags them. The Gemini extractor reads "
            "both layouts at 97% accuracy. See the Evaluation tab / README."
        )

with tab_audit:
    log = read_log()
    if log:
        st.dataframe(pd.DataFrame(log), hide_index=True, width="stretch")
    else:
        st.info("No decisions recorded yet.")

with tab_eval:
    reports = sorted(RESULTS_DIR.glob("results_*.md"))
    if not reports:
        st.info("Run `python evals/run_eval.py` to create evaluation results.")
    for report in reports:
        with st.expander(report.stem, expanded=len(reports) == 1):
            st.markdown(report.read_text())
