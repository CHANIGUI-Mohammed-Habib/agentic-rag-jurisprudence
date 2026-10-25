# TP3 — Agentic RAG sur la jurisprudence

Assistant de recherche sur les arrêts de la **Chambre sociale** (Cour de cassation) relatifs au
**licenciement**. Un agent LangGraph décide quand rechercher, quelle décision lire, puis soumet une note
de preuves citées à un vérificateur. Les citations sont retrouvées mot pour mot dans le texte original.

- Architecture et graphe : [docs/architecture.md](docs/architecture.md)
- Rapport (corpus, traces, comparaison, analyse) : [REPORT.md](REPORT.md)

## Installation

Prérequis : Python 3.13 et [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env        # puis renseigner ANTHROPIC_API_KEY
```

## 1. Construire le corpus (une fois, ~1 min après téléchargement)

```bash
uv run python -m jurisrag.ingest          # télécharge la révision figée (1,7 Go), sélectionne, découpe, indexe
uv run python scripts/eval_retrieval.py   # contrôle de l'index (recall@k)
```

Produit `data/corpus/` : `cases.jsonl` (décisions complètes), `passages.jsonl` (passages + offsets),
`bm25.pkl` (index), `manifest.json` (révision, règle de sélection, comptes, omissions).

## 2. Lancer l'interface

```bash
uv run streamlit run app.py
```

Choisir *Agent*, *Baseline* ou *Comparer les deux*. La trace (DECISION → TOOL → OBSERVATION → CHECK →
FINAL) s'affiche en direct ; chaque citation s'ouvre sur le passage original surligné.

## 3. Rejouer les trois scénarios du TP

```bash
uv run python scripts/run_scenarios.py                  # les 3 scénarios, agent + baseline
uv run python scripts/run_scenarios.py s2_multi_etapes  # un seul
```

Sorties : `runs/<scénario>/trace.md` (trace lisible), `agent.json`, `baseline.json`, et `runs/comparison.md`.

## Tests (hors ligne, sans clé API)

```bash
uv run pytest -q
```

Vérifient l'intégrité des offsets, les outils et leurs erreurs, le contrôle des citations, et le flux du
graphe avec un LLM scripté (chemin simple, erreur d'outil, notes rejetées → lacune, budget d'outils).

## Configuration (`.env`)

| Variable | Défaut | Rôle |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | clé API Claude |
| `JURISRAG_MODEL` | `claude-sonnet-5-5` | modèle de l'agent, du vérificateur et de la baseline |
| `JURISRAG_AGENT_EFFORT` | `medium` | effort de l'agent et de la baseline |
| `JURISRAG_VERIFIER_EFFORT` | `medium` | effort du vérificateur |

Les limites (5 appels d'outils, 3 notes, 12 tours) sont dans `src/jurisrag/config.py`.

## Arborescence

```
app.py                    interface Streamlit
scenarios.json            les 3 questions de test
src/jurisrag/
  ingest.py               corpus figé -> décisions, passages, index
  store.py, bm25.py, text.py   store + recherche lexicale
  tools.py                search_cases, read_case (+ définitions d'outils Claude)
  agent.py                graphe LangGraph (decide / tools / verify / finalize / gap / fail)
  verifier.py, brief.py   format de note, contrôle mécanique, contrôle de support
  baseline.py             RAG statique : 1 recherche + 1 réponse
  llm.py                  client Claude + métriques (appels, tokens, latence, coût)
  render.py               rendu Markdown des traces
scripts/                  eval_retrieval.py, run_scenarios.py
tests/                    tests hors ligne
```
