# 🧪 Logger NI — Acquisition de données National Instruments

Application d'acquisition et d'enregistrement de données multi-canaux pour cartes **NI-DAQmx**,
développée en Python avec une architecture MVC inspirée des design patterns LabVIEW.

## ✨ Caractéristiques

- **Acquisition temps réel** via les tâches configurées dans NI MAX
- **Affichage pyqtgraph** haute performance (graphique instantané 60 s + longue durée)
- **Enregistrement TSV** avec timestamps basés sur le compteur d'échantillons (précision nanosecondes)
- **Interface PySide6** moderne avec thème sombre Catppuccin
- **Architecture MVC + design patterns LabVIEW** : QMH, State Machine, Producer/Consumer
- **Persistance** des préférences utilisateur (tâche, période, répertoire, préfixe)
- **Mode simulation** sans carte DAQ (pour le développement)

## 🏛️ Architecture — Design Patterns LabVIEW en Python

| Pattern LabVIEW | Implémentation Python | Fichier |
|---|---|---|
| **Event Structure** (boucle UI) | `QApplication.exec()` + Signal/Slot | `src/main_logger.py` |
| **Queued Message Handler** (QMH) | `queue.Queue` + `Message(Enum)` + `QMHWorker(QThread)` | `src/controller/main_controller.py` |
| **State Machine** (acquisition) | `AcquisitionState(Enum)` dans `QThread.run()` | `src/model/daq_model.py` |
| **Producer/Consumer** | View (signaux) → Controller (file) → DAQModel (commandes) | Tous |
| **Shift Register** | Attributs d'instance du QThread | `src/model/daq_model.py` |
| **DVR / Semaphore** | `QMutex` pour les buffers partagés | `src/model/daq_model.py` |

```
┌──────────┐  Signaux Qt  ┌────────────┐  command_queue  ┌──────────┐
│   View   │ ────────────► │ Controller │ ──────────────► │ DAQModel │
│ (PySide6)│               │   (QMH)    │                 │ (QThread)│
│          │ ◄──────────── │            │ ◄────────────── │          │
└──────────┘  méthodes     └────────────┘  Signal(state)  └──────────┘
     │                          │                              │
Boutons/Inputs            QTimer 100ms                   State Machine
→ emit Signal()           → display refresh              IDLE → CONFIGURING
                          → poll buffers                 → ACQUIRING → STOPPING
                          → update plots
```

## 📁 Structure du projet

```
Logger_NI_MAX/
├── src/                              ← 🎯 Code source Python
│   ├── main_logger.py                ← Point d'entrée (QApplication)
│   ├── model/
│   │   ├── daq_model.py              ← QThread + State Machine + command_queue
│   │   └── data_model.py             ← Écriture fichier TSV (SubVI File I/O)
│   ├── view/
│   │   ├── main_view.py              ← QMainWindow + Signaux + pyqtgraph
│   │   └── style.qss                 ← Thème Catppuccin (QSS)
│   ├── controller/
│   │   └── main_controller.py        ← QMH : QMHWorker + message_queue + Signal/Slot
│   └── utils/
│       ├── config.py                 ← Configuration centralisée
│       ├── messages.py               ← Enums Message + AcquisitionState
│       ├── settings_manager.py       ← Persistance JSON des préférences
│       └── daq_utils.py              ← Utilitaires DAQmx (lister tâches/devices)
├── script_compile/                   ← 🔧 Scripts de build et lancement
│   ├── build_exe.bat                 ← Création de l'exécutable (CMD)
│   ├── build_exe.ps1                 ← Création de l'exécutable (PowerShell)
│   ├── logger_ni.spec                ← Configuration PyInstaller
│   ├── run.bat                       ← Lancement de l'application (CMD)
│   └── run.ps1                       ← Lancement de l'application (PowerShell)
├── data/                             ← Données enregistrées (*.txt TSV)
├── logger_config.json                ← Préférences utilisateur (auto-créé)
├── requirements.txt                  ← Dépendances Python
├── test_installation.py              ← Script de vérification de l'installation
└── venv_logger_max/                  ← Environnement virtuel
```

## 🚀 Lancement rapide

### Prérequis

- **Python 3.10+**
- **NI-DAQmx Runtime** installé (gratuit, depuis [ni.com](https://www.ni.com/downloads/drivers/ni-daqmx/))
- Au moins une **tâche DAQmx configurée** dans NI MAX

### Installation

```powershell
# Cloner le dépôt
git clone https://github.com/votre-user/Logger_NI_MAX.git
cd Logger_NI_MAX

# Créer l'environnement virtuel
python -m venv venv_logger_max

# Activer l'environnement
.\venv_logger_max\Scripts\Activate.ps1

# Installer les dépendances
pip install -r requirements.txt
```

### Exécution

```powershell
# Avec le venv activé :
python src/main_logger.py

# Ou directement :
.\venv_logger_max\Scripts\python.exe src\main_logger.py

# Ou via le script de lancement :
.\script_compile\run.ps1
```

## ⚙️ Configuration

Les paramètres principaux sont dans `src/utils/config.py` :

| Paramètre | Valeur | Description |
|---|---|---|
| `SAMPLE_RATE` | `10` Hz | Fréquence d'échantillonnage |
| `INSTANT_MAX_SAMPLES` | `600` | Fenêtre glissante (60 s à 10 Hz) |
| `MAX_LONGUE_DUREE_SAMPLES` | `100000` | Max points graphique longue durée |
| `DEFAULT_RECORD_PERIOD` | `60` s | Période d'enregistrement par défaut |
| `ENABLE_SIMULATION` | `True` | Mode simulation (sans carte DAQ) |

Les **tâches et canaux** sont configurés dans **NI MAX** — l'application les charge automatiquement.

## 📊 Stack technologique

| Composant | Technologie | Rôle |
|---|---|---|
| Interface | **PySide6** (Qt 6) | Widgets, layout, boucle d'événements |
| Graphiques | **pyqtgraph** | Affichage temps réel haute performance |
| Acquisition | **nidaqmx** | API National Instruments DAQmx |
| Calculs | **numpy** | Buffers, opérations vectorielles |
| Threading | **QThread** + **QMutex** | Acquisition parallèle thread-safe |
| Communication | **Signal/Slot** + `queue.Queue` | Inter-composants et inter-threads |

## 📚 Documentation

| Document | Contenu |
|---|---|
| `QUICKSTART.md` | Guide de démarrage rapide |
| `ARCHITECTURE_COMPLETE.md` | Architecture détaillée + diagrammes |
| `BUILD_EXECUTABLE.md` | Création d'exécutable + déploiement |
| `INSTALLATION_DEPLOIEMENT.md` | Installation NI-DAQmx + déploiement |
| `TIMESTAMP_IMPROVEMENT.md` | Système de timestamps précis |
| `MVC_DESIGN_PATTERN.md` | Règles MVC + application au projet |

## 📝 Licence

Voir `LICENSE`.
