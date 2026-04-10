# 🏛️ Design Pattern MVC — Règles et application au Logger NI

## 📋 Table des matières

1. Qu'est-ce que le MVC ?
2. Les 3 composants et leurs règles
3. Les règles d'or du MVC
4. Application au Logger NI
5. Flux de communication MVC dans le Logger NI
6. Correspondance LabVIEW
7. Exemples concrets dans le code

---

## 🎯 Qu'est-ce que le MVC ?

**MVC** (Model–View–Controller) est un design pattern qui sépare une application en
3 composants ayant chacun une **responsabilité unique** :

```
┌──────────────────────────────────────────────────────────────────────┐
│                         MVC — Vue d'ensemble                         │
│                                                                       │
│   ┌───────────┐      commandes      ┌──────────────┐                │
│   │           │ ────────────────────► │              │                │
│   │   VIEW    │                      │  CONTROLLER  │                │
│   │           │ ◄──────────────────── │              │                │
│   └───────────┘   mise à jour UI     └──────┬───────┘                │
│        │                                     │                        │
│        │ L'utilisateur voit                  │ Lit / Modifie          │
│        │ et interagit                        │                        │
│        │                              ┌──────▼───────┐                │
│        │                              │              │                │
│        └─ aucun lien direct ─────X──► │    MODEL     │                │
│                                       │              │                │
│                                       └──────────────┘                │
│                                                                       │
│   La View ne connaît PAS le Model.                                   │
│   Le Model ne connaît PAS la View.                                   │
│   Seul le Controller connaît les deux.                               │
└──────────────────────────────────────────────────────────────────────┘
```

**Objectif** : pouvoir modifier un composant **sans impacter les autres**.

- Changer le thème graphique ? → Modifier uniquement la **View**.
- Changer de carte d'acquisition ? → Modifier uniquement le **Model**.
- Ajouter un bouton ? → Modifier la **View** + le **Controller** (pas le Model).

---

## 🔧 Les 3 composants et leurs règles

### 1. Model (Modèle) — « Les données et la logique métier »

```
📁 src/model/daq_model.py   → Acquisition hardware, buffers, State Machine
📁 src/model/data_model.py  → Écriture fichier TSV
```

**Ce que le Model FAIT :**
- Contient les **données** de l'application (buffers, compteurs, état)
- Implémente la **logique métier** (acquisition, enregistrement, timestamps)
- Expose des **API** pour que le Controller puisse le commander
- **Notifie** les changements d'état via des Signaux Qt

**Ce que le Model ne fait JAMAIS :**
- ❌ Créer ou manipuler des widgets UI (pas de QLabel, QMessageBox, etc.)
- ❌ Connaître l'existence de la View
- ❌ Décider de la couleur, du texte ou de la mise en forme d'un indicateur
- ❌ Importer quoi que ce soit depuis `src/view/`

### 2. View (Vue) — « L'interface utilisateur »

```
📁 src/view/main_view.py    → QMainWindow, pyqtgraph, widgets PySide6
📁 src/view/style.qss       → Feuille de style (thème Catppuccin)
```

**Ce que la View FAIT :**
- **Affiche** les données qu'on lui donne (graphiques, texte, indicateurs)
- **Émet des signaux** quand l'utilisateur interagit (clic, sélection, saisie)
- Gère toute la **présentation** : couleurs, polices, disposition, animations
- Expose des **méthodes publiques** pour que le Controller mette à jour l'affichage

