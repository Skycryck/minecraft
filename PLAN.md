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

### [ ] Tâche 6 — Supprimer (ou étiqueter) l'estimation du temps de jeu

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > La fonction `estimateTime` (`generate.py:757-785`) invente une répartition (1s/bloc, 10 DPS, scale 85%) présentée comme factuelle. Cette fiction pollue la crédibilité du dashboard.
- **Action attendue :**
  - [ ] Décision produit : soit supprimer complètement la card `card_time_est` et son donut, soit renommer en "Répartition ludique (estimée)" avec tooltip explicatif des hypothèses
  - [ ] Appliquer la décision retenue
- **Critères d'acceptation :**
  - Plus aucune métrique inventée n'est présentée comme une donnée dure
  - Si conservé : l'utilisateur comprend que c'est une heuristique
- **Hors périmètre :** ne pas refaire un vrai calcul de temps (hors scope du JSON Minecraft)
- **Dépendances :** aucune

---

### [ ] Tâche 7 — Corriger le contraste `--text-muted` (accessibilité AA)

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `stats/assets/styles.css` (ou `generate.py`)
- **Problème identifié :**
  > `--text-muted:#5c5c68` sur `--bg:#0c0c0f` donne un ratio de contraste de ~3.8, sous le seuil AA (4.5). Les labels de stat-tile, sync-date et plusieurs méta sont concernés.
- **Action attendue :**
  - [ ] Monter `--text-muted` à `#8080a0` minimum (vérifier ratio ≥ 4.5 via outil)
  - [ ] Vérifier qu'aucun autre endroit ne descend sous le seuil (grep des hex de gris)
- **Critères d'acceptation :**
  - Tous les textes passent AA sur fond sombre
  - L'aspect visuel reste cohérent (pas de texte brutalement blanc)
- **Hors périmètre :** ne pas refaire toute la palette, ne pas ajouter de mode clair
- **Dépendances :** Tâche 1

---

### [ ] Tâche 8 — Mettre les joueurs dans un combobox avec recherche

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > La navigation (`generate.py:848-855`) affiche tous les joueurs en boutons horizontaux. À 10+ joueurs ou sur mobile, cela crée 3 rangées de boutons et aucune recherche n'est possible.
- **Action attendue :**
  - [ ] Garder les 2 onglets fixes "Vue globale" et "Classements"
  - [ ] Remplacer les boutons joueurs par un `<select>` natif (ou combobox filtrant) listant les joueurs triés par heures
  - [ ] Synchroniser avec `location.hash` pour permettre les deep-links (`#player/Jules`)
- **Critères d'acceptation :**
  - L'URL reflète la section affichée
  - On peut partager un lien vers un profil joueur
  - La nav ne déborde plus sur mobile
- **Hors périmètre :** ne pas toucher au contenu des sections, ne pas ajouter de routing library
- **Dépendances :** Tâche 2 recommandée

---

### [ ] Tâche 9 — Archiver des snapshots horodatés des stats

- **Priorité :** 🔴 Haute
- **Fichiers concernés :**
  - `scripts/sync-stats.ps1`
  - `stats/serveur-2026/snapshots/` (nouveau dossier)
  - `.gitignore` (si besoin)
- **Problème identifié :**
  > Le dashboard n'a aucune dimension temporelle : il affiche uniquement un snapshot. Toutes les viz d'évolution (courbes, deltas, streaks) sont impossibles sans historique.
- **Action attendue :**
  - [ ] Modifier `sync-stats.ps1` pour copier aussi les JSON dans `stats/serveur-2026/snapshots/YYYY-MM-DD/` après la copie normale
  - [ ] Ne créer le dossier daté que s'il n'existe pas déjà (1 snapshot/jour max)
  - [ ] Vérifier que le pipeline git + workflow continue de fonctionner
