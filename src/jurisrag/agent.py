"""Agentic RAG as an explicit LangGraph state machine.

    decide ──(search/read)──> tools ──> decide
       │                                  ▲
       └──(submit_brief)──> verify ──fail─┘   (while drafts and turns remain)
                              ├─ pass ──────> finalize   (verified brief)
                              └─ fail, limit > gap        (explicit evidence gap)
    any controlled error ─────────────────> fail

Stop conditions: verified brief, MAX_TOOL_CALLS tool calls (then only submit_brief is offered),
MAX_DRAFTS rejected drafts, MAX_LLM_TURNS decisions, or an API/refusal error.
"""

import json
import operator
import time
from typing import Annotated, Iterator, TypedDict

from langgraph.graph import END, START, StateGraph

from . import config
from .brief import BRIEF_SCHEMA
from .llm import ClaudeLLM, LLMError
from .store import CorpusStore
from .tools import TOOL_DEFS, ToolError, observation, run_tool
from .verifier import verify

SUBMIT_TOOL = {
    "name": "submit_brief",
    "description": "Soumet la note de preuves finale au vérificateur. À appeler seul, quand les preuves "
                   "suffisent ou quand il est établi que le corpus ne permet pas de répondre.",
    "input_schema": {
        **BRIEF_SCHEMA,
        "properties": {"rationale": {"type": "string"}, **BRIEF_SCHEMA["properties"]},
        "required": ["rationale", *BRIEF_SCHEMA["required"]],
    },
    "strict": True,
}

SYSTEM = f"""Tu es un assistant de recherche en jurisprudence. Ton corpus : les arrêts de la Chambre sociale
de la Cour de cassation publiés au Bulletin (2020 à mars 2025) qui portent sur le licenciement. Tu rédiges
une note de preuves citées, pas une consultation juridique.

Outils : search_cases trouve des pistes (passages classés) ; read_case ouvre le texte original d'une
décision ; submit_brief remet la note au vérificateur.

Décide toi-même de la prochaine action :
- si des passages répondent directement à la question, soumets la note sans autre appel ;
- ouvre une décision (read_case) quand la question porte sur une affaire précise, sa solution ou son
  raisonnement, et que les passages de recherche ne suffisent pas ;
- si les résultats sont hors sujet, reformule (autres termes juridiques, zone='motivations') plutôt que
  de répéter la même requête ;
- budget : au plus {config.MAX_TOOL_CALLS} appels search_cases/read_case au total.

Règles de la note :
- chaque affirmation cite au moins un passage reçu pendant cette session, par passage_id, avec une
  citation copiée mot pour mot (au moins 8 mots contigus, sans ellipse ni reformulation) ;
- un passage de zone 'moyens' rapporte l'argument d'une partie : ne le présente jamais comme la
  position de la Cour ; appuie les règles sur 'motivations' et les solutions sur 'dispositif' ;
- n'ajoute rien qui ne figure pas dans les passages (pas de connaissance générale, ni article, date ou
  solution non cités) ; mentionne le numéro de pourvoi et la date des décisions citées ;
- si le corpus ne permet pas de répondre, ne comble pas : answer_status='insufficient_evidence' et
  explique précisément ce qui manque dans evidence_gaps.
Le champ rationale de chaque outil : une phrase opérationnelle courte (pas de raisonnement détaillé)."""


class AgentState(TypedDict, total=False):
    question: str
    messages: list[dict]
    evidence: dict  # passage_id -> passage seen by the agent (search results or read_case)
    cases_read: list[str]
    pending: list[dict]  # tool_use blocks awaiting execution
    draft: dict | None
    verification: dict | None
    tool_calls: int
    drafts: int
    llm_turns: int
    status: str
    error: str | None
    final: dict | None
    trace: Annotated[list[dict], operator.add]


def event(kind: str, label: str, **detail) -> dict:
    return {"type": kind, "label": label, "detail": detail, "ts": time.time()}


def _brief_from(tool_input: dict) -> dict:
    return {k: tool_input.get(k) for k in BRIEF_SCHEMA["properties"]}