**Ce que la View ne fait JAMAIS :**
- ❌ Contenir de la logique métier (calculs, décisions, algorithmes)
- ❌ Appeler directement le Model (pas d'import depuis `src/model/`)
- ❌ Décider quoi faire quand un bouton est cliqué (elle émet juste un Signal)
- ❌ Accéder au hardware, aux fichiers, ou à la configuration

### 3. Controller (Contrôleur) — « Le chef d'orchestre »

```
📁 src/controller/main_controller.py  → QMH, connexions Signal/Slot, orchestration
```

**Ce que le Controller FAIT :**
- **Connecte** les signaux de la View aux actions du Model
- **Traite** les messages (QMH : match/case)
- **Lit** les données du Model et les **transmet** à la View
- Gère la **logique applicative** (quand démarrer, quand arrêter, quand sauvegarder)

**Ce que le Controller ne fait JAMAIS :**
- ❌ Créer des widgets UI (pas de QMessageBox, QDialog, etc.)
- ❌ Connaître les détails de présentation (couleurs, polices, styles)
- ❌ Manipuler directement le hardware (c'est le rôle du Model)

---

## 📏 Les règles d'or du MVC

### Règle 1 — La View ne connaît pas le Model

```
src/view/main_view.py  ──X──►  src/model/daq_model.py
                       INTERDIT
```

La View ne doit **jamais** importer ou référencer le Model.
Elle reçoit des données **via le Controller** (appels de méthodes).

### Règle 2 — Le Model ne connaît pas la View

```
src/model/daq_model.py  ──X──►  src/view/main_view.py
                        INTERDIT
```

Le Model ne doit **jamais** importer ou référencer la View.
Il notifie les changements **via des Signaux** que le Controller écoute.

### Règle 3 — Le Controller ne fait pas de présentation

```python
# ❌ VIOLATION MVC — le Controller connaît les couleurs
self.view.set_status("Erreur", "#f38ba8")

# ✅ CONFORME MVC — le Controller envoie un niveau sémantique
self.view.set_status("Erreur", "error")
# La View décide que "error" = rouge
```

Le Controller envoie des **informations sémantiques** (état, données, niveaux).
La View traduit ces informations en **éléments visuels** (couleurs, icônes, animations).

### Règle 4 — Le Controller ne crée pas de widgets

```python
# ❌ VIOLATION MVC — le Controller crée un widget UI
QMessageBox.warning(self.view, "Erreur", message)

# ✅ CONFORME MVC — le Controller délègue à la View
self.view.show_error("Erreur", message)
# La View décide comment afficher l'erreur (QMessageBox, banner, toast, etc.)
```

### Règle 5 — Les données circulent dans un seul sens

```
User ──► View ──Signal──► Controller ──commande──► Model
                               │                     │
                               │◄────Signal/état──────┘
                               │
                               └──mise à jour──► View
```

Pas de raccourci. Pas de View → Model direct.

---

## 🔗 Application au Logger NI

### Mapping MVC → Fichiers du projet

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    MVC DANS LE LOGGER NI v3.0                            │
├──────────────┬───────────────────────────────────────────────────────────┤
│ COMPOSANT    │ FICHIER(S) ET RESPONSABILITÉS                            │
├──────────────┼───────────────────────────────────────────────────────────┤
│              │ src/model/daq_model.py                                   │
│   MODEL      │   → QThread + State Machine d'acquisition                │
│              │   → Lecture hardware NI-DAQmx                            │
│              │   → Gestion des buffers (instantané + longue durée)      │
│              │   → Calcul des timestamps                                │
│              │   → Signaux : state_changed, error_occurred              │
│              │                                                          │
│              │ src/model/data_model.py                                  │
│              │   → Écriture fichier TSV (open/write/close)              │
│              │   → Aucune dépendance vers View ou Controller            │
├──────────────┼───────────────────────────────────────────────────────────┤
│              │ src/view/main_view.py                                    │
│   VIEW       │   → QMainWindow + pyqtgraph (Front Panel)               │
│              │   → Signaux : start_requested, stop_requested, etc.      │
│              │   → Méthodes : set_status(), update_instant_plot(), etc. │
│              │   → Gère les couleurs, la mise en forme, les dialogues   │
│              │   → Aucune logique métier, aucun import de src/model/    │
│              │                                                          │
│              │ src/view/style.qss                                       │
│              │   → Feuille de style Qt (thème Catppuccin Mocha)         │
├──────────────┼───────────────────────────────────────────────────────────┤
│              │ src/controller/main_controller.py                        │
│ CONTROLLER   │   → Queued Message Handler (QMH)                        │
│              │   → QMHWorker (thread consumer, Dequeue bloquant)        │
│              │   → Connecte View.signaux → message_queue                │
│              │   → match/case sur Message Enum (Case Structure)         │
│              │   → Lit Model.buffers → appelle View.update_plot()       │
│              │   → Aucun widget UI, aucune couleur, aucun QMessageBox   │
├──────────────┼───────────────────────────────────────────────────────────┤
│              │ src/utils/messages.py                                    │
│   UTILS      │   → Enums Message + AcquisitionState + MessagePacket     │
│ (partagé)    │   → Contrat d'interface entre les 3 composants           │
│              │   → Pas de logique, juste des définitions                │
│              │                                                          │
│              │ src/utils/config.py, settings_manager.py, daq_utils.py   │
│              │   → Configuration et utilitaires transversaux            │
└──────────────┴───────────────────────────────────────────────────────────┘
```

### Matrice des dépendances (imports)

```
                    Model    View    Controller    Utils
                  ────────  ──────  ──────────  ──────
Model             —         ❌       ❌          ✅
View              ❌        —        ❌          ✅
Controller        ✅        ✅       —           ✅
Utils             ❌        ❌       ❌          —

✅ = peut importer     ❌ = ne doit JAMAIS importer
```

Le Controller est le **seul** composant qui importe à la fois le Model et la View.
C'est le point de jonction unique — le **chef d'orchestre**.

---

## 🌊 Flux de communication MVC dans le Logger NI

### Flux 1 : L'utilisateur clique "Démarrer"

```
  👤 Utilisateur
   │
   │ clic sur bouton "▶ Démarrer"
   ▼
┌──────────┐
│   VIEW   │  btn_start.clicked → emit start_requested
└────┬─────┘
     │  Signal Qt : start_requested
     ▼
┌──────────────┐
│  CONTROLLER  │  _enqueue(Message.START_ACQUISITION)
│              │  → QMHWorker défile le message
│              │  → _on_message_received()
│              │  → match START_ACQUISITION
│              │  → _handle_start()
│              │  → daq_model.send_command(START_ACQUISITION, task_name=...)
└──────┬───────┘
       │  command_queue (queue.Queue)
       ▼
┌──────────┐
│  MODEL   │  _process_commands() → _change_state(CONFIGURING)
│          │  _do_configure() → charge la tâche NI MAX
│          │  _change_state(ACQUIRING) → acquisition démarre
│          │  emit state_changed(ACQUIRING)
└──────┬───┘
       │  Signal Qt : state_changed
       ▼
┌──────────────┐
│  CONTROLLER  │  _on_state_changed(ACQUIRING)
│              │  → view.setup_plot_channels(channel_names)
│              │  → view.set_recording_state(True)
│              │  → view.set_status("● Enregistrement", "recording")
└──────┬───────┘
       │  appels de méthodes
       ▼
┌──────────┐
│   VIEW   │  Met à jour les widgets :
│          │  → Label status → rouge "● Enregistrement"
│          │  → Bouton Start désactivé
│          │  → Bouton Stop activé
└──────────┘
```

### Flux 2 : Rafraîchissement des graphiques (QTimer 100ms)

```
┌──────────────┐
│  CONTROLLER  │  QTimer timeout → _refresh_ui()
│              │  → timestamps, data = daq_model.get_instant_data()
│              │  → view.update_instant_plot(timestamps, data)
└──────┬───────┘
       │
  ┌────▼────┐              ┌───────────┐
  │  MODEL  │ ◄─── lit ──── │CONTROLLER │ ──── écrit ──► │  VIEW  │
  │ buffers │   (QMutex)    │           │   (méthodes)    │ plots  │
  └─────────┘              └───────────┘                  └────────┘

Le Controller est l'intermédiaire : lit le Model, écrit la View.
Le Model et la View ne se connaissent pas.
```

### Flux 3 : Erreur pendant l'acquisition

```
┌──────────┐
│  MODEL   │  Exception dans _do_acquire()
│          │  → emit error_occurred("Carte déconnectée")
└────┬─────┘
     │  Signal Qt
     ▼
┌──────────────┐
│  CONTROLLER  │  _on_error("Carte déconnectée")
│              │  → view.show_error("Erreur DAQ", "Carte déconnectée")
│              │           ▲
│              │           │ Le Controller NE CRÉE PAS le QMessageBox
│              │           │ Il délègue à la View (conformité MVC)
└──────┬───────┘
       │
       ▼
┌──────────┐
│   VIEW   │  show_error() → crée un QMessageBox.warning()
│          │  C'est la View qui décide COMMENT afficher l'erreur
└──────────┘
```

---

## 🔄 Correspondance LabVIEW

```
┌──────────────────────┬──────────────────────────────────────────────────┐
│ MVC                  │ LABVIEW                                          │
├──────────────────────┼──────────────────────────────────────────────────┤
│ View                 │ Front Panel                                      │
│ (src/view/)          │ → Contrôles (boutons, menus) génèrent des        │
│                      │   événements vers l'Event Structure              │
│                      │ → Indicateurs (graphiques, labels) sont mis à    │
│                      │   jour par le diagramme                          │
│                      │ → Aucune logique dans le Front Panel             │
├──────────────────────┼──────────────────────────────────────────────────┤
│ Controller           │ Diagramme principal (consumer loop du QMH)       │
│ (src/controller/)    │ → Event Structure → Enqueue Element (producer)   │
│                      │ → While Loop + Dequeue → Case Structure          │
│                      │ → Lit les données, met à jour les indicateurs    │
│                      │ → Orchestre les boucles parallèles               │
├──────────────────────┼──────────────────────────────────────────────────┤
│ Model                │ SubVIs + boucle d'acquisition parallèle          │
│ (src/model/)         │ → State Machine dans While Loop parallèle        │
│                      │ → SubVI File I/O (écriture fichier)              │
│                      │ → DVR (données partagées protégées)              │
│                      │ → User Events (notifications vers le consumer)   │
├──────────────────────┼──────────────────────────────────────────────────┤
│ Utils                │ Type Def Enum partagé entre les boucles          │
│ (src/utils/)         │ → Enum Message (cases du Case Structure)         │
│                      │ → Cluster (message + data) dans la Queue         │
└──────────────────────┴──────────────────────────────────────────────────┘
```

---

## 💻 Exemples concrets dans le code

### Exemple 1 : Le Controller envoie un état sémantique, la View choisit la couleur

```python
# src/controller/main_controller.py — Le Controller ne connaît PAS les couleurs
self.view.set_status("● Enregistrement", "recording")
self.view.set_status("● Prêt", "info")
self.view.set_status("⚠ Sélectionnez une tâche", "warning")

# src/view/main_view.py — La View traduit les niveaux en couleurs
def set_status(self, text: str, level: str = "info"):
    level_colors = {
        "info":      COLORS["accent_blue"],     # Bleu
        "warning":   COLORS["accent_yellow"],   # Jaune
        "recording": COLORS["accent_red"],      # Rouge
        "error":     COLORS["accent_red"],       # Rouge
        "stopped":   COLORS["text_gray"],        # Gris
    }
    color = level_colors.get(level, COLORS["text_white"])
    self.status_label.setStyleSheet(f"color: {color}; ...")
```

→ Si demain on change le thème de rouge à orange pour "recording", on modifie **uniquement la View**.

### Exemple 2 : L'affichage d'erreur est dans la View

```python
# src/controller/main_controller.py — Le Controller ne crée PAS de widget
def _on_error(self, error_msg: str):
    self.view.show_error("Erreur DAQ", error_msg)

# src/view/main_view.py — La View décide COMMENT afficher l'erreur
def show_error(self, title: str, message: str):
    QMessageBox.warning(self, title, message)
```

→ Si demain on veut remplacer le QMessageBox par un bandeau animé, on modifie **uniquement la View**.

### Exemple 3 : La View émet des signaux, le Controller décide quoi faire

```python
# src/view/main_view.py — La View ne sait PAS ce que fait "Démarrer"
self.btn_start.clicked.connect(self.start_requested.emit)
# Elle émet juste un signal. C'est tout.

# src/controller/main_controller.py — Le Controller décide l'action
self.view.start_requested.connect(
    lambda: self._enqueue(Message.START_ACQUISITION)
)
# Il traduit l'événement en commande pour le Model.
```

→ Le bouton pourrait déclencher n'importe quelle action sans changer la View.

---

## ✅ Checklist de conformité MVC

| Règle | Conforme ? | Vérification |
|---|---|---|
| View n'importe pas model/ | ✅ | Aucun `from model import` dans main_view.py |
| Model n'importe pas view/ | ✅ | Aucun `from view import` dans daq_model.py |
| Controller n'importe pas de couleurs/styles | ✅ | Niveaux sémantiques (`"info"`, `"error"`) |
| Controller ne crée pas de widgets | ✅ | `view.show_error()` au lieu de `QMessageBox()` |
| View émet des signaux (pas de logique) | ✅ | `start_requested`, `stop_requested`, etc. |
| Model émet des signaux (pas de vue) | ✅ | `state_changed`, `error_occurred` |
| Données circulent View → Controller → Model | ✅ | Signal → Queue → command_queue |
| Données circulent Model → Controller → View | ✅ | Signal/buffer → Controller → méthodes View |

---

**Version** : 3.0
**Architecture** : MVC + QMH + State Machine (PySide6 + pyqtgraph) — 3 threads
