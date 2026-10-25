"""Run the three test scenarios through the agent and the static baseline; save full traces.

Run:  uv run python scripts/run_scenarios.py            (all scenarios)
      uv run python scripts/run_scenarios.py s2_multi_etapes
Output: runs/<scenario>/{agent,baseline}.json + trace.md, and runs/comparison.md
"""

import json
import sys

from jurisrag import config
from jurisrag.agent import run_agent
from jurisrag.baseline import run_baseline
from jurisrag.llm import ClaudeLLM
from jurisrag.render import run_md
from jurisrag.store import CorpusStore


def main(only: list[str]) -> None:
    store, llm = CorpusStore(), ClaudeLLM()
    scenarios = json.loads((config.ROOT / "scenarios.json").read_text(encoding="utf-8"))
    rows = []
    for sc in scenarios:
        if only and sc["id"] not in only:
            continue
        out = config.RUNS_DIR / sc["id"]
        out.mkdir(parents=True, exist_ok=True)
        print(f"\n=== {sc['title']}\n{sc['question']}")

        trace = []
        for ev in run_agent(sc["question"], store, llm):
            if ev["type"] == "RESULT":
                agent = ev
            else:
                trace.append(ev)
                print(f"  {ev['step']:>2} {ev['elapsed_s']:>6}s {ev['type']:<12} {ev['label'][:150]}")
        agent["trace"] = trace
        base = run_baseline(sc["question"], store, llm)

        for name, res in (("agent", agent), ("baseline", base)):
            (out / f"{name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        md = [f"# {sc['title']}", f"_Attendu : {sc['expectation']}_",
              run_md("Agentic RAG", agent, agent["trace"]), run_md("Baseline RAG statique", base, base["trace"])]
        (out / "trace.md").write_text("\n\n".join(md), encoding="utf-8")
        for name, res in (("agent", agent), ("baseline", base)):
            f, m = res["final"], res["metrics"]
            mech = (f.get("verification") or {}).get("mechanical") or {}
            n_cit = sum(len(c["citations"]) for c in (f["brief"] or {}).get("claims") or [])
            rows.append(f"| {sc['id']} | {name} | {f['status']} | {len(f['citations'])}/{n_cit} "
                        f"| {len(mech.get('issues', []))} | {m['tool_calls']} | {m['llm_calls']} "
                        f"| {m['latency_s']} | {m['cost_usd']} |")
        print(f"  -> agent {agent['final']['status']}, baseline {base['final']['status']}; saved in {out}")

    table = ["| Scénario | Système | Statut | Citations valides | Défauts citation (final) | Outils | Appels LLM | Latence (s) | Coût ($) |",
             "|---|---|---|---|---|---|---|---|---|"] + rows
    (config.RUNS_DIR / "comparison.md").write_text("\n".join(table) + "\n", encoding="utf-8")
    print("\n" + "\n".join(table))


if __name__ == "__main__":
    main(sys.argv[1:])
