# Scénario 1 — RAG simple

_Attendu : Une recherche (zone motivations) suffit ; l'agent doit soumettre sans lecture inutile._

### Agentic RAG

**Question :** Le juge peut-il écarter le barème d'indemnisation du licenciement sans cause réelle et sérieuse (article L. 1235-3 du code du travail) en se fondant sur la Charte sociale européenne ou sur la convention n° 158 de l'OIT ?

Modèle `claude-sonnet-5-5` · appels LLM 6 {'agent': 4, 'verifier': 2} · outils 2 ['search_cases', 'read_case'] · notes soumises 2 · tokens in/out 49102/4436 · latence 48.51 s · coût estimé $0.1426

#### Trace

| Étape | t (s) | Type | Détail |
|---|---|---|---|
| 1 | 0.0 | DECISION | Nouvelle question reçue : l'agent planifie. |
| 2 | 12.12 | DECISION | Rechercher — Trouver arrêts sur barème et Charte sociale européenne / convention 158 OIT |
| 3 | 12.12 | TOOL | search_cases({"query": "barème indemnité licenciement sans cause réelle et sérieuse Charte sociale européenne convention n° 158 OIT écarter", "k": 8, "zone": "motivations"}) |
| 4 | 12.12 | OBSERVATION | 8 passages dans 6 décisions (19-11.986, 19-22.922, 21-14.490, 21-15.247, 21-23.387, 22-17.340) ; zones : 8 motivations. Meilleur score 21.48. |
| 5 | 14.62 | DECISION | Lire la décision — Vérifier raisonnement sur effet direct art. 10 convention 158 et dispositif |
| 6 | 14.63 | TOOL | read_case({"case_id": "627b537f4d359c057dd01cf4"}) |
| 7 | 14.63 | OBSERVATION | Décision 21-14.490 du 2022-05-11 (Cassation) : 15 passages, dont 11 de motivation. |
| 8 | 26.38 | DECISION | Soumettre la note au vérificateur — Preuves suffisantes |
| 9 | 33.01 | CHECK | Preuves suffisantes : non — 4 affirmations, 5/5 citations vérifiées mot pour mot, 4 affirmations étayées (note 1/3). |
|  |  |  | ↳ Élément non sourcé : La qualification qui renvoie la qualification (qualifications) selon laquelle le barème ne s'applique pas aux licenciements nuls de l'article L. 1235-3-1 n'est pas établie par les passages cités : le §21 cité mentionne seulement les articles L. 1235-3, L. 1235-3-1 et L. 1235-4 comme permettant une indemnité adéquate, sans dire que le barème ne s'applique pas aux licenciements nuls. |
|  |  |  | ↳ Élément non sourcé : Le constat principal évoque « deux arrêts du 11 mai 2022 » ; seuls les passages des pourvois 21-15.247 et 21-14.490 sont cités, ce qui est cohérent, mais l'effet direct de la Charte « entre particuliers » n'est cité que pour le 21-15.247. |
|  |  |  | ↳ Consigne : Corriger la qualification sur l'article L. 1235-3-1 : citer un passage établissant que le barème ne s'applique pas aux licenciements nuls, ou la reformuler en indiquant seulement que le §21 mentionne cet article parmi les dispositions permettant une indemnité adéquate. Le reste est étayé. |
| 10 | 33.01 | DECISION | Vérification échouée : retour à l'agent avec les défauts relevés. |
| 11 | 44.29 | DECISION | Soumettre la note au vérificateur — Correction de la qualification |
| 12 | 48.51 | CHECK | Preuves suffisantes : oui — 4 affirmations, 5/5 citations vérifiées mot pour mot, 4 affirmations étayées (note 2/3). |
| 13 | 48.51 | FINAL | Note verified — 5 citations, 2 décisions. |

#### Réponse

**Statut : Vérifiée** — arrêt : note vérifiée

