# AVR High Voltage Parallel Programmer (HVPP) Configurator GUI - Python Version

Application Python multi-plateforme pour configurer les microcontrôleurs AVR via un programmateur HVPP.

## Compatibilité

Cette application est compatible avec :
- **Linux x86_64** (PC standard)
- **Linux ARM64** (Raspberry Pi 3/4/5)
- **Windows 10/11** (x86_64)

## Prérequis

- Python 3.6 ou supérieur
- Accès au port série (USB/UART)

## Installation

### Sur Linux (x86_64 ou ARM64)

```bash
# Installer Python et pip si nécessaire
sudo apt update
sudo apt install python3 python3-pip python3-tk

# Installer les dépendances Python
pip3 install -r requirements.txt

# Ajouter l'utilisateur au groupe dialout pour accéder au port série
sudo usermod -a -G dialout $USER
# Déconnexion/reconnexion nécessaire pour que les changements prennent effet

# Rendre le script exécutable (optionnel)
chmod +x hvpp_gui.py
```

### Sur Windows 10/11

```batch
# Installer Python depuis python.org (version 3.6+)
# Puis dans une invite de commandes :

pip install -r requirements.txt
```

## Utilisation

### Lancer l'application

**Linux :**
```bash
python3 hvpp_gui.py
```

ou si le script est exécutable :
```bash
./hvpp_gui.py
```

**Windows :**
```batch
python hvpp_gui.py
```

ou double-cliquer sur le fichier `hvpp_gui.py`

### Utilisation de l'interface

1. **Sélectionner la puce cible** : Choisir le microcontrôleur AVR dans la liste déroulante
2. **Sélectionner le port série** : Choisir le port COM (Windows) ou /dev/ttyUSB* (Linux)
3. **Connecter** : Cliquer sur "Connect" pour établir la connexion
4. **Opérations disponibles** :
   - Lire la signature du circuit
   - Lire/écrire les fuses (Low, High, Extended)
   - Lire l'octet de calibration
   - Effacer la puce
   - Écrire l'octet de verrouillage

## Puces supportées

- ATMEGA8(A)(L)
- ATMEGA48
- ATMEGA168(P)(PA)
- ATMEGA328(P)
- ATTINY2313(V)
- ATMEGA1284(P)

## Structure du projet

```
.
├── hvpp_gui.py           # Interface graphique principale
├── hvpp_programmer.py    # Module de communication avec le programmateur
├── requirements.txt      # Dépendances Python
└── README.md            # Ce fichier
```

## Dépannage

### Problème d'accès au port série sous Linux

Si vous obtenez une erreur "Permission denied" :
```bash
sudo chmod 666 /dev/ttyUSB0  # Remplacer par le bon port
# OU mieux, ajouter l'utilisateur au groupe dialout (voir Installation)
```

### Port série non détecté

- Vérifier que le câble USB est bien connecté
- Sous Linux, vérifier avec `ls /dev/ttyUSB*` ou `ls /dev/ttyACM*`
- Sous Windows, vérifier dans le Gestionnaire de périphériques

### L'application ne se lance pas

- Vérifier la version de Python : `python3 --version` (doit être >= 3.6)
- Vérifier que tkinter est installé : `python3 -m tkinter`
- Réinstaller les dépendances : `pip3 install --force-reinstall -r requirements.txt`

## Développement

Cette application est un portage Python de l'application C# originale pour améliorer la compatibilité multi-plateforme.

**Technologies utilisées :**
- Python 3
- tkinter (interface graphique)
- pyserial (communication série)

## Licence

Développé par Shichang Zhuo (version C# originale)
Porté en Python par Thierry (2025)
