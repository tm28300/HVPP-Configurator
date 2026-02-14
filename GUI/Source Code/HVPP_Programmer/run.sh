#!/bin/bash
# Script de lancement pour Linux

# Obtenir le répertoire où se trouve ce script
SCRIPT_DIR="$(dirname "$0")"

# Vérifier si Python 3 est installé
if ! command -v python3 &> /dev/null
then
    echo "Python 3 n'est pas installé. Veuillez l'installer avec:"
    echo "sudo apt install python3 python3-pip python3-tk"
    exit 1
fi

# Vérifier si les dépendances sont installées
if ! python3 -c "import serial" 2>/dev/null; then
    echo "Installation des dépendances..."
    pip3 install -r requirements.txt
fi

# Lancer l'application
python3 "${SCRIPT_DIR}"/hvpp_gui.py
