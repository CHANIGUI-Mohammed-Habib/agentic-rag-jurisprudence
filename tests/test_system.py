"""Offline tests: corpus integrity, tools, citation checks, and agent control flow with a scripted LLM."""

import json

import pytest

from jurisrag import config
from jurisrag.agent import run_agent
from jurisrag.brief import check_citations, locate_quote
from jurisrag.llm import LLMResult, Metrics
from jurisrag.store import CorpusStore
from jurisrag.tools import ToolError, read_case, search_cases


@pytest.fixture(scope="module")
def store():
    return CorpusStore()


# ---------- corpus and tools ----------

def test_passages_are_exact_spans(store):
    for p in store.passages:
        assert store.cases[p["case_id"]]["text"][p["start"]:p["end"]] == p["text"]
        assert p["zone"] in ("expose", "moyens", "motivations", "dispositif")


def test_search_structure_and_diversity(store):
    out = search_cases(store, "barème indemnité licenciement sans cause réelle et sérieuse", 6, "motivations")
    assert 0 < out["n_results"] <= 6
    assert all(r["zone"] == "motivations" for r in out["results"])
    per_case = {}
    for r in out["results"]:
        per_case[r["case_id"]] = per_case.get(r["case_id"], 0) + 1
    assert max(per_case.values()) <= 2


@pytest.mark.parametrize("query,k,zone,code", [
    ("", 5, "any", "empty_query"),
    ("le la les de", 5, "any", "empty_query"),
    ("licenciement", 0, "any", "bad_argument"),
    ("licenciement", 5, "annexes", "bad_argument"),
])
def test_search_errors(store, query, k, zone, code):
    with pytest.raises(ToolError) as e:
        search_cases(store, query, k, zone)
    assert e.value.code == code


def test_read_case_by_id_and_number(store):
    case = next(iter(store.cases.values()))
    by_id = read_case(store, case["id"])
    by_number = read_case(store, case["number"])
    assert by_id["case"]["case_id"] == by_number["case"]["case_id"]
    with pytest.raises(ToolError) as e:
        read_case(store, "00-00.000")
    assert e.value.code == "unknown_case"


def test_locate_quote_tolerates_whitespace_and_apostrophes():
    text = "Mais attendu que l'arrêt\n retient  que le salarié"
    assert locate_quote(text, "attendu que l’arrêt retient que") is not None
    assert locate_quote(text, "attendu que l'arrêt décide") is None


def test_check_citations_rejects_unseen_and_paraphrased(store):
    p = store.passages[0]
    words = p["text"].split()
    good = {"passage_id": p["passage_id"], "quote": " ".join(words[:10])}
    brief = {"answer_status": "answered", "claims": [{"statement": "x", "citations": [good]}]}
    assert check_citations(brief, store, {p["passage_id"]})["ok"]
    assert not check_citations(brief, store, set())["ok"]  # never retrieved in this run
    brief["claims"][0]["citations"] = [{"passage_id": p["passage_id"], "quote": "texte inventé " * 5}]
    assert not check_citations(brief, store, {p["passage_id"]})["ok"]


# ---------- agent control flow with a scripted LLM ----------

class ScriptedLLM:
    """Stands in for ClaudeLLM. `policy(messages, tools)` returns tool_use inputs for the agent."""

    model = "scripted"

    def __init__(self, policy, verdict="supported"):
        self.policy, self.verdict = policy, verdict
        self.metrics = Metrics()
        self.offered: list[list[str]] = []
        self.n = 0

    def reset_metrics(self):
        self.metrics = Metrics()
        return self.metrics

    def complete(self, *, role, system, messages, effort, tools=None, json_schema=None, max_tokens=0):
        self.metrics.add(role, self.model, {"input_tokens": 1, "output_tokens": 1}, 0.0)
        if role == "verifier":
            n_claims = messages[0]["content"].count("## Affirmation")
            body = {"claims": [{"index": i, "verdict": self.verdict, "reason": "test"} for i in range(n_claims)],
                    "main_finding_supported": self.verdict == "supported", "unsourced_content": [], "feedback": ""}
            return LLMResult([{"type": "text", "text": json.dumps(body)}], "end_turn", self.model, {}, 0.0)
        self.offered.append([t["name"] for t in tools])
        name, args = self.policy(messages, tools)
        self.n += 1
        block = {"type": "tool_use", "id": f"tu_{self.n}", "name": name, "input": {"rationale": "test", **args}}
        return LLMResult([block], "tool_use", self.model, {}, 0.0)


