"""Retrieval sanity check: use each decision's official headnote (never indexed) as a query and
measure whether search_cases returns that decision. Prints case-level recall@k and MRR.

Run:  uv run python scripts/eval_retrieval.py
"""

import json

from jurisrag import config
from jurisrag.store import CorpusStore

K = (1, 5, 10)


def main() -> None:
    store = CorpusStore()
    cases = [c for c in store.cases.values() if c.get("summary")]
    hits_at = {k: 0 for k in K}
    rr = 0.0
    for c in cases:
        query = c["summary"][:600]
        ranked = []
        for p, _ in store.search(query, k=40, per_case=1):
            ranked.append(p["case_id"])
        if c["id"] in ranked:
            rank = ranked.index(c["id"]) + 1
            rr += 1 / rank
            for k in K:
                hits_at[k] += rank <= k
    n = len(cases)
    report = {"queries": n, **{f"recall@{k}": round(hits_at[k] / n, 3) for k in K}, "mrr": round(rr / n, 3)}
    print(json.dumps(report, indent=2))
    (config.CORPUS_DIR / "retrieval_eval.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
