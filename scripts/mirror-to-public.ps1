<#
.SYNOPSIS
    Rebuild the local "public-main" branch from "main" with personal data
    (servers, dev plans, local sync script) stripped out, then show how to
    push to the public remote.

.DESCRIPTION
    Each call produces a new commit on public-main whose tree =
    main's tree minus the paths listed in -Exclude. public-main's history
    is therefore a linear chain of "mirror from main" snapshots -
    no history of personal data ever leaks to the public repo.

    If the public-main branch does not exist, it is created as an orphan
    (zero shared history with main).

.USAGE
    .\scripts\mirror-to-public.ps1
    .\scripts\mirror-to-public.ps1 -Push            # mirror + git push public
    .\scripts\mirror-to-public.ps1 -Exclude @("stats/my-server", "PLAN.md")

.PARAMETER SourceBranch
    Source branch (default: main).

.PARAMETER TargetBranch
    Local branch to (re)build (default: public-main).

.PARAMETER Exclude
    Paths (files or folders) to strip from the mirror, relative to repo root.

.PARAMETER Push
    If set, pushes TargetBranch to the "public" remote as main.
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

# -- Checks --
$inRepo = git rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not in a git repo." -ForegroundColor Red
    exit 1
}
Set-Location $inRepo

if (git status --porcelain) {
    Write-Host "Worktree not clean. Commit or stash first." -ForegroundColor Red
    exit 1
}

$current = git rev-parse --abbrev-ref HEAD
$sourceSha = git rev-parse --short $SourceBranch
if ($LASTEXITCODE -ne 0) {
    Write-Host "Source branch not found: $SourceBranch" -ForegroundColor Red
    exit 1
}

# -- Switch to TargetBranch (created as orphan if missing) --
git show-ref --verify --quiet "refs/heads/$TargetBranch"
$targetExists = ($LASTEXITCODE -eq 0)

if (-not $targetExists) {
    Write-Host "Creating orphan branch $TargetBranch..." -ForegroundColor Cyan
    git checkout --orphan $TargetBranch
    git rm -rf . 2>$null | Out-Null
    git commit --allow-empty -m "init public-main" | Out-Null
} else {
    git checkout $TargetBranch
}

# -- Wipe contents then recopy from SourceBranch --
Write-Host "Recopying tree from $SourceBranch ($sourceSha)..." -ForegroundColor Cyan
git rm -rf . 2>$null | Out-Null
git checkout $SourceBranch -- .

# -- Strip excluded paths --
foreach ($p in $Exclude) {
    if (Test-Path $p) {
        Write-Host "  excluded: $p" -ForegroundColor Yellow
        git rm -rf $p | Out-Null
    }
}

# -- Commit if diff --
git add -A
if (git diff --staged --quiet) {
    Write-Host "No changes since the previous mirror." -ForegroundColor Yellow
} else {
    git commit -m "mirror from $SourceBranch @ $sourceSha" | Out-Null
    Write-Host "public-main updated." -ForegroundColor Green
}

# -- Back to initial branch --
git checkout $current | Out-Null

# -- Optional push --
if ($Push) {
    Write-Host "Push to 'public' remote (${TargetBranch}:main)..." -ForegroundColor Cyan
    git push public "${TargetBranch}:main"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Push failed. Is the 'public' remote configured?" -ForegroundColor Red
        Write-Host "  git remote add public git@github.com:<user>/<repo-public>.git" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "To push to the public repo:" -ForegroundColor Cyan
    Write-Host "  git push public ${TargetBranch}:main" -ForegroundColor White
}
