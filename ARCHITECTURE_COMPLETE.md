# 🏗️ Architecture Complète — Logger NI v3.0

## 📋 Table des matières
1. [Vue d'ensemble](#vue-densemble)
2. [Design Patterns LabVIEW → Python](#design-patterns-labview--python)
3. [Architecture MVC](#architecture-mvc)
4. [Architecture des threads](#architecture-des-threads)
5. [Queued Message Handler (QMH)](#queued-message-handler-qmh)
6. [State Machine d'acquisition](#state-machine-dacquisition)
7. [Flux de données](#flux-de-données)
8. [Gestion du buffer](#gestion-du-buffer)
9. [Système de timestamps](#système-de-timestamps)
10. [Architecture des fichiers](#architecture-des-fichiers)

---

## 🎯 Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LOGGER NI v3.0                                   │
│       Architecture MVC + QMH + State Machine (PySide6) — 3 threads     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
            ┌───────▼──────┐  ┌────▼─────┐  ┌──────▼──────┐
            │    MODEL     │  │   VIEW   │  │ CONTROLLER  │
            │ DAQModel     │  │ MainView │  │ MainCtrl    │
            │ (QThread)    │  │(QMainWin)│  │  (QMH)      │
            │ DataModel    │  │(pyqtgraph│  │ QMHWorker   │
            └──────────────┘  └──────────┘  │(QThread)    │
                    │                       │+QTimer(disp)│
        ┌───────────┼───────────┐           └─────────────┘
        │                       │                  │
  ┌─────▼─────┐          ┌──────▼──────┐    ┌─────▼───────┐
  │  NI-DAQmx │          │ DataModel   │    │  Settings   │
  │  Hardware  │          │ (File I/O) │    │  Manager    │
  └───────────┘          └─────────────┘    └─────────────┘
```

---

## 🔄 Design Patterns LabVIEW → Python

Ce projet implémente les principaux design patterns LabVIEW en Python/PySide6 :

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    CORRESPONDANCE LABVIEW → PYTHON                      │
├──────────────────────┬───────────────────────────────────────────────────┤
│ LABVIEW              │ PYTHON / PYSIDE6                                 │
├──────────────────────┼───────────────────────────────────────────────────┤
│ Event Structure      │ QApplication.exec() + Signal/Slot                │
│ (boucle UI)          │ → La boucle d'événements Qt dispatche les        │
│                      │   signaux aux slots connectés                    │
├──────────────────────┼───────────────────────────────────────────────────┤
│ Queued Message       │ queue.Queue + Message(Enum) + QMHWorker(QThread)  │
│ Handler (QMH)        │ → QMHWorker = While Loop + Dequeue Element (-1)  │
│                      │   bloquant. Se réveille à l'arrivée d'un message │
│                      │   match/case (≡ Case Structure LabVIEW)          │
├──────────────────────┼───────────────────────────────────────────────────┤
│ State Machine        │ AcquisitionState(Enum) dans QThread.run()        │
│ (boucle acq.)        │ → match state: IDLE/CONFIGURING/ACQUIRING/...   │
│                      │   (≡ Case Structure sur Enum dans While Loop)   │
├──────────────────────┼───────────────────────────────────────────────────┤
│ Producer/Consumer    │ View (producer) émet des Signal                  │
│                      │ Controller (consumer) traite via la Queue        │
│                      │ DAQModel (producer) émet data_ready Signal       │
├──────────────────────┼───────────────────────────────────────────────────┤
│ Shift Register       │ Attributs d'instance (self.xxx) dans le QThread  │
│ (données de boucle)  │ → Persistent entre les itérations de run()      │
├──────────────────────┼───────────────────────────────────────────────────┤
│ DVR / Semaphore      │ QMutex + QMutexLocker                           │
│ (accès concurrent)   │ → Protège les buffers partagés entre threads    │
├──────────────────────┼───────────────────────────────────────────────────┤
│ Functional Global    │ Signal Qt typé (cross-thread, auto-marshalled)   │
│ / Notifier           │ → Émis depuis un thread, reçu dans un autre    │
├──────────────────────┼───────────────────────────────────────────────────┤
│ Type Def Enum        │ Python Enum (Message, AcquisitionState)          │
│ (messages/états)     │ → Partagés entre producteur et consommateur     │
├──────────────────────┼───────────────────────────────────────────────────┤
│ SubVI                │ Classe Python (DataModel = SubVI File I/O)       │
│ (sous-modules)       │ → Encapsulation d'une fonctionnalité           │
└──────────────────────┴───────────────────────────────────────────────────┘
```

---

## 🏛️ Architecture MVC

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       src/main_logger.py                                 │
│              Point d'entrée = "main.vi" LabVIEW                          │
│  1. QApplication()       ← Init runtime                                 │
│  2. DAQModel, DataModel  ← Créer les modèles                           │
│  3. MainView             ← Créer le Front Panel                         │
│  4. MainController       ← Connecter tout (QMH)                        │
│  5. app.exec()           ← Lancer la boucle Event (bloque)             │
└──────────────────────────────────────────────────────────────────────────┘

MODEL (src/model/)
├─ daq_model.py         → QThread + State Machine d'acquisition
│  ├─ command_queue     → Reçoit les ordres du Controller
│  ├─ Signaux Qt        → Émet state_changed, data_ready, error_occurred
│  ├─ QMutex            → Protège buffers partagés
│  └─ State Machine     → IDLE → CONFIGURING → ACQUIRING → STOPPING
│
└─ data_model.py        → Écriture fichier TSV (SubVI File I/O)
   ├─ open_file()       → Crée fichier + en-tête
   ├─ write_row()       → Écrit une ligne de données
   └─ close_file()      → Ferme et retourne résumé

VIEW (src/view/)
├─ main_view.py         → QMainWindow (Front Panel PySide6)
│  ├─ Signaux Qt        → start_requested, stop_requested, task_changed, etc.
│  ├─ pyqtgraph         → 2 PlotWidget (instantané + longue durée)
│  ├─ Widgets PySide6   → QComboBox, QSpinBox, QLineEdit, QPushButton, etc.
│  └─ Méthodes publiques → set_status(), update_plot(), setup_channels(), etc.
│
└─ style.qss            → Feuille de style Qt (thème Catppuccin Mocha)

CONTROLLER (src/controller/)
└─ main_controller.py   → Queued Message Handler (QMH)
   ├─ QMHWorker(QThread)→ Thread consumer avec Dequeue bloquant
   ├─ message_queue     → queue.Queue de MessagePacket
   ├─ QTimer (100ms)    → Display refresh uniquement (graphiques)
   ├─ Signal/Slot       → Connecte View ↔ Model
   └─ SettingsManager   → Persistance JSON

UTILS (src/utils/)
├─ config.py            → Paramètres globaux (fréquence, buffers, voltages)
├─ messages.py          → Enums Message + AcquisitionState + MessagePacket
├─ settings_manager.py  → Lecture/écriture logger_config.json
└─ daq_utils.py         → list_available_tasks(), list_available_devices()
```

---

## 🧵 Architecture des threads

Fidèle au QMH LabVIEW : **3 boucles parallèles = 3 threads Python**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│              THREAD 1 — PRINCIPAL (GUI / Event Loop)                    │
├─────────────────────────────────────────────────────────────────────────┤
│  QApplication.exec()                                                    │
│  ├─ Dispatch signaux Qt (Signal/Slot)                                  │
│  ├─ Rendu de l'interface PySide6 + pyqtgraph                           │
│  ├─ Réception des signaux du QMHWorker → _on_message_received()        │
│  │   → match/case sur Message Enum (≡ Case Structure du consumer)      │
│  └─ QTimer (100ms) → _refresh_ui()                                     │
│     │                                                                    │
│     ├─ Poll buffers du DAQModel (via QMutex)                           │
│     └─ Met à jour la View (plots, indicateurs, temps écoulé)           │
│                                                                         │
│  Note : le QTimer ne traite PAS les messages — uniquement l'affichage  │
│         Le traitement des messages est déclenché par le Signal du       │
│         QMHWorker (thread 2), pas par un timer.                        │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                    Communication thread-safe :
                    • message_queue (View → QMHWorker → Controller)
                    • command_queue (Controller → DAQModel)
                    • Signaux Qt    (DAQModel → Controller)
                    • QMutex        (accès buffers partagés)
                                 │
┌─────────────────────────────────────────────────────────────────────────┐
│           THREAD 2 — QMH CONSUMER (QMHWorker QThread)                  │
├─────────────────────────────────────────────────────────────────────────┤
│  QMHWorker.run()  ←  While Loop + Dequeue Element (timeout=-1)         │
│                                                                          │
│  while self._running:                                                   │
│    packet = queue.get(block=True)   ← BLOQUANT : dort si file vide     │
│    //                                  se réveille IMMÉDIATEMENT       │
│    //                                  quand un message arrive         │
│    emit message_received(packet)    ← Signal Qt → main thread          │
│    if QUIT: break                                                       │
│                                                                          │
│  Équiv. LabVIEW : While Loop parallèle au UI, dédiée au consumer       │
│  avec Dequeue Element (timeout = -1). Le thread dort quand la file     │
│  est vide (0% CPU), se réveille instantanément à l'arrivée d'un msg.   │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────────────┐
│           THREAD 3 — ACQUISITION (DAQModel QThread)                     │
├─────────────────────────────────────────────────────────────────────────┤
│  DAQModel.run()  ←  Boucle While avec State Machine                    │
│                                                                          │
│  while self._running:                                                   │
│    ├─ process_commands()    ← Dequeue Element (timeout=0)              │
│    ├─ match self._state:    ← Case Structure (Enum)                    │
│    │  ├─ IDLE        → msleep(50)                                      │
│    │  ├─ CONFIGURING → load NI MAX task → transition ACQUIRING         │
│    │  ├─ ACQUIRING   → read DAQ data + update buffers                  │
│    │  │               → if recording: write file via DataModel         │
│    │  ├─ STOPPING    → close task + file → transition IDLE             │
│    │  └─ ERROR       → emit error signal → transition IDLE             │
│    └─ Émet signaux Qt (state_changed, data_ready, etc.)                │
│                                                                          │
│  Thread Safety :                                                        │
│  ├─ self._mutex (QMutex) protège buffer_instantane, recorded_data      │
│  ├─ self._command_queue (queue.Queue) est intrinsèquement thread-safe  │
│  └─ Signaux Qt sont auto-marshalled entre threads par Qt               │
└─────────────────────────────────────────────────────────────────────────┘

Comparaison directe LabVIEW → Python (3 boucles parallèles) :

    ┌────────────────────┬──────────────────────────────────────────┐
    │ LABVIEW            │ PYTHON / PYSIDE6                         │
    ├────────────────────┼──────────────────────────────────────────┤
    │ UI While Loop      │ Thread 1 : QApplication.exec()          │
    │ + Event Structure  │         + QTimer 100ms (display only)   │
    ├────────────────────┼──────────────────────────────────────────┤
    │ Consumer While Loop│ Thread 2 : QMHWorker.run()              │
    │ + Dequeue(-1)      │         + queue.get(block=True)         │
    │ + Case Structure   │         → Signal → match/case           │
    ├────────────────────┼──────────────────────────────────────────┤
    │ Acquisition Loop   │ Thread 3 : DAQModel.run()               │
    │ + State Machine    │         + match state:                  │
    └────────────────────┴──────────────────────────────────────────┘
```

---

## 📨 Queued Message Handler (QMH)

Le QMH est le pattern central. Le QMHWorker (Thread 2) est le **consumer** ;
la View et le Model sont les **producers**.
Le match/case s'exécute sur le thread principal via Signal Qt.

```
┌────────────────────────────────────────────────────────────────────────┐
│  PRODUCER : View (Front Panel) — Thread 1                              │
│  ─────────────────────────────                                         │
│  Bouton cliqué → Signal Qt émis → Slot du Controller                  │
│  → Controller enfile un MessagePacket dans message_queue               │
│                                                                        │
│  Exemple :                                                             │
│    view.start_requested.connect(                                       │
│        lambda: self._enqueue(Message.START_ACQUISITION, {...})         │
│    )                                                                   │
└────────────────────┬───────────────────────────────────────────────────┘
                     │  queue.Queue (thread-safe FIFO)
                     │  contient des MessagePacket(message, payload)
┌────────────────────▼───────────────────────────────────────────────────┐
│  CONSUMER : QMHWorker (Thread 2) — Dequeue bloquant                    │
│  ──────────────────────────────────────────────────                     │
│  while running:                                                        │
│      packet = queue.get(block=True)  ← DORT si file vide (0% CPU)    │
│      //                                 se réveille à l'arrivée msg   │
│      emit message_received(packet)   ← Signal Qt → thread principal   │
│                                                                        │
│  Équiv. LabVIEW : While Loop parallèle + Dequeue Element (timeout=-1) │
└────────────────────┬───────────────────────────────────────────────────┘
                     │  Signal Qt (auto-marshalling cross-thread)
                     │  exécute le slot sur le thread principal
┌────────────────────▼───────────────────────────────────────────────────┐
│  HANDLER : Controller._on_message_received() — Thread 1                │
│  ──────────────────────────────────────────────                         │
│  match packet.message:              ← Case Structure (sur main thread)│
│      Message.START_ACQUISITION → configure + start DAQ thread          │
│      Message.STOP_ACQUISITION  → stop DAQ thread                       │
│      Message.CHANGE_TASK       → save setting                          │
│      Message.CHANGE_PERIOD     → update period                         │
│      Message.QUIT              → cleanup + close app                   │
│      Message.ERROR             → show error dialog                     │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│  DISPLAY : QTimer 100ms — Thread 1 (indépendant du consumer)           │
│  ────────────────────────────────────────────────                       │
│  _refresh_ui() :                                                       │
│      - Poll buffers DAQModel (via QMutex)                              │
│      - Mise à jour graphiques pyqtgraph                                │
│      - Mise à jour indicateurs (temps écoulé, buffer)                  │
│                                                                        │
│  Équiv. LabVIEW : Boucle Display séparée (Timed Loop)                 │
└────────────────────────────────────────────────────────────────────────┘

Messages disponibles (src/utils/messages.py) :

    class Message(Enum):
        START_ACQUISITION   # Démarrer acquisition + enregistrement
        STOP_ACQUISITION    # Arrêter tout
        START_RECORDING     # Démarrer enregistrement fichier
        STOP_RECORDING      # Arrêter enregistrement uniquement
        CHANGE_TASK         # Changer tâche NI MAX
        CHANGE_PERIOD       # Modifier période d'enregistrement
        QUIT                # Quitter proprement
        ERROR               # Signaler une erreur

    @dataclass
    class MessagePacket:
        message: Message
        payload: dict       # Données associées au message
```

---

## 🔄 State Machine d'acquisition

Le `DAQModel(QThread)` implémente une State Machine identique à un Case Structure
sur Enum dans une boucle While LabVIEW :

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    STATE MACHINE D'ACQUISITION                          │
│               (DAQModel QThread — src/model/daq_model.py)               │
└─────────────────────────────────────────────────────────────────────────┘

    class AcquisitionState(Enum):
        IDLE         # En attente de commande
        CONFIGURING  # Chargement tâche NI MAX
        ACQUIRING    # Acquisition active (+ enregistrement si activé)
        STOPPING     # Fermeture tâche + fichier
        ERROR        # Gestion d'erreur

    Transitions :

    ┌──────────┐  CMD: START    ┌──────────────┐  success   ┌───────────┐
    │   IDLE   │ ──────────────►│ CONFIGURING  │ ──────────►│ ACQUIRING │
    │          │                │              │            │           │
    │ sleep()  │                │ load NI MAX  │   fail     │ read DAQ  │
    │          │◄───────────────│ task         │───┐        │ if rec:   │
    └──────────┘  CMD: QUIT     └──────────────┘   │        │   write   │
         ▲                                         │        └─────┬─────┘
         │                      ┌──────────┐       │              │
         │                      │  ERROR   │◄──────┘              │
         │                      │          │         CMD: STOP    │
         │  auto-transition     │ emit err │              │       │
         └──────────────────────│ signal   │              ▼       │
                                └──────────┘        ┌───────────┐ │
                                     ▲              │ STOPPING  │◄┘
                                     │              │           │
                                     │  exception   │ close     │
                                     └──────────────│ task+file │
                                                    │ → IDLE    │
                                                    └───────────┘
```

---

## 🌊 Flux de données

### Flux complet (acquisition → affichage)

```
HARDWARE                   DAQModel (QThread)         Controller (QMH)        View (Front Panel)
   │                          │                          │                       │
   │  Signal physique         │                          │                       │
   ├─────────────────────────►│                          │                       │
   │                          │                          │                       │
   │                     task.read(1)                    │                       │
   │                          │                          │                       │
   │                     ┌────▼────────────┐             │                       │
   │                     │ Calcul timestamp│             │                       │
   │                     │ = n / sample_rate│            │                       │
   │                     └────┬────────────┘             │                       │
   │                          │                          │                       │
   │                     ┌────▼────────────┐             │                       │
   │                     │ buffer_instantane│ ◄── QMutex │                       │
   │                     │ (fenêtre 60s)   │             │                       │
   │                     └────┬────────────┘             │                       │
   │                          │                          │                       │
   │                          │  Si recording:           │                       │
   │                     ┌────▼────────────┐             │                       │
   │                     │ DataModel       │             │                       │
   │                     │ .write_row()    │             │                       │
   │                     │ + recorded_data │             │                       │
   │                     └─────────────────┘             │                       │
   │                          │                          │                       │
   │                          │       QTimer 100ms       │                       │
   │                          │   (display refresh only) │                       │
   │                          │◄────────────────────────┤                       │
   │                          │                          │                       │
   │                          │  get_instant_data()      │                       │
   │                          │  (QMutex lock/unlock)    │                       │
   │                          ├─────────────────────────►│                       │
   │                          │                          │                       │
   │                          │                          │  update_instant_plot()│
   │                          │                          ├──────────────────────►│
   │                          │                          │                       │
   │                          │                          │         ┌─────────────▼──┐
   │                          │                          │         │  pyqtgraph     │
   │                          │                          │         │  PlotWidget    │
   │                          │                          │         └────────────────┘
```

---

## 🗄️ Gestion du buffer

### Buffer instantané (fenêtre glissante)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      BUFFER SOFTWARE (Python)                           │
│                      buffer_instantane (numpy)                          │
│                    Fenêtre glissante 60 secondes                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Capacité : 600 points (60s × 10 Hz)                                   │
│  Type : numpy.ndarray (n_channels × 600)                               │
│  Protection : QMutex (accès concurrent thread acq. / thread UI)        │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ [Point t-60s] ... [Point t-30s] ... [Point t-10s] ... [Point t]│    │
│  │     Ancien    →→→   Milieu   →→→   Récent   →→→   Dernier     │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Algorithme :                                                           │
│  1. QMutex.lock()                                                       │
│  2. Ajouter nouveau point à droite (np.hstack)                         │
│  3. Si taille > 600 → Supprimer points à gauche (slicing)              │
│  4. QMutex.unlock()                                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Buffer d'enregistrement

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      BUFFER ENREGISTREMENT                              │
│                         recorded_data (numpy)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Capacité max : 100 000 points (configurable)                           │
│  Fréquence d'ajout : selon record_period (ex: 1 point/s)              │
│                                                                          │
│  Double sauvegarde :                                                    │
│  ├─ En mémoire (recorded_data) → graphique longue durée               │
│  └─ Sur disque  (DataModel)    → fichier TSV permanent                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ⏱️ Système de timestamps

```
PRINCIPE
════════
    Timestamp = total_samples_acquired / sample_rate

    timestamp (s) = N / 10.0 Hz

    → Précision sub-nanoseconde (float64)
    → Pas de jitter (déterministe)
    → Pas de dérive (compteur hardware)

AVANTAGES vs time.time()
════════════════════════
    ┌──────────────────┬──────────────────┬─────────────────┐
    │                  │   time.time()    │  sample/freq    │
    ├──────────────────┼──────────────────┼─────────────────┤
    │ Résolution       │ ~1 ms            │ ~0.000000001 ns │
    │ Jitter           │ ±1-10 ms         │ 0 (déterministe)│
    │ Dérive           │ Possible (OS)    │ Aucune          │
    │ Synchronisation  │ Non garantie     │ Parfaite        │
    └──────────────────┴──────────────────┴─────────────────┘
```

---

## 📁 Architecture des fichiers

```
Logger_NI_MAX/
│
├─ 📂 src/                               ← Code source Python
│  ├─ 📄 main_logger.py                  ← Point d'entrée (QApplication)
│  │
│  ├─ 📁 model/
│  │  ├─ __init__.py
│  │  ├─ daq_model.py                    ← QThread + State Machine + QMutex
│  │  └─ data_model.py                   ← Écriture fichier TSV (SubVI)
│  │
│  ├─ 📁 view/
│  │  ├─ __init__.py
│  │  ├─ main_view.py                    ← QMainWindow + pyqtgraph + Signaux
│  │  └─ style.qss                       ← Thème Catppuccin Mocha (QSS)
│  │
│  ├─ 📁 controller/
│  │  ├─ __init__.py
│  │  └─ main_controller.py              ← QMH : QMHWorker + Queue + Signal/Slot
│  │
│  └─ 📁 utils/
│     ├─ __init__.py
│     ├─ config.py                       ← Paramètres globaux
│     ├─ messages.py                     ← Enums Message + AcquisitionState
│     ├─ settings_manager.py             ← Persistance JSON
│     └─ daq_utils.py                    ← Utilitaires DAQmx
│
├─ 📂 script_compile/                    ← Scripts de build et lancement
│  ├─ build_exe.bat                      ← Création exécutable (CMD)
│  ├─ build_exe.ps1                      ← Création exécutable (PowerShell)
│  ├─ logger_ni.spec                     ← Configuration PyInstaller
│  ├─ run.bat                            ← Lancement application (CMD)
│  └─ run.ps1                            ← Lancement application (PowerShell)
│
├─ 📂 data/                              ← Données enregistrées (*.txt TSV)
│
├─ 📄 logger_config.json                 ← Préférences utilisateur
├─ 📄 requirements.txt                   ← PySide6, pyqtgraph, numpy, nidaqmx
├─ 📄 test_installation.py               ← Script de vérification
└─ 📂 venv_logger_max/                   ← Environnement virtuel
```

---

## 📊 Stack technologique

```
┌─────────────────────────────────────────────────────────────┐
│                      STACK TECHNOLOGIQUE                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Langage : Python 3.10+                                      │
│                                                              │
│  Interface graphique                                         │
│  ├─ PySide6 (Qt 6 pour Python)                              │
│  ├─ pyqtgraph (graphiques temps réel haute performance)     │
│  └─ QSS (Qt Style Sheets — thème sombre Catppuccin)        │
│                                                              │
│  Acquisition de données                                      │
│  ├─ nidaqmx (API National Instruments)                      │
│  └─ NI-DAQmx Runtime (driver hardware)                      │
│                                                              │
│  Calculs numériques                                          │
│  └─ numpy (arrays, opérations vectorielles)                 │
│                                                              │
│  Threading & Synchronisation                                 │
│  ├─ QThread (thread d'acquisition + QMH consumer)           │
│  ├─ QMutex + QMutexLocker (protection buffers)              │
│  ├─ queue.Queue (file de commandes thread-safe)             │
│  └─ Signal/Slot Qt (communication cross-thread)             │
│                                                              │
│  Persistance                                                 │
│  ├─ JSON (logger_config.json — préférences utilisateur)     │
│  └─ TSV (fichiers de données — tab-separated)               │
│                                                              │
│  Packaging                                                   │
│  └─ PyInstaller (création d'exécutable autonome)            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

**Version** : 3.0
**Date** : Avril 2026
**Architecture** : MVC + QMH + State Machine (PySide6 + pyqtgraph) — 3 threads
