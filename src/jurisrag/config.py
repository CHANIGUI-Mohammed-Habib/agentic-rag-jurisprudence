"""Central configuration: paths, dataset pin, model settings, agent limits."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# Dataset pin (Hugging Face) - every corpus build reads this exact revision.
DATASET_ID = "antoinejeannot/jurisprudence"
DATASET_REVISION = "8019db1080cf6dc8a34d73ee44d704a8e90b558e"  # release v2025.03.20
DATASET_FILE = "cour_de_cassation.parquet"

RAW_DIR = ROOT / "data" / "raw"
CORPUS_DIR = ROOT / "data" / "corpus"
CASES_FILE = CORPUS_DIR / "cases.jsonl"
PASSAGES_FILE = CORPUS_DIR / "passages.jsonl"
INDEX_FILE = CORPUS_DIR / "bm25.pkl"
MANIFEST_FILE = CORPUS_DIR / "manifest.json"
RUNS_DIR = ROOT / "runs"

# LLM
MODEL = os.getenv("JURISRAG_MODEL", "claude-sonnet-5-5")
AGENT_EFFORT = os.getenv("JURISRAG_AGENT_EFFORT", "medium")
VERIFIER_EFFORT = os.getenv("JURISRAG_VERIFIER_EFFORT", "medium")
MAX_TOKENS = 16000

# USD per million tokens (input, output) - used for the observability panel only.
PRICES = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}

# Agent limits (explicit stop conditions)
MAX_TOOL_CALLS = 5  # search_cases + read_case calls per question
MAX_DRAFTS = 3  # submit_brief attempts checked by the verifier
MAX_LLM_TURNS = 12  # hard safety net on decision calls
