# 🎯 Guide de démarrage rapide — Logger NI v3.0

## ✅ Architecture PySide6 + design patterns LabVIEW

L'application utilise une architecture MVC avec des patterns LabVIEW :
- ✅ **QMH** (Queued Message Handler) → Controller + `queue.Queue` + `QMHWorker(QThread)`
- ✅ **State Machine** d'acquisition → `DAQModel(QThread)` + `AcquisitionState(Enum)`
- ✅ **Producer/Consumer** → View (signaux Qt) / Controller (consumer)
- ✅ **Event Structure** → `QApplication.exec()` (boucle d'événements Qt)
- ✅ **Interface PySide6** + graphiques **pyqtgraph** temps réel
- ✅ **Thread-safe** : `QMutex` pour les buffers partagés
- ✅ **3 threads** : UI + QMH Consumer + Acquisition

---

## 🚀 Lancement rapide

### Option 1 : Ligne de commande (recommandé)
```powershell
cd "c:\TRAVAIL\RepositoriesGithub\Logger_NI_MAX"
.\venv_logger_max\Scripts\Activate.ps1
python src/main_logger.py
```

### Option 2 : Sans activer le venv
```powershell
.\venv_logger_max\Scripts\python.exe src\main_logger.py
```

### Option 3 : Script de lancement
- **`script_compile\run.bat`** (Windows CMD)
- **`script_compile\run.ps1`** (PowerShell)

---

## 📂 Structure du projet

```
Logger_NI_MAX/
├── 📂 src/                           ← 🎯 Code source Python
│   ├── main_logger.py                ← Point d'entrée (QApplication)
│   │
│   ├── 📂 model/                     # Modèle (logique métier)
│   │   ├── daq_model.py              # QThread + State Machine + acquisition DAQmx
│   │   └── data_model.py             # Écriture fichier TSV
│   │
│   ├── 📂 view/                      # Vue (Front Panel)
│   │   ├── main_view.py              # QMainWindow + signaux Qt + pyqtgraph
│   │   └── style.qss                 # Thème sombre Catppuccin (QSS)
│   │
│   ├── 📂 controller/                # Contrôleur (QMH)
│   │   └── main_controller.py        # QMHWorker + message_queue + Signal/Slot
│   │
│   └── 📂 utils/                     # Utilitaires
│       ├── config.py                 # ⚙️ Configuration centralisée
│       ├── messages.py               # Enums Message + AcquisitionState
│       ├── settings_manager.py       # Persistance JSON des préférences
│       └── daq_utils.py              # Utilitaires DAQmx (liste tâches/devices)
│
├── 📂 script_compile/                ← 🔧 Scripts de build et lancement
│   ├── build_exe.bat                 # Création de l'exécutable (CMD)
│   ├── build_exe.ps1                 # Création de l'exécutable (PowerShell)
│   ├── logger_ni.spec                # Configuration PyInstaller
│   ├── run.bat                       # Lancement application (CMD)
│   └── run.ps1                       # Lancement application (PowerShell)
│
├── 📂 data/                          ← Données enregistrées (*.txt TSV)
├── 📄 logger_config.json             ← Préférences utilisateur (auto-créé)
├── 📄 requirements.txt               ← Dépendances : PySide6, pyqtgraph, numpy, nidaqmx
├── 📄 test_installation.py           ← Script de vérification de l'installation
└── 📂 venv_logger_max/               ← Environnement virtuel Python
```

---

## ⚙️ Configuration

### Tâches et canaux DAQmx

Les canaux ne sont **pas** configurés dans le code. Ils sont chargés automatiquement
depuis les **tâches NI MAX** :

1. Ouvrir **NI MAX** (Measurement & Automation Explorer)
2. Créer ou modifier une tâche d'acquisition (ex : `Cuve_exp`)
3. Ajouter les canaux d'entrée analogique souhaités
4. Lancer l'application → sélectionner la tâche dans la combobox

### Paramètres dans `src/utils/config.py`

```python
SAMPLE_RATE = 10                # Fréquence d'acquisition (Hz)
INSTANT_MAX_SAMPLES = 600       # Fenêtre glissante = 60 s à 10 Hz
MAX_LONGUE_DUREE_SAMPLES = 100000
DEFAULT_RECORD_PERIOD = 60      # Période d'enregistrement (s)
ENABLE_SIMULATION = True        # Mode simulation sans carte DAQ
```

### Tester l'installation

```powershell
.\venv_logger_max\Scripts\python.exe test_installation.py
```

---

## 🎮 Utilisation de l'interface

### Panneau de contrôle (gauche)

| Élément | Description |
|---|---|
| **📋 Tâche DAQmx** | Sélection de la tâche NI MAX (combobox) |
| **⏱️ Période** | Période d'enregistrement en secondes (0 = chaque point) |
| **📁 Préfixe** | Préfixe du nom de fichier de sortie |
| **📂 Répertoire** | Dossier de sauvegarde des données |
| **💬 Commentaire** | Commentaire écrit en en-tête du fichier |

### Boutons

| Bouton | Action |
|---|---|
| **▶ Démarrer** | Lance l'acquisition + enregistrement fichier |
| **◼ Arrêter** | Arrête et ferme le fichier. Affiche un résumé |
| **✕ Quitter** | Ferme proprement (aussi : touche Échap) |
| **ℹ À propos** | Informations sur l'application et l'architecture |

### Graphiques (droite, onglets)

| Onglet | Contenu |
|---|---|
| **📈 Graphique Instantané** | Fenêtre glissante des 60 dernières secondes |
| **📊 Graphique Longue Durée** | Tous les points enregistrés depuis le début |

### Barre de statut (bas)

- **Statut** : ● Arrêté / ● Enregistrement
- **Buffer** : Nombre de points disponibles dans le buffer hardware DAQmx
- **Temps écoulé** : Depuis le début de l'acquisition courante
- **Échelle** : Auto ou manuelle (Min/Max des axes Y)

---

## 📊 Fichiers de données

Les données sont sauvegardées en format **TSV** (tab-separated) :

```
data/data_test__20251210_170004.txt
```

Format du fichier :
```tsv
# commentaire utilisateur
Temps	Dev3/ai0	Dev3/ai1
0.000000	2.34567	1.23456
1.000000	2.34612	1.23478
2.000000	2.34589	1.23412
```

- Les timestamps sont basés sur le **compteur d'échantillons** (précision nanosecondes)
- La période entre chaque ligne dépend du paramètre **Période d'enregistrement**
- Le séparateur est la **tabulation** (compatible Excel)

---

## 🔧 Dépannage

### L'application ne démarre pas
**Vérifier** : Utilisez bien le Python du venv :
```powershell
.\venv_logger_max\Scripts\python.exe src\main_logger.py
```

### "No module named PySide6"
**Solution** : Installer les dépendances dans le venv :
```powershell
.\venv_logger_max\Scripts\Activate.ps1
pip install -r requirements.txt
```

### "Aucune tâche DAQmx configurée"
**Solution** : Ouvrir NI MAX → créer une tâche → ajouter des canaux AI

### Erreur au démarrage de l'acquisition
**Vérifier** :
1. La carte DAQ est connectée et visible dans NI MAX
2. La tâche fonctionne dans NI MAX (bouton "Test")
3. NI-DAQmx Runtime est installé

### Mode simulation
Pour tester sans carte DAQ, activer le mode simulation dans `src/utils/config.py` :
```python
ENABLE_SIMULATION = True
```

---

## 📚 Documentation complémentaire

| Document | Contenu |
|---|---|
| `README.md` | Vue d'ensemble du projet |
| `ARCHITECTURE_COMPLETE.md` | Architecture détaillée, diagrammes, design patterns |
| `BUILD_EXECUTABLE.md` | Création d'exécutable |
| `INSTALLATION_DEPLOIEMENT.md` | Déploiement et installation NI-DAQmx |
| `TIMESTAMP_IMPROVEMENT.md` | Système de timestamps précis |
| `MVC_DESIGN_PATTERN.md` | Règles MVC + application au projet |

---

**Version** : 3.0 (PySide6 + pyqtgraph)
**Architecture** : MVC + QMH + State Machine — 3 threads
