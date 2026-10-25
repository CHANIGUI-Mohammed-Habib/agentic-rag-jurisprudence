# Scénario 3 — Information insuffisante

_Attendu : Le premier retrieval est hors sujet ; l'agent doit reformuler puis déclarer la lacune au lieu d'inventer._

### Agentic RAG

**Question :** Un employeur peut-il licencier un salarié pour avoir utilisé un outil d'intelligence artificielle générative comme ChatGPT sans autorisation ?

Modèle `claude-sonnet-5-5` · appels LLM 8 {'agent': 5, 'verifier': 3} · outils 3 ['search_cases', 'search_cases', 'search_cases'] · notes soumises 3 · tokens in/out 57507/5060 · latence 40.13 s · coût estimé $0.1656

#### Trace

| Étape | t (s) | Type | Détail |
|---|---|---|---|
| 1 | 0.0 | DECISION | Nouvelle question reçue : l'agent planifie. |
| 2 | 1.78 | DECISION | Rechercher — Chercher jurisprudence sur IA générative et licenciement |
| 3 | 1.78 | TOOL | search_cases({"query": "intelligence artificielle générative ChatGPT licenciement salarié outil sans autorisation", "k": 5, "zone": "any"}) |
| 4 | 1.78 | OBSERVATION | 5 passages dans 3 décisions (19-10.534, 23-11.860, 23-15.410) ; zones : 3 motivations, 2 moyens. Meilleur score 9.22. |
| 5 | 5.87 | DECISION | Soumettre la note au vérificateur — Aucune décision sur l'IA générative trouvée |
| 6 | 10.68 | CHECK | Preuves suffisantes : non — 0 affirmations, 0/0 citations vérifiées mot pour mot, 0 affirmations étayées (note 1/3). |
|  |  |  | ↳ Élément non sourcé : Période du corpus : 2020 à mars 2025 |
|  |  |  | ↳ Élément non sourcé : Affirmation d'absence totale de décision sur l'IA dans le corpus, au-delà d'une recherche unique |
|  |  |  | ↳ Consigne : Nuancer : indiquer que seule une recherche a été faite et qu'elle n'a pas fait remonter de décision pertinente, sans affirmer l'absence de toute décision dans le corpus. Justifier la période 2020-mars 2025 ou la retirer. Idéalement, faire d'autres recherches avec des formulations variées (outil informatique, charte, usage détourné, faute grave). |
| 7 | 10.68 | DECISION | Vérification échouée : retour à l'agent avec les défauts relevés. |
| 8 | 13.41 | DECISION | Rechercher — Reformuler: usage outil informatique contraire charte, faute |
| 9 | 13.41 | DECISION | Rechercher — Recherche termes algorithme / intelligence artificielle |
| 10 | 13.41 | TOOL | search_cases({"query": "utilisation outil informatique employeur charte informatique interdiction faute grave licenciement", "k": 6, "zone": "motivations"}) |
| 11 | 13.42 | OBSERVATION | 6 passages dans 6 décisions (17-19.523, 20-21.848, 22-11.016, 22-16.805, 22-20.539, 23-11.860) ; zones : 6 motivations. Meilleur score 18.79. |
| 12 | 13.42 | TOOL | search_cases({"query": "intelligence artificielle algorithme salarié", "k": 5, "zone": "any"}) |
| 13 | 13.42 | OBSERVATION | 5 passages dans 4 décisions (19-12.025, 19-15.039, 20-19.957, 22-12.381) ; zones : 3 motivations, 2 moyens. Meilleur score 6.15. |
| 14 | 20.66 | DECISION | Soumettre la note au vérificateur — Trois recherches sans décision sur l'IA; note nuancée |
| 15 | 26.69 | CHECK | Preuves suffisantes : non — 2 affirmations, 2/2 citations vérifiées mot pour mot, 1 affirmations étayées (note 2/3). |
|  |  |  | ↳ Affirmation 2 partially_supported : Le passage confirme l'article 26 du règlement intérieur (interdiction d'usage sans autorisation préalable, y compris informatique) et l'approbation de la déduction de la cour d'appel. Mais il présente cette interdiction comme retenue par la cour d'appel (« Elle a retenu »), non comme une relevé de la Cour de cassation. De plus, la Cour ne s'appuie pas sur le seul fait que les messages relevaient de la vie personnelle : elle souligne aussi l'absence d'abus (neuf messages en onze mois), ce que l'affirmation omet. Le numéro de pourvoi et la date sont cohérents avec les métadonnées fournies." |
|  |  |  | ↳ Élément non sourcé : Le constat principal sur l'absence de résultats des recherches (trois recherches, termes utilisés) ne peut pas être vérifié à partir des passages fournis. |
|  |  |  | ↳ Élément non sourcé : L'affirmation selon laquelle les deux arrêts cités ne permettent pas de dire si l'usage non autorisé d'une IA peut justifier un licenciement est une appréciation de l'agent, non établie par les passages. |
|  |  |  | ↳ Consigne : Pour l'affirmation 1, préciser que le règlement intérieur et les constats sont ceux de la cour d'appel, repris par la Cour de cassation, et mentionner le critère de l'absence d'abus (neuf messages en onze mois) en plus du caractère personnel des messages. |
| 16 | 26.69 | DECISION | Vérification échouée : retour à l'agent avec les défauts relevés. |
| 17 | 34.9 | DECISION | Soumettre la note au vérificateur — Note simplifiée, claims prudents |
| 18 | 40.13 | CHECK | Preuves suffisantes : non — 2 affirmations, 3/3 citations vérifiées mot pour mot, 2 affirmations étayées (note 3/3). |
|  |  |  | ↳ Élément non sourcé : Les trois recherches effectuées avec des termes variés (qualification) ne sont pas vérifiables à partir des passages fournis, mais relèvent de la méthode et non du fond juridique. |
| 19 | 40.13 | DECISION | Vérification échouée et limite atteinte : arrêt avec lacune explicite. |
| 20 | 40.13 | FINAL | Lacune explicite : 2 affirmation(s) vérifiée(s) conservée(s), 0 retirée(s). |

