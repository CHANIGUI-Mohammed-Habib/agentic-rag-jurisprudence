"""Markdown rendering of traces and briefs (used for saved runs and the report)."""

STATUS_LABELS = {
    "verified": "Vérifiée",
    "insufficient_evidence": "Preuves insuffisantes (déclaré et vérifié)",
    "gap_limit": "Lacune explicite (limite de vérification atteinte)",
    "unverified": "Non vérifiée (baseline)",
    "error": "Erreur contrôlée",
}


def trace_md(trace: list[dict]) -> str:
    rows = ["| Étape | t (s) | Type | Détail |", "|---|---|---|---|"]
    for e in trace:
        label = e["label"].replace("|", "\\|").replace("\n", " ")
        rows.append(f"| {e['step']} | {e.get('elapsed_s', '')} | {e['type']} | {label} |")
        for issue in (e.get("detail") or {}).get("issues") or []:
            rows.append(f"|  |  |  | ↳ {issue.replace('|', '\\|')} |")
    return "\n".join(rows)


def brief_md(final: dict) -> str:
    out = [f"**Statut : {STATUS_LABELS.get(final['status'], final['status'])}** — arrêt : {final['stop_reason']}", ""]
    brief = final.get("brief")
    if not brief:
        return "\n".join(out)
    out += ["**Constat principal.** " + brief["main_finding"], ""]
    by_claim: dict[int, list[dict]] = {}
    for c in final.get("citations") or []:
        by_claim.setdefault(c["claim_index"], []).append(c)
    if brief["claims"]:
        out.append("**Décisions et passages à l'appui**")
        for i, claim in enumerate(brief["claims"]):
            out.append(f"{i + 1}. {claim['statement']}")
            for c in by_claim.get(i, []) or []:
                out.append(f"   - Cass. soc., {c['date']}, n° {c['number']} ({c['solution']}) — zone `{c['zone']}`, "
                           f"car. {c['start']}–{c['end']}, `{c['passage_id']}` : « {c['quote']} »")
        out.append("")
    if brief["qualifications"]:
        out += ["**Nuances**"] + [f"- {q}" for q in brief["qualifications"]] + [""]
    if brief["evidence_gaps"]:
        out += ["**Lacunes de preuve**"] + [f"- {g}" for g in brief["evidence_gaps"]] + [""]
    sources = {c["case_id"]: c for c in final.get("citations") or []}
    if sources:
        out.append("**Sources (corpus)**")
        out += [f"- n° {c['number']}, {c['date']} — {c['url']}" for c in sources.values()]
    return "\n".join(out)


def metrics_md(m: dict) -> str:
    return (f"Modèle `{m['model']}` · appels LLM {m['llm_calls']} {m['calls_by_role']} · outils {m['tool_calls']} "
            f"{m['tools_used']} · notes soumises {m['drafts']} · tokens in/out {m['input_tokens']}/{m['output_tokens']} · "
            f"latence {m['latency_s']} s · coût estimé ${m['cost_usd']}")


def run_md(title: str, result: dict, trace: list[dict]) -> str:
    return "\n\n".join([f"### {title}", f"**Question :** {result['question']}", metrics_md(result["metrics"]),
                        "#### Trace", trace_md(trace), "#### Réponse", brief_md(result["final"])])
