# Script PowerShell de création de l'exécutable Logger NI
# Utilise PyInstaller pour générer un fichier .exe
# Ce script doit être lancé depuis le répertoire script_compile/

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "BUILD EXECUTABLE - Logger NI" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Se positionner dans le répertoire du projet (parent de script_compile)
Set-Location (Join-Path $PSScriptRoot "..")

# Vérifier si PyInstaller est installé
try {
    python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller not found"
    }
} catch {
    Write-Host "PyInstaller n'est pas installé. Installation en cours..." -ForegroundColor Yellow
    pip install pyinstaller
    Write-Host ""
}

Write-Host "Nettoyage des fichiers précédents..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "LoggerNI.exe") { Remove-Item -Force "LoggerNI.exe" }
Write-Host ""

Write-Host "Création de l'exécutable avec PyInstaller..." -ForegroundColor Yellow
pyinstaller script_compile\logger_ni.spec --clean
Write-Host ""

if (Test-Path "dist\LoggerNI.exe") {
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "BUILD RÉUSSI!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "L'exécutable se trouve dans: dist\LoggerNI.exe" -ForegroundColor Green
    Write-Host ""
    Write-Host "Vous pouvez:" -ForegroundColor White
    Write-Host "1. Copier dist\LoggerNI.exe où vous voulez" -ForegroundColor White
    Write-Host "2. Distribuer ce fichier sans Python installé" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "ERREUR lors de la création" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Write-Host ""
}

Write-Host "Appuyez sur une touche pour continuer..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
