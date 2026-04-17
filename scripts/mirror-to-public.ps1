<#
.SYNOPSIS
    Reconstruit la branche locale "public-main" depuis "main" en retirant
    les donnees perso (serveurs, plans de dev, script de sync local), puis
    indique comment pousser vers le remote public.

.DESCRIPTION
    Chaque appel produit un nouveau commit sur public-main dont l'arbre =
    arbre de main moins les chemins listes dans -Exclude. L'historique de
    public-main est donc une chaine lineaire de snapshots "mirror from main"
    - pas d'historique des donnees perso ne fuite vers le depot public.

    Si la branche public-main n'existe pas, elle est creee comme orpheline
    (zero historique partage avec main).

.USAGE
    .\scripts\mirror-to-public.ps1
    .\scripts\mirror-to-public.ps1 -Push            # mirror + git push public
    .\scripts\mirror-to-public.ps1 -Exclude @("stats/mon-serveur", "PLAN.md")

.PARAMETER SourceBranch
    Branche source (defaut: main).

.PARAMETER TargetBranch
    Branche locale a (re)construire (defaut: public-main).

.PARAMETER Exclude
    Chemins (fichiers ou dossiers) a retirer du mirror, relatifs a la racine.

.PARAMETER Push
    Si present, pousse TargetBranch vers le remote "public" en tant que main.
#>
param(
    [string]$SourceBranch = "main",
    [string]$TargetBranch = "public-main",
    [string[]]$Exclude = @(
        "stats/serveur-2026",
        "stats/serveur-2020",
        "scripts/sync-stats.ps1",
        "PLAN.md"
    ),
    [switch]$Push
)

# -- Verifications --
$inRepo = git rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Pas dans un repo git." -ForegroundColor Red
    exit 1
}
Set-Location $inRepo

if (git status --porcelain) {
    Write-Host "Worktree non propre. Commit ou stash d'abord." -ForegroundColor Red
    exit 1
}

$current = git rev-parse --abbrev-ref HEAD
$sourceSha = git rev-parse --short $SourceBranch
if ($LASTEXITCODE -ne 0) {
    Write-Host "Branche source introuvable : $SourceBranch" -ForegroundColor Red
    exit 1
}

# -- Bascule sur TargetBranch (cree comme orpheline si absente) --
git show-ref --verify --quiet "refs/heads/$TargetBranch"
$targetExists = ($LASTEXITCODE -eq 0)

if (-not $targetExists) {
    Write-Host "Creation de la branche orpheline $TargetBranch..." -ForegroundColor Cyan
    git checkout --orphan $TargetBranch
    git rm -rf . 2>$null | Out-Null
    git commit --allow-empty -m "init public-main" | Out-Null
} else {
    git checkout $TargetBranch
}

# -- Efface le contenu puis recopie depuis SourceBranch --
Write-Host "Recopie de l'arbre depuis $SourceBranch ($sourceSha)..." -ForegroundColor Cyan
git rm -rf . 2>$null | Out-Null
git checkout $SourceBranch -- .

# -- Retrait des chemins exclus --
foreach ($p in $Exclude) {
    if (Test-Path $p) {
        Write-Host "  exclu: $p" -ForegroundColor Yellow
        git rm -rf $p | Out-Null
    }
}

# -- Commit si diff --
git add -A
if (git diff --staged --quiet) {
    Write-Host "Aucun changement par rapport au mirror precedent." -ForegroundColor Yellow
} else {
    git commit -m "mirror from $SourceBranch @ $sourceSha" | Out-Null
    Write-Host "public-main mis a jour." -ForegroundColor Green
}

# -- Retour branche initiale --
git checkout $current | Out-Null

# -- Push optionnel --
if ($Push) {
    Write-Host "Push vers remote 'public' (${TargetBranch}:main)..." -ForegroundColor Cyan
    git push public "${TargetBranch}:main"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Push echoue. Remote 'public' configure ? " -ForegroundColor Red
        Write-Host "  git remote add public git@github.com:<user>/<repo-public>.git" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "Pour pousser vers le depot public :" -ForegroundColor Cyan
    Write-Host "  git push public ${TargetBranch}:main" -ForegroundColor White
}