#### Réponse

**Statut : Lacune explicite (limite de vérification atteinte)** — arrêt : limite de vérification atteinte

**Constat principal.** Le corpus ne permet pas d'établir une réponse vérifiée à cette question. Seules les affirmations ci-dessous ont été vérifiées.

**Décisions et passages à l'appui**
1. Règle voisine : l'employeur ne peut pas, sans violation de la vie privée, utiliser le contenu de messages personnels émis par le salarié via un outil informatique professionnel pour le sanctionner (Soc., pourvoi n° 23-11.860, 25 septembre 2024). Cette règle ne vise pas l'IA.
   - Cass. soc., 2024-09-25, n° 23-11.860 (Rejet) — zone `motivations`, car. 13947–14086, `66f3a7dc5c2cfc5a084ac60f-p010` : « L'employeur ne peut dès lors, sans violation de cette liberté fondamentale, utiliser le contenu des messages personnels émis par le salarié »
2. Dans le pourvoi n° 22-11.016 (6 mars 2024), la Cour de cassation juge que la cour d'appel a exactement déduit que l'employeur ne pouvait pas se fonder, pour licencier, sur le contenu de messages relevant de la vie personnelle. Dans ce passage, la cour d'appel avait retenu qu'un salarié pouvait utiliser sa messagerie professionnelle pour des messages privés dès lors qu'il n'en abusait pas, et que neuf messages en onze mois n'étaient pas excessifs. Elle avait aussi relevé que le règlement intérieur interdisait d'utiliser sans autorisation préalable les équipements, y compris informatiques. Ce passage ne concerne pas l'IA.
   - Cass. soc., 2024-03-06, n° 22-11.016 (Rejet) — zone `motivations`, car. 7649–7781, `65e81550a743ca0008c68c1d-p006` : « un salarié pouvait toutefois utiliser sa messagerie professionnelle pour envoyer des messages privés dès lors qu'il n'en abusait pas »
   - Cass. soc., 2024-03-06, n° 22-11.016 (Rejet) — zone `motivations`, car. 7934–8083, `65e81550a743ca0008c68c1d-p006` : « Elle en a exactement déduit que l'employeur ne pouvait, pour procéder au licenciement de la salariée, se fonder sur le contenu des messages litigieux »

**Nuances**
- Trois recherches ont été faites, avec des termes variés. Elles n'ont pas fait remonter de décision sur l'IA, mais cela n'établit pas qu'il n'en existe aucune dans le corpus.
- Les deux décisions citées portent sur des messages personnels, pas sur une IA. Elles ne permettent pas de conclure sur la question posée.

**Lacunes de preuve**
- Aucun passage reçu ne traite de l'usage non autorisé d'une IA générative comme motif de licenciement.
- Aucun passage reçu ne traite de l'effet d'une charte informatique ou d'un règlement intérieur sur l'IA.
- Aucun passage reçu ne traite de la gravité de la faute en cas d'usage d'une IA.