def last_tool_payload(messages):
    for block in messages[-1]["content"]:
        if block.get("type") == "tool_result" and not block.get("is_error"):
            return json.loads(block["content"])
    return None


def brief_quoting(passage, n_words=12):
    quote = " ".join(passage["text"].split()[:n_words])
    return {"main_finding": "f", "answer_status": "answered", "qualifications": [], "evidence_gaps": [],
            "claims": [{"statement": "s", "citations": [{"passage_id": passage["passage_id"], "quote": quote}]}]}


def run(question, store, llm):
    events = list(run_agent(question, store, llm))
    return events[:-1], events[-1]


def test_simple_path_one_search_then_verified(store):
    def policy(messages, tools):
        if len(messages) == 1:
            return "search_cases", {"query": "barème licenciement sans cause réelle et sérieuse", "k": 5, "zone": "motivations"}
        return "submit_brief", brief_quoting(last_tool_payload(messages)["results"][0])

    trace, result = run("barème ?", store, ScriptedLLM(policy))
    assert result["final"]["status"] == "verified"
    assert result["metrics"]["tool_calls"] == 1
    kinds = [e["type"] for e in trace]
    assert kinds[-1] == "FINAL" and "CHECK" in kinds and "OBSERVATION" in kinds


def test_tool_error_is_visible_and_recoverable(store):
    def policy(messages, tools):
        if len(messages) == 1:
            return "read_case", {"case_id": "does-not-exist"}
        return "submit_brief", {"main_finding": "Rien trouvé.", "answer_status": "insufficient_evidence",
                                "claims": [], "qualifications": [], "evidence_gaps": ["affaire introuvable"]}

    trace, result = run("q", store, ScriptedLLM(policy))
    assert any(e["type"] == "TOOL_ERROR" and "unknown_case" in e["label"] for e in trace)
    assert result["final"]["status"] == "insufficient_evidence"


def test_rejected_drafts_end_in_explicit_gap(store):
    def policy(messages, tools):
        if len(messages) == 1:
            return "search_cases", {"query": "licenciement faute grave", "k": 3, "zone": "any"}
        pid = next(iter(store.by_passage_id))
        return "submit_brief", {"main_finding": "f", "answer_status": "answered", "qualifications": [],
                                "evidence_gaps": [], "claims": [{"statement": "s", "citations": [
                                    {"passage_id": pid, "quote": "une citation qui n'existe nulle part dans le texte"}]}]}

    trace, result = run("q", store, ScriptedLLM(policy))
    assert result["final"]["status"] == "gap_limit"
    assert result["metrics"]["drafts"] == config.MAX_DRAFTS
    assert result["final"]["brief"]["claims"] == []
    assert sum(e["type"] == "CHECK" for e in trace) == config.MAX_DRAFTS


def test_unsupported_claims_are_dropped_in_gap(store):
    def policy(messages, tools):
        if len(messages) == 1:
            return "search_cases", {"query": "licenciement faute grave", "k": 3, "zone": "any"}
        payload = last_tool_payload(messages)
        seen = payload["results"][0] if payload else store.passages[0]
        if payload is None:  # after a rejection, reuse the first passage seen in the run
            first = json.loads(messages[2]["content"][0]["content"])
            seen = first["results"][0]
        return "submit_brief", brief_quoting(seen)

    _, result = run("q", store, ScriptedLLM(policy, verdict="unsupported"))
    assert result["final"]["status"] == "gap_limit"
    assert result["final"]["brief"]["claims"] == []
    assert any("Non établi" in g for g in result["final"]["brief"]["evidence_gaps"])


def test_tool_budget_then_only_submit_offered(store):
    def policy(messages, tools):
        names = [t["name"] for t in tools]
        if "search_cases" in names:
            return "search_cases", {"query": f"licenciement {len(messages)}", "k": 2, "zone": "any"}
        return "submit_brief", {"main_finding": "Insuffisant.", "answer_status": "insufficient_evidence",
                                "claims": [], "qualifications": [], "evidence_gaps": ["budget"]}

    llm = ScriptedLLM(policy)
    trace, result = run("q", store, llm)
    assert result["metrics"]["tool_calls"] == config.MAX_TOOL_CALLS
    assert llm.offered[-1] == ["submit_brief"]
    assert any("Limite d'outils atteinte" in e["label"] for e in trace)
