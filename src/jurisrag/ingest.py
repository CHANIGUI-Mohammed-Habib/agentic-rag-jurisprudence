"""Offline ingestion: pinned dataset -> selected decisions -> passages with exact offsets -> BM25 index.

Run:  uv run python -m jurisrag.ingest
"""

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

from . import config
from .bm25 import BM25Index
from .text import tokenize

# Corpus selection rule (kept as data so the manifest records exactly what was applied).
RULE = {
    "jurisdiction": "Cour de cassation",
    "chamber": "Chambre sociale",
    "decision_date_min": "2020-01-01",
    "publication_contains": "Publié au Bulletin",
    "requires_zone": "motivations",
    "topic": "'licenci' appears in the official themes, the headnote (summary) or the court's reasoning "
             "(motivations zone)",
}
INDEXED_ZONES = ("expose", "moyens", "motivations", "dispositif")
TARGET_CHARS = 1500  # passage size target
HARD_MAX_CHARS = 2000

COLUMNS = ["id", "number", "ecli", "decision_date", "chamber", "solution", "publication",
           "themes", "summary", "zones", "text"]


def download_raw() -> str:
    return hf_hub_download(config.DATASET_ID, config.DATASET_FILE, repo_type="dataset",
                           revision=config.DATASET_REVISION, local_dir=config.RAW_DIR)


def select(rows: list[dict], funnel: Counter) -> list[dict]:
    kept = []
    for r in rows:
        funnel["chamber_and_date"] += 1
        if not any(RULE["publication_contains"] in p for p in (r["publication"] or [])):
            continue
        funnel["published_bulletin"] += 1
        if not (r["zones"] and r["zones"].get(RULE["requires_zone"])):
            continue
        funnel["has_motivations_zone"] += 1
        reasoning = " ".join(r["text"][z["start"] : z["end"]] for z in r["zones"]["motivations"])
        topic = " ".join(r["themes"] or []) + " " + (r["summary"] or "") + " " + reasoning
        if "licenci" not in topic.lower():
            continue
        funnel["dismissal_topic"] += 1
        kept.append(r)
    return kept


def _spans(text: str, start: int, end: int):
    """Yield trimmed paragraph spans inside [start, end)."""
    pos = start
    for m in re.finditer(r"\n\s*\n", text[start:end]):
        yield from _trim(text, pos, start + m.start())
        pos = start + m.end()
    yield from _trim(text, pos, end)


def _trim(text: str, s: int, e: int):
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    if e > s:
        yield (s, e)


def _split_long(text: str, s: int, e: int):
    """Split an over-long paragraph at sentence / clause boundaries."""
    while e - s > HARD_MAX_CHARS:
        window = text[s : s + TARGET_CHARS]
        cut = max(window.rfind(". "), window.rfind(" ; "), window.rfind(", "))
        cut = s + (cut + 2 if cut > TARGET_CHARS // 3 else TARGET_CHARS)
        yield from _trim(text, s, cut)
        s = cut
    yield from _trim(text, s, e)


def chunk_case(case: dict) -> list[dict]:
    text = case["text"]
    # Source zones sometimes end one char past the text (off-by-one on the last zone): clamp.
    zone_spans = sorted(
        (z["start"], min(z["end"], len(text)), name)
        for name in INDEXED_ZONES
        for z in (case["zones"].get(name) or [])
    )
    passages: list[dict] = []
    for zs, ze, zone in zone_spans:
        pieces = [p for s, e in _spans(text, zs, ze) for p in _split_long(text, s, e)]
        cur = None
        for s, e in pieces:
            if cur and e - cur[0] <= TARGET_CHARS:
                cur = (cur[0], e)
            else:
                if cur:
                    passages.append((zone, *cur))
                cur = (s, e)
        if cur:
            passages.append((zone, *cur))
    return [
        {"passage_id": f"{case['id']}-p{i:03d}", "case_id": case["id"], "zone": zone,
         "start": s, "end": e, "text": text[s:e]}
        for i, (zone, s, e) in enumerate(passages)
    ]


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    raw = download_raw()
    print(f"raw file: {raw}")
    table = pq.read_table(raw, columns=COLUMNS, filters=[
        ("chamber", "=", RULE["chamber"]), ("decision_date", ">=", RULE["decision_date_min"])])
    funnel: Counter = Counter()
    selected = select(table.to_pylist(), funnel)
    selected.sort(key=lambda r: (r["decision_date"], r["id"]))

    config.CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    all_passages, zone_counts = [], Counter()
    with open(config.CASES_FILE, "w", encoding="utf-8") as fc:
        for r in selected:
            case = {
                "id": r["id"], "number": r["number"], "ecli": r["ecli"],
                "decision_date": r["decision_date"], "chamber": r["chamber"],
                "solution": r["solution"], "publication": r["publication"],
                "themes": r["themes"] or [], "summary": r["summary"],
                "url": f"https://www.courdecassation.fr/decision/{r['id']}",
                "zones": {k: v for k, v in r["zones"].items() if v},
                "text": r["text"],
            }
            ps = chunk_case(case)
            for p in ps:
                assert case["text"][p["start"] : p["end"]] == p["text"]
                zone_counts[p["zone"]] += 1
            all_passages.extend(ps)
            fc.write(json.dumps(case, ensure_ascii=False) + "\n")

    with open(config.PASSAGES_FILE, "w", encoding="utf-8") as fp:
        for p in all_passages:
            fp.write(json.dumps(p, ensure_ascii=False) + "\n")

    BM25Index.build([tokenize(p["text"]) for p in all_passages]).save(config.INDEX_FILE)

    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": config.DATASET_ID,
        "revision": config.DATASET_REVISION,
        "file": config.DATASET_FILE,
        "file_sha256": sha256(raw),
        "selection_rule": RULE,
        "funnel": dict(funnel),
        "cases": len(selected),
        "passages": len(all_passages),
        "passages_per_zone": dict(zone_counts),
        "indexed_zones": list(INDEXED_ZONES),
        "omissions": [
            "zone 'introduction' (court header, parties, counsel) is kept in the case store but not indexed",
            "zone 'annexes' (lawyers' full pleadings appended to the decision) is kept in the store but not "
            "indexed: it is party argument, not the court's reasoning, and is often longer than the decision",
            "'summary' (official headnote) is stored as metadata only; it is editorial, so it is never cited",
            "unpublished decisions (Non publié) and decisions without a 'motivations' zone are excluded",
        ],
        "passage_chunking": f"paragraphs merged up to {TARGET_CHARS} chars, never across zones; "
                            f"paragraphs over {HARD_MAX_CHARS} chars split at sentence/clause boundaries",
        "index": "Okapi BM25 (k1=1.2, b=0.75), French Snowball stemming, accent folding, stopwords",
    }
    config.MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("funnel", "cases", "passages", "passages_per_zone")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
