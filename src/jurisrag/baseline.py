"""Static RAG baseline (TP2-style): one search with the raw question, one answer, same brief format.

The citation check is run and reported but never fed back: there is no loop.
"""

import json
import time

from . import config
from .brief import BRIEF_SCHEMA, check_citations
from .llm import ClaudeLLM, LLMError
from .store import CorpusStore
from .tools import ToolError, observation, search_cases

K = 5

SYSTEM = """Tu es un assistant de recherche en jurisprudence (Chambre sociale, licenciement). Réponds à la
question uniquement à partir des passages fournis, sous forme de note de preuves. Chaque affirmation cite
un passage par passage_id avec une citation copiée mot pour mot (au moins 8 mots contigus). Un passage de
zone 'moyens' est l'argument d'une partie, pas la position de la Cour. N'ajoute rien qui ne figure pas dans
les passages. Si les passages ne permettent pas de répondre : answer_status='insufficient_evidence'."""


def run_baseline(question: str, store: CorpusStore, llm: ClaudeLLM) -> dict:
    metrics = llm.reset_metrics()
    t0 = time.time()
    trace = []

    def add(kind, label, **detail):
        trace.append({"step": len(trace) + 1, "type": kind, "label": label, "detail": detail,
                      "elapsed_s": round(time.time() - t0, 2)})

    args = {"query": question, "k": K, "zone": "any"}
    add("TOOL", f"search_cases({json.dumps(args, ensure_ascii=False)})", tool="search_cases", args=args)
    try:
        hits = search_cases(store, **args)
    except ToolError as e:
        add("TOOL_ERROR", f"{e.code} : {e.message}")
        hits = {"results": [], "n_results": 0}
    add("OBSERVATION", observation("search_cases", hits) if hits["results"] else "0 résultat.")

    context = json.dumps(hits["results"], ensure_ascii=False, indent=1)
    final: dict
    try:
        resp = llm.complete(role="baseline", system=SYSTEM, effort=config.AGENT_EFFORT, json_schema=BRIEF_SCHEMA,
                            messages=[{"role": "user", "content": f"Question : {question}\n\nPassages :\n{context}"}])
        if resp.stop_reason in ("refusal", "max_tokens"):
            raise LLMError(f"Appel LLM interrompu (stop_reason={resp.stop_reason}).")
        brief = json.loads(resp.text)
        mech = check_citations(brief, store, {r["passage_id"] for r in hits["results"]})
        add("CHECK", f"Contrôle (non bouclé) : {len(mech['resolved'])} citations vérifiées mot pour mot, "
                     f"{len(mech['issues'])} défaut(s).", issues=mech["issues"])
        final = {"status": "unverified", "stop_reason": "réponse unique", "brief": brief,
                 "citations": mech["resolved"], "verification": {"mechanical": mech}}
        add("FINAL", f"Réponse ({brief['answer_status']}) — {len(mech['resolved'])} citations.")
    except LLMError as e:
        add("ERROR", str(e))
        final = {"status": "error", "stop_reason": str(e), "brief": None, "citations": [], "verification": None}
    return {
        "type": "RESULT", "question": question, "system": "baseline", "final": final, "trace": trace,
        "metrics": {**metrics.as_dict(), "tool_calls": 1, "tools_used": ["search_cases"], "drafts": 1,
                    "cases_read": [], "latency_s": round(time.time() - t0, 2), "model": llm.model},
    }
