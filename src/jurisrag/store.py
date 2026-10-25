"""Case store (original decisions) + passage index (leads). Loaded once, read-only."""

import json
from functools import cached_property
from pathlib import Path

import numpy as np

from . import config
from .bm25 import BM25Index
from .text import tokenize


class StorageError(RuntimeError):
    pass


class CorpusStore:
    def __init__(self, corpus_dir: Path = config.CORPUS_DIR):
        self.dir = corpus_dir
        try:
            self.cases = {c["id"]: c for c in _jsonl(corpus_dir / config.CASES_FILE.name)}
            self.passages = list(_jsonl(corpus_dir / config.PASSAGES_FILE.name))
            self.index = BM25Index.load(corpus_dir / config.INDEX_FILE.name)
            self.manifest = json.loads((corpus_dir / config.MANIFEST_FILE.name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, EOFError) as e:
            raise StorageError(f"corpus not readable in {corpus_dir} ({e}); run `python -m jurisrag.ingest`") from e
        if len(self.passages) != len(self.index.doc_len):
            raise StorageError("passages.jsonl and bm25.pkl are out of sync; rebuild the corpus")
        self.by_passage_id = {p["passage_id"]: p for p in self.passages}
        self.by_number = {}
        for c in self.cases.values():
            self.by_number.setdefault(c["number"], c["id"])
        self.passages_of: dict[str, list[dict]] = {}
        for p in self.passages:
            self.passages_of.setdefault(p["case_id"], []).append(p)

    @cached_property
    def zone_array(self) -> np.ndarray:
        return np.array([p["zone"] for p in self.passages])

    def resolve_case_id(self, ref: str) -> str | None:
        ref = ref.strip()
        if ref in self.cases:
            return ref
        return self.by_number.get(ref)

    def search(self, query: str, k: int, zone: str = "any", per_case: int = 2) -> list[tuple[dict, float]]:
        scores = self.index.scores(tokenize(query))
        if zone != "any":
            scores = np.where(self.zone_array == zone, scores, 0.0)
        hits, per = [], {}
        for i in np.argsort(-scores):
            if scores[i] <= 0 or len(hits) >= k:
                break
            p = self.passages[i]
            if per.get(p["case_id"], 0) >= per_case:
                continue
            per[p["case_id"]] = per.get(p["case_id"], 0) + 1
            hits.append((p, float(scores[i])))
        return hits


def _jsonl(path: Path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)