**Constat principal.** Non. Selon deux arrêts du 11 mai 2022, le juge ne peut écarter le barème de l'article L. 1235-3 ni sur la Charte sociale européenne, dépourvue d'effet direct entre particuliers (pourvoi 21-15.247), ni sur l'article 10 de la convention n° 158 de l'OIT (pourvoi 21-14.490). Cet article est d'effet direct, mais la Cour juge le barème compatible avec lui. Le juge doit donc fixer l'indemnité entre le minimum et le maximum légaux.

**Décisions et passages à l'appui**
1. Charte sociale européenne : ses dispositions n'ayant pas d'effet direct dans un litige entre particuliers, son article 24 ne permet pas d'écarter l'article L. 1235-3 (Soc., 11 mai 2022, pourvoi n° 21-15.247, rejet).
   - Cass. soc., 2022-05-11, n° 21-15.247 (Rejet) — zone `motivations`, car. 15658–15923, `627b537f76c5d9057df7fe01-p013` : « les dispositions de la Charte sociale européenne n'étant pas d'effet direct en droit interne dans un litige entre particuliers, l'invocation de son article 24 ne pouvait pas conduire à écarter l'application des dispositions de l'article L. 1235-3 du code du travail »
2. Convention n° 158 de l'OIT : l'article 10 est d'effet direct en droit interne (Soc., 11 mai 2022, pourvoi n° 21-14.490).
   - Cass. soc., 2022-05-11, n° 21-14.490 (Cassation) — zone `motivations`, car. 8735–8897, `627b537f4d359c057dd01cf4-p006` : « n'ont pas pour objet exclusif de régir les relations entre Etats et ne requièrent l'intervention d'aucun acte complémentaire, sont d'effet direct en droit interne »
3. Malgré cet effet direct, la Cour juge le barème compatible avec l'article 10 de la convention n° 158.
   - Cass. soc., 2022-05-11, n° 21-14.490 (Cassation) — zone `motivations`, car. 15579–15737, `627b537f4d359c057dd01cf4-p012` : « Il en résulte que les dispositions de l'article L. 1235-3 du code du travail sont compatibles avec les stipulations de l'article 10 de la Convention précitée. »
4. Le juge ne peut pas écarter le barème au vu de la situation concrète du salarié. Il doit seulement fixer l'indemnité entre les montants minimaux et maximaux. La cassation du 11 mai 2022 (n° 21-14.490) censure une cour d'appel qui avait alloué 32 000 euros au-delà du plafond.
   - Cass. soc., 2022-05-11, n° 21-14.490 (Cassation) — zone `motivations`, car. 16692–16864, `627b537f4d359c057dd01cf4-p013` : « alors qu'il lui appartenait seulement d'apprécier la situation concrète de la salariée pour déterminer le montant de l'indemnité due entre les montants minimaux et maximaux »
   - Cass. soc., 2022-05-11, n° 21-14.490 (Cassation) — zone `dispositif`, car. 17159–17299, `627b537f4d359c057dd01cf4-p014` : « CASSE ET ANNULE, mais seulement en ce qu'il condamne la société Pleyel centre de santé mutualiste à payer à Mme [E] la somme de 32 000 euros »

**Nuances**
- L'absence d'effet direct est citée pour la Charte sociale européenne dans l'arrêt n° 21-15.247, et l'effet direct de l'article 10 de la convention n° 158 dans l'arrêt n° 21-14.490.

**Lacunes de preuve**
- L'arrêt n° 21-14.490 cite l'avis de l'Assemblée plénière du 17 juillet 2019. Je n'ai pas consulté cet avis, qui est hors corpus.
- Je n'ai pas examiné d'autres textes, comme l'article 6 de la CEDH.

**Sources (corpus)**
- n° 21-15.247, 2022-05-11 — https://www.courdecassation.fr/decision/627b537f76c5d9057df7fe01
- n° 21-14.490, 2022-05-11 — https://www.courdecassation.fr/decision/627b537f4d359c057dd01cf4

### Baseline RAG statique

**Question :** Le juge peut-il écarter le barème d'indemnisation du licenciement sans cause réelle et sérieuse (article L. 1235-3 du code du travail) en se fondant sur la Charte sociale européenne ou sur la convention n° 158 de l'OIT ?

