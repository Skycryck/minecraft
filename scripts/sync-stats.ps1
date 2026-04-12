<#
.SYNOPSIS
    Sync des stats Minecraft depuis Crafty Controller vers le repo GitHub.
    Copie uniquement les fichiers modifies, puis git add/commit/push.
.USAGE
    .\sync-stats.ps1
#>

$Source = "A:\crafty-4\servers\42a06917-c011-47c9-9f59-59b22687007f\world\players\stats"
$Dest   = "C:\Users\jules\Desktop\minecraft\stats\serveur-2026\data"
$Repo   = "C:\Users\jules\Desktop\minecraft"

# -- Verifications --
if (-not (Test-Path $Source)) {
    Write-Host "Dossier source introuvable : $Source" -ForegroundColor Red
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}

if (-not (Test-Path "$Repo\.git")) {
    Write-Host "Pas un repo git : $Repo" -ForegroundColor Red
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}

if (-not (Test-Path $Dest)) {
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
}

# -- Git pull --
Set-Location $Repo
Write-Host "Git pull..." -ForegroundColor Cyan
git pull

# -- Copie des fichiers modifies --
$copied = 0
Get-ChildItem -Path $Source -Filter "*.json" | ForEach-Object {
    $destFile = Join-Path $Dest $_.Name
    $needCopy = $false

    if (-not (Test-Path $destFile)) {
        $needCopy = $true
    }
    elseif ($_.LastWriteTime -gt (Get-Item $destFile).LastWriteTime) {
        $needCopy = $true
    }

    if ($needCopy) {
        Copy-Item $_.FullName -Destination $destFile -Force
        Write-Host "  Copie: $($_.Name)" -ForegroundColor Green
        $copied++
    }
}

if ($copied -eq 0) {
    Write-Host "Aucun fichier modifie, rien a faire." -ForegroundColor Yellow
    Read-Host "Appuie sur Entree pour fermer"
    exit 0
}

Write-Host "$copied fichier(s) copie(s)" -ForegroundColor Cyan

# -- Git add / commit / push --
Set-Location $Repo
git add stats/serveur-2026/data/*.json
git commit -m "Update stats serveur-2026 $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git push

Write-Host "Push effectue, les workflows vont se declencher." -ForegroundColor Green

Read-Host "Appuie sur Entree pour fermer"
