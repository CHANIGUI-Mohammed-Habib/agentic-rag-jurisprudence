"""Streamlit interface: question -> live operational trace -> cited evidence brief.

Run:  uv run streamlit run app.py
"""

import html
import json
import time

import streamlit as st

from jurisrag import config
from jurisrag.agent import run_agent
from jurisrag.baseline import run_baseline
from jurisrag.llm import ClaudeLLM
from jurisrag.render import STATUS_LABELS
from jurisrag.store import CorpusStore, StorageError

st.set_page_config(page_title="Agentic RAG — Jurisprudence", layout="wide")

TYPE_COLORS = {"DECISION": "#b45309", "TOOL": "#1d4ed8", "OBSERVATION": "#475569", "TOOL_ERROR": "#b91c1c",
               "CHECK": "#6d28d9", "FINAL": "#047857", "ERROR": "#b91c1c"}


@st.cache_resource
def load_store() -> CorpusStore:
    return CorpusStore()


def trace_html(events: list[dict]) -> str:
    rows = []
    for e in events:
        color = TYPE_COLORS.get(e["type"], "#334155")
        issues = "".join(f"<div style='margin-left:1em;color:#64748b'>↳ {html.escape(i)}</div>"
                         for i in (e.get("detail") or {}).get("issues") or [])
        rows.append(
            f"<tr><td style='padding:2px 8px'>{e['step']}</td><td style='padding:2px 8px;color:#64748b'>{e['elapsed_s']}s</td>"
            f"<td style='padding:2px 8px'><span style='background:{color};color:white;border-radius:4px;padding:1px 6px;"
            f"font-size:0.8em'>{e['type']}</span></td><td style='padding:2px 8px'>{html.escape(e['label'])}{issues}</td></tr>")
    return "<table style='width:100%;font-size:0.9em'>" + "".join(rows) + "</table>"


def highlight(store: CorpusStore, c: dict, margin: int = 400) -> str:
    text = store.cases[c["case_id"]]["text"]
    s, e = c["start"], c["end"]
    before, quote, after = text[max(0, s - margin):s], text[s:e], text[e:e + margin]
    return (f"<div style='font-size:0.9em;white-space:pre-wrap'>…{html.escape(before)}"
            f"<mark>{html.escape(quote)}</mark>{html.escape(after)}…</div>")


def show_result(store: CorpusStore, result: dict) -> None:
    final, m = result["final"], result["metrics"]
    cols = st.columns(5)
    cols[0].metric("Appels LLM", m["llm_calls"])
    cols[1].metric("Appels d'outils", m["tool_calls"])
    cols[2].metric("Latence", f"{m['latency_s']} s")
    cols[3].metric("Tokens in/out", f"{m['input_tokens']}/{m['output_tokens']}")
    cols[4].metric("Coût estimé", f"${m['cost_usd']}")
    st.caption(f"Outils : {m['tools_used']} · appels par rôle : {m['calls_by_role']} · modèle {m['model']}")

    status = STATUS_LABELS.get(final["status"], final["status"])
    {"verified": st.success, "insufficient_evidence": st.warning, "gap_limit": st.warning,
     "unverified": st.info}.get(final["status"], st.error)(f"{status} — condition d'arrêt : {final['stop_reason']}")
    brief = final.get("brief")
    if not brief:
        return
    st.markdown(f"#### Constat principal\n{brief['main_finding']}")
    by_claim: dict[int, list[dict]] = {}
    for c in final["citations"]:
        by_claim.setdefault(c["claim_index"], []).append(c)
    if brief["claims"]:
        st.markdown("#### Décisions et passages à l'appui")
        for i, claim in enumerate(brief["claims"]):
            st.markdown(f"**{i + 1}.** {claim['statement']}")
            for c in by_claim.get(i, []):
                with st.expander(f"Cass. soc., {c['date']}, n° {c['number']} ({c['solution']}) · zone {c['zone']} · "
                                 f"car. {c['start']}–{c['end']}"):
                    st.markdown(highlight(store, c), unsafe_allow_html=True)
                    st.caption(f"{c['passage_id']} · source : corpus local · {c['url']}")
    if brief["qualifications"]:
        st.markdown("#### Nuances\n" + "\n".join(f"- {q}" for q in brief["qualifications"]))
    if brief["evidence_gaps"]:
        st.markdown("#### Lacunes de preuve\n" + "\n".join(f"- {g}" for g in brief["evidence_gaps"]))
    v = final.get("verification") or {}
    if v.get("issues"):
        with st.expander("Défauts relevés par le vérificateur (dernière note)"):
            st.markdown("\n".join(f"- {i}" for i in v["issues"]))


def save(result: dict) -> None:
    out = config.RUNS_DIR / "ui"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{time.strftime('%Y%m%d-%H%M%S')}-{result['system']}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


try:
    store = load_store()
except StorageError as e:
    st.error(str(e))
    st.stop()

with st.sidebar:
    st.header("Corpus")
    man = store.manifest
    st.markdown(f"**{man['cases']}** arrêts · **{man['passages']}** passages  \n"
                f"Chambre sociale, publiés au Bulletin, ≥ {man['selection_rule']['decision_date_min']}, licenciement  \n"
                f"`{man['dataset']}` @ `{man['revision'][:10]}`")
    st.header("Exécution")
    mode = st.radio("Système", ["Agent", "Baseline (RAG statique)", "Comparer les deux"])
    st.markdown(f"Modèle `{config.MODEL}` · effort agent `{config.AGENT_EFFORT}`  \n"
                f"Limites : {config.MAX_TOOL_CALLS} appels d'outils, {config.MAX_DRAFTS} notes, "
                f"{config.MAX_LLM_TURNS} décisions")

st.title("Assistant jurisprudence — Agentic RAG")
st.caption("Note de preuves citées, pas un avis juridique. Chaque citation est vérifiée mot pour mot dans le texte original.")
scenarios = json.loads((config.ROOT / "scenarios.json").read_text(encoding="utf-8"))
pick = st.selectbox("Exemples", ["(question libre)"] + [s["title"] for s in scenarios])
default = next((s["question"] for s in scenarios if s["title"] == pick), "")
question = st.text_area("Question", value=default, height=90)

if st.button("Lancer", type="primary", disabled=not question.strip()):
    llm = ClaudeLLM()
    systems = {"Agent": ["agent"], "Baseline (RAG statique)": ["baseline"]}.get(mode, ["agent", "baseline"])
    cols = st.columns(len(systems))
    for col, system in zip(cols, systems):
        with col:
            st.subheader("Agentic RAG" if system == "agent" else "Baseline RAG statique")
            if system == "agent":
                events, placeholder = [], None
                with st.status("Agent en cours…", expanded=True) as status:
                    placeholder = st.empty()
                    for ev in run_agent(question, store, llm):
                        if ev["type"] == "RESULT":
                            result = ev
                            break
                        events.append(ev)
                        status.update(label=f"Étape {ev['step']} · {ev['type']} · {ev['label'][:90]}")
                        placeholder.markdown(trace_html(events), unsafe_allow_html=True)
                    status.update(label=f"Terminé — {STATUS_LABELS.get(result['final']['status'])}",
                                  state="complete" if result["final"]["status"] != "error" else "error")
                result["trace"] = events
            else:
                with st.spinner("Recherche unique + réponse…"):
                    result = run_baseline(question, store, llm)
                with st.expander("Trace", expanded=True):
                    st.markdown(trace_html(result["trace"]), unsafe_allow_html=True)
            show_result(store, result)
            save(result)