Modèle `claude-sonnet-5-5` · appels LLM 1 {'baseline': 1} · outils 1 ['search_cases'] · notes soumises 1 · tokens in/out 4933/975 · latence 7.91 s · coût estimé $0.0196

#### Trace

| Étape | t (s) | Type | Détail |
|---|---|---|---|
| 1 | 0.0 | TOOL | search_cases({"query": "Le juge peut-il écarter le barème d'indemnisation du licenciement sans cause réelle et sérieuse (article L. 1235-3 du code du travail) en se fondant sur la Charte sociale européenne ou sur la convention n° 158 de l'OIT ?", "k": 5, "zone": "any"}) |
| 2 | 0.0 | OBSERVATION | 5 passages dans 3 décisions (19-11.986, 21-14.490, 21-15.247) ; zones : 4 moyens, 1 motivations. Meilleur score 39.84. |
| 3 | 7.91 | CHECK | Contrôle (non bouclé) : 2 citations vérifiées mot pour mot, 0 défaut(s). |
| 4 | 7.91 | FINAL | Réponse (partial) — 2 citations. |

#### Réponse

**Statut : Non vérifiée (baseline)** — arrêt : réponse unique

**Constat principal.** Les passages indiquent, dans l'arrêt 21-14.490 du 11 mai 2022 (cassation), que la Cour de cassation juge l'article L. 1235-3 compatible avec l'article 10 de la convention n° 158 de l'OIT, ce qui a conduit à censurer une cour d'appel ayant écarté le barème en raison de la situation concrète de la salariée. Sur la Charte sociale européenne, seul un moyen est reproduit, sans la réponse de la Cour : le corpus ne permet pas de conclure sur ce point.

**Décisions et passages à l'appui**
1. La Cour de cassation juge les dispositions de l'article L. 1235-3 compatibles avec l'article 10 de la convention n° 158 de l'OIT.
   - Cass. soc., 2022-05-11, n° 21-14.490 (Cassation) — zone `motivations`, car. 15579–15737, `627b537f4d359c057dd01cf4-p012` : « Il en résulte que les dispositions de l'article L. 1235-3 du code du travail sont compatibles avec les stipulations de l'article 10 de la Convention précitée. »
2. La Cour a relevé que la cour d'appel avait dépassé le montant maximal du barème en se fondant sur la situation concrète de la salariée et sur l'article 10 de la convention n° 158. L'arrêt est cassé (solution : Cassation), ce qui suggère que ce raisonnement ne peut justifier d'écarter le barème.
   - Cass. soc., 2022-05-11, n° 21-14.490 (Cassation) — zone `motivations`, car. 15745–15874, `627b537f4d359c057dd01cf4-p012` : « Pour condamner l'employeur au paiement d'une somme supérieure au montant maximal prévu par l'article L. 1235-3 du code du travail »

**Nuances**
- Les passages de zone « moyens » (21-15.247 sur l'article 24 de la Charte, 21-14.490 premier moyen, 19-11.986) exposent des arguments de parties et non la position de la Cour.
- Le passage 21-15.247-p004 mentionne une motivation d'appel selon laquelle l'article 24 de la Charte n'est pas d'effet direct, mais il est cité dans un moyen ; la Cour n'a pas été vue se prononcer dans les passages (le pourvoi a été rejeté).
- Le raisonnement de la Cour sur la cassation dans 21-14.490 n'est que partiellement reproduit : seuls les paragraphes 21 à 23 figurent.

**Lacunes de preuve**
- Aucun passage de motivation de la Cour ne statue sur l'effet direct de l'article 24 de la Charte sociale européenne.
- Le dispositif et le raisonnement complet de la cassation dans 21-14.490 ne sont pas fournis.
- Les avis de l'Assemblée plénière du 17 juillet 2019 ne sont évoqués que dans un moyen.

**Sources (corpus)**
- n° 21-14.490, 2022-05-11 — https://www.courdecassation.fr/decision/627b537f4d359c057dd01cf4