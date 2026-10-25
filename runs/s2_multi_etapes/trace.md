# Scénario 2 — Recherche multi-étapes

_Attendu : Trouver l'affaire (passage d'exposé), puis read_case pour la solution et le raisonnement de la Cour._

### Agentic RAG

**Question :** Un conseiller d'une mission locale a été licencié pour faute grave après avoir publié des messages sur Facebook. Quelle a été la décision de la Cour de cassation dans cette affaire et sur quel raisonnement repose-t-elle ?

Modèle `claude-sonnet-5-5` · appels LLM 4 {'agent': 3, 'verifier': 1} · outils 2 ['search_cases', 'read_case'] · notes soumises 1 · tokens in/out 27297/2418 · latence 18.27 s · coût estimé $0.0788

#### Trace

| Étape | t (s) | Type | Détail |
|---|---|---|---|
| 1 | 0.0 | DECISION | Nouvelle question reçue : l'agent planifie. |
| 2 | 2.17 | DECISION | Rechercher — Trouver l'arrêt sur conseiller mission locale licencié pour messages Facebook |
| 3 | 2.17 | TOOL | search_cases({"query": "conseiller mission locale licenciement faute grave messages Facebook", "k": 5, "zone": "motivations"}) |
| 4 | 2.17 | OBSERVATION | 5 passages dans 4 décisions (20-19.711, 21-12.370, 22-11.016, 22-20.970) ; zones : 5 motivations. Meilleur score 12.68. |
| 5 | 3.63 | DECISION | Lire la décision — Vérifier le dispositif et le raisonnement complet |
| 6 | 3.63 | TOOL | read_case({"case_id": "634f93f8b5afe5adfff28804"}) |
| 7 | 3.63 | OBSERVATION | Décision 21-12.370 du 2022-10-19 (Cassation) : 14 passages, dont 7 de motivation. |
| 8 | 12.83 | DECISION | Soumettre la note au vérificateur — Arrêt identifié et lu intégralement |
| 9 | 18.27 | CHECK | Preuves suffisantes : oui — 6 affirmations, 7/7 citations vérifiées mot pour mot, 6 affirmations étayées (note 1/3). |
| 10 | 18.27 | FINAL | Note verified — 7 citations, 1 décisions. |

#### Réponse

**Statut : Vérifiée** — arrêt : note vérifiée

**Constat principal.** Par arrêt du 19 octobre 2022 (pourvoi n° 21-12.370), la Chambre sociale a cassé l'arrêt d'appel qui avait annulé le licenciement pour discrimination. Elle juge que le salarié d'une mission locale est soumis aux principes de laïcité et de neutralité du service public et donc à une obligation de réserve. La cour d'appel n'avait pas recherché si les propos Facebook pouvaient caractériser un manquement à cette obligation.

**Décisions et passages à l'appui**
1. Les faits : le conseiller a été licencié pour faute grave en raison de publications sur son compte Facebook public.
   - Cass. soc., 2022-10-19, n° 21-12.370 (Cassation) — zone `expose`, car. 2818–2906, `634f93f8b5afe5adfff28804-p001` : « Par lettre du 15 décembre 2015, la mission locale a licencié le salarié pour faute grave »
2. La cour d'appel avait jugé le licenciement discriminatoire et l'avait annulé. Elle avait retenu que le salarié restait libre de s'exprimer et de critiquer l'État en dehors de son travail.
   - Cass. soc., 2022-10-19, n° 21-12.370 (Cassation) — zone `motivations`, car. 12838–13054, `634f93f8b5afe5adfff28804-p010` : « Pour dire que la mission locale a discriminé le salarié en raison de l'expression de ses opinions politiques et de ses convictions religieuses en procédant à son licenciement et annuler en conséquence le licenciement »
3. Règle posée par la Cour : les missions locales associatives sont des personnes de droit privé gérant un service public. Leur salarié est donc soumis à la laïcité, à la neutralité et à une obligation de réserve en dehors de ses fonctions.
   - Cass. soc., 2022-10-19, n° 21-12.370 (Cassation) — zone `motivations`, car. 11130–11281, `634f93f8b5afe5adfff28804-p009` : « est soumis aux principes de laïcité et de neutralité du service public et dès lors à une obligation de réserve en dehors de l'exercice de ses fonctions »
4. La même règle vaut pour le salarié de droit privé mis à disposition d'une collectivité territoriale.
   - Cass. soc., 2022-10-19, n° 21-12.370 (Cassation) — zone `motivations`, car. 12593–12748, `634f93f8b5afe5adfff28804-p010` : « le salarié de droit privé mis à disposition d'une collectivité publique territoriale est soumis aux principes de laïcité et de neutralité du service public »
5. Motif de la cassation : manque de base légale. La cour d'appel n'avait pas recherché si le compte Facebook permettait d'identifier le salarié comme conseiller affecté à la commune, notamment par les jeunes qu'il suivait. Elle n'avait pas non plus recherché si, vu la virulence et la publicité des propos, ceux-ci caractérisaient un manquement à l'obligation de réserve justifiant le licenciement au titre de l'article L. 1133-1.
   - Cass. soc., 2022-10-19, n° 21-12.370 (Cassation) — zone `motivations`, car. 16317–16359, `634f93f8b5afe5adfff28804-p012` : « n'a pas donné de base légale à sa décision »
   - Cass. soc., 2022-10-19, n° 21-12.370 (Cassation) — zone `motivations`, car. 15769–15863, `634f93f8b5afe5adfff28804-p012` : « au regard de la virulence des propos litigieux ainsi que de la publicité qui leur était donnée »
