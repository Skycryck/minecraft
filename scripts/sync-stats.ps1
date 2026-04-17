<#
.SYNOPSIS
    Sync Minecraft stats from Crafty Controller to the GitHub repo.
    Copies only modified files, then runs git add/commit/push.
.USAGE
    .\sync-stats.ps1
    .\sync-stats.ps1 -ServerName "my-server" -Source "D:\path\to\stats"
.PARAMETER Source
    Source folder holding the Minecraft stats files (Crafty Controller).
.PARAMETER Repo
    Root of the local git repo.
.PARAMETER ServerName
    Name of the sub-folder under stats/ (e.g. "serveur-2026").
    The script writes to <Repo>\stats\<ServerName>\data and snapshots.
#>
param(
    [string]$Source     = "A:\crafty-4\servers\42a06917-c011-47c9-9f59-59b22687007f\world\players\stats",
    [string]$Repo       = "C:\Users\jules\Desktop\minecraft",
    [string]$ServerName = "serveur-2026"
)

$Dest = Join-Path $Repo "stats\$ServerName\data"

# -- Checks --
if (-not (Test-Path $Source)) {
    Write-Host "Source folder not found: $Source" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

if (-not (Test-Path "$Repo\.git")) {
    Write-Host "Not a git repo: $Repo" -ForegroundColor Red
    Read-Host "Press Enter to close"
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
    Write-Host "Git pull failed (code $LASTEXITCODE). Check your connection." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

# -- Copy modified files --
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
        Write-Host "  Copied: $($_.Name)" -ForegroundColor Green
        $copied++
    }
}

if ($copied -eq 0) {
    Write-Host "No modified files, nothing to do." -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    exit 0
}

Write-Host "$copied file(s) copied" -ForegroundColor Cyan

# -- Dated snapshot (1 per day max) --
$snapshotDate = Get-Date -Format 'yyyy-MM-dd'
$snapshotDir  = Join-Path $Repo "stats\$ServerName\snapshots\$snapshotDate"
if (-not (Test-Path $snapshotDir)) {
    New-Item -ItemType Directory -Path $snapshotDir -Force | Out-Null
    Copy-Item (Join-Path $Dest "*.json") -Destination $snapshotDir -Force
    Write-Host "Snapshot created: stats\$ServerName\snapshots\$snapshotDate" -ForegroundColor Green
} else {
    Write-Host "Today's snapshot already present, skipping: stats\$ServerName\snapshots\$snapshotDate" -ForegroundColor Yellow
}

# -- Git add / commit / push --
Set-Location $Repo
git add "stats/$ServerName/data/*.json" "stats/$ServerName/snapshots"
git commit -m "Update stats $ServerName $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git push
if ($LASTEXITCODE -ne 0) {
    Write-Host "Git push failed (code $LASTEXITCODE). Check your connection." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Push complete, workflows will start running." -ForegroundColor Green

Read-Host "Press Enter to close"
