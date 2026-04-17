<#
.SYNOPSIS
    Sync des stats Minecraft depuis Crafty Controller vers le repo GitHub.
    Copie uniquement les fichiers modifies, puis git add/commit/push.
.USAGE
    .\sync-stats.ps1
    .\sync-stats.ps1 -ServerName "mon-serveur" -Source "D:\path\to\stats"
.PARAMETER Source
    Dossier source des fichiers stats Minecraft (Crafty Controller).
.PARAMETER Repo
    Racine du repo git local.
.PARAMETER ServerName
    Nom du sous-dossier sous stats/ (par ex. "serveur-2026").
    Le script ecrit dans <Repo>\stats\<ServerName>\data et snapshots.
#>
param(
    [string]$Source     = "A:\crafty-4\servers\42a06917-c011-47c9-9f59-59b22687007f\world\players\stats",
    [string]$Repo       = "C:\Users\jules\Desktop\minecraft",
    [string]$ServerName = "serveur-2026"
)

$Dest = Join-Path $Repo "stats\$ServerName\data"

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
if ($LASTEXITCODE -ne 0) {
    Write-Host "Git pull a echoue (code $LASTEXITCODE). Verifie ta connexion." -ForegroundColor Red
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}

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

# -- Snapshot horodate (1 par jour max) --
$snapshotDate = Get-Date -Format 'yyyy-MM-dd'
$snapshotDir  = Join-Path $Repo "stats\$ServerName\snapshots\$snapshotDate"
if (-not (Test-Path $snapshotDir)) {
    New-Item -ItemType Directory -Path $snapshotDir -Force | Out-Null
    Copy-Item (Join-Path $Dest "*.json") -Destination $snapshotDir -Force
    Write-Host "Snapshot cree : stats\$ServerName\snapshots\$snapshotDate" -ForegroundColor Green
} else {
    Write-Host "Snapshot du jour deja present, skip : stats\$ServerName\snapshots\$snapshotDate" -ForegroundColor Yellow
}

# -- Git add / commit / push --
Set-Location $Repo
git add "stats/$ServerName/data/*.json" "stats/$ServerName/snapshots"
git commit -m "Update stats $ServerName $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git push
if ($LASTEXITCODE -ne 0) {
    Write-Host "Git push a echoue (code $LASTEXITCODE). Verifie ta connexion." -ForegroundColor Red
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}

Write-Host "Push effectue, les workflows vont se declencher." -ForegroundColor Green

Read-Host "Appuie sur Entree pour fermer"