6. Dispositif : cassation et annulation en toutes dispositions de l'arrêt de la cour d'appel d'Aix-en-Provence du 18 décembre 2020. Renvoi devant la cour d'appel de Nîmes.
   - Cass. soc., 2022-10-19, n° 21-12.370 (Cassation) — zone `dispositif`, car. 16679–16722, `634f93f8b5afe5adfff28804-p013` : « les renvoie devant la cour d'appel de Nîmes »

**Nuances**
- La Cour ne tranche pas elle-même la qualification de faute grave. Elle casse pour défaut de base légale et renvoie l'examen à la cour de renvoi.
- Je n'ai pas vérifié le sort de l'affaire après le renvoi.

**Lacunes de preuve**
- Le corpus consulté ne donne pas la décision de la cour d'appel de renvoi (Nîmes).

**Sources (corpus)**
- n° 21-12.370, 2022-10-19 — https://www.courdecassation.fr/decision/634f93f8b5afe5adfff28804

### Baseline RAG statique

**Question :** Un conseiller d'une mission locale a été licencié pour faute grave après avoir publié des messages sur Facebook. Quelle a été la décision de la Cour de cassation dans cette affaire et sur quel raisonnement repose-t-elle ?

Modèle `claude-sonnet-5-5` · appels LLM 1 {'baseline': 1} · outils 1 ['search_cases'] · notes soumises 1 · tokens in/out 4664/929 · latence 6.74 s · coût estimé $0.0186

#### Trace

| Étape | t (s) | Type | Détail |
|---|---|---|---|
| 1 | 0.0 | TOOL | search_cases({"query": "Un conseiller d'une mission locale a été licencié pour faute grave après avoir publié des messages sur Facebook. Quelle a été la décision de la Cour de cassation dans cette affaire et sur quel raisonnement repose-t-elle ?", "k": 5, "zone": "any"}) |
| 2 | 0.01 | OBSERVATION | 5 passages dans 3 décisions (19-12.058, 19-21.138, 21-12.370) ; zones : 2 expose, 3 moyens. Meilleur score 28.59. |
| 3 | 6.74 | CHECK | Contrôle (non bouclé) : 3 citations vérifiées mot pour mot, 0 défaut(s). |
| 4 | 6.74 | FINAL | Réponse (partial) — 3 citations. |

#### Réponse

**Statut : Non vérifiée (baseline)** — arrêt : réponse unique

**Constat principal.** Les passages indiquent que la décision du 19 octobre 2022 (pourvoi 21-12.370) est une cassation, et exposent les griefs de l'employeur contre l'arrêt d'appel. Le corpus ne contient toutefois pas les motifs de la Cour de cassation elle-même, de sorte que son raisonnement ne peut être établi.

**Décisions et passages à l'appui**
1. Le conseiller de la mission locale a été licencié pour faute grave en raison de publications sur un compte Facebook accessible au public, comportant critiques politiques et appels à diffuser le Coran.
   - Cass. soc., 2022-10-19, n° 21-12.370 (Cassation) — zone `expose`, car. 2850–2986, `634f93f8b5afe5adfff28804-p001` : « la mission locale a licencié le salarié pour faute grave, en lui reprochant d'avoir publié sur son compte Facebook, accessible au public »
2. L'employeur invoquait une atteinte à l'obligation de neutralité, englobant devoir de réserve et respect de la laïcité, ainsi qu'un abus de la liberté d'expression.
   - Cass. soc., 2022-10-19, n° 21-12.370 (Cassation) — zone `expose`, car. 3613–3701, `634f93f8b5afe5adfff28804-p001` : « laquelle « englobe un devoir de réserve ainsi qu'une obligation de respect de la laïcité »
3. Le pourvoi (argument du demandeur, non position de la Cour) reprochait à la cour d'appel d'avoir jugé que l'employeur ne pouvait interdire le prosélytisme religieux hors travail et que le devoir de réserve ne couvrait pas l'expression de la foi, en violation du principe de laïcité du service public.
   - Cass. soc., 2022-10-19, n° 21-12.370 (Cassation) — zone `moyens`, car. 6286–6350, `634f93f8b5afe5adfff28804-p004` : « la cour d'appel a violé le principe de laïcité du service public »

**Nuances**
- La solution « Cassation » figure dans les métadonnées des passages, mais aucun passage de motivation de la Cour n'est fourni.
- Le passage de zone « moyens » (p004) est l'argumentation de l'employeur demandeur au pourvoi, non le raisonnement de la Cour.
- Les passages des affaires 19-12.058 et 19-21.138 concernent d'autres litiges et ne répondent pas à la question.

**Lacunes de preuve**
- Les motifs de la Cour de cassation (zone motivation) dans l'arrêt 21-12.370 ne sont pas fournis.
- Le dispositif précis (portée de la cassation, renvoi) n'est pas établi par les passages.
- La position de la Cour sur la laïcité, le devoir de réserve et la liberté d'expression du salarié reste inconnue.

**Sources (corpus)**
- n° 21-12.370, 2022-10-19 — https://www.courdecassation.fr/decision/634f93f8b5afe5adfff28804