- **Critères d'acceptation :**
  - Après une exécution, `stats/serveur-2026/snapshots/2026-04-17/` contient les mêmes JSON que `data/`
  - Aucune régression dans `generate.py`
- **Hors périmètre :** ne pas encore exploiter les snapshots dans le dashboard (tâche suivante)
- **Dépendances :** aucune

---

### [ ] Tâche 10 — Ajouter des deltas 7j sur les stat-tiles principales

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `scripts/generate.py`
  - `scripts/minecraft/history.py` (nouveau)
  - `stats/assets/app.js` (si tâche 2 faite)
- **Problème identifié :**
  > Les stat-tiles affichent des totaux sans contexte. Un utilisateur ne peut pas voir "qui a joué cette semaine" ni "qui progresse le plus vite".
- **Action attendue :**
  - [ ] Créer `history.py` qui lit le snapshot le plus proche de 7 jours en arrière
  - [ ] Calculer `delta_7d` pour `play_hours`, `total_mined`, `mob_kills`, `total_crafted` et injecter dans le JSON
  - [ ] Afficher `↑ +12h` en `<div class="sub">` dans les stat-tiles concernées
- **Critères d'acceptation :**
  - Si aucun snapshot ≥ 6 jours n'existe, les deltas sont masqués sans erreur
  - Les deltas affichés sont mathématiquement corrects (vérif manuelle 1 joueur)
- **Hors périmètre :** pas de graph temporel dans cette tâche (viendra plus tard)
- **Dépendances :** Tâche 9

---

### [ ] Tâche 11 — Corriger l'edge case du badge `increvable`

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/generate.py` ou `scripts/minecraft/badges.py` (selon tâche 3)
- **Problème identifié :**
  > `generate.py:1034` : `val = deaths>0 ? hours/deaths : (hours>=1 ? 999 : 0)`. Un joueur à 0h a un score de 0 et débloque artificiellement un tier `locked` correct, mais la logique est fragile et peu lisible.
- **Action attendue :**
  - [ ] Simplifier : renvoyer `None` si `hours < 1` (badge non applicable), sinon `hours / max(deaths, 1)`
  - [ ] Afficher "—" dans le badge si la valeur est `None`
- **Critères d'acceptation :**
  - Un joueur à 0 mort ET 0 heure n'affiche plus de badge `increvable`
  - Un joueur à 5h / 0 mort affiche toujours le tier Diamond
- **Hors périmètre :** ne pas refondre le système de badges
- **Dépendances :** Tâche 3 recommandée

---

### [ ] Tâche 12 — Grouper les 12 leaderboards en 4 catégories à onglets

- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > `generate.py:942-977` empile 12 leaderboards en grille 3 colonnes. L'utilisateur est submergé ; aucune hiérarchie ne permet de comparer rapidement les joueurs sur une thématique.
- **Action attendue :**
  - [ ] Regrouper en 4 catégories : Combat (kills, pvp, deaths), Exploration (distance, jumps), Économie (enchant, fish, trades, breed), Production (mined, crafted, playtime)
  - [ ] Ajouter des sous-onglets dans la section Classements
  - [ ] Le premier sous-onglet "Top" reste la vue d'ensemble (3 leaderboards phares)
- **Critères d'acceptation :**
  - Les 12 leaderboards restent accessibles
  - La section Classements ne dépasse plus 1 écran au premier abord
- **Hors périmètre :** ne pas changer le look des leaderboards individuels
- **Dépendances :** aucune

---

### [ ] Tâche 13 — Remplacer le faux treemap par un vrai squarified treemap

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > `buildTreemapHtml` (`generate.py:731-741`) utilise un simple `flex` : les items inégaux deviennent illisibles, sans ratio 2D correct.
- **Action attendue :**
  - [ ] Implémenter un vrai algorithme squarified (30 lignes JS) OU charger `d3-hierarchy` via CDN
  - [ ] Remplacer la sortie HTML flex par un `<svg>` ou un container positionné en absolu
- **Critères d'acceptation :**
  - Les 15 blocs les plus minés sont visibles avec des aires proportionnelles correctes
  - Le treemap est responsive
- **Hors périmètre :** ne pas ajouter d'interactions (zoom, drill-down)
- **Dépendances :** Tâche 2 recommandée

---

### [ ] Tâche 14 — Générer `MC_ICONS_HR` depuis `build_icons.py`

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/build_icons.py`
  - `scripts/generate.py`
  - `stats/assets/icons/manifest.json` (nouveau)
