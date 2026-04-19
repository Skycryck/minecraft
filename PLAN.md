# PLAN.md — Refactoring Dashboard Minecraft Serveur 2026

> **Pour Claude Code :** à chaque nouvelle session (`/clear`), lis ce fichier,
> choisis la **première tâche `[ ]`** dont les dépendances sont satisfaites,
> exécute-la, puis coche-la `[x]` + ajoute une entrée au Journal.
> **Ne traite qu'une seule tâche par session.**

---

## 🎯 Contexte du projet

- **URL live :** https://skycryck.github.io/minecraft/stats/serveur-2026/
- **Stack identifiée :** Python 3.12 (stdlib uniquement, pas de pip install), HTML/CSS/JS vanilla, Chart.js 4.4.1 via CDN, GitHub Pages
- **Architecture :** `scripts/generate.py` (JSON → HTML shell) → `stats/assets/{styles.css,app.js}` (rendu côté client, `PLAYERS_DATA` injecté inline) + `scripts/minecraft/{badges.py,history.py}` (logique métier Python)
- **Objectif global :** enrichir les données (streak, context relatif, records hebdo), moderniser l'UX (heatmap serveur, comparaison 2 joueurs, deltas honnêtes), nettoyer le code (split `app.js`, tests Python, palettes centralisées)
- **Branches :** `refactor/task-N-<slug>` par tâche (merge dans `main` après review)
- **Tests/build :** `python scripts/generate.py stats/serveur-2026/data --title "Test"` — la génération doit réussir et l'HTML doit s'ouvrir sans erreur console. Pour les tâches ajoutant des tests : `python -m unittest discover -s tests`.
- **Déploiement :** push sur `main` → `update-stats.yml` régénère si `stats/*/data/**` change → `static.yml` redéploie via `workflow_run`

---

## 📐 Règles d'exécution (pour CHAQUE tâche)

1. **Lire** les fichiers concernés avant modification (`Read` sur chaque chemin cité)
2. **Créer une branche** dédiée : `git checkout -b refactor/task-N-<slug>`
3. **Commits atomiques** conventionnels (`feat:`, `refactor:`, `fix:`, `style:`, `test:`, `docs:`)
4. **Vérifier le rendu local** avant de clore : `python scripts/generate.py stats/serveur-2026/data --title "Serveur 2026"` puis ouvrir `stats/serveur-2026/index.html` dans un navigateur (console = 0 erreur, sections visibles, toggle FR/EN OK)
5. **Ne pas dépasser le périmètre** déclaré de la tâche ("tant qu'on y est…" = anti-pattern)
6. **Cocher `[x]`** + entrée Journal (date ISO, branche, commits, effets de bord éventuels)
7. **Commit final** du PLAN.md : `chore: mark task N as done`

---

## 📋 Tâches

### [ ] Tâche 1 — Afficher correctement les deltas négatifs et nuls

- **Catégorie :** UX/UI
- **Priorité :** 🔴 Haute
- **Fichiers concernés :** `stats/assets/app.js` (fonction `deltaSub`, lignes ~605-610), `stats/assets/styles.css` (ajouter `.delta-sub--neutral`, `.delta-sub--neg`)
- **Problème identifié :**
  > `deltaSub` cache les deltas `<= 0` (`app.js:607`), un joueur sans activité 7j apparaît identique à un joueur sans baseline. Malhonnête : on ne distingue pas "pas de baseline" de "0h joué cette semaine".
- **Action attendue :**
  - [ ] Modifier `deltaSub(value, suffix)` : rendre `↑ +X` (vert = `--c-mining`) si `value > 0`, `= 0` (gris = `--text-muted`) si `value === 0`, `↓ -X` (rouge = `--c-combat`) si `value < 0`
  - [ ] Garder le retour `''` uniquement quand `value == null` ou `!_baselineDays`
  - [ ] Ajouter les classes CSS associées dans `styles.css` (3 couleurs distinctes)
  - [ ] Régénérer les 2 dashboards et vérifier : 1 joueur inactif affiche `= 0`, 1 joueur sans baseline n'affiche rien
- **Critères d'acceptation :**
  - Les 3 états sont visuellement distincts
  - Aucune valeur n'est masquée silencieusement sauf cas "pas de baseline"
  - Le rendu se dégrade proprement (valeurs décimales arrondies, formatage via `fmt`)
- **Hors périmètre :** ne pas toucher au calcul des deltas côté Python, ne pas changer le placement des stat-tiles
- **Dépendances :** aucune

---

### [ ] Tâche 2 — Ajouter un hash SRI sur Chart.js

- **Catégorie :** Code (sécurité)
- **Priorité :** 🟢 Basse
- **Fichiers concernés :** `scripts/generate.py` (balise `<script src="...chart.umd.min.js">` ligne ~218)
- **Problème identifié :**
  > Chart.js est chargé depuis `cdnjs.cloudflare.com` sans attribut `integrity`. Compromission CDN → exécution arbitraire. Fix trivial.
- **Action attendue :**
  - [ ] Récupérer le SRI officiel de Chart.js 4.4.1 UMD min sur https://www.srihash.org/ (ou générer localement : `curl -s <url> | openssl dgst -sha384 -binary | openssl base64 -A`)
  - [ ] Ajouter `integrity="sha384-..."` et `crossorigin="anonymous"` sur la balise script
  - [ ] Régénérer les 2 dashboards, ouvrir la console : aucun warning SRI
- **Critères d'acceptation :**
  - Chart.js se charge sans erreur console
  - Si on altère le hash d'un caractère, le navigateur refuse le script (test manuel)
- **Hors périmètre :** ne pas changer la version de Chart.js, ne pas bouger vers un autre CDN
- **Dépendances :** aucune

---

### [ ] Tâche 3 — Extraire i18n dans `stats/assets/i18n.js`

