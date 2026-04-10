# Script de lancement pour Logger NI
# Windows PowerShell — lance depuis la racine du projet

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Logger NI - Lancement de l'application" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Naviguer vers la racine du projet (parent de script_compile/)
Set-Location (Join-Path $PSScriptRoot "..")

# Vérifier si l'environnement virtuel existe
if (-not (Test-Path "venv_logger_max\Scripts\python.exe")) {
    Write-Host "Erreur: Environnement virtuel non trouvé" -ForegroundColor Red
    Write-Host "Veuillez d'abord exécuter l'installation" -ForegroundColor Yellow
    pause
    exit 1
}

# Lancer l'application avec l'environnement virtuel
Write-Host "Démarrage de l'application..." -ForegroundColor Green
Write-Host ""

& ".\venv_logger_max\Scripts\python.exe" src\main_logger.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "Une erreur s'est produite" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    pause
}
