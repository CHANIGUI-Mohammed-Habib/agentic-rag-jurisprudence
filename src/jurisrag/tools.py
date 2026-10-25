"""The two agent tools (search_cases, read_case) and their Claude tool definitions.

Tools return plain dicts. Bad input, unknown IDs and storage problems raise ToolError, which the
agent turns into a visible TOOL_ERROR trace row and an `is_error` tool_result for the model.
"""

from .store import CorpusStore, StorageError
from .text import tokenize

ZONES = ["any", "expose", "moyens", "motivations", "dispositif"]
ZONE_LABELS = {
    "expose": "faits et procédure",
    "moyens": "arguments du demandeur au pourvoi (pas la position de la Cour)",
    "motivations": "raisonnement de la Cour",
    "dispositif": "décision (PAR CES MOTIFS)",
}


class ToolError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message

    def as_dict(self) -> dict:
        return {"error": self.code, "message": self.message}


def _case_meta(c: dict) -> dict:
    return {"case_id": c["id"], "number": c["number"], "date": c["decision_date"],
            "solution": c["solution"], "themes": c["themes"][:6], "url": c["url"]}


def search_cases(store: CorpusStore, query: str, k: int = 5, zone: str = "any") -> dict:
    if not isinstance(query, str) or not query.strip():
        raise ToolError("empty_query", "query is empty")
    if not tokenize(query):
        raise ToolError("empty_query", "query has no searchable terms after stopword removal")
    if not isinstance(k, int) or not 1 <= k <= 10:
        raise ToolError("bad_argument", f"k must be an integer between 1 and 10 (got {k!r})")
    if zone not in ZONES:
        raise ToolError("bad_argument", f"zone must be one of {ZONES} (got {zone!r})")
    try:
        hits = store.search(query, k, zone)
    except StorageError as e:
        raise ToolError("storage_error", str(e)) from e
    results = []
    for p, score in hits:
        c = store.cases[p["case_id"]]
        results.append({
            "passage_id": p["passage_id"], "score": round(score, 2),
            "zone": p["zone"], "zone_label": ZONE_LABELS[p["zone"]],
            **_case_meta(c), "text": p["text"],
        })
    return {"query": query, "k": k, "zone": zone, "n_results": len(results), "results": results}


def read_case(store: CorpusStore, case_id: str) -> dict:
    if not isinstance(case_id, str) or not case_id.strip():
        raise ToolError("bad_argument", "case_id is empty")
    cid = store.resolve_case_id(case_id)
    if cid is None:
        raise ToolError("unknown_case", f"no decision with id or number {case_id!r} in the corpus; "
                                        "use a case_id returned by search_cases")
    c = store.cases[cid]
    passages = [
        {"passage_id": p["passage_id"], "zone": p["zone"], "zone_label": ZONE_LABELS[p["zone"]],
         "text": p["text"]}
        for p in store.passages_of.get(cid, [])
    ]
    return {"case": _case_meta(c), "n_passages": len(passages), "passages": passages}


def run_tool(store: CorpusStore, name: str, args: dict) -> dict:
    if name == "search_cases":
        return search_cases(store, args.get("query", ""), args.get("k", 5), args.get("zone", "any"))
    if name == "read_case":
        return read_case(store, args.get("case_id", ""))
    raise ToolError("unknown_tool", f"no tool named {name!r}")


def observation(name: str, result: dict) -> str:
    """One-line summary of a tool result for the trace."""
    if name == "search_cases":
        cases = {r["number"] for r in result["results"]}
        zones = {}
        for r in result["results"]:
            zones[r["zone"]] = zones.get(r["zone"], 0) + 1
        z = ", ".join(f"{n} {k}" for k, n in zones.items())
        if not result["results"]:
            return "0 résultat."
        return (f"{result['n_results']} passages dans {len(cases)} décisions "
                f"({', '.join(sorted(cases))}) ; zones : {z}. Meilleur score {result['results'][0]['score']}.")
    if name == "read_case":
        c = result["case"]
        motiv = sum(p["zone"] == "motivations" for p in result["passages"])
        return (f"Décision {c['number']} du {c['date']} ({c['solution']}) : {result['n_passages']} passages, "
                f"dont {motiv} de motivation.")
    return "ok"


_RATIONALE = {"type": "string", "description": "Une phrase courte : pourquoi cette action maintenant."}

TOOL_DEFS = [
    {
        "name": "search_cases",
        "description": (
            "Recherche lexicale (BM25) dans les passages des arrêts publiés de la Chambre sociale "
            "(2020-2025) portant sur le licenciement. Renvoie des pistes : passages classés avec "
            "identifiant, zone de la décision et métadonnées de l'affaire. Au plus 2 passages par affaire. "
            "Utiliser des mots-clés juridiques précis en français. zone='motivations' restreint au "
            "raisonnement de la Cour ; 'moyens' sont les arguments d'une partie, pas la position de la Cour."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "rationale": _RATIONALE,
                "query": {"type": "string", "description": "Mots-clés de recherche en français."},
                "k": {"type": "integer", "description": "Nombre de passages (1-10)."},
                "zone": {"type": "string", "enum": ZONES},
            },
            "required": ["rationale", "query", "k", "zone"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "read_case",
        "description": (
            "Ouvre une décision du corpus et renvoie tous ses passages indexés (exposé, moyens, "
            "motivations, dispositif) avec leurs identifiants. À utiliser quand un passage de recherche ne "
            "suffit pas : vérifier le raisonnement complet, la solution, ou le contexte d'une affaire."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "rationale": _RATIONALE,
                "case_id": {"type": "string", "description": "case_id renvoyé par search_cases, ou numéro de pourvoi."},
            },
            "required": ["rationale", "case_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]
