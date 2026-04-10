# 🏗️ Création de l'exécutable — Logger NI v3.0

## 🎯 Objectif

Créer un exécutable Windows autonome (`.exe`) qui ne nécessite **aucune installation Python** sur le PC cible.

- **Outil** : [PyInstaller](https://pyinstaller.org/)
- **Résultat** : Un seul fichier `LoggerNI.exe` (~50-80 MB)
- **Dépendance externe** : NI-DAQmx Runtime uniquement

---

## 📋 Prérequis

```powershell
# 1. Activer l'environnement virtuel
cd "c:\TRAVAIL\RepositoriesGithub\Logger_NI_MAX"
.\venv_logger_max\Scripts\Activate.ps1

# 2. Installer PyInstaller
pip install pyinstaller

# 3. Vérifier
pyinstaller --version
```

---

## 🚀 Méthode rapide

### Windows Batch
```batch
script_compile\build_exe.bat
```

### PowerShell
```powershell
.\script_compile\build_exe.ps1
```

### Directement (depuis la racine du projet)
```powershell
pyinstaller script_compile\logger_ni.spec --clean
```

L'exécutable est généré dans : `dist\LoggerNI.exe`

---

## ⚙️ Configuration du `.spec`

Le fichier `script_compile/logger_ni.spec` contrôle la création de l'exécutable.
Il doit être exécuté depuis la **racine du projet** (pas depuis `script_compile/`).

### Paramètres importants pour PySide6 + pyqtgraph

```python
# script_compile/logger_ni.spec — Configuration PyInstaller

import os
src_dir = os.path.join('.', 'src')

a = Analysis(
    [os.path.join('src', 'main_logger.py')],
    pathex=[src_dir],
    binaries=[],
    datas=[
        ('logger_config.json', '.'),                              # Config
        (os.path.join('src', 'view', 'style.qss'), 'view/'),     # Stylesheet Qt
    ],
    hiddenimports=[
        # PySide6 — imports dynamiques nécessaires
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',

        # pyqtgraph — imports dynamiques
        'pyqtgraph',
        'pyqtgraph.graphicsItems',
        'pyqtgraph.graphicsItems.PlotDataItem',
        'pyqtgraph.graphicsItems.AxisItem',
        'pyqtgraph.graphicsItems.ViewBox',

        # numpy — requis par pyqtgraph
        'numpy',
        'numpy.core',
        'numpy.core._methods',
        'numpy.lib',
        'numpy.lib.format',

        # nidaqmx
        'nidaqmx',
        'nidaqmx.system',
        'nidaqmx.task',
        'nidaqmx.constants',
        'nidaqmx.errors',
        'nitypes',
    ],
    excludes=[
        # Exclure modules inutiles pour réduire la taille
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'PIL',
        'cv2',
        'test',
        'unittest',
    ],
    optimize=2,
)
```

> **Note** : Le `pathex=[src_dir]` permet à PyInstaller de résoudre les imports
> `from model.daq_model import ...` qui sont relatifs au dossier `src/`.

---

## 🔍 Résolution des problèmes courants

### Problème : "ModuleNotFoundError" au lancement de l'exe

**Cause** : PyInstaller n'a pas détecté un import dynamique.

**Solution** : Ajouter le module dans `hiddenimports` du `.spec` :
```python
hiddenimports=['module_manquant', ...],
```

### Problème : PySide6 plugins manquants

**Cause** : Les plugins Qt (platforms, imageformats) ne sont pas inclus.

**Solution** : Ajouter dans `datas` :
```python
import PySide6
pyside6_path = os.path.dirname(PySide6.__file__)
datas=[
    (os.path.join(pyside6_path, 'plugins', 'platforms'), 'PySide6/plugins/platforms'),
],
```

### Problème : Exe trop volumineux (> 150 MB)

**Solutions** :
1. Vérifier les `excludes` (tkinter, matplotlib, scipy…)
2. Installer UPX : https://upx.github.io/ et ajouter au PATH
3. Utiliser `--onefile` avec compression

### Problème : Style QSS non chargé

**Cause** : Le fichier `style.qss` n'est pas dans le bundle.

**Solution** : Vérifier dans `datas` :
```python
datas=[(os.path.join('src', 'view', 'style.qss'), 'view/'), ...],
```

Et dans le code, utiliser le chemin relatif à l'exécutable :
```python
import sys, os
base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
qss_path = os.path.join(base, 'view', 'style.qss')
```

---

## 📏 Taille de l'exécutable attendue

| Composant        | Taille approx. |
|------------------|----------------|
| Python Runtime   | ~10 MB         |
| PySide6 (Qt 6)  | ~40 MB         |
| pyqtgraph        | ~5 MB          |
| numpy            | ~15 MB         |
| nidaqmx          | ~2 MB          |
| Code application | < 1 MB         |
| **Total**        | **~50-80 MB**  |

> Avec UPX activé, la taille peut descendre à ~35-50 MB.

---

## 🧪 Test de l'exécutable

```powershell
# 1. Créer l'exécutable
pyinstaller script_compile\logger_ni.spec --clean

# 2. Tester en mode console (pour voir les erreurs)
# Modifier temporairement console=True dans le .spec
pyinstaller script_compile\logger_ni.spec --clean
.\dist\LoggerNI.exe

# 3. Vérifier la taille
Get-Item dist\LoggerNI.exe | Select-Object Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB,1)}}
```

---

## 📦 Artefacts de build

```
build/                        ← Fichiers temporaires (peut être supprimé)
  └── logger_ni/
dist/                         ← Exécutable final
  └── LoggerNI.exe
script_compile/
  └── logger_ni.spec          ← Configuration PyInstaller
```

> Le dossier `build/` peut être supprimé après la création. Seul `dist/LoggerNI.exe` est nécessaire.

---

**Version** : 3.0
**Stack** : Python 3.10 + PySide6 + pyqtgraph + nidaqmx
**Outil** : PyInstaller 6.x
