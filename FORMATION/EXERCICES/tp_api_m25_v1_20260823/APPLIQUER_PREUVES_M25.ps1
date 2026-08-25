[CmdletBinding()]
param(
    [Parameter()]
    [string]$ProjectPath = "."
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$overlay = $PSScriptRoot
$project = (Resolve-Path -LiteralPath $ProjectPath).Path
$lockPath = Join-Path $project "uv.lock"
if (-not (Test-Path -LiteralPath $lockPath)) {
    throw "Le dossier cible n'est pas la racine de CISIA_29062026 : uv.lock absent."
}

$copies = @(
    @{ Source = "tests\test_readiness_probe.py"; Target = "tests\test_readiness_probe.py" },
    @{ Source = "tests\test_model_card_gate.py"; Target = "tests\test_model_card_gate.py" },
    @{ Source = "tests\fixtures\model_card_template.md"; Target = "tests\fixtures\model_card_template.md" },
    @{ Source = "scripts\validate_model_card.py"; Target = "scripts\validate_model_card.py" }
)

$required = @(
    "templates\model_card.md",
    "README.md"
) + $copies.Source
foreach ($relativePath in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $overlay $relativePath))) {
        throw "Surcouche M25 incomplète : $relativePath est absent."
    }
}

$lockBefore = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupRoot = Join-Path $env:TEMP "CISIA_M25_backup_$stamp"
$backupUsed = $false

foreach ($item in $copies) {
    $source = Join-Path $overlay $item.Source
    $target = Join-Path $project $item.Target
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null

    if (Test-Path -LiteralPath $target) {
        $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        $targetHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
        if ($sourceHash -eq $targetHash) {
            Write-Host "DEJA_IDENTIQUE $($item.Target)"
            continue
        }

        $backupTarget = Join-Path $backupRoot $item.Target
        New-Item -ItemType Directory -Path (Split-Path -Parent $backupTarget) -Force | Out-Null
        Copy-Item -LiteralPath $target -Destination $backupTarget -Force
        $backupUsed = $true
        Write-Host "SAUVEGARDE $($item.Target) -> $backupTarget"
    }

    Copy-Item -LiteralPath $source -Destination $target -Force
    Write-Host "INSTALLE $($item.Target)"
}

$card = Join-Path $project "docs\model_card.md"
if (-not (Test-Path -LiteralPath $card)) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $card) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $overlay "templates\model_card.md") -Destination $card
    Write-Host "INITIALISE docs\model_card.md"
} else {
    Write-Host "PRESERVE docs\model_card.md"
}

$lockAfter = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
if ($lockAfter -ne $lockBefore) {
    throw "uv.lock a changé pendant l'application de la surcouche M25."
}

if ($backupUsed) {
    Write-Host "BACKUP_ROOT=$backupRoot"
} else {
    Write-Host "BACKUP_ROOT=NON_NECESSAIRE"
}
Write-Host "M25_OVERLAY=READY"
