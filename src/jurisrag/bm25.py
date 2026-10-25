"""Minimal Okapi BM25 over an inverted index (numpy, no external search engine)."""

import math
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


class BM25Index:
    def __init__(self, k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        self.postings: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self.idf: dict[str, float] = {}
        self.doc_len = np.zeros(0)
        self.avgdl = 0.0

    @classmethod
    def build(cls, docs: list[list[str]], **kw) -> "BM25Index":
        idx = cls(**kw)
        raw: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, toks in enumerate(docs):
            for term, tf in Counter(toks).items():
                raw[term].append((i, tf))
        n = len(docs)
        idx.doc_len = np.array([len(d) for d in docs], dtype=np.float32)
        idx.avgdl = float(idx.doc_len.mean()) if n else 0.0
        for term, plist in raw.items():
            ids = np.array([p[0] for p in plist], dtype=np.int32)
            tfs = np.array([p[1] for p in plist], dtype=np.float32)
            idx.postings[term] = (ids, tfs)
            df = len(plist)
            idx.idf[term] = math.log(1 + (n - df + 0.5) / (df + 0.5))
        return idx

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        out = np.zeros(len(self.doc_len), dtype=np.float32)
        for term in set(query_tokens):
            if term not in self.postings:
                continue
            ids, tfs = self.postings[term]
            norm = self.k1 * (1 - self.b + self.b * self.doc_len[ids] / self.avgdl)
            out[ids] += self.idf[term] * tfs * (self.k1 + 1) / (tfs + norm)
        return out

    def save(self, path: Path) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: Path) -> "BM25Index":
        with open(path, "rb") as f:
            return pickle.load(f)
