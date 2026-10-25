"""Evidence verifier: mechanical citation check, then an LLM check that cited text supports each claim."""

import json

from . import config
from .brief import check_citations
from .llm import ClaudeLLM
from .store import CorpusStore
from .tools import ZONE_LABELS

VERDICTS = ["supported", "partially_supported", "unsupported"]

SUPPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "verdict": {"type": "string", "enum": VERDICTS},
                    "reason": {"type": "string"},
                },
                "required": ["index", "verdict", "reason"],
                "additionalProperties": False,
            },
        },
        "main_finding_supported": {"type": "boolean"},
        "unsourced_content": {"type": "array", "items": {"type": "string"},
                              "description": "Éléments de la note absents des passages cités."},
        "feedback": {"type": "string", "description": "Consigne courte de correction pour l'agent (vide si tout est étayé)."},
    },
    "required": ["claims", "main_finding_supported", "unsourced_content", "feedback"],
    "additionalProperties": False,
}

SYSTEM = """Tu es le vérificateur d'une note de preuves juridique. Tu ne connais que les passages fournis.
Pour chaque affirmation, juge si les passages cités l'établissent :
- supported : le texte cité établit l'affirmation telle qu'elle est formulée ;
- partially_supported : l'affirmation va au-delà du texte (généralisation, portée, date, chiffre ou nuance absents) ;
- unsupported : le texte ne l'établit pas, ou une prétention d'une partie (zone 'moyens') est présentée comme la position de la Cour.
Vérifie aussi que le constat principal découle des affirmations étayées, et liste tout élément de fond
(règle, article, date, solution, fait) présent dans le constat, les nuances ou les affirmations mais absent des passages.
N'utilise aucune connaissance juridique extérieure pour compléter les passages. Réponds en français."""


def _support_prompt(question: str, brief: dict, store: CorpusStore) -> str:
    lines = [f"Question : {question}", "", "Note à vérifier :",
             json.dumps({k: brief.get(k) for k in ("main_finding", "answer_status", "qualifications", "evidence_gaps")},
                        ensure_ascii=False, indent=1), ""]
    for i, claim in enumerate(brief.get("claims") or []):
        lines.append(f"## Affirmation {i}\n{claim['statement']}")
        for c in claim.get("citations") or []:
            p = store.by_passage_id[c["passage_id"]]
            case = store.cases[p["case_id"]]
            lines.append(f"- Passage {p['passage_id']} (pourvoi {case['number']}, {case['decision_date']}, "
                         f"zone {p['zone']} = {ZONE_LABELS[p['zone']]})\n  Citation invoquée : « {c['quote']} »\n"
                         f"  Texte complet du passage : {p['text']}")
        lines.append("")
    return "\n".join(lines)


def verify(question: str, brief: dict, store: CorpusStore, seen_ids: set[str], llm: ClaudeLLM) -> dict:
    """Returns {"passed", "mechanical", "support", "issues", "supported_claims"}."""
    mech = check_citations(brief, store, seen_ids)
    result = {"passed": False, "mechanical": mech, "support": None, "issues": list(mech["issues"]),
              "supported_claims": []}
    if not mech["ok"]:
        return result  # no point asking the LLM about citations that do not exist

    resp = llm.complete(role="verifier", system=SYSTEM, effort=config.VERIFIER_EFFORT,
                        messages=[{"role": "user", "content": _support_prompt(question, brief, store)}],
                        json_schema=SUPPORT_SCHEMA)
    if resp.stop_reason in ("refusal", "max_tokens"):
        result["issues"].append(f"Vérificateur interrompu ({resp.stop_reason}).")
        return result
    support = json.loads(resp.text)
    result["support"] = support

    verdicts = {c["index"]: c for c in support["claims"]}
    for i, claim in enumerate(brief.get("claims") or []):
        v = verdicts.get(i)
        if v is None:
            result["issues"].append(f"Affirmation {i + 1} non évaluée par le vérificateur.")
        elif v["verdict"] == "supported":
            result["supported_claims"].append(i)
        else:
            result["issues"].append(f"Affirmation {i + 1} {v['verdict']} : {v['reason']}")
    if not support["main_finding_supported"]:
        result["issues"].append("Le constat principal ne découle pas des affirmations étayées.")
    for item in support["unsourced_content"]:
        result["issues"].append(f"Élément non sourcé : {item}")
    if support["feedback"] and result["issues"]:
        result["issues"].append(f"Consigne : {support['feedback']}")
    result["passed"] = not result["issues"]
    return result
