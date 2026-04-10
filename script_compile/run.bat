@echo off
REM Script de lancement pour Logger NI
REM Windows Batch — lance depuis la racine du projet

echo ============================================================
echo Logger NI - Lancement de l'application
echo ============================================================
echo.

cd /d "%~dp0\.."

REM Vérifier si l'environnement virtuel existe
if not exist "venv_logger_max\Scripts\python.exe" (
    echo Erreur: Environnement virtuel non trouve
    echo Veuillez d'abord executer l'installation
    pause
    exit /b 1
)

REM Lancer l'application avec l'environnement virtuel
echo Demarrage de l'application...
echo.
"venv_logger_max\Scripts\python.exe" src\main_logger.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo Une erreur s'est produite
    echo ============================================================
    pause
)