- **Catégorie :** Code
- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :** `stats/assets/app.js` (blocs `const T={fr:...,en:...}` lignes ~51-237, fonctions `t()` et `label()` lignes 238-239), `stats/assets/i18n.js` (nouveau), `scripts/generate.py` (ajouter une balise `<script src="../assets/i18n.js"></script>` **avant** `app.js`)
- **Problème identifié :**
  > Le dict `T` occupe ~190 lignes dans `app.js`. Couplé à la logique de rendu, il gonfle un fichier déjà à 1197 l. L'extraction est triviale (pas de dépendance avec le DOM) et ouvre la voie au split général d'`app.js`.
- **Action attendue :**
  - [ ] Créer `stats/assets/i18n.js` contenant : `const T = {fr:..., en:...};`, les fonctions `t()` et `label()`, et une déclaration `let lang = ...` initialisée identiquement
  - [ ] Exposer ces symboles sur `window` (ou les garder globaux du script) de sorte qu'`app.js` les consomme sans modification de logique
  - [ ] Retirer les blocs extraits d'`app.js`, vérifier qu'il reste uniquement les appels (`t('foo')`, `label('x')`)
  - [ ] Modifier `generate.py` pour injecter `<script src="../assets/i18n.js"></script>` juste avant `app.js`
  - [ ] Régénérer et tester : toggle FR/EN fonctionne, aucune clé ne tombe en fallback non voulu
- **Critères d'acceptation :**
  - `app.js` perd ~190 lignes
  - Aucune régression de traduction (comparer visuellement les 2 langues avant/après)
  - `window.lang` reste mutable (switch FR/EN toujours fonctionnel)
- **Hors périmètre :** ne pas refactorer la structure interne du dict, ne pas ajouter de clés EN manquantes
- **Dépendances :** aucune
- **Alternatives modernes suggérées :** passer ultérieurement en `<script type="module">` avec `import`/`export` — pas maintenant, pour garder une tâche atomique.

---

### [ ] Tâche 4 — Extraire palettes et helpers couleurs dans `stats/assets/colors.js`

- **Catégorie :** Code
- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :** `stats/assets/app.js` (blocs `PALETTE`, `_PALETTE_HUES`, `_hslHex`, `playerColor`, `PLAYER_COLORS_MAP` lignes ~16-28 ; `DYE_COLORS`, `WOOD_COLORS`, `LEAF_COLORS`, `BLOCK_COLORS`, `blockColor` lignes ~367-417 ; `deathColors` `app.js:911`, `distColors` `app.js:923`, `dp` ligne 1153, `fallback` dans `buildTreemapHtml` ligne 467), `stats/assets/colors.js` (nouveau), `scripts/generate.py` (script tag)
- **Problème identifié :**
  > Au moins 4 palettes hardcodées dupliquées (`deathColors`, `distColors`, `dp`, `fallback` du treemap) se baladent dans le fichier. Elles se ressemblent mais diffèrent subtilement, ce qui rend la cohérence visuelle fragile.
- **Action attendue :**
  - [ ] Créer `stats/assets/colors.js` avec : `PALETTE`, `playerColor(i)`, `PLAYER_COLORS_MAP` (initialisé après import des données), `DYE_COLORS`/`WOOD_COLORS`/`LEAF_COLORS`/`BLOCK_COLORS`, `blockColor(key, fallback)`, et une palette unifiée `CHART_PALETTE` (fusionnant `deathColors`, `distColors`, `dp`, `fallback` en un seul tableau canonique)
  - [ ] Remplacer les 4 tableaux dans `app.js` par des références à `CHART_PALETTE`
  - [ ] Ajouter `<script src="../assets/colors.js"></script>` dans `generate.py`, placé **avant** `app.js`
  - [ ] Vérifier visuellement : treemap, death pie, dist stacked, per-player dist bar — aucune couleur ne doit changer d'aspect global (les nuances exactes peuvent varier si on fusionne, documenter)
