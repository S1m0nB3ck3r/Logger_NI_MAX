# 📦 Guide d'installation et de déploiement — Logger NI v3.0

## ✅ Installation simple en 2 étapes

Pour déployer sur un PC cible, vous avez besoin de :

1. ✅ **Installer NI-DAQmx Runtime** sur le PC cible
2. ✅ **Copier l'exécutable** `LoggerNI.exe`

C'est tout ! 🎉

---

## 📋 Installation détaillée

### Étape 1 : Installer NI-DAQmx Runtime

Sur le PC cible :

1. **Télécharger NI-DAQmx Runtime** depuis :
   - https://www.ni.com/fr-fr/support/downloads/drivers/download.ni-daqmx.html
   - Chercher : "NI-DAQmx Runtime" (GRATUIT)

2. **Installer** :
   - Version recommandée : **NI-DAQmx 2023 Q3** ou plus récent
   - Suivre l'assistant d'installation
   - Redémarrer si demandé

3. **Vérifier** :
   - Lancer **NI MAX** (Measurement & Automation Explorer)
   - Vérifier que les périphériques DAQ apparaissent
   - Vérifier que les tâches configurées sont présentes

> ⚠️ Le **Runtime** est suffisant (pas besoin du SDK complet). Il est **GRATUIT** et redistribuable.

### Étape 2 : Copier l'exécutable

```
dist\LoggerNI.exe
```

Copier n'importe où : Bureau, `C:\Program Files\LoggerNI\`, clé USB, etc.

L'exécutable est **100% autonome** et contient :
- ✅ Python 3.10 embedded
- ✅ PySide6 (interface Qt)
- ✅ pyqtgraph (graphiques)
- ✅ numpy (calculs numériques)
- ✅ nidaqmx (bibliothèque Python)
- ✅ Code de l'application

---

## 🔧 Création de l'exécutable (développeur)

### Prérequis développement

```powershell
cd "c:\TRAVAIL\RepositoriesGithub\Logger_NI_MAX"
.\venv_logger_max\Scripts\Activate.ps1

# Installer PyInstaller
pip install pyinstaller
```

### Méthode rapide

```batch
script_compile\build_exe.bat
```
ou
```powershell
.\script_compile\build_exe.ps1
```

### Méthode manuelle (depuis la racine du projet)

```powershell
pyinstaller script_compile\logger_ni.spec --clean
```

L'exécutable est créé dans `dist\LoggerNI.exe`.

### Configuration avancée (`script_compile/logger_ni.spec`)

#### Ajouter une icône
```python
exe = EXE(
    ...
    icon='path/to/icon.ico',
)
```

#### Cacher la console
```python
exe = EXE(
    ...
    console=False,  # Application GUI pure
)
```

#### Inclure des fichiers supplémentaires
```python
a = Analysis(
    ...
    datas=[
        ('logger_config.json', '.'),
        (os.path.join('src', 'view', 'style.qss'), 'view/'),
    ],
)
```

---

## 📂 Structure de déploiement

```
MonDossierApplication/
├── LoggerNI.exe              ← L'exécutable
├── logger_config.json        ← Créé automatiquement au 1er lancement
└── data/                     ← Dossier de données (créé automatiquement)
    └── *.txt                 ← Fichiers de mesures TSV
```

---

## 💻 Configuration requise

### Système d'exploitation
- ✅ Windows 10 / 11 (64 bits)
- ✅ Pas besoin de Python installé
- ✅ Pas besoin de Visual Studio

### Matériel
- ✅ Carte d'acquisition NI-DAQmx compatible
- ✅ 4 GB RAM minimum (8 GB recommandé)
- ✅ 200 MB d'espace disque (+ espace pour les données)

### Logiciels
- ✅ **NI-DAQmx Runtime** (seul prérequis)
- ✅ Tâches DAQmx configurées dans NI MAX

---

## 🚀 Utilisation

1. **Double-cliquer** sur `LoggerNI.exe`
2. Sélectionner la tâche DAQmx dans la combobox
3. Configurer la période d'enregistrement
4. Cliquer sur **▶ Démarrer**

Au premier lancement, l'application crée automatiquement :
- `logger_config.json` (préférences utilisateur)
- Dossier `data/` (si nécessaire)

---

## 📦 Distribution

### Pour distribuer à d'autres utilisateurs :

1. Créer un dossier :
   ```
   LoggerNI_v3.0/
   ├── LoggerNI.exe
   └── INSTALL.txt
   ```

2. Compresser en `.zip`

3. Instructions pour l'utilisateur final :
   ```
   1. Installer NI-DAQmx Runtime (lien fourni)
   2. Extraire le .zip
   3. Double-cliquer sur LoggerNI.exe
   ```

---

## ❓ Dépannage

### L'exécutable ne démarre pas
- ✅ Vérifier que NI-DAQmx Runtime est installé
- ✅ Vérifier les droits (pas besoin d'admin normalement)
- ✅ Ajouter une exception antivirus si nécessaire

### "Aucune tâche DAQmx configurée"
- ✅ Ouvrir NI MAX
- ✅ Créer ou importer des tâches DAQmx
- ✅ Vérifier que les tâches sont bien enregistrées

### Erreur au démarrage de l'acquisition
- ✅ Vérifier que la carte DAQ est connectée
- ✅ Vérifier dans NI MAX que la carte est détectée
- ✅ Tester la tâche dans NI MAX avant

### Erreur "Module not found" dans les logs
Ajouter le module manquant dans `hiddenimports` du `script_compile/logger_ni.spec` :
```python
hiddenimports=['nidaqmx', 'pyqtgraph', 'numpy', 'module_manquant'],
```

---

## 🔄 Mise à jour

1. Remplacer `LoggerNI.exe` par la nouvelle version
2. Conserver `logger_config.json` (préférences)
3. Conserver le dossier `data/` (données)

---

**Version** : 3.0
**Stack** : Python 3.10 + PySide6 + pyqtgraph + nidaqmx
