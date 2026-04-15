# Minecraft Stats Dashboard

Dashboard web interactif qui transforme les fichiers de statistiques bruts d'un serveur Minecraft en tableaux de bord visuels, déployés automatiquement via GitHub Pages.

## Fonctionnalités

- **Profils joueurs** — Heures de jeu, morts, mobs tués, blocs minés, distances parcourues, objets craftés, avec détection automatique d'archétype (Mineur, Combattant, Explorateur, Bâtisseur, Fermier)
- **Système de badges** — 32 badges répartis en 4 paliers (Bronze → Argent → Or → Diamant), avec tooltips de progression au survol
- **Visualisations interactives** — Graphiques Chart.js : répartition du temps de jeu, distances par mode de déplacement, blocs minés, mobs tués, estimation du temps passé par activité
- **Leaderboards** — Classements sur 15+ métriques
- **Fun facts** — Faits amusants générés automatiquement pour chaque joueur
- **Pipeline automatisé** — Push de données JSON → GitHub Actions régénère le HTML → déploiement GitHub Pages

## Stack technique

| Composant | Technologie |
|---|---|
| Génération | Python 3.12+ (stdlib uniquement) |
| Frontend | HTML5 / CSS3 / JavaScript vanilla (ES6+) |
| Graphiques | Chart.js 4.4.1 |
| Polices | JetBrains Mono, Space Grotesk |
| CI/CD | GitHub Actions |
| Hébergement | GitHub Pages |
| Sync locale | PowerShell |

## Structure du projet

```
├── scripts/
│   ├── generate.py          # Générateur principal (JSON → HTML)
│   └── sync-stats.ps1       # Script de synchronisation Windows
├── stats/
│   ├── serveur-2026/
│   │   ├── data/            # Fichiers JSON bruts (stats Minecraft)
│   │   ├── index.html       # Dashboard généré automatiquement
│   │   └── .uuid_cache.json # Cache UUID → pseudo Mojang
│   └── serveur-2020/
│       ├── data/
│       ├── index.html
│       └── .uuid_cache.json
└── .github/workflows/
    ├── update-stats.yml     # Régénère le dashboard à chaque changement
    └── static.yml           # Déploie sur GitHub Pages
```

## Utilisation

### Prérequis

- Python 3.12+
- Git

### Générer un dashboard localement

```bash
python scripts/generate.py stats/serveur-2026/data --title "Serveur 2026"
```

Le fichier `stats/serveur-2026/index.html` est généré automatiquement.

### Synchroniser les stats depuis un serveur (Windows)

```powershell
.\scripts\sync-stats.ps1
```

Ce script copie les fichiers JSON modifiés depuis Crafty Controller, commit et push vers GitHub.

### Pipeline CI/CD

1. `sync-stats.ps1` copie les JSON et push sur GitHub
2. GitHub Actions (`update-stats.yml`) détecte les changements dans `stats/*/data/`
3. `generate.py` régénère les fichiers `index.html`
4. GitHub Actions (`static.yml`) déploie sur GitHub Pages

## Détails techniques

### Résolution UUID

Les UUID Minecraft sont convertis en pseudos via l'API Mojang Session Server, avec un cache local (`.uuid_cache.json`) pour éviter le rate-limiting.

### Conversion des unités

| Unité Minecraft | Conversion |
|---|---|
| `play_one_minute` (ticks) | ÷ 72 000 → heures |
| `*_one_cm` (distances) | ÷ 100 000 → km |
| `damage_*` | ÷ 20 → cœurs |

### Badges

Les 32 badges couvrent 8 catégories : Minage, Combat, Survie, Exploration, Agriculture, Artisanat, Vie quotidienne et Prestige. Chaque badge possède 4 seuils progressifs avec indicateur visuel de progression.