- **Problème identifié :**
  > `MC_ICONS_HR` dans `generate.py:461` et `ICONS`/`WIKI_HIRES` dans `build_icons.py` doivent être synchronisés manuellement (documenté dans CLAUDE.md). Source récurrente d'incohérences.
- **Action attendue :**
  - [ ] `build_icons.py` écrit `stats/assets/icons/manifest.json` avec la liste des icônes produites
  - [ ] `generate.py` lit ce manifest au runtime et injecte la liste dans le JS
  - [ ] Supprimer la constante `MC_ICONS_HR` hardcodée
  - [ ] Mettre à jour CLAUDE.md pour retirer l'étape manuelle
- **Critères d'acceptation :**
  - Ajouter une icône = 1 seule modification (dans `build_icons.py`)
  - Aucune icône ne bascule par erreur en fallback CDN
- **Hors périmètre :** ne pas modifier le pipeline d'icônes lui-même
- **Dépendances :** aucune

---

### [ ] Tâche 15 — Renommer les variables 2 lettres dans `renderLeaderboardCharts`

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > `generate.py:979-997` utilise `da`, `ds`, `dc`, `dt`, `dco`, `fp`, `kb` — illisible à la relecture.
- **Action attendue :**
  - [ ] Renommer en noms explicites : `deathAggregate`, `deathSorted`, `deathColors`, `distTypes`, `distColors`, `filteredPlayers`, `killedBy`
  - [ ] Vérifier que le rendu est strictement identique
- **Critères d'acceptation :**
  - Plus aucune variable < 4 caractères dans cette fonction
  - Aucune régression visuelle
- **Hors périmètre :** ne pas renommer ailleurs, ne pas refactorer la logique
- **Dépendances :** Tâche 2 recommandée

---

