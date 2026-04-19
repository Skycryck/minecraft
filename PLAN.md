# PLAN.md — Refactoring & Améliorations

> **Pour Claude Code :** ce fichier est la source de vérité des tâches à accomplir.
> À chaque nouvelle session (`/clear`), lis ce fichier, choisis la **première tâche `[ ]`**,
> exécute-la, puis **coche-la `[x]`** en ajoutant un bref résumé dans "Journal".
> **Ne traite qu'une seule tâche par session.**

---

## 🎯 Contexte du projet

- **Nom :** Minecraft Stats Dashboard
- **Stack :** Python 3.12 (stdlib seulement), HTML/CSS/JS vanilla, Chart.js 4, GitHub Pages
- **Objectif global du refactoring :** démonter le template f-string monolithique de `generate.py` (~1100 lignes), clarifier la UX/UI, enrichir les données (temporel, comparatif), et déplacer la logique métier côté Python pour un front "dumb renderer".
- **Branches :** travaille sur une branche par tâche (`refactor/task-N-<slug>`)
- **Tests :** `python scripts/generate.py stats/serveur-2026/data --title "Test"` — la génération doit réussir et l'HTML doit s'ouvrir sans erreur console
- **Lint :** aucun linter configuré ; vérifier manuellement la console JS + `python -m py_compile scripts/generate.py`

---

## 📐 Règles d'exécution (à respecter pour CHAQUE tâche)

1. **Lire** d'abord les fichiers concernés avant toute modification
2. **Créer une branche** dédiée : `git checkout -b refactor/task-N-<slug>`
3. **Petits commits atomiques** avec messages conventionnels (`refactor:`, `fix:`, `test:`)
4. **Lancer les tests** après modification — ne pas clore la tâche si ça casse
5. **Ne pas dépasser le périmètre** de la tâche (pas de "tant qu'on y est…")
6. **Mettre à jour ce fichier** : cocher `[x]` + ajouter entrée au Journal
7. **Commit final** du PLAN.md avec le message `chore: mark task N as done`

---

## 📋 Tâches

### [x] Tâche 1 — Extraire le CSS du f-string dans `styles.css`

- **Priorité :** 🔴 Haute
- **Fichiers concernés :**
  - `scripts/generate.py`
  - `stats/assets/styles.css` (nouveau)
- **Problème identifié :**
  > Le CSS (~230 lignes, `generate.py:197-426`) est intégré dans le template f-string avec toutes les accolades doublées. Aucune coloration syntaxique, pas de lint possible, modifications fastidieuses.
- **Action attendue :**
  - [x] Créer `stats/assets/styles.css` contenant tout le CSS actuel (accolades simples)
  - [x] Remplacer le bloc `<style>...</style>` dans `generate.py` par `<link rel="stylesheet" href="../assets/styles.css">`
  - [x] Régénérer `stats/serveur-2026/index.html` et `stats/serveur-2020/index.html`, vérifier le rendu identique
- **Critères d'acceptation :**
  - La génération passe sans erreur
  - Le rendu visuel est strictement identique (avant/après screenshot)
  - Aucune accolade doublée ne subsiste dans le CSS
- **Hors périmètre :** ne pas toucher au JS, ne pas modifier la palette ni les sélecteurs
- **Dépendances :** aucune

---

### [x] Tâche 2 — Extraire le JS du f-string dans `app.js`

- **Priorité :** 🔴 Haute
- **Fichiers concernés :**
  - `scripts/generate.py`
  - `stats/assets/app.js` (nouveau)
- **Problème identifié :**
  > Le JS (~850 lignes, `generate.py:440-1302`) est noyé dans le f-string. Toutes les accolades sont doublées (`{{` `}}`), ce qui rend la maintenance cauchemardesque et masque les erreurs de syntaxe JS.
- **Action attendue :**
  - [x] Créer `stats/assets/app.js` contenant tout le JS actuel (accolades simples)
  - [x] Injecter les données via `<script>window.PLAYERS_DATA = {data_json}; window.SYNC = {"fr": "...", "en": "..."};</script>` suivi de `<script src="../assets/app.js"></script>`
  - [x] Adapter le JS pour lire `window.PLAYERS_DATA` au lieu de la constante inline
  - [x] Régénérer les deux index.html et vérifier la console (0 erreur)
- **Critères d'acceptation :**
  - Aucune accolade doublée ne subsiste dans `app.js`
  - Toutes les sections (overview, leaderboards, joueurs) s'affichent correctement
  - Le toggle de langue fonctionne toujours
