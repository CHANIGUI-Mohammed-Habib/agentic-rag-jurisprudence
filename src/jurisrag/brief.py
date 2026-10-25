"""Evidence brief format (shared by agent and baseline) and the mechanical citation check."""

import re

from .store import CorpusStore

ANSWER_STATUS = ["answered", "partial", "insufficient_evidence"]
MIN_QUOTE_WORDS = 6

BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "main_finding": {"type": "string", "description": "Constat principal, 1 à 3 phrases, fondé sur les affirmations citées."},
        "answer_status": {"type": "string", "enum": ANSWER_STATUS},
        "claims": {
            "type": "array",
            "description": "Affirmations de fond, chacune appuyée par au moins une citation exacte.",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "passage_id": {"type": "string"},
                                "quote": {"type": "string", "description": "Copie exacte et contiguë du passage, sans ellipse."},
                            },
                            "required": ["passage_id", "quote"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["statement", "citations"],
                "additionalProperties": False,
            },
        },
        "qualifications": {"type": "array", "items": {"type": "string"},
                           "description": "Nuances et limites de portée (sans fait nouveau non sourcé)."},
        "evidence_gaps": {"type": "array", "items": {"type": "string"},
                          "description": "Ce que le corpus ne permet pas d'établir."},
    },
    "required": ["main_finding", "answer_status", "claims", "qualifications", "evidence_gaps"],
    "additionalProperties": False,
}

_APOS = "['’ʼ]"
_QUOTES = "[«»\"“”]"


def _token_pattern(tok: str) -> str:
    out = []
    for ch in tok:
        if ch in "'’ʼ":
            out.append(_APOS)
        elif ch in "«»\"“”":
            out.append(_QUOTES)
        else:
            out.append(re.escape(ch))
    return "".join(out)


def locate_quote(text: str, quote: str) -> tuple[int, int] | None:
    """Find `quote` verbatim in `text`, tolerating only whitespace and apostrophe/quote-mark variants."""
    tokens = quote.strip().strip("«»\"“” ").split()
    if not tokens:
        return None
    m = re.search(r"\s+".join(_token_pattern(t) for t in tokens), text)
    return (m.start(), m.end()) if m else None


def check_citations(brief: dict, store: CorpusStore, seen_ids: set[str]) -> dict:
    """Mechanical verification: IDs exist and were retrieved in this run, quotes are verbatim.

    Returns {"ok": bool, "issues": [str], "resolved": [citation with absolute offsets]}.
    """
    issues, resolved = [], []
    claims = brief.get("claims") or []
    if brief.get("answer_status") in ("answered", "partial") and not claims:
        issues.append("Aucune affirmation citée : une réponse 'answered'/'partial' exige des preuves.")
    for i, claim in enumerate(claims):
        cites = claim.get("citations") or []
        if not cites:
            issues.append(f"Affirmation {i + 1} sans citation : « {claim.get('statement', '')[:80]} »")
        for c in cites:
            pid, quote = c.get("passage_id", ""), c.get("quote", "")
            p = store.by_passage_id.get(pid)
            if p is None:
                issues.append(f"Affirmation {i + 1} : passage_id inconnu {pid!r}.")
                continue
            if pid not in seen_ids:
                issues.append(f"Affirmation {i + 1} : le passage {pid} n'a pas été obtenu par un outil pendant ce run.")
                continue
            if len(quote.split()) < MIN_QUOTE_WORDS:
                issues.append(f"Affirmation {i + 1} : citation trop courte dans {pid} (minimum {MIN_QUOTE_WORDS} mots).")
                continue
            span = locate_quote(p["text"], quote)
            if span is None:
                issues.append(f"Affirmation {i + 1} : la citation n'apparaît pas mot pour mot dans {pid} : « {quote[:90]} »")
                continue
            case = store.cases[p["case_id"]]
            start, end = p["start"] + span[0], p["start"] + span[1]
            resolved.append({
                "claim_index": i, "passage_id": pid, "case_id": case["id"], "number": case["number"],
                "date": case["decision_date"], "solution": case["solution"], "zone": p["zone"],
                "quote": case["text"][start:end], "start": start, "end": end, "url": case["url"],
            })
    return {"ok": not issues, "issues": issues, "resolved": resolved}
