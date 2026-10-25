# TP3 — Agentic RAG sur la jurisprudence : rapport

> **Note sur le TP2.** Aucune implémentation du TP2 n'était disponible : la fondation RAG (corpus,
> découpage, index, store) a été construite dans ce projet (`src/jurisrag/ingest.py`, `store.py`,
> `bm25.py`). La baseline statique (`baseline.py`) joue le rôle du RAG du TP2 pour la comparaison.

## 1. Architecture

Voir [docs/architecture.md](docs/architecture.md) (schéma, nœuds, état, conditions d'arrêt).
En résumé : `decide` (Claude choisit un outil) → `tools` → `decide` … → `submit_brief` → `verify`
(contrôle mécanique + contrôle de support) → `finalize`, ou retour à `decide` avec les défauts relevés,
ou `gap` (lacune explicite) quand les limites sont atteintes.

## 2. Corpus

| Élément | Valeur |
|---|---|
| Source | `antoinejeannot/jurisprudence`, fichier `cour_de_cassation.parquet` |
| Révision figée | `8019db1080cf6dc8a34d73ee44d704a8e90b558e` (release v2025.03.20), sha256 du fichier dans `data/corpus/manifest.json` |
| Règle | Chambre sociale · décision ≥ 2020-01-01 · « Publié au Bulletin » · zone `motivations` présente · « licenci » dans les thèmes, le sommaire ou la motivation |
| Entonnoir | 13 974 arrêts soc. ≥ 2020 → 1 167 publiés → 1 139 avec motivation → **436 retenus** |
| Passages | **4 399** (exposé 525 · moyens 1 640 · motivations 1 750 · dispositif 484) |

**Découpage.** Les zones Judilibre (`introduction`, `expose`, `moyens`, `motivations`, `dispositif`,
`annexes`) donnent des offsets dans le texte. Les paragraphes sont regroupés jusqu'à ~1 500 caractères
sans jamais traverser une zone ; chaque passage garde `case_id`, zone, `start`/`end`, et
`texte[start:end] == passage` est vérifié à l'ingestion et par les tests.

**Omissions (et pourquoi).** `introduction` (en-tête, parties) et `annexes` (mémoires des avocats,
souvent plus longs que l'arrêt) sont conservées dans le store mais non indexées : ce sont des
arguments de parties, pas le raisonnement de la Cour. Le sommaire officiel est gardé comme métadonnée,
jamais cité (texte éditorial). **Anomalie de données** : la fin de la dernière zone dépasse le texte
d'un caractère sur les 436 décisions ; elle est bornée à la longueur du texte (les autres offsets
s'alignent : chaque `dispositif` commence bien par « PAR CES MOTIFS »).

**Index.** BM25 (k1 = 1,2, b = 0,75), racinisation Snowball française, suppression des accents et des
mots vides (y compris le vocabulaire procédural omniprésent). `search_cases` renvoie au plus 2 passages
par décision pour diversifier les pistes et peut se restreindre à une zone.

**Contrôle de l'index** (`scripts/eval_retrieval.py`) : le sommaire officiel de chaque décision (non
indexé) sert de requête ; on cherche la décision d'origine.

| Requêtes | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| 375 | 0,912 | 0,997 | 1,000 | 0,951 |

Ce test est **optimiste** : un sommaire reprend le vocabulaire de son arrêt. Les questions en langage
naturel (scénario 3) sont nettement plus difficiles pour un index lexical.

## 3. Outils

| Outil | Entrée | Sortie | Erreurs gérées |
|---|---|---|---|
| `search_cases` | `query`, `k` (1-10), `zone` | passages classés : id, score, zone, n° de pourvoi, date, solution, thèmes, texte | requête vide ou sans terme utile, `k`/zone invalides, store illisible |
| `read_case` | `case_id` (ou n° de pourvoi) | métadonnées + tous les passages indexés de la décision | identifiant inconnu, argument vide |

Les erreurs deviennent un `tool_result` `is_error` pour le modèle et une ligne **TOOL_ERROR** dans la trace.

## 4. Scénarios et traces

Questions choisies après inspection du corpus (`scenarios.json`) :

| # | Question (résumé) | Pourquoi ce scénario |
|---|---|---|
| 1 | Le barème L. 1235-3 peut-il être écarté au nom de la Charte sociale européenne / convention 158 OIT ? | La motivation des arrêts du 11 mai 2022 (n° 21-14.490, 21-15.247) répond directement : une recherche suffit. |
| 2 | Conseiller de mission locale licencié pour des messages Facebook : décision et raisonnement ? | La recherche trouve l'exposé des faits (n° 21-12.370) ; la solution et le raisonnement exigent `read_case`. |
| 3 | Licenciement pour usage non autorisé d'une IA générative (ChatGPT) ? | Aucune décision du corpus ne traite ce point : il faut reformuler puis déclarer la lacune. |

Traces complètes : `runs/s1_rag_simple/trace.md`, `runs/s2_multi_etapes/trace.md`,
`runs/s3_info_insuffisante/trace.md` (générées par `scripts/run_scenarios.py`).

Runs du 25/10/2026, modèle `claude-sonnet-5-5`, effort `medium` (agent et vérificateur).

**Scénario 1 — RAG simple** (vérifiée à la 2ᵉ note)

| Étape | Type | Détail |
|---|---|---|
| 2 | DECISION | Rechercher — trouver les arrêts sur le barème et la Charte / convention 158 |
| 3 | TOOL | `search_cases({query: "barème indemnité licenciement … Charte sociale européenne convention n° 158 OIT écarter", k: 8, zone: "motivations"})` |
| 4 | OBSERVATION | 8 passages dans 6 décisions (dont 21-14.490, 21-15.247) ; 8 motivations |
| 5-7 | DECISION / TOOL / OBS. | `read_case(21-14.490)` — vérifier le raisonnement sur l'effet direct et le dispositif |
| 9 | CHECK | non — 5/5 citations exactes, 4/4 affirmations étayées, mais une **nuance non sourcée** (« le barème ne s'applique pas aux licenciements nuls ») |
| 11-12 | DECISION / CHECK | note corrigée → oui |
| 13 | FINAL | vérifiée — 5 citations, 2 décisions (21-15.247 : Charte sans effet direct ; 21-14.490 : art. 10 OIT d'effet direct mais barème compatible) |

**Scénario 2 — Multi-étapes** (vérifiée à la 1ʳᵉ note)

| Étape | Type | Détail |
|---|---|---|
| 3 | TOOL | `search_cases({query: "conseiller mission locale licenciement faute grave messages Facebook", k: 5, zone: "motivations"})` |
| 4 | OBSERVATION | 5 passages dans 4 décisions, dont 21-12.370 |
| 5 | DECISION | Lire la décision — vérifier le dispositif et le raisonnement complet |
| 6-7 | TOOL / OBS. | `read_case(634f93f8…)` → 21-12.370 du 19/10/2022 (Cassation), 14 passages |
| 9 | CHECK | oui — 6 affirmations, 7/7 citations exactes, 6/6 étayées |
| 10 | FINAL | cassation pour manque de base légale : obligation de réserve du salarié d'une mission locale (service public) ; renvoi à Nîmes |

**Scénario 3 — Information insuffisante** (lacune explicite)

| Étape | Type | Détail |
|---|---|---|
| 3-4 | TOOL / OBS. | `search_cases("intelligence artificielle générative ChatGPT licenciement …")` → 5 passages hors sujet (score max 9,2) |
| 5 | DECISION | Soumettre — aucune décision sur l'IA générative |
| 6 | CHECK | non — « absence totale de décision » affirmée après **une seule** recherche ; période du corpus non sourcée |
| 8-13 | DECISION ×2 / TOOL ×2 | reformulations en parallèle : « outil informatique, charte, faute grave » (zone motivations) et « intelligence artificielle algorithme » |
| 15 | CHECK | non — une affirmation `partially_supported` (motif attribué à la Cour au lieu de la cour d'appel) |
| 18 | CHECK | non — seul défaut restant : « trois recherches effectuées » jugé non vérifiable |
| 20 | FINAL | lacune explicite : 2 règles voisines vérifiées conservées (23-11.860, 22-11.016), aucune réponse sur l'IA |

## 5. Comparaison avec le RAG statique

| Scénario | Système | Statut | Citations exactes | Outils | Appels LLM | Latence (s) | Coût ($) |
|---|---|---|---|---|---|---|---|
| 1 | agent | vérifiée | 5/5 | 2 | 6 | 48,5 | 0,143 |
| 1 | baseline | partielle | 2/2 | 1 | 1 | 7,9 | 0,020 |
| 2 | agent | vérifiée | 7/7 | 2 | 4 | 18,3 | 0,079 |
| 2 | baseline | partielle | 3/3 | 1 | 1 | 6,7 | 0,019 |
| 3 | agent | lacune (limite) | 3/3 | 3 | 8 | 40,1 | 0,166 |
| 3 | baseline | preuves insuffisantes | 3/3 | 1 | 1 | 6,5 | 0,019 |

Coût estimé aux tarifs publics. Aucune citation inventée d'un côté comme de l'autre : avec la même
consigne, la baseline est restée honnête (elle s'abstient au lieu d'inventer). La différence porte sur
la **couverture** des preuves.

- **Où l'agent apporte une vraie valeur — scénario 2.** Avec la question brute, la baseline n'a reçu que
  l'exposé et des moyens (2 `expose`, 3 `moyens`). Elle a correctement conclu que « le raisonnement ne
  peut être établi ». L'agent a ouvert la décision et cité la règle de la Cour (obligation de réserve dans
  un service public), le motif de cassation et le dispositif. La décision `read_case` a changé la réponse.
  Même effet, plus faible, au scénario 1 : la recherche limitée à `motivations` a trouvé la réponse sur
  la Charte sociale, que la baseline (4 passages de `moyens` sur 5) n'a pas pu donner.
- **Où le RAG simple est préférable — scénario 3.** La baseline donne en 6,5 s et pour 0,02 $ une réponse
  « preuves insuffisantes » équivalente en substance à la lacune de l'agent (40 s, 8 appels, 8× le coût).
  Quand la réponse attendue est « le corpus ne le dit pas », la boucle n'apporte pas d'information nouvelle.

## 6. Analyse

- **Ce qui fonctionne.**
  - Les 15 citations finales de l'agent sont retrouvées mot pour mot dans le texte original, localisées
    par offsets, et chacune a été jugée « étayée ».
  - Le vérificateur a attrapé de vraies erreurs : une nuance juridique inventée au scénario 1 (barème et
    licenciements nuls) ; au scénario 3, un motif de la cour d'appel présenté comme position de la Cour
    de cassation.
  - Le choix de zone (`motivations`) et la lecture ciblée (`read_case`) sont de vraies décisions de
    l'agent, visibles dans la trace, qui améliorent la couverture.
- **Échec observé — scénario 3.** Le vérificateur traite les phrases de méthode (« trois recherches ont été
  effectuées ») comme des éléments de fond non sourcés. Aucun passage ne peut prouver l'historique de
  recherche : la 3ᵉ note, dont les deux affirmations étaient étayées, a donc été rejetée pour ce seul motif,
  et le run s'est terminé par la limite (`gap_limit`) au lieu d'une lacune vérifiée. Deuxième défaut : au
  scénario 1, l'agent a lu 21-14.490 alors que les passages de motivation suffisaient (6 appels LLM pour
  une question à une recherche) ; le TP demande justement d'éviter cette étape inutile.
- **Amélioration possible.** Donner au vérificateur le journal des appels d'outils du run, et séparer dans
  la note un champ `search_log` (méthode) des `qualifications` (fond). Les phrases de méthode seraient
  alors vérifiées contre la trace, pas contre le corpus. Ensuite : recherche hybride (BM25 + embeddings)
  pour les questions en langage courant, où l'index lexical rate des formulations éloignées du
  vocabulaire juridique.

**Question directrice.** En partie, l'agent prend de meilleures décisions : au scénario 2 (lire la
décision) et au scénario 1 (restreindre aux motivations), ses choix ont produit une réponse que le RAG
statique ne pouvait pas donner. Mais au scénario 3, les reformulations ont été déclenchées par le
**vérificateur**, pas par l'agent, qui voulait conclure après une recherche. Elles n'ont rien changé à la
conclusion, pour 4 à 8 fois le coût et la latence. La valeur vient surtout de la boucle
« vérifier → corriger », qui retire des nuances inventées, plus que de la planification de l'agent.

## 7. Bonus réalisés

- **Observabilité** : appels LLM par rôle (agent / vérificateur / baseline), outils utilisés, tokens,
  latence de chaque outil et du run, coût estimé, affichés dans l'interface et les traces.
- **Vérificateur séparé** : le contrôle de support est un appel distinct, avec son propre prompt et une
  sortie JSON contrainte, que le graphe appelle après chaque `submit_brief`.
