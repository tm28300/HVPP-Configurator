@echo off
REM Script de lancement pour Windows

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo Python n'est pas installé ou n'est pas dans le PATH
    echo Téléchargez Python depuis https://www.python.org/
    pause
    exit /b 1
)

REM Vérifier si les dépendances sont installées
python -c "import serial" >nul 2>&1
if errorlevel 1 (
    echo Installation des dépendances...
    pip install -r requirements.txt
)

REM Lancer l'application
python hvpp_gui.py
pause