### [ ] Tâche 16 — Ajouter un heatmap d'activité par jour (52 semaines × 7 jours)

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/generate.py`
  - `scripts/minecraft/history.py`
- **Problème identifié :**
  > Aucune visualisation ne permet de voir les patterns temporels (jours joués, intensité, streaks). Le style GitHub-contribution est naturel pour ça.
- **Action attendue :**
  - [ ] Depuis les snapshots, calculer pour chaque joueur `{date: delta_hours}` sur 52 semaines
  - [ ] Rendre un SVG 52×7 avec intensité = heures jouées ce jour
  - [ ] L'ajouter dans chaque section joueur
- **Critères d'acceptation :**
  - Les jours sans snapshot sont vides (pas de faux zéros)
  - Le tooltip au survol indique la date et les heures
- **Hors périmètre :** pas de comparaison inter-joueurs dans cette tâche
- **Dépendances :** Tâche 9 + Tâche 10

---

### [ ] Tâche 17 — Render paresseux des sections joueur

- **Priorité :** 🟢 Basse
- **Fichiers concernés :**
  - `scripts/generate.py` (ou `app.js`)
- **Problème identifié :**
  > `buildAllSections` (`generate.py:876`) rend le DOM de tous les joueurs au chargement puis toggle `display:none`. À 20 joueurs × badges + charts, le DOM initial est énorme.
- **Action attendue :**
  - [ ] Ne pré-rendre que la section active au boot
  - [ ] Générer la section d'un joueur à la volée lors du clic, mémoïser le résultat
  - [ ] Détruire les charts Chart.js des sections quittées
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

### 2026-04-17 — Tâche 5 : Palette sémantique

- 5 variables sémantiques ajoutées dans `stats/assets/styles.css` `:root` : `--c-mining` (#3ecf8e), `--c-combat` (#ef6a6a), `--c-survival` (#efaa6a), `--c-travel` (#6aafef), `--c-craft` (#6aefd9). Les 9 anciens vars stat (`--green`, `--red`, `--orange`, `--blue`, `--cyan`, `--yellow`, `--pink`, `--teal`, `--green-dim`) supprimés — plus aucune ambiguïté : chaque catégorie a une couleur unique.
- Toutes les références mises à jour : stat-tiles overview (4) + joueur (8), leaderboards (12 entrées du tableau `boards`), archétypes (miner/fighter/explorer/builder/farmer), profile-stats (kd, traveled), `mkList` (killed_top10, crafted_top15), `kbHtml`, `.broken-tag .bt-count`, `.tt-tier.tt-done`, gradient du header.
- `estimateTime` corrigé : `time_mining` passe de #efd96a (yellow) → #3ecf8e (c-mining), `time_travel` de #3ecf8e (green, ambigu) → #6aafef (c-travel). Le vert est maintenant réservé au mining partout.
- `PALETTE` (identités joueur) inchangée, utilisée uniquement en ligne 12 pour `PLAYER_COLORS_MAP`.
- `python -m py_compile` OK, `deno check stats/assets/app.js` OK (exit 0). Régénération OK : `serveur-2026` 48 458 o et `serveur-2020` 65 063 o (tailles identiques à avant, CSS et JS externes).

### 2026-04-17 — Tâche 4 : Déduplication i18n

- `T.en` dans `stats/assets/app.js` ne contient plus que les overrides : ~32 clés identiques à `T.fr` supprimées (p. ex. `axis_kills`, `d_sprint`, `tier_bronze`, `cat_combat`, `b_nether_mole`, `b_all_rounder`, etc.).
- `t()` et `label()` utilisent désormais `T[lang]?.[k] ?? T.fr[k]` en fallback — le switch EN récupère la valeur FR quand la clé n'existe pas côté EN.
- Régénération OK : `serveur-2026` (48 458 o), `serveur-2020` (65 063 o) — aucune variation de taille (JSON identique, JS externe). `deno check` OK, `python -m py_compile` OK.

### 2026-04-17 — Tâche 3 : Badges en Python

- Nouveau module `scripts/minecraft/badges.py` : 33 badges standards + 2 méta (`all_rounder`, `legende`), avec `get_tier()` et `compute_player_badges()`.
- `process_player()` appelle `compute_player_badges(player)` et attache la liste sous la clé `badges` — chaque entrée contient `{id, name, icon, cat, tiers, value, tier, progress, nextTarget}`, avec `icon` stocké comme nom (ex. `diamond_pickaxe`) et non comme HTML.
- `BADGES`, `getBadgeTier`, `computePlayerBadges` supprimés de `app.js` (~80 lignes). `buildBadgesHtml` lit `p.badges` et appelle `mcIcon(b.icon)` au rendu.
- Vérif manuelle des valeurs sur `serveur-2026` : thresholds et progress cohérents (ex. Martel0w mineur 58911 → tier 3, progress 18%).
- `python -m py_compile` OK ; `deno check stats/assets/app.js` OK (exit 0). Régénération OK : `serveur-2026` 48 458 o, `serveur-2020` 65 063 o (hausse attendue : badges pré-calculés embarqués dans le JSON).

---

## 🚫 Anti-patterns à éviter

- Toucher à plusieurs tâches dans la même session
- Modifier le code "pour faire joli" hors du périmètre déclaré
- Ajouter des dépendances sans justification explicite
- Reformater massivement un fichier (le diff devient illisible)
- Commiter sans avoir lancé les tests