def build_graph(store: CorpusStore, llm: ClaudeLLM):
    def decide(state: AgentState) -> dict:
        budget_left = config.MAX_TOOL_CALLS - state["tool_calls"]
        tools = (TOOL_DEFS + [SUBMIT_TOOL]) if budget_left > 0 else [SUBMIT_TOOL]
        try:
            resp = llm.complete(role="agent", system=SYSTEM, messages=state["messages"], tools=tools,
                                effort=config.AGENT_EFFORT)
        except LLMError as e:
            return {"status": "error", "error": str(e), "trace": [event("ERROR", str(e))]}
        turns = state["llm_turns"] + 1
        if resp.stop_reason in ("refusal", "max_tokens"):
            msg = f"Appel LLM interrompu (stop_reason={resp.stop_reason})."
            return {"llm_turns": turns, "status": "error", "error": msg, "trace": [event("ERROR", msg)]}

        messages = state["messages"] + [{"role": "assistant", "content": resp.content}]
        calls = resp.tool_uses
        if not calls:
            nudge = "Utilise un outil : search_cases, read_case ou submit_brief."
            return {"messages": messages + [{"role": "user", "content": nudge}], "pending": [],
                    "llm_turns": turns,
                    "trace": [event("DECISION", "Réponse sans outil : relance de l'agent.", text=resp.text[:300])]}
        trace = []
        for c in calls:
            why = c["input"].get("rationale", "")
            action = {"search_cases": "Rechercher", "read_case": "Lire la décision",
                      "submit_brief": "Soumettre la note au vérificateur"}.get(c["name"], c["name"])
            trace.append(event("DECISION", f"{action} — {why}", tool=c["name"]))
        return {"messages": messages, "pending": calls, "llm_turns": turns, "trace": trace}

    def route_decide(state: AgentState) -> str:
        if state.get("status") == "error":
            return "fail"
        if any(c["name"] == "submit_brief" for c in state["pending"]):
            return "verify"
        if state["pending"]:
            return "tools"
        return "decide" if state["llm_turns"] < config.MAX_LLM_TURNS else "fail"

    def tools(state: AgentState) -> dict:
        evidence = dict(state["evidence"])
        cases_read = list(state["cases_read"])
        n = state["tool_calls"]
        results, trace = [], []
        for c in state["pending"]:
            args = {k: v for k, v in c["input"].items() if k != "rationale"}
            if n >= config.MAX_TOOL_CALLS:
                err = ToolError("budget_exhausted", f"budget de {config.MAX_TOOL_CALLS} appels d'outils atteint")
                trace.append(event("TOOL_ERROR", f"{c['name']} non exécuté : {err.message}", tool=c["name"], args=args))
                results.append({"type": "tool_result", "tool_use_id": c["id"], "is_error": True,
                                "content": json.dumps(err.as_dict(), ensure_ascii=False)})
                continue
            n += 1
            trace.append(event("TOOL", f"{c['name']}({json.dumps(args, ensure_ascii=False)})", tool=c["name"], args=args))
            t0 = time.perf_counter()
            try:
                out = run_tool(store, c["name"], args)
            except ToolError as e:
                trace.append(event("TOOL_ERROR", f"{e.code} : {e.message}", tool=c["name"], args=args))
                results.append({"type": "tool_result", "tool_use_id": c["id"], "is_error": True,
                                "content": json.dumps(e.as_dict(), ensure_ascii=False)})
                continue
            ms = round((time.perf_counter() - t0) * 1000)
            if c["name"] == "search_cases":
                for r in out["results"]:
                    evidence[r["passage_id"]] = store.by_passage_id[r["passage_id"]]
            else:
                cases_read.append(out["case"]["case_id"])
                for p in out["passages"]:
                    evidence[p["passage_id"]] = store.by_passage_id[p["passage_id"]]
            trace.append(event("OBSERVATION", observation(c["name"], out), tool=c["name"], latency_ms=ms,
                               passage_ids=[r["passage_id"] for r in out.get("results", [])] or None,
                               case=out.get("case")))
            results.append({"type": "tool_result", "tool_use_id": c["id"],
                            "content": json.dumps(out, ensure_ascii=False)})
        content: list[dict] = list(results)
        if n >= config.MAX_TOOL_CALLS:
            content.append({"type": "text", "text": (
                f"Budget d'outils épuisé ({n}/{config.MAX_TOOL_CALLS}). Appelle maintenant submit_brief avec les "
                "seuls passages déjà reçus, et déclare dans evidence_gaps ce qui n'a pas pu être établi.")})
            trace.append(event("CHECK", f"Limite d'outils atteinte ({n}/{config.MAX_TOOL_CALLS}) : seule la soumission reste possible."))
        return {"messages": state["messages"] + [{"role": "user", "content": content}],
                "evidence": evidence, "cases_read": cases_read, "tool_calls": n, "pending": [], "trace": trace}

    def verify_node(state: AgentState) -> dict:
        submit = next(c for c in state["pending"] if c["name"] == "submit_brief")
        draft = _brief_from(submit["input"])
        drafts = state["drafts"] + 1
        try:
            v = verify(state["question"], draft, store, set(state["evidence"]), llm)
        except LLMError as e:
            return {"draft": draft, "drafts": drafts, "status": "error", "error": str(e),
                    "trace": [event("ERROR", str(e))]}
        mech = v["mechanical"]
        n_cit = sum(len(c["citations"]) for c in draft["claims"] or [])
        label = (f"Preuves suffisantes : {'oui' if v['passed'] else 'non'} — {len(draft['claims'] or [])} affirmations, "
                 f"{len(mech['resolved'])}/{n_cit} citations vérifiées mot pour mot"
                 + ("" if v["support"] is None else f", {len(v['supported_claims'])} affirmations étayées")
                 + f" (note {drafts}/{config.MAX_DRAFTS}).")
        trace = [event("CHECK", label, passed=v["passed"], issues=v["issues"])]
        update = {"draft": draft, "drafts": drafts, "verification": v, "trace": trace}
        if v["passed"]:
            return update

        # Rejected: give the model the exact failures, as the result of its submit_brief call.
        remaining = config.MAX_TOOL_CALLS - state["tool_calls"]
        hint = (f"Il te reste {remaining} appel(s) d'outils : relance une recherche ou lis une décision si des preuves manquent."
                if remaining > 0 else
                "Plus d'appel d'outil possible : retire les affirmations non étayées et déclare les lacunes.")
        feedback = "Note rejetée par le vérificateur :\n- " + "\n- ".join(v["issues"]) + "\n" + hint
        results = []
        for c in state["pending"]:
            text = feedback if c is submit else "Non exécuté : submit_brief doit être appelé seul."
            results.append({"type": "tool_result", "tool_use_id": c["id"], "is_error": True, "content": text})
        update["messages"] = state["messages"] + [{"role": "user", "content": results}]
        update["pending"] = []
        trace.append(event("DECISION", "Vérification échouée : retour à l'agent avec les défauts relevés."
                           if drafts < config.MAX_DRAFTS and state["llm_turns"] < config.MAX_LLM_TURNS
                           else "Vérification échouée et limite atteinte : arrêt avec lacune explicite."))
        return update

    def route_verify(state: AgentState) -> str:
        if state.get("status") == "error":
            return "fail"
        if state["verification"]["passed"]:
            return "finalize"
        if state["drafts"] < config.MAX_DRAFTS and state["llm_turns"] < config.MAX_LLM_TURNS:
            return "decide"
        return "gap"

    def finalize(state: AgentState) -> dict:
        draft, v = state["draft"], state["verification"]
        status = "insufficient_evidence" if draft["answer_status"] == "insufficient_evidence" else "verified"
        final = {"status": status, "stop_reason": "note vérifiée", "brief": draft,
                 "citations": v["mechanical"]["resolved"], "verification": v}
        return {"final": final, "status": status,
                "trace": [event("FINAL", f"Note {status} — {len(final['citations'])} citations, "
                                         f"{len(set(c['case_id'] for c in final['citations']))} décisions.")]}

    def gap(state: AgentState) -> dict:
        draft = state.get("draft") or {"main_finding": "", "claims": [], "qualifications": [], "evidence_gaps": []}
        v = state.get("verification") or {"supported_claims": [], "mechanical": {"resolved": []}, "issues": []}
        keep = set(v["supported_claims"])
        claims = [c for i, c in enumerate(draft["claims"] or []) if i in keep]
        dropped = [c["statement"] for i, c in enumerate(draft["claims"] or []) if i not in keep]
        brief = {
            "main_finding": ("Le corpus ne permet pas d'établir une réponse vérifiée à cette question."
                             + (" Seules les affirmations ci-dessous ont été vérifiées." if claims else "")),
            "answer_status": "insufficient_evidence",
            "claims": claims,
            "qualifications": draft.get("qualifications") or [],
            "evidence_gaps": (draft.get("evidence_gaps") or []) + [f"Non établi par les passages cités : {s}" for s in dropped],
        }
        citations = [c for c in v["mechanical"]["resolved"] if c["claim_index"] in keep]
        final = {"status": "gap_limit", "stop_reason": "limite de vérification atteinte",
                 "brief": brief, "citations": citations, "verification": v}
        return {"final": final, "status": "gap_limit",
                "trace": [event("FINAL", f"Lacune explicite : {len(claims)} affirmation(s) vérifiée(s) conservée(s), "
                                         f"{len(dropped)} retirée(s).")]}

    def fail(state: AgentState) -> dict:
        reason = state.get("error") or f"limite de {config.MAX_LLM_TURNS} décisions atteinte sans note"
        final = {"status": "error", "stop_reason": reason, "brief": None, "citations": [], "verification": None}
        return {"final": final, "status": "error", "trace": [event("FINAL", f"Arrêt sur erreur contrôlée : {reason}")]}

    g = StateGraph(AgentState)
    g.add_node("decide", decide)
    g.add_node("tools", tools)
    g.add_node("verify", verify_node)
    g.add_node("finalize", finalize)
    g.add_node("gap", gap)
    g.add_node("fail", fail)
    g.add_edge(START, "decide")
    g.add_conditional_edges("decide", route_decide, ["tools", "verify", "decide", "fail"])
    g.add_edge("tools", "decide")
    g.add_conditional_edges("verify", route_verify, ["finalize", "decide", "gap", "fail"])
    for n in ("finalize", "gap", "fail"):
        g.add_edge(n, END)
    return g.compile()


