# Pousser des changements de code vers Tickstats (repo public)

Note perso rangée dans `docs/` (exclu du mirror). Visible sur `origin` (repo privé), jamais poussée sur `public` (Tickstats).

## Workflow standard

```powershell
cd C:\Users\jules\Desktop\minecraft
git checkout main
git pull

# ... tu fais tes modifs de code, tu commit, tu push sur main comme d'habitude ...

# Quand tu veux publier ces changements sur Tickstats :
.\scripts\mirror-to-public.ps1 -Push
```

Le script recrée `public-main` depuis `main` en retirant les exclusions, commit `"mirror from main @ <sha>"`, et push vers le remote `public` en tant que `main`.

## Ce qui est exclu du mirror

Défini dans `scripts/mirror-to-public.ps1` (paramètre `$Exclude`) :

- `stats/serveur-2026/` — données perso
- `stats/serveur-2020/` — données perso
- `stats/hermitcraft-s10/` — demo (sert de preview sur le site perso uniquement)
- `scripts/sync-stats.ps1` — script de sync Crafty-specific
- `scripts/mirror-to-public.ps1` — script de maintenance du repo privé
- `docs/` — journaux de dev internes (PLAN-1, PLAN-2, ce fichier, etc.)

Pour ajouter une exclusion ponctuelle :

```powershell
.\scripts\mirror-to-public.ps1 -Push -Exclude @("stats/serveur-2026","stats/autre-truc")
```

Pour une exclusion permanente : éditer la liste `$Exclude` par défaut dans le script et commit.

## Remotes configurés

- `origin` → `github.com/Skycryck/minecraft` (perso, avec données)
- `public` → `github.com/Skycryck/Tickstats` (template)

Vérifier avec `git remote -v`. Si `public` manque :

```powershell
git remote add public https://github.com/Skycryck/Tickstats.git
```

## En cas de pépin

**Quelque chose de perso a fuité sur Tickstats** (mauvaise exclusion, oubli) :

```powershell
# ajoute l'exclusion manquante dans mirror-to-public.ps1, commit sur main, puis :
git branch -D public-main
.\scripts\mirror-to-public.ps1
git push public public-main:main --force
```

Le force-push est safe ici : `public-main` est une chaîne linéaire de commits de mirror automatiques, aucun historique humain à préserver.

**Le script dit "Worktree not clean"** : check `git status`. Commit/stash/supprime les modifs non-trackées avant de re-lancer.

**Pages failed sur Tickstats après un push** : vérifier `Settings > Pages > Source: GitHub Actions` (pas "Deploy from a branch").

## Règle d'hygiène

Jamais de `git add .` à la racine sans relire — risque d'ajouter accidentellement un dossier perso sur `main` qui se propagerait au prochain mirror si pas dans l'exclude.