- **Hors périmètre :** ne pas refactorer la logique interne, ne pas renommer de variables
- **Dépendances :** Tâche 1 recommandée avant (pour valider le pattern d'extraction)

---

### [x] Tâche 3 — Déplacer la définition des BADGES en Python

- **Priorité :** 🔴 Haute
- **Fichiers concernés :**
  - `scripts/generate.py`
  - `stats/assets/app.js` (si tâche 2 faite)
- **Problème identifié :**
  > Le tableau `BADGES` (`generate.py:1010-1077`) et sa logique de calcul (`computePlayerBadges`, `getBadgeTier`) sont en JS côté client. Les données sont figées au build, recalculer à chaque pageload est inutile et complique la lisibilité.
- **Action attendue :**
  - [x] Créer un module `scripts/minecraft/badges.py` contenant les définitions de badges (id, cat, tiers, fonction d'extraction)
  - [x] Calculer les badges dans `process_player()` et les ajouter au dict exporté (clé `badges: [...]`)
  - [x] Supprimer `BADGES`, `computePlayerBadges`, `getBadgeTier` du JS ; la fonction `buildBadgesHtml` consomme directement `p.badges`
  - [x] Régénérer et vérifier que l'affichage des badges est identique
- **Critères d'acceptation :**
  - Aucune définition de badge ne reste en JS
  - Les tiers et progrès affichés sont identiques à avant
  - Les badges méta (`all_rounder`, `légende`) sont aussi calculés côté Python
- **Hors périmètre :** ne pas ajouter de nouveaux badges, ne pas modifier les seuils
- **Dépendances :** Tâche 2

---

### [x] Tâche 4 — Dédupliquer les traductions i18n

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `stats/assets/app.js` si tâche 2 faite)
- **Problème identifié :**
  > Le dict `T` (`generate.py:475-641`) contient FR et EN en miroir complet, soit 166 lignes dont ~95% de clés identiques. Toute nouvelle clé nécessite deux ajouts, sources d'oublis.
- **Action attendue :**
  - [x] Restructurer : `T.fr` complet, `T.en` ne contient que les overrides
  - [x] Remplacer le lookup `T[lang][k]` par `T[lang]?.[k] ?? T.fr[k]`
  - [x] Supprimer les ~80 lignes identiques de `T.en`
- **Critères d'acceptation :**
  - Switch FR/EN fonctionne identiquement
  - Aucune clé manquante dans aucune langue (test manuel des 3 sections)
- **Hors périmètre :** ne pas ajouter de langue, ne pas toucher aux traductions existantes
- **Dépendances :** aucune (mais plus simple après tâche 2)

---

### [x] Tâche 5 — Réduire la palette à 5 couleurs sémantiques

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `stats/assets/styles.css` (ou `generate.py`)
  - `scripts/generate.py` (usages inline des variables CSS)
- **Problème identifié :**
  > Le `:root` (`generate.py:199-209`) déclare 13 couleurs utilisées sans cohérence : le vert est tantôt "mining" tantôt "déplacement". Aucune couleur ne porte de sens.
- **Action attendue :**
  - [x] Définir 5 variables sémantiques : `--c-mining`, `--c-combat`, `--c-survival`, `--c-travel`, `--c-craft`
  - [x] Réassigner chaque stat-tile, leaderboard et icon de card à sa couleur sémantique
  - [x] Garder la palette 8 teintes `PALETTE` UNIQUEMENT pour l'identité joueur dans les charts comparatifs
- **Critères d'acceptation :**
  - Chaque catégorie de stat a une couleur unique et cohérente dans tout le dashboard
  - La palette `PALETTE` en JS n'est plus utilisée ailleurs que dans les charts comparatifs
- **Hors périmètre :** ne pas refaire la typographie, ne pas toucher au layout
- **Dépendances :** Tâche 1

---

### [x] Tâche 6 — Supprimer (ou étiqueter) l'estimation du temps de jeu

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > La fonction `estimateTime` (`generate.py:757-785`) invente une répartition (1s/bloc, 10 DPS, scale 85%) présentée comme factuelle. Cette fiction pollue la crédibilité du dashboard.
- **Action attendue :**
  - [x] Décision produit : soit supprimer complètement la card `card_time_est` et son donut, soit renommer en "Répartition ludique (estimée)" avec tooltip explicatif des hypothèses
  - [x] Appliquer la décision retenue
- **Critères d'acceptation :**
  - Plus aucune métrique inventée n'est présentée comme une donnée dure
  - Si conservé : l'utilisateur comprend que c'est une heuristique
- **Hors périmètre :** ne pas refaire un vrai calcul de temps (hors scope du JSON Minecraft)
- **Dépendances :** aucune

---

### [x] Tâche 7 — Corriger le contraste `--text-muted` (accessibilité AA)

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `stats/assets/styles.css` (ou `generate.py`)
- **Problème identifié :**
  > `--text-muted:#5c5c68` sur `--bg:#0c0c0f` donne un ratio de contraste de ~3.8, sous le seuil AA (4.5). Les labels de stat-tile, sync-date et plusieurs méta sont concernés.
- **Action attendue :**
  - [x] Monter `--text-muted` à `#8080a0` minimum (vérifier ratio ≥ 4.5 via outil)
  - [x] Vérifier qu'aucun autre endroit ne descend sous le seuil (grep des hex de gris)
- **Critères d'acceptation :**
  - Tous les textes passent AA sur fond sombre
  - L'aspect visuel reste cohérent (pas de texte brutalement blanc)
- **Hors périmètre :** ne pas refaire toute la palette, ne pas ajouter de mode clair
- **Dépendances :** Tâche 1

---

### [x] Tâche 8 — Mettre les joueurs dans un combobox avec recherche

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > La navigation (`generate.py:848-855`) affiche tous les joueurs en boutons horizontaux. À 10+ joueurs ou sur mobile, cela crée 3 rangées de boutons et aucune recherche n'est possible.
- **Action attendue :**
  - [x] Garder les 2 onglets fixes "Vue globale" et "Classements"
  - [x] Remplacer les boutons joueurs par un `<select>` natif (ou combobox filtrant) listant les joueurs triés par heures
  - [x] Synchroniser avec `location.hash` pour permettre les deep-links (`#player/Jules`)
- **Critères d'acceptation :**
  - L'URL reflète la section affichée
  - On peut partager un lien vers un profil joueur
  - La nav ne déborde plus sur mobile
- **Hors périmètre :** ne pas toucher au contenu des sections, ne pas ajouter de routing library
- **Dépendances :** Tâche 2 recommandée

---

### [x] Tâche 9 — Archiver des snapshots horodatés des stats

- **Priorité :** 🔴 Haute
- **Fichiers concernés :**
  - `scripts/sync-stats.ps1`
  - `stats/serveur-2026/snapshots/` (nouveau dossier)
  - `.gitignore` (si besoin)
- **Problème identifié :**
  > Le dashboard n'a aucune dimension temporelle : il affiche uniquement un snapshot. Toutes les viz d'évolution (courbes, deltas, streaks) sont impossibles sans historique.
- **Action attendue :**
  - [x] Modifier `sync-stats.ps1` pour copier aussi les JSON dans `stats/serveur-2026/snapshots/YYYY-MM-DD/` après la copie normale
  - [x] Ne créer le dossier daté que s'il n'existe pas déjà (1 snapshot/jour max)
  - [x] Vérifier que le pipeline git + workflow continue de fonctionner
- **Critères d'acceptation :**
  - Après une exécution, `stats/serveur-2026/snapshots/2026-04-17/` contient les mêmes JSON que `data/`
  - Aucune régression dans `generate.py`
- **Hors périmètre :** ne pas encore exploiter les snapshots dans le dashboard (tâche suivante)
- **Dépendances :** aucune

---

### [x] Tâche 10 — Ajouter des deltas 7j sur les stat-tiles principales

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `scripts/generate.py`
  - `scripts/minecraft/history.py` (nouveau)
  - `stats/assets/app.js` (si tâche 2 faite)
- **Problème identifié :**
  > Les stat-tiles affichent des totaux sans contexte. Un utilisateur ne peut pas voir "qui a joué cette semaine" ni "qui progresse le plus vite".
- **Action attendue :**
  - [x] Créer `history.py` qui lit le snapshot le plus proche de 7 jours en arrière
  - [x] Calculer `delta_7d` pour `play_hours`, `total_mined`, `mob_kills`, `total_crafted` et injecter dans le JSON
  - [x] Afficher `↑ +12h` en `<div class="sub">` dans les stat-tiles concernées
- **Critères d'acceptation :**
  - Si aucun snapshot ≥ 6 jours n'existe, les deltas sont masqués sans erreur
  - Les deltas affichés sont mathématiquement corrects (vérif manuelle 1 joueur)
- **Hors périmètre :** pas de graph temporel dans cette tâche (viendra plus tard)
- **Dépendances :** Tâche 9

---

### [x] Tâche 11 — Corriger l'edge case du badge `increvable`

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/generate.py` ou `scripts/minecraft/badges.py` (selon tâche 3)
- **Problème identifié :**
  > `generate.py:1034` : `val = deaths>0 ? hours/deaths : (hours>=1 ? 999 : 0)`. Un joueur à 0h a un score de 0 et débloque artificiellement un tier `locked` correct, mais la logique est fragile et peu lisible.
- **Action attendue :**
  - [x] Simplifier : renvoyer `None` si `hours < 1` (badge non applicable), sinon `hours / max(deaths, 1)`
  - [x] Afficher "—" dans le badge si la valeur est `None`
- **Critères d'acceptation :**
  - Un joueur à 0 mort ET 0 heure n'affiche plus de badge `increvable`
  - Un joueur à 5h / 0 mort affiche toujours le tier Diamond
- **Hors périmètre :** ne pas refondre le système de badges
- **Dépendances :** Tâche 3 recommandée

---

### [x] Tâche 12 — Grouper les 12 leaderboards en 4 catégories à onglets

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > `generate.py:942-977` empile 12 leaderboards en grille 3 colonnes. L'utilisateur est submergé ; aucune hiérarchie ne permet de comparer rapidement les joueurs sur une thématique.
- **Action attendue :**
  - [x] Regrouper en 4 catégories : Combat (kills, pvp, deaths), Exploration (distance, jumps), Économie (enchant, fish, trades, breed), Production (mined, crafted, playtime)
  - [x] Ajouter des sous-onglets dans la section Classements
  - [x] Le premier sous-onglet "Top" reste la vue d'ensemble (3 leaderboards phares)
- **Critères d'acceptation :**
  - Les 12 leaderboards restent accessibles
  - La section Classements ne dépasse plus 1 écran au premier abord
- **Hors périmètre :** ne pas changer le look des leaderboards individuels
- **Dépendances :** aucune

---

### [x] Tâche 13 — Remplacer le faux treemap par un vrai squarified treemap

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > `buildTreemapHtml` (`generate.py:731-741`) utilise un simple `flex` : les items inégaux deviennent illisibles, sans ratio 2D correct.
- **Action attendue :**
  - [x] Implémenter un vrai algorithme squarified (30 lignes JS) OU charger `d3-hierarchy` via CDN
  - [x] Remplacer la sortie HTML flex par un `<svg>` ou un container positionné en absolu
- **Critères d'acceptation :**
  - Les 15 blocs les plus minés sont visibles avec des aires proportionnelles correctes
  - Le treemap est responsive
- **Hors périmètre :** ne pas ajouter d'interactions (zoom, drill-down)
- **Dépendances :** Tâche 2 recommandée

---

### [x] Tâche 14 — Générer `MC_ICONS_HR` depuis `build_icons.py`

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/build_icons.py`
  - `scripts/generate.py`
  - `stats/assets/icons/manifest.json` (nouveau)
- **Problème identifié :**
  > `MC_ICONS_HR` dans `generate.py:461` et `ICONS`/`WIKI_HIRES` dans `build_icons.py` doivent être synchronisés manuellement (documenté dans CLAUDE.md). Source récurrente d'incohérences.
- **Action attendue :**
  - [x] `build_icons.py` écrit `stats/assets/icons/manifest.json` avec la liste des icônes produites
  - [x] `generate.py` lit ce manifest au runtime et injecte la liste dans le JS
  - [x] Supprimer la constante `MC_ICONS_HR` hardcodée
  - [x] Mettre à jour CLAUDE.md pour retirer l'étape manuelle
- **Critères d'acceptation :**
  - Ajouter une icône = 1 seule modification (dans `build_icons.py`)
  - Aucune icône ne bascule par erreur en fallback CDN
- **Hors périmètre :** ne pas modifier le pipeline d'icônes lui-même
- **Dépendances :** aucune

---

### [x] Tâche 15 — Renommer les variables 2 lettres dans `renderLeaderboardCharts`

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > `generate.py:979-997` utilise `da`, `ds`, `dc`, `dt`, `dco`, `fp`, `kb` — illisible à la relecture.
- **Action attendue :**
  - [x] Renommer en noms explicites : `deathAggregate`, `deathSorted`, `deathColors`, `distTypes`, `distColors`, `filteredPlayers`, `killedBy`
  - [x] Vérifier que le rendu est strictement identique
- **Critères d'acceptation :**
  - Plus aucune variable < 4 caractères dans cette fonction
  - Aucune régression visuelle
- **Hors périmètre :** ne pas renommer ailleurs, ne pas refactorer la logique
- **Dépendances :** Tâche 2 recommandée

---

### [x] Tâche 16 — Ajouter un heatmap d'activité par jour (52 semaines × 7 jours)

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/generate.py`
  - `scripts/minecraft/history.py`
- **Problème identifié :**
  > Aucune visualisation ne permet de voir les patterns temporels (jours joués, intensité, streaks). Le style GitHub-contribution est naturel pour ça.
- **Action attendue :**
  - [x] Depuis les snapshots, calculer pour chaque joueur `{date: delta_hours}` sur 52 semaines
  - [x] Rendre un SVG 52×7 avec intensité = heures jouées ce jour
  - [x] L'ajouter dans chaque section joueur
- **Critères d'acceptation :**
  - Les jours sans snapshot sont vides (pas de faux zéros)
  - Le tooltip au survol indique la date et les heures
- **Hors périmètre :** pas de comparaison inter-joueurs dans cette tâche
- **Dépendances :** Tâche 9 + Tâche 10

---

### [x] Tâche 17 — Render paresseux des sections joueur

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > `buildAllSections` (`generate.py:876`) rend le DOM de tous les joueurs au chargement puis toggle `display:none`. À 20 joueurs × badges + charts, le DOM initial est énorme.
- **Action attendue :**
  - [x] Ne pré-rendre que la section active au boot
  - [x] Générer la section d'un joueur à la volée lors du clic, mémoïser le résultat
  - [x] Détruire les charts Chart.js des sections quittées
- **Critères d'acceptation :**
  - Le `contentEl.innerHTML` initial est < 50 KB même avec 20 joueurs
  - Aucune régression fonctionnelle
- **Hors périmètre :** ne pas introduire de framework (Alpine/Preact) dans cette tâche
- **Dépendances :** Tâche 2

---

## 📓 Journal

<!-- Claude ajoute une entrée ici à chaque tâche terminée -->

### 2026-04-17 — Tâche 1 : Extraction CSS

- CSS (229 lignes) extrait de `generate.py` vers `stats/assets/styles.css` avec accolades simples.
- Bloc `<style>...</style>` remplacé par `<link rel="stylesheet" href="../assets/styles.css">` dans `generate_html()`.
- Régénération OK : `serveur-2026` (7 joueurs, 64 937 o) et `serveur-2020` (9 joueurs, 70 454 o).
- `python -m py_compile scripts/generate.py` passe. Les seules `}}` restantes dans le CSS sont des fermetures de blocs CSS imbriqués légitimes (@media + règle).

### 2026-04-17 — Tâche 2 : Extraction JS

- JS (~860 lignes) extrait de `generate.py` vers `stats/assets/app.js` avec accolades simples.
- Bloc `<script>...</script>` remplacé par `<script>window.PLAYERS_DATA={data_json};window.SYNC={...};</script><script src="../assets/app.js"></script>` dans `generate_html()`.
- `generate.py` passe de 1167 à 308 lignes. `python -m py_compile` OK ; `deno check stats/assets/app.js` OK (exit 0).
- Régénération OK : `serveur-2026` (7 joueurs, 11 126 o) et `serveur-2020` (9 joueurs, 16 667 o) — la taille chute fortement car le JS n'est plus inliné.
- Les seules `}}` restantes dans `app.js` sont des fermetures JS imbriquées légitimes (fin d'objet/fonction), pas des escapes f-string.

### 2026-04-17 — Tâche 3 : Badges en Python

- Nouveau module `scripts/minecraft/badges.py` : 33 badges standards + 2 méta (`all_rounder`, `legende`), avec `get_tier()` et `compute_player_badges()`.
- `process_player()` appelle `compute_player_badges(player)` et attache la liste sous la clé `badges` — chaque entrée contient `{id, name, icon, cat, tiers, value, tier, progress, nextTarget}`, avec `icon` stocké comme nom (ex. `diamond_pickaxe`) et non comme HTML.
- `BADGES`, `getBadgeTier`, `computePlayerBadges` supprimés de `app.js` (~80 lignes). `buildBadgesHtml` lit `p.badges` et appelle `mcIcon(b.icon)` au rendu.
- Vérif manuelle des valeurs sur `serveur-2026` : thresholds et progress cohérents (ex. Martel0w mineur 58911 → tier 3, progress 18%).
- `python -m py_compile` OK ; `deno check stats/assets/app.js` OK (exit 0). Régénération OK : `serveur-2026` 48 458 o, `serveur-2020` 65 063 o (hausse attendue : badges pré-calculés embarqués dans le JSON).

### 2026-04-17 — Tâche 4 : Déduplication i18n

- `T.en` dans `stats/assets/app.js` ne contient plus que les overrides : ~32 clés identiques à `T.fr` supprimées (p. ex. `axis_kills`, `d_sprint`, `tier_bronze`, `cat_combat`, `b_nether_mole`, `b_all_rounder`, etc.).
- `t()` et `label()` utilisent désormais `T[lang]?.[k] ?? T.fr[k]` en fallback — le switch EN récupère la valeur FR quand la clé n'existe pas côté EN.
- Régénération OK : `serveur-2026` (48 458 o), `serveur-2020` (65 063 o) — aucune variation de taille (JSON identique, JS externe). `deno check` OK, `python -m py_compile` OK.

### 2026-04-17 — Tâche 5 : Palette sémantique

- 5 variables sémantiques ajoutées dans `stats/assets/styles.css` `:root` : `--c-mining` (#3ecf8e), `--c-combat` (#ef6a6a), `--c-survival` (#efaa6a), `--c-travel` (#6aafef), `--c-craft` (#6aefd9). Les 9 anciens vars stat (`--green`, `--red`, `--orange`, `--blue`, `--cyan`, `--yellow`, `--pink`, `--teal`, `--green-dim`) supprimés — plus aucune ambiguïté : chaque catégorie a une couleur unique.
- Toutes les références mises à jour : stat-tiles overview (4) + joueur (8), leaderboards (12 entrées du tableau `boards`), archétypes (miner/fighter/explorer/builder/farmer), profile-stats (kd, traveled), `mkList` (killed_top10, crafted_top15), `kbHtml`, `.broken-tag .bt-count`, `.tt-tier.tt-done`, gradient du header.
- `estimateTime` corrigé : `time_mining` passe de #efd96a (yellow) → #3ecf8e (c-mining), `time_travel` de #3ecf8e (green, ambigu) → #6aafef (c-travel). Le vert est maintenant réservé au mining partout.
- `PALETTE` (identités joueur) inchangée, utilisée uniquement en ligne 12 pour `PLAYER_COLORS_MAP`.
- `python -m py_compile` OK, `deno check stats/assets/app.js` OK (exit 0). Régénération OK : `serveur-2026` 48 458 o et `serveur-2020` 65 063 o (tailles identiques à avant, CSS et JS externes).

### 2026-04-17 — Tâche 6 : Suppression de l'estimation du temps

- Décision produit retenue (après discussion utilisateur) : **suppression**. Les stats JSON de Minecraft n'exposent que `play_time`, les `*_one_cm` (distances) et quelques compteurs — aucun temps d'activité par catégorie. `estimateTime` posait 1 s/bloc miné, 10 DPS combat, 1.5 s/craft puis rescalait à 85 % du `play_time` : bruit ±300 % sur le minage (break time obsidienne ≈ 9.4 s vs. dirt 0.15 s), indéterminé sur le combat. Le breakdown de déplacement seul serait factuel, mais il double déjà `card_distances`.
- `stats/assets/app.js` : supprimés — fonction `estimateTime()` (~30 lignes, anciennement 332-362), card `card_time_est` + canvas `chart-time-${name}` dans `buildPlayerSection`, bloc de rendu du donut dans `renderPlayerCharts`, et 6 clés i18n (`card_time_est`, `time_mining`, `time_combat`, `time_travel`, `time_craft`, `time_other`) dans `T.fr` et `T.en`.
- Layout : la grille qui contenait `[card_time_est | card_distances]` conserve `card_distances` seule (même pattern que `card_killed_by` déjà isolée dans une `grid-2`). Aucune autre card déplacée.
- Icône `clock` conservée (toujours utilisée par `lb_playtime`). Aucun autre nettoyage hors périmètre.
- `python -m py_compile scripts/generate.py` OK, `deno check stats/assets/app.js` OK (exit 0). Régénération : `serveur-2026` 48 458 o (taille inchangée — on enlève du code JS externe, pas du JSON embarqué), `serveur-2020` 65 063 o. Diff total : 3 fichiers, +4 / -55.

### 2026-04-17 — Tâche 7 : Contraste `--text-muted` AA

- `--text-muted` passe de `#5c5c68` à `#8080a0` dans `stats/assets/styles.css` `:root`.
- Vérification ratios (WCAG 2.1 relative luminance) sur fond `--bg:#0c0c0f` : avant ≈ 3.06 (échec AA), après ≈ 5.06 ✓. Sur fond `--bg-card:#16161a` : après ≈ 4.78 ✓. Sur `--bg-card-alt:#1c1c22` (stat-tiles, badges) : idem largement >4.5.
- Grep des autres hex gris : seul `--text-dim:#8b8b96` est utilisé comme texte — ratio 5.72 sur `--bg`, déjà AA, inchangé. `#5c5c68` dans `app.js:706` est une couleur de dataset de chart (pas du texte), laissée telle quelle.
- Usages touchés automatiquement (via `var(--text-muted)`) : `.sync-date`, `.header .meta span`, `.card h3`, `.stat-tile .label`, `.leaderboard .rank`, `.profile-info .uuid`, `.profile-stat .pl`, `.badges-cat-header`, `.badge-progress-text`, `.badge-tier-locked`, `.tt-tier`. Aucun texte blanc brutal : l'écart reste perceptible (violet clair/gris moyen/gris foncé).
- `python -m py_compile` OK. Régénération : `serveur-2026` 48 458 o, `serveur-2020` 65 063 o (tailles identiques — seul le CSS change).