**Sources (corpus)**
- n° 23-11.860, 2024-09-25 — https://www.courdecassation.fr/decision/66f3a7dc5c2cfc5a084ac60f
- n° 22-11.016, 2024-03-06 — https://www.courdecassation.fr/decision/65e81550a743ca0008c68c1d

### Baseline RAG statique

**Question :** Un employeur peut-il licencier un salarié pour avoir utilisé un outil d'intelligence artificielle générative comme ChatGPT sans autorisation ?

Modèle `claude-sonnet-5-5` · appels LLM 1 {'baseline': 1} · outils 1 ['search_cases'] · notes soumises 1 · tokens in/out 4842/927 · latence 6.49 s · coût estimé $0.019

#### Trace

| Étape | t (s) | Type | Détail |
|---|---|---|---|
| 1 | 0.0 | TOOL | search_cases({"query": "Un employeur peut-il licencier un salarié pour avoir utilisé un outil d'intelligence artificielle générative comme ChatGPT sans autorisation ?", "k": 5, "zone": "any"}) |
| 2 | 0.0 | OBSERVATION | 5 passages dans 4 décisions (20-21.848, 22-11.016, 23-11.860, 23-20.168) ; zones : 4 motivations, 1 moyens. Meilleur score 15.36. |
| 3 | 6.49 | CHECK | Contrôle (non bouclé) : 3 citations vérifiées mot pour mot, 0 défaut(s). |
| 4 | 6.49 | FINAL | Réponse (insufficient_evidence) — 3 citations. |

#### Réponse

**Statut : Non vérifiée (baseline)** — arrêt : réponse unique

**Constat principal.** Les passages fournis ne traitent pas de l'usage d'un outil d'IA générative comme ChatGPT et ne permettent donc pas de répondre directement à la question. Ils portent seulement sur des principes voisins (utilisation d'outils informatiques professionnels, vie personnelle, règlement intérieur), sans en tirer de règle sur l'IA.

**Décisions et passages à l'appui**
1. Un motif tiré de la vie personnelle du salarié ne justifie en principe pas un licenciement disciplinaire, sauf manquement à une obligation découlant du contrat de travail.
   - Cass. soc., 2024-09-25, n° 23-11.860 (Rejet) — zone `motivations`, car. 14290–14398, `66f3a7dc5c2cfc5a084ac60f-p010` : « un motif tiré de la vie personnelle du salarié ne peut justifier, en principe, un licenciement disciplinaire »
2. Dans une affaire distincte, la Cour relève qu'un règlement intérieur interdisait d'utiliser sans autorisation préalable les équipements de l'employeur, y compris informatiques, pour un usage propre, mais a jugé que l'usage limité de la messagerie professionnelle pour des messages privés n'était pas excessif et que l'employeur ne pouvait se fonder sur leur contenu.
   - Cass. soc., 2024-03-06, n° 22-11.016 (Rejet) — zone `motivations`, car. 7436–7602, `65e81550a743ca0008c68c1d-p006` : « l'article 26 du règlement intérieur interdisait aux salariés d'utiliser pour leur propre compte et sans autorisation préalable les équipements appartenant à la caisse »
   - Cass. soc., 2024-03-06, n° 22-11.016 (Rejet) — zone `motivations`, car. 7966–8083, `65e81550a743ca0008c68c1d-p006` : « l'employeur ne pouvait, pour procéder au licenciement de la salariée, se fonder sur le contenu des messages litigieux »

**Nuances**
- Ces solutions concernent des messages personnels et la vie privée, non l'usage d'une IA générative à des fins professionnelles.
- Le passage de la décision 20-21.848 est un moyen du demandeur au pourvoi, non la position de la Cour, et n'est pas utilisé comme fondement.
- Le passage 23-20.168 concerne le travail temporaire et n'est pas pertinent.

**Lacunes de preuve**
- Aucun passage ne mentionne ChatGPT ou l'intelligence artificielle générative.
- Le corpus ne permet pas d'établir si l'usage non autorisé d'un tel outil constitue une faute, ni sa gravité (cause réelle et sérieuse, faute grave).
- Le corpus ne précise pas le rôle d'une charte informatique ou d'une interdiction expresse pour l'IA.

**Sources (corpus)**
- n° 23-11.860, 2024-09-25 — https://www.courdecassation.fr/decision/66f3a7dc5c2cfc5a084ac60f
- n° 22-11.016, 2024-03-06 — https://www.courdecassation.fr/decision/65e81550a743ca0008c68c1d