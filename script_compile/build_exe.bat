@echo off
REM Script de création de l'exécutable Logger NI
REM Utilise PyInstaller pour générer un fichier .exe
REM Ce script doit être lancé depuis le répertoire script_compile/

echo ================================================
echo BUILD EXECUTABLE - Logger NI
echo ================================================
echo.

REM Se positionner dans le répertoire du projet (parent de script_compile)
cd /d "%~dp0\.."

REM Vérifier si PyInstaller est installé
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller n'est pas installe. Installation en cours...
    pip install pyinstaller
    echo.
)

echo Nettoyage des fichiers precedents...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "LoggerNI.exe" del /q "LoggerNI.exe"
echo.

echo Création de l'executable avec PyInstaller...
pyinstaller script_compile\logger_ni.spec --clean
echo.

if exist "dist\LoggerNI.exe" (
    echo ================================================
    echo BUILD REUSSI!
    echo ================================================
    echo.
    echo L'executable se trouve dans: dist\LoggerNI.exe
    echo.
    echo Vous pouvez:
    echo 1. Copier dist\LoggerNI.exe ou vous voulez
    echo 2. Distribuer ce fichier sans Python installe
    echo.
    pause
) else (
    echo ================================================
    echo ERREUR lors de la creation
    echo ================================================
    echo.
    pause
)