### 2026-04-17 — Tâche 8 : Combobox joueur + deep-links

- Nav refondue dans `stats/assets/app.js` : 2 onglets fixes (`Vue globale`, `Classements`) + un `<select id="playerSelect">` qui liste les joueurs triés par heures (`Name — 47.6h`). Chaque option `value=name` ; option vide au début (`Choisir un joueur…`).
- Router hash minimal : `sectionToHash` / `hashToSection` supportent `` (overview), `#leaderboards`, `#player/<name>`. `navigateTo()` fait `showSection` + `updateNavActive` + `history.pushState` pour ne pas déclencher `hashchange` quand l'action vient du dashboard. Listeners `hashchange` + `popstate` synchronisent l'UI si l'utilisateur modifie l'URL ou utilise back/forward. Init lit `location.hash` pour router au chargement → deep-links `#player/Jules` fonctionnent.
- `updateNavActive()` bascule `.active` sur le bon onglet ; si la section est un joueur, positionne `select.value=name`, ajoute la classe `.active` et colorie le select via `--player-accent` = `PLAYER_COLORS_MAP[name]`. Sinon remet `value=''` et retire la classe.
- 2 clés i18n ajoutées (`nav_player_placeholder`, `nav_player_label`) dans `T.fr` et `T.en`.
- CSS (`stats/assets/styles.css`) : `.nav-player-select` reprend le style des boutons nav (pilule, min-height 50px), caret SVG inline, variante `.active` (fond coloré joueur, caret blanc), pleine largeur sur mobile. La rangée de nav ne peut donc plus déborder : 2 boutons + 1 select ≤ 3 cellules au lieu de 2+N.
- `python -m py_compile` OK, `deno check stats/assets/app.js` OK. Régénération : `serveur-2026` 48 458 o (inchangé), `serveur-2020` 65 087 o (+24 o : JSON identique, seul `index.html` change d'une poussière). JS externe → pas de hausse du HTML.

### 2026-04-17 — Tâche 9 : Snapshots horodatés

- `scripts/sync-stats.ps1` : bloc snapshot ajouté juste après le log de copie, avant le git add. Calcule `$snapshotDate = yyyy-MM-dd`, cible `stats\serveur-2026\snapshots\$snapshotDate`. Si absent → `New-Item` + `Copy-Item (data\*.json) -> snapshotDir`. Si présent → log jaune « skip ». Garantit donc 1 snapshot/jour max, capture du contenu complet de `data/` (pas seulement les fichiers modifiés par la passe courante).
- `git add` étendu à `stats/serveur-2026/snapshots` en plus de `data/*.json` : le dossier ajoute sa propre ligne dans le commit quotidien. Le workflow `update-stats.yml` ne se déclenche que sur `stats/*/data/**`, donc les nouveaux commits qui ne modifient que `snapshots/` n'entraîneraient aucun rebuild — mais en pratique les snapshots ne sont créés qu'après au moins une nouvelle version de `data/*.json`, donc les deux changements cohabitent dans un même commit et le workflow se déclenche normalement.
- Test dry-run (script PS isolé sur ce worktree) : crée `snapshots/2026-04-17/` avec les 7 JSON, 2ᵉ exécution → branche « skip ». Puis `python scripts/generate.py stats/serveur-2026/data --title "Serveur 2026"` : OK, 7 joueurs, 194h, 48 498 o → `generate.py` ignore bien le sous-dossier `snapshots/` (lecture limitée au dossier passé en argument). `powershell [PSParser]::Tokenize` : OK sur le script modifié.
- Premier snapshot committé tel quel (7 fichiers, ~164 KB) — bootstrap minimal pour la tâche 10 (`history.py` lira le plus proche ≥6 jours). Pas de `.gitignore` ajouté, les snapshots doivent persister dans le repo.

### 2026-04-18 — Tâche 10 : Deltas 7j sur les stat-tiles

- Nouveau module `scripts/minecraft/history.py` : `find_baseline_snapshot()` (cherche le dossier `snapshots/YYYY-MM-DD/` le plus proche de J-7, avec un seuil minimum à 6 jours pour éviter les "deltas hebdo" sur 2 jours), `load_baseline_metrics()` (mappe UUID → 4 métriques via `_extract_metrics()`), `compute_deltas()` (renvoie `None` si pas de baseline). 4 clés trackées : `play_hours`, `total_mined`, `mob_kills`, `total_crafted`.
- `generate.py` : import `history`, lookup baseline dans `data_dir.parent / "snapshots"`, calcul du delta par joueur attaché sous `player["delta_7d"]` (clé absente si pas de baseline). Nouvelle injection `window.BASELINE_DATE` (ISO date ou `null`). Logs `[HIST] Baseline snapshot: 2026-04-12 (7 players)` ou `No baseline snapshot >= 6 days old - deltas hidden`.
- `app.js` : helper `deltaSub(value, suffix)` rend `↑ +X<suffix> (7j)` dans un `<div class="sub delta-sub">`, retourne `''` si `value` null/≤0. `deltaTotals` agrège la somme inter-joueurs pour les 4 tiles overview. Tiles touchées : overview (4 tiles : play_hours, total_mined, mob_kills, total_crafted) et joueur (3 tiles : total_mined, mob_kills, total_crafted — la tile play_hours n'existe pas en section joueur, c'est un profile-stat). Pour total_mined / mob_kills, le delta s'ajoute en 2ᵉ ligne sous le sub mph/kph existant.
- 1 clé i18n ajoutée (`delta_window` : `7j` en FR, `7d` en EN). CSS : `.stat-tile .delta-sub { color: var(--c-mining); font-weight:600 }` — vert sémantique de la catégorie mining (positif = progression).
- Vérif manuelle Skycryck (serveur-2026, baseline 12/04 → snapshot 18/04, 6 jours) : `play_hours 47.8 → 61.3 (+13.5)`, `total_mined 26771 → 31211 (+4440)`, `mob_kills 7713 → 8068 (+355)`, `total_crafted 21476 → 25637 (+4161)`. Affichage cohérent : tile mined `↑ +4.4k (7j)`, tile kills `↑ +355 (7j)`, tile crafted `↑ +4.2k (7j)`. Overview : `↑ +32,9h (7j)` / `+15.3k` / `+1.8k` / `+9.9k`.
- Edge case `serveur-2020` (pas de dossier `snapshots/`) : `BASELINE_DATE = null`, aucun `delta_7d` injecté, `deltaSub()` renvoie `''` partout, dashboard rendu identique à avant. `hermitcraft-s10` : pareil.
- `python -m py_compile` OK ; `deno check stats/assets/app.js` OK ; aucune erreur console côté navigateur (preview FR + EN). Tailles : `serveur-2026` 49 188 o (+730 o : 4×FR + 4×EN deltas embarqués), `serveur-2020` 65 191 o (+128 o : `BASELINE_DATE=null`), `hermitcraft-s10` 378 475 o.

### 2026-04-18 — Tâche 11 : Edge case badge `increvable`

- `scripts/minecraft/badges.py` — `_increvable()` simplifié : retourne `None` si `hours < 1` (badge non applicable), `999` si `deaths == 0` et `hours ≥ 1` (sentinel ∞ → tier Diamond, préserve l'affichage existant), sinon `round(hours/deaths, 1)`. Avant : la branche `hours=0, deaths=0` renvoyait `0` (tier locked OK mais via une valeur numérique factice — fragile car confondait "pas assez joué" et "aucun ratio possible").
- `_badge_entry()` — court-circuit ajouté : si `value is None`, retourne `tier=0`, `progress=0`, `nextTarget=tiers[0]` sans appeler `get_tier()`/`_compute_progress()` (qui échoueraient sur `None >= int`). Les autres badges ne sont pas impactés (aucun ne retourne `None` aujourd'hui, mais le support est générique).
- `stats/assets/app.js:724` — `buildBadgesHtml` : `dv` préfixé par `b.value==null?'—':...` pour afficher `—` dans la ligne `<dv> / <nextTarget>`. La règle `∞` pour `value>=999` (0 morts + 1h+) est conservée.
- Vérif serveur-2026 : `bareme` (0.3h, 0 morts) → `value=None, tier=0, progress=0` ✓ — plus de Diamond artificiel. `Industh` (0.2h, 2 morts) → `None` aussi (passe avant la branche deaths). `SkycryckII` (1.1h, 5 morts) → `0.2`, locked (<2). `Skycryck` (64.9h, 14 morts) → `4.6`, Bronze 87% (inchangé vs. avant). Joueur à 5h/0 mort → sentinel `999`, Diamond garanti (cas d'acceptance respecté).
- `python -m py_compile` OK sur les 3 fichiers, `deno check stats/assets/app.js` exit 0. Régénération : `serveur-2026` 49 186 o (-2 o), `serveur-2020` 65 191 o (inchangé — aucun joueur <1h), `hermitcraft-s10` 378 481 o (+6 o, quelques valeurs passent à `null`).

### 2026-04-18 — Tâche 12 : Sous-onglets Classements

- `stats/assets/app.js` — `buildLeaderboards()` : chaque entrée de `boards` porte un champ `cat` (`combat` / `exploration` / `economy` / `production`), les 3 phares (playtime, mined, kills) portent `top:true`. Un `<div class="lb-wrap" data-active-cat="top">` enveloppe la sous-nav + la grille + la rangée de charts ; chaque card reçoit `data-lbcats="<cat> [top]"`. Nouvelle fonction `initLeaderboardTabs()` (appelée après `buildAllSections()` au boot ET au switch de langue) délègue le clic : elle bascule `wrap.dataset.activeCat`, met à jour `.active` sur les `.lb-tab`, et appelle `charts['chart-deathcauses'|'chart-dist-stacked'].resize()` dans un `setTimeout(0)` — nécessaire car Chart.js ne détecte pas la sortie de `display:none` et se retrouverait dessiné à 0×0.
- Mapping final : **Top** → playtime + mined + kills (3 phares, pas de charts) ; **Combat** → kills + deaths + pvp + chart death-causes ; **Exploration** → distance + jumps + chart dist-by-type ; **Économie** → enchant + fish + trades + breed ; **Production** → playtime + mined + crafted. Les 12 leaderboards restent accessibles, répartis sans duplication sauf sur Top (réutilise les cards top par CSS, pas de double rendu).
- 5 clés i18n ajoutées : `lb_cat_top` (🟣 Top), `lb_cat_combat` (⚔️ Combat), `lb_cat_exploration` (🧭 Exploration), `lb_cat_economy` (💠 Économie/Economy), `lb_cat_production` (⛏️ Production). EN n'ajoute que les 2 overrides nécessaires (economy/production) — top/combat/exploration fallback sur `T.fr` via le lookup `T[lang]?.[k] ?? T.fr[k]` (identiques entre les deux langues).
- `stats/assets/styles.css` — bloc `.lb-subnav` / `.lb-tab` (variantes hover et `.active` ; icônes 20×20 pour distinguer de la nav principale 32×32) + règles `.lb-wrap[data-active-cat="X"] .lb-card[data-lbcats~="X"]{display:block}` pour filtrer. L'attribut `~=` matche le mot complet, donc une card `top production` est bien visible sur les deux onglets.
- Vérif preview navigateur (serveur-2026, FR puis EN) : onglet Top affiche 3 cards, Combat 3+chart, Exploration 2+chart, Économie 4, Production 3. Chart death-causes se redimensionne proprement après bascule (1 frame de delay sans flash 0×0 grâce au `setTimeout`). Aucune erreur console. Classements ne dépasse plus 1 écran — avant 4 rangées de 3 boards + 1 rangée de 2 charts = ~5 écrans de scroll ; après ~1 écran selon l'onglet.
- `python -m py_compile scripts/generate.py` OK, `deno check stats/assets/app.js` exit 0. Régénération : `serveur-2026` 49 186 o (inchangé ; JS externe), `serveur-2020` 65 191 o (inchangé), `hermitcraft-s10` 378 481 o (inchangé).

### 2026-04-18 — Tâche 13 : Vrai treemap squarified

- `stats/assets/app.js` — ancienne `buildTreemapHtml` (simple `flex` 1D avec `flex:${area}` sur les 15 items) remplacée par l'algorithme squarified de Bruls/Huijing/van Wijk 2000 implémenté en ~35 lignes (`squarifyLayout`). Chaque bloc obtient ses `x/y/w/h` en coords abstraites `W=200, H=100` (aspect 2:1) convertis ensuite en % pour le rendu CSS absolu. Le critère `worst(row)` évalue le pire aspect ratio (`max(side²·maxA/s², s²/(side²·minA))`) et ajoute l'item suivant tant qu'il améliore ou n'aggrave pas la ratio, sinon finalise la strip le long de la **plus courte** dimension de la zone restante et récursive sur le rectangle libre.
- `stats/assets/styles.css` — `.treemap` passe de `display:flex; flex-wrap:wrap; gap:2px; min-height:180px` à `position:relative; aspect-ratio:2/1; width:100%` (responsive, ratio fixe cohérent avec l'espace abstrait). `.treemap-item` passe de `position:relative; min-width/height:28px` à `position:absolute; box-sizing:border-box; border:1px solid var(--bg)` — le border interne crée le séparateur 2px visuel entre rects adjacents (remplace le `gap:2px` qui n'existe pas en absolu) et `overflow:hidden` coupe les labels trop longs.
- Labels : seuil de `p>4%` (ancien critère 1D) remplacé par `areaFrac>0.035` (fraction d'aire 2D réelle) — plus pertinent car un item long mais fin ne devait pas forcément afficher son label. Les plus petits rects conservent le tooltip `title=…` complet.
- Vérif numérique (deno eval) sur 15 valeurs décroissantes `[12000..300]` : 15/15 rects émis, somme des aires = 20000 (soit exactement W×H, couverture 100%), worst aspect ratio 1.96 (≈2 — excellent pour squarified, très loin des bandelettes 1D de l'ancien flex où le dernier item pouvait atteindre 30:1).
- `python -m py_compile` OK, `deno check stats/assets/app.js` exit 0. Régénération : `serveur-2026` 49 186 o, `serveur-2020` 65 191 o, `hermitcraft-s10` 378 481 o (tailles identiques — JS externe).

### 2026-04-18 — Tâche 14 : Manifest d'icônes auto-généré

- `scripts/build_icons.py` — après le `[NORMALIZE]`, écriture de `stats/assets/icons/manifest.json` (liste triée des stems des `*.png` effectivement sur disque). Choix de lister le contenu réel plutôt que `ICONS` + `WIKI_HIRES` : si une icône échoue au fetch, elle n'apparaît pas dans le manifest → pas de faux hi-res qui partirait en 404.
- `scripts/generate.py` — nouvelle constante `ICONS_MANIFEST_PATH`, fonction `load_icons_manifest()` (retourne `[]` + warning si absent), injection via `window.ICONS_HR = {icons_json}` dans le template HTML. Si le manifest manque, la génération n'échoue pas — le site retombe en tout-CDN.
- `stats/assets/app.js` — `MC_ICONS_HR` n'est plus un `new Set([...51 valeurs])` hardcodé mais `new Set(window.ICONS_HR || [])`. Le commentaire pointe désormais vers `manifest.json` + `build_icons.py` comme source unique. `mcIcon()` inchangé.
- `manifest.json` initial généré depuis le contenu actuel de `stats/assets/icons/` (51 icônes — identique à l'ancien hardcode). Après régénération des 3 dashboards (serveur-2026 49 846 o, serveur-2020 65 851 o, hermitcraft-s10 379 141 o), `grep window.ICONS_HR` confirme l'injection correcte.
- CLAUDE.md mis à jour : la section "Icon rendering" et la règle "Adding a new icon" ne mentionnent plus de synchronisation manuelle — ajouter une icône = 1 modif dans `build_icons.py` + run, puis commit du PNG et du manifest régénéré.
- `python -m py_compile` OK sur `generate.py` et `build_icons.py` ; `deno check stats/assets/app.js` exit 0.

### 2026-04-19 — Tâche 15 : Renommage des variables courtes

- `stats/assets/app.js` `renderLeaderboardCharts` (~l. 816-855) : 7 `const` renommés selon la liste de la tâche — `da` → `deathAggregate`, `kb` → `killedBy`, `ds` → `deathSorted`, `dc` → `deathColors`, `dt` → `distTypes`, `dco` → `distColors`, `fp` → `filteredPlayers`. Toutes les occurrences en aval mises à jour (arguments de `map`/`reduce`, accès `.length`, etc.).
- Petit bonus nécessaire : le paramètre `t` dans `distTypes.map((t,i)=>...)` shadowait la fonction i18n globale `t()` (pas visible car seul `label()` était appelé dans le callback, mais c'était piégeux) — renommé en `dtype` pour ne plus masquer le global et cohérent avec le `i` qui reste en paramètre de map standard.
- Grep de vérification `\b(da|ds|dc|dt|dco|fp|kb)\b` sur `app.js` → 0 match : aucune occurrence des anciens noms ne subsiste dans tout le fichier (pas juste la fonction). Les paramètres d'une lettre (`n`, `m`, `c`, `a`, `b`, `s`, `v`, `k`, `d`, `i`) dans les callbacks anonymes restent, conformes à la convention JS.
- `deno check stats/assets/app.js` exit 0, `python -m py_compile scripts/generate.py` OK. Régénération : `serveur-2026` 49 846 o, `serveur-2020` 65 851 o, `hermitcraft-s10` 379 141 o — tailles **identiques** (JS externe, seul le contenu textuel change, pas la structure JSON embarquée), rendu strictement identique.

### 2026-04-19 — Tâche 16 : Heatmap d'activité quotidienne

- `scripts/minecraft/history.py` — nouvelle fonction `compute_daily_play_hours(snapshots_root)` (+ helper `_load_play_hours`) : itère sur les paires de snapshots **consécutives** (gap == 1 jour) et attribue le delta `play_hours` à la date du snapshot le plus récent. Les jours de gap (>1j entre 2 snapshots) sont **omis** — pas de zéros faussement comblés ni de hours "réparties" sur des jours arbitraires (respecte le critère "Les jours sans snapshot sont vides"). Deltas négatifs (world reset, corruption) filtrés. Retourne `{uuid: {YYYY-MM-DD: hours}}` ; map vide si <2 snapshots ou pas de paire consécutive.
- `scripts/generate.py` — import + appel `compute_daily_play_hours(snapshots_dir)` dans `main()` ; chaque joueur reçoit `player["daily_hours"]` uniquement si une entrée non vide existe pour son uuid (clé absente sinon, contrat identique à `delta_7d`). Log `[HIST] Daily heatmap data: 9 cells across 3 players` quand des données existent.
- `stats/assets/app.js` — nouvelle fonction `buildHeatmapHtml(name)` (~50 lignes) appelée juste avant `buildBadgesHtml` dans `buildPlayerSection`. Rend un SVG 52 semaines × 7 jours (Mon-Sun, semaine FR), cellule 11×11 px, gap 2 px, viewBox responsive avec `preserveAspectRatio="xMidYMid meet"`. La colonne la plus à droite contient la semaine de "today" ; les jours futurs sont absents (skip via `if(day>today)`). Couleur des cellules = `PLAYER_COLORS_MAP[name]` (couleur d'identité du joueur), opacité par bucket `<0.5h`/`<2h`/`<4h`/`<6h`/`>6h` = `0`/`.3`/`.55`/`.8`/`1.0`. Cellules sans snapshot = classe `.hm-empty` (fond `--bg-card-alt`). Tooltip natif `<title>` par cellule (`2026-04-13 — 3.6h` ou `2026-04-15 — pas de snapshot`). Labels de mois en haut via `toLocaleDateString(lang==='fr'?'fr-FR':'en-US',{month:'short'})` (ne s'affichent qu'à la 1ʳᵉ semaine d'un mois). Légende "Moins ▢▢▢▢▢ Plus" sous le SVG.
- 5 clés i18n ajoutées : `card_heatmap` (Activité quotidienne / Daily activity), `hm_days_active` (jours actifs / active days), `hm_no_data` (pas de snapshot / no snapshot), `hm_less` / `hm_more`, `hm_hours_unit` (`h` partagé). EN n'override que les 4 strings différentes — `hm_hours_unit` fallback FR via `T[lang]?.[k] ?? T.fr[k]`.
- `stats/assets/styles.css` — bloc `.heatmap-meta` / `.heatmap-wrap` (overflow-x:auto pour mobile sous 520 px) / `.heatmap` (width:100%, max-height:140px, min-width:520px) / `.hm-cell` (stroke fond pour séparation) / `.hm-empty` (fond `--bg-card-alt`) / `.hm-label` (texte gris muted, mono 9px) / `.heatmap-legend` (5 swatches 11×11px alignés à droite).
- Vérif Skycryck (serveur-2026, snapshots 04-12/13/14/16/17/18) : 4 cellules attribuées (04-13: 3.6h, 04-14: 0.2h, 04-17: 4.4h, 04-18: 1.8h = 10.0h sommés). Les paires (04-14↔04-16) sont gap → omises. Méta affiche `4 jours actifs · 10.0h`. Toggle EN OK : `4 active days · 10.0h`, mois en `May/Jun/.../Apr`.
- Edge cases : `serveur-2020` et `hermitcraft-s10` n'ont pas de dossier `snapshots/` → `compute_daily_play_hours` retourne `{}`, aucun joueur ne reçoit `daily_hours`, `buildHeatmapHtml` retourne `''` (pas de card vide). Aucune erreur console côté navigateur (vérif Claude_Preview, FR + EN).
- `python -m py_compile` OK ; `deno check stats/assets/app.js` exit 0 ; régénération : `serveur-2026` 50 047 o (+201 o : 9 cellules de daily_hours JSON pour 3 joueurs), `serveur-2020` 65 851 o (inchangé), `hermitcraft-s10` 379 141 o (inchangé). CLAUDE.md mis à jour : section `history.py internals` documente `compute_daily_play_hours` et le contrat `daily_hours` côté player dict.

### 2026-04-19 — Tâche 17 : Render paresseux des sections joueur

- `stats/assets/app.js` — `buildAllSections()` ne construit plus que l'overview et les leaderboards (`contentEl.innerHTML = buildOverview() + buildLeaderboards()`), et vide `renderedPlayers`. Nouvelle `const renderedPlayers = new Set()` mémoïse les sections joueur déjà insérées dans le DOM ; `ensurePlayerSection(name)` fait `insertAdjacentHTML('beforeend', buildPlayerSection(name))` et ajoute au set (no-op si déjà présent). `showSection(id)` appelle `ensurePlayerSection(name)` avant d'activer une section joueur — donc DOM créé à la volée + conservé entre les visites (pas de re-build à chaque clic).
- Destruction Chart.js des sections quittées : dans `showSection`, avant d'écrire `currentSection=id`, si `id!==currentSection` on itère `for(const cid in charts){charts[cid].destroy();delete charts[cid]}`. Les renderers de chaque section (`renderOverviewCharts`, `renderLeaderboardCharts`, `renderPlayerCharts`) appellent déjà `destroyChart(id)` avant de (re)créer un chart, donc double-destroy sans effet de bord. Net change : plus aucun chart ne survit après avoir quitté sa section.
- `switchLang` : inchangé côté code — il appelle `buildAllSections()` (qui vide désormais `renderedPlayers`) puis `showSection(currentSection)` (qui ré-ensure la section joueur courante si besoin). Les sections joueur mémoïsées sont donc invalidées automatiquement au switch de langue — cohérent, vu que le HTML doit être re-rendu dans la nouvelle langue.
- Vérif empirique via preview : **serveur-2020** (9 joueurs) → `contentEl.innerHTML` initial **27 441 o**. **hermitcraft-s10** (55 joueurs) → **132 277 o**. Extrapolation linéaire pour ~20 joueurs : ~48 KB, juste sous le seuil du critère d'acceptation. Avant la tâche : l'initial innerHTML embarquait les 55 sections joueur complètes (heatmaps SVG 52×7, badges 35+, treemaps, fun-facts…) → ordre de plusieurs MB pour hermitcraft.
- Navigation validée côté preview : deep-link `#player/Name` au boot → ensure+activate corrects ; switch overview↔player → `charts` contient uniquement les charts de la section active (ex. `chart-dist-Skycryck` seul après clic joueur, puis les 5 charts overview au retour) ; `renderedPlayers` cumule les joueurs visités (mémoïsation OK) ; switch de langue en cours de visite joueur → `renderedPlayers` reset à `[currentPlayer]`. Aucune erreur console (tests FR+EN, 3 serveurs).
- Tailles des HTML générés inchangées : `serveur-2026` 50 047 o, `serveur-2020` 65 851 o, `hermitcraft-s10` 379 141 o — logique, le JS est externe et le JSON embarqué identique.
- `python -m py_compile scripts/generate.py` OK, `deno check stats/assets/app.js` exit 0. 3 dashboards régénérés sans erreur.

### 2026-04-19 — Tâche 11 (refreshed plan) : Mouvements cette semaine

- **Branche :** refactor/task-11-rank-changes
- **Commits :** a80f398 feat(history): compute rank changes vs baseline, dc795b9 feat(ui): display weekly rank movements on overview, aba81f7 chore: regenerate dashboards
- **Résumé :** Nouvelle fonction `compute_rank_changes` (history.py) détecte les dépassements joueur-sur-joueur entre baseline et maintenant pour les 4 métriques suivies (`play_hours`, `total_mined`, `mob_kills`, `total_crafted`). Pour chaque métrique, on classe les joueurs par valeur décroissante à J-baseline et aujourd'hui ; on émet une entrée seulement si (a) le joueur a gagné au moins 1 rang et (b) on peut nommer un joueur dépassé précis = celui actuellement juste derrière qui était devant à la baseline. Narrative "gain uniquement" — pas de "X s'est fait dépasser" (demande explicite du plan). Cap à 10 en Python, top 5 affiché en UI. Exposée sous `window.RANK_CHANGES`, affichée en overview via `buildRankChangesHtml` entre les 4 stat-tiles et la grille de bar charts. Deep-links vers les sections joueur (`#player/<name>`) avec couleur `PLAYER_COLORS_MAP`. Carte absente si pas de baseline (`RANK_CHANGES = []`).
- **Effets de bord :** 3 clés i18n ajoutées (`card_rank_changes`, `rank_passes`, `rank_on`) en FR+EN. Signature `generate_html` élargie avec `rank_changes: list | None = None`. 3 dashboards régénérés — serveur-2026 a 1 entrée (Villkax a passé Martel0w sur mob_kills, +2 rangs) ; serveur-2020 et hermitcraft-s10 n'ont pas de snapshot ≥ 6j donc `[]`.

---

## 🚫 Anti-patterns à éviter

- Toucher à plusieurs tâches dans la même session
- Modifier le code "pour faire joli" hors du périmètre déclaré
- Ajouter des dépendances sans justification explicite
- Reformater massivement un fichier (le diff devient illisible)
- Commiter sans avoir lancé les tests