def run_agent(question: str, store: CorpusStore, llm: ClaudeLLM) -> Iterator[dict]:
    """Stream trace events as the graph runs; the last yielded item is {"type": "RESULT", ...}."""
    metrics = llm.reset_metrics()
    graph = build_graph(store, llm)
    t0 = time.time()
    init: AgentState = {
        "question": question,
        "messages": [{"role": "user", "content": f"Question : {question}"}],
        "evidence": {}, "cases_read": [], "pending": [], "draft": None, "verification": None,
        "tool_calls": 0, "drafts": 0, "llm_turns": 0, "status": "running", "error": None, "final": None,
        "trace": [event("DECISION", "Nouvelle question reçue : l'agent planifie.")],
    }
    step, state = 0, None
    for state in graph.stream(init, stream_mode="values", config={"recursion_limit": 60}):
        for ev in state["trace"][step:]:
            step += 1
            yield {**ev, "step": step, "elapsed_s": round(ev["ts"] - t0, 2)}
    tools_used = [ev["detail"]["tool"] for ev in state["trace"] if ev["type"] == "TOOL"]
    yield {
        "type": "RESULT", "question": question, "system": "agent", "final": state["final"],
        "metrics": {**metrics.as_dict(), "tool_calls": state["tool_calls"], "tools_used": tools_used,
                    "drafts": state["drafts"], "cases_read": state["cases_read"],
                    "latency_s": round(time.time() - t0, 2), "model": llm.model},
    }