- **Critères d'acceptation :**
  - Plus aucun array de couleurs littéral dans `app.js` (sauf palette d'identité qui reste sémantique)
  - `PLAYER_COLORS_MAP` reste construit une seule fois à partir de `PALETTE`
  - `app.js` perd ~30 lignes
- **Hors périmètre :** ne pas modifier la palette sémantique CSS (`--c-mining`, etc.), ne pas changer les couleurs des stat-tiles
- **Dépendances :** aucune (mais recommandé après tâche 3 pour valider le pattern d'extraction)

---

### [ ] Tâche 5 — Tests unitaires pour `scripts/minecraft/history.py`

- **Catégorie :** Code
- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :** `tests/test_history.py` (nouveau), `tests/__init__.py` (nouveau vide), `scripts/minecraft/history.py` (lecture seule)
- **Problème identifié :**
  > `find_baseline_snapshot` (fenêtre `[6, 30]j`, choix du plus proche de 7j), `compute_daily_play_hours` (dates consécutives uniquement, filtrage deltas négatifs), `compute_deltas` (None si baseline manquante) sont de la logique critique sans test. Une régression silencieuse casserait les deltas sans signal.
- **Action attendue :**
  - [ ] Créer un dossier `tests/` à la racine du repo
  - [ ] Ajouter `tests/test_history.py` utilisant `unittest` (stdlib) + `tempfile` pour fabriquer un `snapshots/` fictif avec plusieurs dossiers `YYYY-MM-DD/*.json`
  - [ ] Couvrir au minimum :
    - `find_baseline_snapshot` retourne `None` si dir vide / uniquement snapshots < 6j / > 30j
    - retourne le dossier le plus proche de 7j quand plusieurs candidats existent
    - `compute_daily_play_hours` ignore les sauts de date, filtre les deltas négatifs (simuler un world reset)
    - `compute_deltas` retourne `None` si `baseline` est vide, sinon dict avec clés `DELTA_KEYS`
  - [ ] Ajouter une section "Tests" dans le `README.md` expliquant `python -m unittest discover -s tests`
  - [ ] Pas de refacto du code source (tests = boîte noire)
- **Critères d'acceptation :**
  - `python -m unittest discover -s tests` passe 100%
  - Au moins 6 cas de test (≥ 2 par fonction principale)
  - Aucune dépendance ajoutée (stdlib uniquement)
- **Hors périmètre :** ne pas tester `badges.py` (tâche 6), ne pas toucher `generate.py`
- **Dépendances :** aucune

---

### [ ] Tâche 6 — Tests unitaires pour `scripts/minecraft/badges.py`

- **Catégorie :** Code
- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :** `tests/test_badges.py` (nouveau), `scripts/minecraft/badges.py` (lecture seule)
- **Problème identifié :**
  > `get_tier`, `_compute_progress`, `_increvable` (edge case `deaths=0`), et le calcul des meta-badges `all_rounder` / `legende` n'ont aucun test. Une erreur off-by-one sur un seuil propage silencieusement.
- **Action attendue :**
  - [ ] Créer `tests/test_badges.py` avec des players-fixtures minimaux (dicts)
  - [ ] Couvrir :
    - `get_tier`: valeurs en-dessous du bronze, exactement au bronze, au gold, au-dessus du diamond
    - `_compute_progress`: progression 0%, 50%, 100%, saturation au tier 4
    - `_increvable`: player < 1h retourne `None`, deaths=0 retourne 999, ratio correct sinon
    - `compute_player_badges`: un joueur minimal retourne 35 entrées (33 + 2 meta), chaque entrée a les clés `id/name/icon/cat/tiers/value/tier/progress/nextTarget`
    - `all_rounder` tier correct quand toutes catégories ont au moins bronze
    - `legende` compte bien les badges ≥ gold
  - [ ] Pas de modification du code source
- **Critères d'acceptation :**
  - `python -m unittest discover -s tests` passe toutes les suites (tâche 5 + 6)
  - Au moins 8 cas de test
- **Hors périmètre :** ne pas réécrire la logique de tier, ne pas ajouter de badges
- **Dépendances :** Tâche 5 (pour la structure `tests/`)

---

### [ ] Tâche 7 — Ajouter une métrique "streak" dans `history.py` et l'afficher sous la heatmap

- **Catégorie :** Données
- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :** `scripts/minecraft/history.py` (nouvelle fonction `compute_streaks`), `scripts/generate.py` (attacher `player["streaks"]` comme pour `daily_hours`), `stats/assets/app.js` (fonction `buildHeatmapHtml`, section méta au-dessus de la heatmap), `stats/assets/i18n.js` ou `T.fr` dans `app.js` (3 nouvelles clés : `hm_streak_current`, `hm_streak_longest`, `hm_days_total`)
- **Problème identifié :**
  > `compute_daily_play_hours` produit déjà toutes les données nécessaires pour calculer des streaks — actuellement seule la heatmap les exploite. Un chiffre comme "plus longue série : 14j consécutifs" est narratif et quasi-gratuit.
- **Action attendue :**
  - [ ] Ajouter dans `history.py` une fonction `compute_streaks(daily_hours: dict[str, dict]) -> dict[str, dict]` retournant pour chaque UUID : `{current: int, longest: int, total_active_days: int}`
  - [ ] Dans `generate.py::main`, si `daily_hours.get(uuid)` existe, attacher `player["streaks"] = streaks[uuid]`
  - [ ] Dans `app.js::buildHeatmapHtml`, si `p.streaks` existe, enrichir la ligne `.heatmap-meta` actuelle avec : `N jours actifs · plus longue série Xj · série en cours Yj`
  - [ ] Ajouter les clés i18n FR + EN correspondantes
  - [ ] Tester avec `serveur-2026` que les valeurs sont plausibles (streaks ≤ jours actifs, current ≤ longest)
- **Critères d'acceptation :**
  - Chaque joueur avec ≥ 2 snapshots affiche les 3 chiffres
  - Un joueur inactif depuis >1j a `current=0`
  - Rendu identique en FR/EN avec les bonnes traductions
- **Hors périmètre :** ne pas modifier la heatmap SVG elle-même, ne pas changer la définition "jour actif" (>0h)
- **Dépendances :** Tâche 5 recommandée (tester `compute_streaks` dans la même foulée)

---

### [ ] Tâche 8 — Ajouter une heatmap serveur agrégée sur l'overview

- **Catégorie :** Données + UX/UI
- **Priorité :** 🔴 Haute
- **Fichiers concernés :** `scripts/generate.py` (exposer `window.SERVER_DAILY = {YYYY-MM-DD: total_hours}`), `scripts/minecraft/history.py` (fonction `aggregate_daily_hours`), `stats/assets/app.js` (nouvelle fonction `buildServerHeatmapHtml`, appel depuis `buildOverview`), `stats/assets/i18n.js` (clé `card_server_heatmap`)
- **Problème identifié :**
  > La heatmap par joueur est déjà une des features les plus parlantes. Une version **agrégée** (somme des heures de tous les joueurs par jour) sur l'overview montre les "soirées serveur", les creux, les pics — ce qu'un bar chart "playtime par joueur" ne montre pas.
- **Action attendue :**
  - [ ] Dans `history.py`, ajouter `aggregate_daily_hours(daily_hours: dict[str, dict]) -> dict[str, float]` qui somme les heures par date sur tous les joueurs
  - [ ] Dans `generate.py`, calculer et injecter `window.SERVER_DAILY = {...}`
  - [ ] Dans `app.js`, créer `buildServerHeatmapHtml()` quasi-identique à `buildHeatmapHtml` mais utilisant `--accent` comme couleur de base (plutôt qu'une couleur d'identité joueur), avec des buckets adaptés (les totaux serveur sont plus gros : `[0, 1, 5, 15, 30, +∞]`)
  - [ ] L'insérer dans `buildOverview()` sous les 4 stat-tiles, avant le grid-2-fixed des bar charts
  - [ ] Ajouter la clé `card_server_heatmap` en FR/EN
- **Critères d'acceptation :**
  - La heatmap s'affiche même avec < 7 jours de snapshots (dégradé correct)
  - Les buckets sont cohérents (pas de case "Plus" quand le max du serveur fait 2h)
  - Mobile : même comportement `overflow-x:auto` que la heatmap joueur
- **Hors périmètre :** ne pas modifier la heatmap par joueur, ne pas toucher aux 4 bar charts de l'overview (tâche 9)
- **Dépendances :** aucune (`daily_hours` existe déjà)

---

### [ ] Tâche 9 — Remplacer les 4 bar charts overview par 1 bar multi-métrique

- **Catégorie :** UX/UI
- **Priorité :** 🔴 Haute
- **Fichiers concernés :** `stats/assets/app.js` (fonctions `buildOverview` et `renderOverviewCharts`), `stats/assets/styles.css` (styles du sélecteur), `stats/assets/i18n.js` (clé `overview_metric_selector`)
- **Problème identifié :**
  > L'overview contient 4 bar charts (playtime, distance, mined, kills) qui comparent les mêmes joueurs sur 4 axes. Juste en dessous, le radar fait déjà la comparaison multi-métrique. Redondance pure. Un seul bar chart avec un sélecteur de métrique libère ~600px de scroll et fait la même chose.
- **Action attendue :**
  - [ ] Remplacer dans `buildOverview` le bloc `<div class="grid grid-2-fixed">...</div>` (4 cards) par une seule card avec : un sélecteur `<select id="overviewMetric">` (options : playtime / mined / kills / distance / crafted / deaths) + un `<canvas id="chart-overview-bar">`
  - [ ] Dans `renderOverviewCharts`, supprimer les 4 appels à `mkBar` et en faire un seul, paramétré par la valeur du select (écouteur `change` qui re-render)
  - [ ] Conserver le radar tel quel
  - [ ] Supprimer les clés i18n orphelines (`chart_playtime`, `chart_distance`, `chart_mined`, `chart_kills`) ou les factoriser en une clé `chart_overview_bar`
  - [ ] Vérifier que la hauteur totale de l'overview a bien diminué (cible : -40% de scroll)
- **Critères d'acceptation :**
  - Le bar chart réagit au changement de métrique sans flash ni erreur
  - Les 4 stat-tiles restent intacts en haut
  - Le radar reste intact en bas
  - Expand/collapse toggle mobile fonctionne toujours sur le bar
- **Hors périmètre :** ne pas toucher au radar, ne pas modifier les leaderboards
- **Dépendances :** Tâche 8 (si la heatmap serveur est au-dessus, on veut que l'overview soit cohérent après)
- **Alternatives modernes suggérées :** Chart.js datasets dynamiques (mise à jour via `chart.data.datasets[0].data = ...; chart.update()`), plus fluide qu'une destruction/recréation.

---

### [ ] Tâche 10 — Contexte relatif sur les stat-tiles joueur

- **Catégorie :** Données + UX/UI
- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :** `stats/assets/app.js` (fonction `buildPlayerSection`, lignes ~1105-1115, stat-tiles avec `sub` existante), `stats/assets/styles.css` (nouvelle classe `.stat-tile .ctx`), `stats/assets/i18n.js` (clés `ctx_pct_server`, `ctx_vs_avg`)
- **Problème identifié :**
  > "12 000 blocs minés" sans référence ne veut rien dire. Est-ce 60% du top ? Sous la moyenne ? Une micro-ligne sous chaque stat-tile joueur ajoutant "X% du serveur" ou "×Y la moyenne" change la lecture.
- **Action attendue :**
  - [ ] Pour chaque stat-tile joueur avec un total-serveur agrégé existant (`totalMined`, `totalKills`, `totalCrafted`, `totalDist`, `totalHours`), calculer `pct = Math.round(value / total * 100)`
  - [ ] Ajouter une ligne `.ctx` sous le `.sub` existant (ou le remplacer si redondant) : `X% du serveur` en FR, `X% of server` en EN
  - [ ] Couleur : `--text-muted`, taille identique à `.sub`
  - [ ] Pour les tiles sans total agrégé pertinent (ex. K/D ratio), ne pas ajouter de contexte
  - [ ] Vérifier que la somme des X% reste ~100% pour les métriques additives (sanity check)
- **Critères d'acceptation :**
  - Au moins 4 tiles joueur ont un contexte relatif
  - Pas de doublon visuel (si une tile a déjà `.sub` et `.delta-sub`, le `.ctx` s'intègre lisiblement)
  - Rendu mobile : pas d'overflow, pas de casse
- **Hors périmètre :** ne pas toucher à l'overview, ne pas ajouter le contexte sur les leaderboards
- **Dépendances :** aucune (`playerNames` et totaux agrégés sont déjà calculés au chargement)

---

### [ ] Tâche 11 — Détecter et afficher les "records pris cette semaine" via snapshots

- **Catégorie :** Données
- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :** `scripts/generate.py` (calcul du classement baseline vs actuel), `scripts/minecraft/history.py` (nouvelle fonction `compute_rank_changes`), `stats/assets/app.js` (nouvelle card ou section "Nouveautés" dans overview), `stats/assets/i18n.js` (clés associées)
- **Problème identifié :**
  > On a la baseline 7j et le classement actuel. Recalculer le classement sur la baseline = détecter qui est passé devant qui cette semaine. "Alice a dépassé Bob sur blocs minés (+1 rang)" = narratif, quasi-gratuit.
- **Action attendue :**
  - [ ] Dans `history.py`, ajouter `compute_rank_changes(current_players: dict, baseline_metrics: dict, keys: list) -> list[dict]` qui retourne les changements de rang significatifs (≥ 1 place) pour les métriques listées
  - [ ] Dans `generate.py`, si baseline disponible, injecter `window.RANK_CHANGES = [...]`
  - [ ] Dans `app.js`, ajouter une card "🏆 Mouvements cette semaine" dans l'overview qui liste au max 5 changements significatifs (format : `{player} dépasse {other} sur {metric} (+1)`)
  - [ ] Ne rien afficher si `RANK_CHANGES` est vide ou absent
  - [ ] Traductions FR/EN
- **Critères d'acceptation :**
  - La card disparaît proprement quand il n'y a pas de baseline
  - Pas plus de 5 entrées affichées (tri par `|delta_rank| * value` ou similaire)
  - Les noms sont cliquables (deep-link `#player/<name>`)
- **Hors périmètre :** ne pas tracker l'historique au-delà de la baseline actuelle (pas de rolling window), ne pas créer une section dédiée
- **Dépendances :** aucune

---

### [ ] Tâche 12 — Sparkline 30j sous le `playtime` dans profile-header

- **Catégorie :** UX/UI + Données
- **Priorité :** 🟡 Moyenne
- **Fichiers concernés :** `stats/assets/app.js` (fonction `buildPlayerSection`, bloc `.profile-stats` ligne ~1099), `stats/assets/styles.css` (classe `.sparkline`)
- **Problème identifié :**
  > `daily_hours` contient déjà les 30+ derniers jours. Une mini-sparkline SVG sous le chiffre `playtime` donne instantanément la tendance (actif / en déclin / irrégulier). 8 lignes de SVG, grosse valeur visuelle.
- **Action attendue :**
  - [ ] Dans `buildPlayerSection`, juste après la `.profile-stat` "Temps de jeu" (ligne ~1100), ajouter un SVG inline (`<svg class="sparkline" viewBox="0 0 100 20">`) tracé à partir des 30 derniers jours de `p.daily_hours` (polyline path)
  - [ ] Couleur : celle du joueur (`PLAYER_COLORS_MAP[name]`)
  - [ ] Si `p.daily_hours` absent ou < 7 entrées : ne rien afficher (dégradation gracieuse)
  - [ ] CSS : `.sparkline { width: 100px; height: 20px; display: block; margin-top: .3rem; }`
  - [ ] Tooltip natif via `<title>` dans le SVG pour le dernier point (jour + heures)
- **Critères d'acceptation :**
  - Les jours manquants sont interpolés visuellement (ligne brisée) ou rendus à 0 — choisir et documenter
  - Pas de surcharge visuelle sur le profile-header (respect de l'alignement existant)
  - Mobile : sparkline reste lisible (pas < 60px de largeur)
- **Hors périmètre :** ne pas ajouter de sparkline sur les autres stat-tiles, ne pas interagir avec la heatmap existante
- **Dépendances :** aucune

---

### [ ] Tâche 13 — Vue de comparaison 2 joueurs (`#compare/alice/bob`)

- **Catégorie :** UX/UI
- **Priorité :** 🔴 Haute
- **Fichiers concernés :** `stats/assets/app.js` (nouvelles fonctions `buildComparePage`, `renderCompareCharts`, routes dans `hashToSection` / `sectionToHash`, entrée dans le select de nav), `stats/assets/i18n.js` (clés `compare_title`, `compare_select_a`, `compare_select_b`, etc.)
- **Problème identifié :**
  > Quand un joueur veut savoir "je mine plus que Bob ?", il doit scroller deux pages et recouper mentalement. Une vue `#compare/alice/bob` avec radar à 2 séries + deltas côte-à-côte répond en 1 regard.
- **Action attendue :**
  - [ ] Ajouter une nouvelle section `compare` gérée par le routeur hash (`#compare/<a>/<b>` → section "compare-<a>-<b>")
  - [ ] Depuis la nav, ajouter un 3e contrôle après le select joueur : un bouton `Comparer…` ouvrant un mini-modal ou 2 selects côte-à-côte
  - [ ] `buildComparePage(a, b)` produit : 2 profile-headers mini-version côte-à-côte + 1 radar à 2 séries (utiliser le même `rm`/`rl` que l'overview radar) + une table de métriques clés avec colonne "différence" (`a - b`)
  - [ ] `renderCompareCharts` instancie le radar via Chart.js
  - [ ] Deep-link testable : `#compare/Alice/Bob` doit charger directement
  - [ ] Traductions FR/EN
- **Critères d'acceptation :**
  - Le deep-link fonctionne au refresh
  - 2 joueurs identiques (`#compare/Alice/Alice`) = redirect vers `#player/Alice` ou message d'erreur propre
  - Les couleurs d'identité (`PLAYER_COLORS_MAP`) sont respectées sur le radar et les headers
  - Mobile : les 2 profile-headers s'empilent verticalement
- **Hors périmètre :** ne pas comparer > 2 joueurs (le radar overview le fait déjà), ne pas ajouter de charts bar/treemap comparatifs
- **Dépendances :** aucune
- **Alternatives modernes suggérées :** pattern "compare view" à la GitHub (diff-style), envisageable ultérieurement mais hors scope.

---

### [ ] Tâche 14 — Accessibilité : skip-link + aria-labels sur treemap

- **Catégorie :** UX/UI (a11y)
- **Priorité :** 🟢 Basse
- **Fichiers concernés :** `stats/assets/app.js` (fonction `buildTreemapHtml`, structure HTML globale dans `buildOverview` et ailleurs), `scripts/generate.py` (ajouter un skip-link statique après `<body>`), `stats/assets/styles.css` (classe `.skip-link`)
- **Problème identifié :**
  > Pas de skip-link (clavier-only : impossible de sauter la nav). `.treemap-item` n'a ni `aria-label` ni `role`. Accessibilité correcte mais incomplète.
- **Action attendue :**
  - [ ] Dans `generate.py`, ajouter après `<body>` : `<a href="#content" class="skip-link">Aller au contenu</a>` (i18n via attribut `data-i18n` ou statique FR — décider, documenter)
  - [ ] CSS : la classe `.skip-link` doit être invisible sauf au focus (pattern classique : `position:absolute; left:-9999px; &:focus { left: 1rem; top: 1rem; ... }`)
  - [ ] Dans `buildTreemapHtml`, ajouter `role="img"` sur chaque `.treemap-item` et `aria-label="${label(r.k)}: ${fmt(r.v)} (${p}%)"`
  - [ ] Vérifier avec Lighthouse ou axe-core : score a11y ne régresse pas, gain mesurable (skip-link détecté, treemap items ont des labels)
- **Critères d'acceptation :**
  - Test clavier : `Tab` depuis le haut de la page fait apparaître le skip-link, `Enter` saute au contenu
  - Lecteur d'écran : les treemap-items sont annoncés avec nom + valeur
- **Hors périmètre :** ne pas réécrire toute la nav pour a11y, ne pas ajouter de landmark roles
- **Dépendances :** aucune

---

### [ ] Tâche 15 — Tap-to-reveal labels sur treemap mobile

- **Catégorie :** UX/UI
- **Priorité :** 🟢 Basse
- **Fichiers concernés :** `stats/assets/app.js` (fonctions `buildTreemapHtml` et `initTreemapTooltip`), `stats/assets/styles.css` (media query mobile sur `.treemap-item`)
- **Problème identifié :**
  > Actuellement `.card` treemap a `.desktop-only`, donc mobile ne voit pas du tout la viz. Alternative : garder le treemap mobile mais passer le tooltip en `touchstart` au lieu de `mouseover`.
- **Action attendue :**
  - [ ] Retirer la classe `.desktop-only` sur la card treemap (et la card `.mobile-only` avec le top-15-list redondant)
  - [ ] Dans `initTreemapTooltip`, ajouter des handlers `touchstart` qui affichent le tooltip au même endroit, et `touchend`/`touchcancel` qui le masquent (délai 2s auto-hide)
  - [ ] CSS mobile : `.treemap-item span` agrandi à `.7rem` (les petits labels sont illisibles à 32% de viewport)
  - [ ] Tester sur émulateur mobile (DevTools) : tap révèle le tooltip, second tap ailleurs le cache
- **Critères d'acceptation :**
  - La viz treemap est visible sur mobile
  - Le tooltip fonctionne au tap (pas d'ambiguïté avec un scroll)
  - La card `.mobile-only` (liste redondante) est supprimée ou factorisée
- **Hors périmètre :** ne pas réécrire l'algo squarify, ne pas changer le rendu desktop
- **Dépendances :** aucune

---

## 📓 Journal

<!-- Entrée par tâche terminée. Format :
### YYYY-MM-DD — Tâche N : <titre>
- **Branche :** refactor/task-N-<slug>
- **Commits :** <hash1> <titre>, <hash2> <titre>
- **Résumé :** <2-3 phrases sur ce qui a bougé>
- **Effets de bord :** <régénération des dashboards, nouvelles clés i18n, etc.>
-->

### 2026-04-19 — Tâche 3 (refreshed plan) : Extraction i18n.js
- **Branche :** refactor/task-3-extract-i18n (poussée via `claude/gifted-kapitsa-4395bf` depuis worktree)
- **Commits :** `refactor(i18n): extract translations and helpers to i18n.js`, `chore: regenerate dashboards after i18n extraction`, `chore: journal entry for task 3 (i18n extraction)`
- **Résumé :** Déplacement de `T` (fr+en), `t()`, `label()`, `lang` et du helper `mcIcon()` (+ `_MI`/`_HR`/`MC_ICONS_HR`) depuis `stats/assets/app.js` vers le nouveau fichier `stats/assets/i18n.js`. Pattern retenu : bindings classiques `let`/`const` au top-level — les scripts classiques partagent le scope lexical global, donc `app.js` voit directement `lang`/`T`/`t`/`label`/`mcIcon` sans passer par `window.*` (zéro changement de référence côté `app.js`). Le helper d'icônes a été co-localisé car `T` l'invoque à l'initialisation. `app.js` passe de **1197 → 993 lignes** (−204) ; `i18n.js` fait 217 lignes.
- **Effets de bord :** nouveau fichier `stats/assets/i18n.js`, `generate.py` injecte un `<script src="../assets/i18n.js">` supplémentaire (avant `app.js`), régénération des deux dashboards (`serveur-2026`, `serveur-2020`). Test navigateur : bascule FR/EN OK, navigation joueur OK, aucune erreur console.

### 2026-04-19 — Tâche 1 : Deltas négatifs/nuls honnêtes

- **Branche :** refactor/task-1-delta-signs
- **Commits :** 4d2bb00 fix(ui): show neutral and negative deltas honestly
- **Résumé :** `deltaSub()` dans `stats/assets/app.js` distingue désormais trois états visuels : `> 0` → `↑ +X` vert (`--c-mining`), `=== 0` → `= 0` gris muted (`--text-muted`), `< 0` → `↓ -X` rouge (`--c-combat`, valeur absolue). Seul un baseline absent (`value==null` ou `!_baselineDays`) masque encore la ligne. La couleur est déplacée de la règle de base `.delta-sub` vers trois modificateurs (`.delta-sub--pos/--zero/--neg`) dans `stats/assets/styles.css` ; la base conserve layout + typographie pour que les sélecteurs `.stat-tile .delta-sub` / `.profile-stat .delta-sub` continuent de fonctionner sur les 7 call sites (overview ×4, profile-stat playtime, stat-tiles joueur ×3). Un joueur inactif pendant la fenêtre de baseline ne ressemble plus à un joueur sans baseline — l'info est honnête.
- **Effets de bord :** régénération des 2 dashboards (serveur-2026 + serveur-2020)

### 2026-04-19 — Tâche 2 : SRI hash Chart.js

- **Branche :** refactor/task-2-sri-chartjs
- **Commits :** 98ac23f fix(security): add SRI hash to Chart.js CDN script · 080f3ef chore: regenerate dashboards with Chart.js SRI attribute
- **Résumé :** Ajout de `integrity="sha384-bs/nf9FbdNouRbMiFcrcZfLXYPKiPaGVGplVbv7dLGECccEXDW+S3zjqSKR5ZEaD"` et `crossorigin="anonymous"` sur le tag `<script>` Chart.js 4.4.1 dans `scripts/generate.py`. Hash SHA-384 calculé via `urllib` + `hashlib` sur le bundle cdnjs (200 807 octets), vérifié deux fois à l'identique. Protège les dashboards contre une compromission du CDN cdnjs.
- **Effets de bord :** régénération des 2 dashboards (`serveur-2026` 50 155 o, `serveur-2020` 65 959 o) — les 2 `index.html` contiennent désormais l'attribut `integrity=`.

### 2026-04-19 — Tâche 5 (refreshed plan) : Tests unitaires history.py

- **Branche :** `refactor/task-5-tests-history`
- **Commits :** `7682bd6` test(history): add unit tests for find_baseline_snapshot, compute_daily_play_hours, compute_deltas ; `6ea66d3` docs(readme): document how to run tests
- **Résumé :** 13 tests couvrant `find_baseline_snapshot` (6), `load_baseline_metrics` (2), `compute_daily_play_hours` (2), `compute_deltas` (3). Fixtures construites à la volée via `tempfile.TemporaryDirectory` + helper `_make_snapshot` qui écrit le schéma minimal attendu par `_extract_metrics` (ticks = heures × 72 000). Tous passent : `Ran 13 tests in 0.018s — OK`.
- **Effets de bord :** nouveau dossier `tests/` (`__init__.py` + `test_history.py`, stdlib uniquement) ; section "Running tests" ajoutée au README ; aucune modif de `scripts/minecraft/history.py` (tests en boîte noire).
- **Clarifications en écrivant les tests :** le contrat `not baseline` de `compute_deltas` absorbe à la fois `None` et `{}` — les deux renvoient `None`, c'est testé explicitement. Le cas de tie-break exact (ages équidistants de la cible) n'est pas testé : le résultat dépend de l'ordre d'itération de `Path.iterdir()` (filesystem-dependent), un test déterministe sans toucher au module a été écarté. Le cas sans ambiguïté (`target=7`, ages 6/10/14 → 6) est testé à la place.

### 2026-04-19 — Tâche 6 (refreshed plan) : Tests unitaires badges.py

- **Branche :** refactor/task-6-tests-badges
- **Commits :** 39e5db8 test(badges): add unit tests for tiers, progress, increvable, and meta-badges
- **Résumé :** 16 tests (`python -m unittest discover -s tests -v` → `Ran 16 tests in 0.002s / OK`) couvrant `get_tier` (3), `_compute_progress` (4), `_increvable` (4) et `compute_player_badges` (5, dont vérification des 35 entrées + présence de `all_rounder` / `legende` en catégorie `prestige`). Fixture "toutes catégories bronze" implémentée en mode brute-force : tous les champs pertinents (top-level + `badge_data` + `distances` + `killed_by`) mis à `1e9` pour garantir diamond sur chaque badge standard, ce qui prouve a fortiori que toutes les catégories META ont au moins bronze. Robuste aux futures modifs de `BADGES`. Subtilité notée : avec le fixture maxed, `_increvable` = hours/deaths, donc `deaths` doit être volontairement modéré (10) pour que le ratio reste élevé — toutes les catégories passent quand même car 10 == seuil bronze de `kamikaze`.
- **Effets de bord :** nouveaux fichiers `tests/__init__.py` (vide) + `tests/test_badges.py` (~210 lignes). Aucune modification de `scripts/minecraft/badges.py`.

### 2026-04-19 — Tâche 4 (refreshed plan) : Extraction colors.js + palette unifiée

- **Branche :** refactor/task-4-extract-colors
- **Commits :** `c2a7ac3` refactor(colors): extract palettes and block-color maps to colors.js · `ae0115c` refactor(colors): replace 4 duplicate palettes with CHART_PALETTE · `1ccffd1` chore: regenerate dashboards after colors extraction
- **Résumé :** Extraction de toutes les définitions de couleurs et helpers associés dans un nouveau fichier `stats/assets/colors.js` (97 lignes) : palette d'identité joueur (`PALETTE`, `_PALETTE_HUES`, `_hslHex`, `playerColor`), maps de couleurs de blocs (`BLOCK_COLORS` + `DYE_COLORS`/`WOOD_COLORS`/`LEAF_COLORS` + `blockColor()` et suffixes). Nouvelle constante `CHART_PALETTE` (15 teintes : 8 premières alignées sur l'identité mais démarrant par le violet brand `#7c6aef`, + 7 teintes muted/dark pour couvrir la taille max de l'ancienne palette `fallback` du treemap) remplace 4 tableaux dupliqués inline (treemap `fallback`, doughnut `deathColors`, stacked bar `distColors`, per-player bar `dp`). `app.js` passe de **1197 → 1123 lignes** (-74). `PLAYER_COLORS_MAP` reste construit dans `app.js` (dépend de `PLAYERS_DATA`) mais utilise `playerColor()` du scope global partagé.
- **Effets de bord :** nouveau fichier `stats/assets/colors.js`, `generate.py` injecte 1 `<script src="../assets/colors.js">` avant `app.js`, régénération de serveur-2026 et serveur-2020 (hermitcraft-s10 non re-généré — hors demande). Smoke test via `deno eval` : tous les symboles retournent les bonnes valeurs (PALETTE 8 hues, CHART_PALETTE 15, 82 BLOCK_COLORS, `blockColor('diamond_ore')='#5ecfd5'`, `blockColor('oak_planks')='#b08a50'`, `blockColor('red_wool')='#b02e26'`, fallback unknown retourne bien l'argument). Parse-check complet OK via `new Function(colorsSrc + '\n' + appSrc)`.

### 2026-04-19 — Tâche 7 (refreshed plan) : Métrique streak sous heatmap

- **Branche :** refactor/task-7-streak-metric
- **Commits :** d6cae2e feat(history): compute per-player streak metrics, ac3b0fe feat(ui): display longest + current streak under heatmap meta line, da2bcce chore: regenerate dashboards with streak data.
- **Résumé :** Nouvelle fonction `compute_streaks(daily_hours, today)` dans `scripts/minecraft/history.py`, exposée sous `player['streaks'] = {current, longest, total_active_days}` via `generate.py`. Affichée en suffixe de la ligne `.heatmap-meta` (`· plus longue série Nj · série en cours Nj` en FR, `· longest streak Nd · current streak Nd` en EN) — l'unité jour réutilise la clé i18n existante `delta_unit` (`j`/`d`).
- **Effets de bord :** 2 nouvelles clés i18n (`hm_streak_current`, `hm_streak_longest`) dupliquées dans `T.fr` et `T.en`. Régénération des 2 dashboards : `serveur-2026` 50 221 o, 3 joueurs ont une clé `streaks` (longest runs de 2 jours) ; `serveur-2020` 65 851 o inchangé (pas de dossier `snapshots/`, `compute_daily_play_hours` retourne `{}` → aucun joueur ne reçoit `streaks`, dégradation propre — le suffixe est vide et la ligne meta garde son ancien format).
- **Invariants vérifiés :** `current ≤ longest ≤ total_active_days` sur les 3 entrées générées (ex. `{current:0,longest:2,total_active_days:3}`). Pas de test automatisé ajouté (scaffolding tests en tâche 5 sur une autre branche).

### 2026-04-19 — Tâche 8 (refreshed plan) : Heatmap serveur agrégée

- **Branche :** refactor/task-8-server-heatmap
- **Commits :** e8f9f37 feat(history): aggregate daily hours across all players, b960d45 feat(ui): add server-wide activity heatmap to overview, d52a7f8 chore: regenerate dashboards with server heatmap data
- **Résumé :** Nouvelle fonction `aggregate_daily_hours(daily_hours)` dans `scripts/minecraft/history.py` (somme des heures/jour agrégées par UUID, arrondi 2 déc.). `generate.py` l'appelle puis la passe à `generate_html(..., server_daily)` qui injecte `window.SERVER_DAILY` dans le shell HTML. Côté JS, `buildServerHeatmapHtml()` (nouveau, à côté de `buildHeatmapHtml`) rend une SVG 52×7 calquée sur la version par joueur mais avec des seuils ajustés aux totaux serveur (buckets `[1, 5, 15, 30]`) et la teinte `--accent` (`#7c6aef`) au lieu d'une identité joueur. La carte est insérée dans `buildOverview()` entre les stat-tiles et la grille des 4 bar-charts ; si `SERVER_DAILY` est `{}` la fonction retourne `''` et la carte disparaît sans template orphelin.
- **Effets de bord :** 1 clé i18n ajoutée (`card_server_heatmap`, FR + EN), signature `generate_html` élargie d'un arg optionnel `server_daily`, régénération des 2 dashboards. `serveur-2020` n'a pas de `snapshots/` donc `SERVER_DAILY = {}` et la carte reste absente — `serveur-2026` affiche la heatmap agrégée (4 jours actifs visibles, max 11.4h cumulées le 13/04).

### 2026-04-19 — Tâche 9 (refreshed plan) : Bar overview unifiée

- **Branche :** `refactor/task-9-overview-unified-bar`
- **Commits :** `1da1e8b` feat(ui): unify overview bar charts behind a metric selector, `b420b3b` chore: regenerate dashboards
- **Résumé :** Les 4 bar charts de l'overview (playtime/distance/mined/kills) sont remplacés par 1 seule carte `chart-overview-bar` avec un `<select id="overviewMetric">` à 6 options (play_hours, total_mined, mob_kills, total_distance_km, total_crafted, deaths). Les labels d'options réutilisent les clés `radar_*` existantes. `renderOverviewCharts` expose un tableau `METRICS` et invoque le helper `mkBar` existant (signature inchangée) avec la métrique courante ; le listener `change` est branché une seule fois via le flag `sel.dataset.wired`. Radar et stat-tiles intouchés. Persistance localStorage (`mc-overview-metric`) implémentée — 5 lignes, trivial.
- **Effets de bord i18n :** ajout de `chart_overview_bar`, `overview_metric_label`, `axis_deaths` dans `T.fr` et `T.en`. Suppression des 4 clés orphelines `chart_playtime`/`chart_distance`/`chart_mined`/`chart_kills` dans les deux dicts (grep confirme : usage uniquement dans les 4 cartes supprimées). `axis_crafted` non ajouté — on réutilise `axis_blocks` comme prévu par le plan.
- **CSS :** nouvelle classe `.overview-metric-select` (mime `.nav-player-select` mais min-height 36px au lieu de 50) + `.overview-bar-header` (flex space-between pour poser le select à droite du h3) + `.sr-only` (utility pour le `<label>` accessible). Dans `stats/assets/styles.css`.
- **Régénération :** `serveur-2026` 50 047 o et `serveur-2020` 65 851 o régénérés (tailles identiques, JS externe).
- **Smoke test navigateur :** non effectué (pas de browser dans ce worktree) ; vérification par grep — 0 occurrence des 4 anciens canvas IDs dans `app.js`, 7 occurrences de `overviewMetric`/`chart-overview-bar`.

### 2026-04-19 — Tâche 10 (refreshed plan) : Contexte relatif stat-tiles joueur

- **Branche :** refactor/task-10-relative-context
- **Commits :** 5861595 feat(ui): add "X% du serveur" context line under player stat-tiles, 615a0d9 chore: regenerate dashboards
- **Résumé :** 4 stat-tiles joueur (mined, kills, deaths, crafted) affichent "X% du serveur" en sous-ligne. Nouvelle classe `.ctx-sub` + helper `ctxPct()`. Filtre 0% pour ne pas polluer.
- **Effets de bord :** 1 clé i18n (`ctx_of_server`), régénération des 2 dashboards

---

## 🚫 Anti-patterns à éviter

- Traiter plusieurs tâches dans la même session (perte du focus, PR trop grosse)
- Refactos hors-périmètre ("tant qu'on y est je renomme toutes les variables") — crée du bruit dans le diff et masque le changement utile
- Reformatage massif (Prettier/autoformat sur tout `app.js`) qui rend le diff illisible
- Ajout de dépendances non justifié (le projet tient sur Python stdlib + Chart.js + Google Fonts : ne pas casser cette contrainte)
- Commit sans vérification du rendu (toujours régénérer et ouvrir le HTML avant de clore)
- Toucher `index.html` manuellement (overwritten par `generate.py`)
- Oublier de régénérer les 2 dashboards (`serveur-2026` + `serveur-2020`) quand une tâche change `app.js` / `styles.css` / `generate.py`
