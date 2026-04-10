"""
MainController — Orchestrateur MVC et Queued Message Handler (QMH).

Architecture 3 threads fidèle au pattern QMH LabVIEW :

    ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │ Thread 1 : UI   │   │ Thread 2 : QMH   │   │ Thread 3 : DAQ   │
    │ (Qt Event Loop) │   │ (Consumer Loop)  │   │ (State Machine)  │
    │                 │   │                  │   │                  │
    │ Signal/Slot     │   │ Dequeue(-1)      │   │ Read hardware    │
    │ Display refresh │◄──│ (bloquant)       │──►│ Write file       │
    │ QTimer 100ms    │   │ Case Structure   │   │                  │
    └─────────────────┘   └──────────────────┘   └──────────────────┘

    Thread 1 (principal) : Qt Event Loop
        - Rendu de l'interface PySide6 + pyqtgraph
        - Dispatch des Signal/Slot
        - QTimer (100ms) : rafraîchissement des graphiques et indicateurs
        - NE TRAITE PAS les messages — uniquement l'affichage

    Thread 2 (QMHWorker) : Consumer Loop du QMH — Dequeue bloquant
        - queue.get(block=True) : dort quand la file est vide (0% CPU)
        - Se réveille INSTANTANÉMENT quand un message arrive
        - Émet Signal message_received → match/case sur le main thread
        - Équiv. LabVIEW : While Loop + Dequeue Element (timeout=-1)

    Thread 3 (DAQModel) : State Machine d'acquisition
        - Boucle While avec match/case sur AcquisitionState
        - Lecture hardware NI-DAQmx + écriture fichier
        - Communique via Signaux Qt (state_changed, error_occurred)

Comparaison directe avec LabVIEW :
    ┌────────────────────┬──────────────────────────────────────────┐
    │ LABVIEW            │ PYTHON / PYSIDE6                         │
    ├────────────────────┼──────────────────────────────────────────┤
    │ UI While Loop      │ Thread 1 : QApplication.exec()          │
    │ + Event Structure  │         + QTimer (display refresh)      │
    ├────────────────────┼──────────────────────────────────────────┤
    │ Consumer While Loop│ Thread 2 : QMHWorker.run()              │
    │ + Dequeue(-1)      │         + queue.get(block=True)         │
    │ + Case Structure   │         → Signal → match/case           │
    ├────────────────────┼──────────────────────────────────────────┤
    │ Acquisition Loop   │ Thread 3 : DAQModel.run()               │
    │ + State Machine    │         + match state:                  │
    └────────────────────┴──────────────────────────────────────────┘
"""

import queue
from PySide6.QtCore import QThread, QTimer, Signal

from utils.messages import Message, MessagePacket, AcquisitionState
from utils.settings_manager import SettingsManager
from utils.daq_utils import list_available_tasks, list_available_devices


# ═══════════════════════════════════════════════════════════════
# Thread 2 : Consumer Loop du QMH — Dequeue bloquant
# Équiv. LabVIEW : While Loop parallèle + Dequeue Element (timeout=-1)
# ═══════════════════════════════════════════════════════════════

class QMHWorker(QThread):
    """
    Thread consumer du Queued Message Handler — Dequeue bloquant.

    Ce thread est l'exact équivalent de la boucle consumer du QMH LabVIEW :
    - Il DORT quand la file de messages est vide (0% CPU)
    - Il se RÉVEILLE instantanément quand un message arrive
    - Il transmet le message au thread principal via Signal Qt

    Équivalent LabVIEW :
        ┌──────────────────────────────────────────────────────────┐
        │  While True:                                              │
        │    message = Dequeue Element(queue, timeout = -1)         │
        │    // ↑ Le thread DORT ici tant que la file est vide      │
        │    //   Se réveille INSTANTANÉMENT à l'arrivée d'un msg   │
        │    Fire User Event(message)   → notifie le main thread    │
        └──────────────────────────────────────────────────────────┘

    Pourquoi un thread dédié ?
        En Qt, le thread principal exécute la boucle d'événements (app.exec())
        pour le rendu UI. On ne peut pas y faire un get() bloquant sans geler
        l'interface. D'où ce thread parallèle, exactement comme la boucle
        consumer est PARALLÈLE à la boucle UI en LabVIEW.
    """

    # Signal émis quand un message est défilé de la queue
    # Le slot connecté s'exécute sur le thread du récepteur (auto-marshalling Qt)
    message_received = Signal(object)  # MessagePacket

    def __init__(self, message_queue: queue.Queue):
        super().__init__()
        self._message_queue = message_queue
        self._running = True

    def run(self):
        """
        Boucle consumer bloquante — cœur du QMH.

        Équiv. LabVIEW :
            While True:
                msg = Dequeue Element(queue_ref, timeout=-1)
                → BLOQUANT : dort si file vide, se réveille à l'arrivée d'un message
                Fire User Event(msg)
                → le handler s'exécute sur le thread principal
        """
        print("[QMHWorker] Thread consumer démarré — en attente de messages")

        while self._running:
            try:
                # ─── Dequeue Element (bloquant, timeout=-1 en LabVIEW) ───
                # timeout=1.0s en Python pour pouvoir vérifier _running
                # En fonctionnement normal, retourne IMMÉDIATEMENT quand
                # un message arrive (pas de polling, 0% CPU en attente)
                packet: MessagePacket = self._message_queue.get(
                    block=True, timeout=1.0
                )

                # ─── Transmettre au thread principal via Signal Qt ───
                # Qt poste le signal dans la event loop du main thread
                # → le slot _on_message_received() s'exécutera sur le main thread
                self.message_received.emit(packet)

                # ─── Condition de sortie (≡ While Loop condition=False) ───
                if packet.message == Message.QUIT:
                    break

            except queue.Empty:
                # Timeout 1s sans message → reboucler pour vérifier _running
                # En LabVIEW : équivalent d'un timeout dans la Dequeue
                # → reboucle vers le While pour revérifier la condition
                continue

        print("[QMHWorker] Thread consumer terminé")

    def request_stop(self):
        """
        Demande l'arrêt propre du thread consumer.
        Le thread s'arrêtera au prochain timeout (max 1s).
        """
        self._running = False


# ═══════════════════════════════════════════════════════════════
# MainController — Orchestrateur MVC
# ═══════════════════════════════════════════════════════════════

class MainController:
    """
    Orchestrateur MVC et handler de messages du QMH.

    Responsabilités :
        1. Connecter les signaux de la View (events) → enfilement de messages
        2. Recevoir les messages du QMHWorker → match/case (consumer)
        3. Rafraîchir les graphiques via QTimer périodique (display loop)
        4. Connecter les signaux du Model → mise à jour de la View
        5. Gérer la persistance des paramètres utilisateur

    Architecture 3 threads :
        Thread 1 (principal) : Event Loop Qt + Display refresh (QTimer 100ms)
        Thread 2 (QMHWorker) : Consumer loop — Dequeue bloquant (queue.get)
        Thread 3 (DAQModel)  : State Machine d'acquisition

    Équiv. LabVIEW :
        - message_queue         = Queue refnum (Obtain Queue)
        - QMHWorker             = While Loop consumer + Dequeue Element (timeout=-1)
        - _on_message_received  = Case Structure du consumer (match/case)
        - _refresh_ui           = Boucle Display séparée (QTimer 100ms)
        - _enqueue              = Enqueue Element (producer)
    """

    def __init__(self, daq_model, data_model, view):
        self.daq_model = daq_model
        self.data_model = data_model
        self.view = view
        self.settings = SettingsManager(self.view.config.CONFIG_FILE)

        # ─── File de messages (partagée entre producers et consumer) ───
        # Équiv. LabVIEW : Obtain Queue → file partagée entre toutes les boucles
        self.message_queue: queue.Queue[MessagePacket] = queue.Queue()

        # ─── État local du controller ───
        self._is_acquiring = False
        self._is_recording = False
        self._current_task = ""

        # ─── Connexions Signal/Slot ───
        # Équiv. LabVIEW : câblage dans le diagramme
        self._connect_view_signals()
        self._connect_model_signals()

        # ─── Thread 2 : Consumer Loop du QMH (Dequeue bloquant) ───
        # Équiv. LabVIEW : While Loop parallèle + Dequeue Element (timeout=-1)
        #   Le thread DORT quand la file est vide (0% CPU)
        #   Se RÉVEILLE instantanément quand un message arrive
        self._qmh_worker = QMHWorker(self.message_queue)
        self._qmh_worker.message_received.connect(self._on_message_received)
        self._qmh_worker.start()

        # ─── Timer de rafraîchissement UI (display loop) ───
        # Équiv. LabVIEW : Boucle Display séparée — mise à jour périodique
        #   des graphiques et indicateurs. Ce timer NE TRAITE PAS les
        #   messages — uniquement l'affichage.
        self._ui_timer = QTimer()
        self._ui_timer.timeout.connect(self._refresh_ui)
        self._ui_timer.start(100)  # 100ms = 10 Hz refresh display

        # ─── Initialisation ───
        self._initialize()

    # ═══════════════════════════════════════════════════════════════
    # Connexions (câblage des signaux)
    # ═══════════════════════════════════════════════════════════════

    def _connect_view_signals(self):
        """
        Connecte les signaux de la View pour enqueue des messages.

        Équiv. LabVIEW : Event Structure → Enqueue Element
            Chaque événement Front Panel → enfile un message dans la file du consumer.
        """
        self.view.start_requested.connect(
            lambda: self._enqueue(Message.START_ACQUISITION)
        )
        self.view.stop_requested.connect(
            lambda: self._enqueue(Message.STOP_ACQUISITION)
        )
        self.view.task_changed.connect(
            lambda name: self._enqueue(Message.CHANGE_TASK, task_name=name)
        )
        self.view.period_changed.connect(
            lambda val: self._enqueue(Message.CHANGE_PERIOD, period=val)
        )
        self.view.quit_requested.connect(
            lambda: self._enqueue(Message.QUIT)
        )

    def _connect_model_signals(self):
        """
        Connecte les signaux du DAQModel (cross-thread).

        Équiv. LabVIEW : Register for User Events dans le consumer loop.
        Qt gère automatiquement le marshalling cross-thread (QueuedConnection).
        """
        self.daq_model.state_changed.connect(self._on_state_changed)
        self.daq_model.error_occurred.connect(self._on_error)

    def _enqueue(self, message: Message, **payload):
        """
        Enfile un message dans la file du QMH.

        Équiv. LabVIEW : Enqueue Element(queue_ref, cluster(message, data))
        Le QMHWorker (thread consumer) se réveillera automatiquement.
        """
        self.message_queue.put(MessagePacket(message, payload))

    # ═══════════════════════════════════════════════════════════════
    # Consumer du QMH — Traitement des messages
    # Déclenché par le Signal du QMHWorker (thread consumer)
    # Exécuté sur le thread principal (auto-marshalling Qt)
    # Équiv. LabVIEW : Case Structure dans le consumer loop
    # ═══════════════════════════════════════════════════════════════

    def _on_message_received(self, packet: MessagePacket):
        """
        Case Structure du QMH — traite un message défilé par le consumer thread.

        Appelé automatiquement sur le thread principal quand le QMHWorker
        défile un message. Le Signal Qt gère le marshalling cross-thread.

        Équiv. LabVIEW :
            Case Structure alimenté par la sortie du Dequeue Element.
            Chaque message a son propre Case avec sa logique métier.

        Note : Cette méthode s'exécute sur le thread principal (main thread)
               grâce au marshalling automatique de Qt. Elle peut donc accéder
               aux widgets de la View en toute sécurité.
        """
        match packet.message:

            case Message.START_ACQUISITION:
                self._handle_start()

            case Message.STOP_ACQUISITION:
                self._handle_stop()

            case Message.CHANGE_TASK:
                self._handle_task_change(
                    packet.payload.get("task_name", ""))

            case Message.CHANGE_PERIOD:
                self._handle_period_change(
                    packet.payload.get("period", 60))

            case Message.QUIT:
                self._handle_quit()

            case Message.ERROR:
                self._on_error(
                    packet.payload.get("error", "Erreur inconnue"))

    # ═══════════════════════════════════════════════════════════════
    # Display Loop — Rafraîchissement périodique de l'UI
    # Déclenché par le QTimer (100ms) — indépendant du consumer
    # Équiv. LabVIEW : Boucle Display séparée (Timed Loop)
    # ═══════════════════════════════════════════════════════════════

    def _refresh_ui(self):
        """
        Rafraîchissement périodique des graphiques et indicateurs.

        Appelé par le QTimer toutes les 100ms, INDÉPENDAMMENT des messages.
        Ne traite PAS les messages — uniquement la mise à jour de l'affichage.

        Équiv. LabVIEW :
            Timed Loop dédiée à l'affichage :
            - Lire les buffers (DVR / Functional Global)
            - Mettre à jour les graphiques (Waveform Chart)
            - Mettre à jour les indicateurs (temps écoulé, buffer, etc.)
        """
        if not self._is_acquiring:
            return

        # ── Indicateurs texte ──
        self.view.set_buffer_info(
            str(self.daq_model.get_buffer_available()))
        self.view.set_elapsed_time(
            self.daq_model.get_elapsed_time_str())

        # ── Graphique instantané (fenêtre glissante 60s) ──
        timestamps, data = self.daq_model.get_instant_data()
        if len(timestamps) > 0:
            self.view.update_instant_plot(timestamps, data)

        # ── Graphique longue durée (enregistrement complet) ──
        if self._is_recording:
            ts_long, data_long = self.daq_model.get_longduration_data()
            if len(ts_long) > 0:
                self.view.update_longduration_plot(ts_long, data_long)

    # ═══════════════════════════════════════════════════════════════
    # Handlers de messages (Cases du Case Structure)
    # ═══════════════════════════════════════════════════════════════

    def _handle_start(self):
        """
        Case START_ACQUISITION du QMH.
        Envoie la commande au DAQModel thread.

        Équiv. LabVIEW : Enqueue "START" dans la file du thread d'acquisition.
        """
        if self._is_acquiring:
            return

        task_name = self.view.get_task_name()
        if not task_name:
            self.view.set_status(
                "⚠ Sélectionnez une tâche", "warning")
            return

        self._current_task = task_name
        self._is_acquiring = True

        # Envoyer la commande au thread d'acquisition
        self.daq_model.send_command(
            Message.START_ACQUISITION, task_name=task_name)

        # Note : la mise à jour UI se fait dans _on_state_changed()
        # quand le Model confirme le passage en ACQUIRING.

    def _handle_stop(self):
        """
        Case STOP_ACQUISITION du QMH.
        Envoie la commande d'arrêt au thread d'acquisition.
        """
        if not self._is_acquiring:
            return
        self.daq_model.send_command(Message.STOP_ACQUISITION)
        # La mise à jour UI se fait dans _on_state_changed()

    def _handle_task_change(self, task_name: str):
        """
        Case CHANGE_TASK du QMH.
        Sauvegarde le choix de tâche dans les préférences.
        """
        if not task_name:
            return
        self._current_task = task_name
        self.settings.set("task_name", task_name)
        self.settings.save_settings()
        print(f"[Controller] Tâche sélectionnée: {task_name}")

    def _handle_period_change(self, period: int):
        """
        Case CHANGE_PERIOD du QMH.
        Met à jour la période et notifie le Model si acquisition en cours.
        """
        self.settings.set("record_period", period)
        if self._is_acquiring:
            self.daq_model.send_command(Message.CHANGE_PERIOD, period=period)

    def _handle_quit(self):
        """
        Case QUIT du QMH.
        Sauvegarde les préférences, arrête tous les threads, ferme la View.

        Équiv. LabVIEW : Save Config + Stop All Loops + Quit Application
        """
        # Sauvegarder les paramètres
        self.settings.update(
            task_name=self.view.get_task_name(),
            record_period=self.view.get_period(),
            file_prefix=self.view.get_prefix(),
            file_comment=self.view.get_comment(),
            last_save_folder=self.view.get_directory()
        )
        self.settings.save_settings()

        # Arrêter le timer de rafraîchissement UI (stop display loop)
        self._ui_timer.stop()

        # Arrêter le thread consumer du QMH
        # (il s'est déjà auto-stoppé après avoir émis QUIT, mais par sécurité)
        self._qmh_worker.request_stop()
        self._qmh_worker.wait(2000)  # Attendre max 2s que le thread se termine

        # Arrêter le thread d'acquisition (thread 3)
        self.daq_model.shutdown()

        # Fermer la fenêtre
        self.view.force_close()

        print("[Controller] Application terminée — 3 threads arrêtés")

    # ═══════════════════════════════════════════════════════════════
    # Handlers des signaux du Model (cross-thread)
    # Équiv. LabVIEW : Handle User Event cases
    # ═══════════════════════════════════════════════════════════════

    def _on_state_changed(self, new_state: AcquisitionState):
        """
        Réagit aux changements d'état du thread d'acquisition.
        Appelé automatiquement dans le thread principal (Qt marshalling).

        Équiv. LabVIEW : Event "User Event: State Changed" dans l'Event Structure
        """
        match new_state:

            case AcquisitionState.CONFIGURING:
                self.view.set_status(
                    "⏳ Configuration...", "warning")

            case AcquisitionState.ACQUIRING:
                # Le Model a confirmé le démarrage de l'acquisition
                channel_names = self.daq_model.get_channel_names()
                self.view.setup_plot_channels(channel_names)
                self.view.set_recording_state(True)
                self.view.set_controls_enabled(False)

                # Démarrer l'enregistrement fichier
                self._start_file_recording()
                self.view.set_status(
                    "● Enregistrement", "recording")

            case AcquisitionState.IDLE:
                if self._is_acquiring:
                    # On vient de s'arrêter
                    self._is_acquiring = False
                    self._is_recording = False
                    self.view.set_recording_state(False)
                    self.view.set_controls_enabled(True)
                    self.view.set_status(
                        "● Arrêté", "stopped")
                    self.view.set_buffer_info("0")
                    self.view.set_elapsed_time("00:00:00")

                    # Afficher le résultat de l'enregistrement
                    result = self.daq_model.get_last_recording_result()
                    if result and result.get("filepath"):
                        self.view.show_recording_result(
                            result["filepath"], result["sample_count"])

            case AcquisitionState.ERROR:
                self._is_acquiring = False
                self._is_recording = False
                self.view.set_recording_state(False)
                self.view.set_controls_enabled(True)
                self.view.set_status("● Erreur", "error")

    def _on_error(self, error_msg: str):
        """Signale une erreur — délègue l'affichage à la View (MVC)."""
        print(f"[Controller] Erreur: {error_msg}")
        self.view.show_error("Erreur DAQ", error_msg)

    # ═══════════════════════════════════════════════════════════════
    # Enregistrement fichier
    # ═══════════════════════════════════════════════════════════════

    def _start_file_recording(self):
        """
        Envoie la commande de démarrage d'enregistrement au Model.
        Appelé automatiquement quand le Model passe en état ACQUIRING.
        """
        directory = self.view.get_directory()
        prefix = self.view.get_prefix()
        comment = self.view.get_comment()
        period = self.view.get_period()

        self._is_recording = True
        self.daq_model.send_command(
            Message.START_RECORDING,
            directory=directory,
            prefix=prefix,
            comment=comment,
            period=period
        )

    # ═══════════════════════════════════════════════════════════════
    # Initialisation au démarrage
    # ═══════════════════════════════════════════════════════════════

    def _initialize(self):
        """
        Configuration initiale de l'application.

        Équiv. LabVIEW : Case "Initialize" de la State Machine principale
                         (charger config, peupler les contrôles, etc.)
        """
        # Charger les paramètres sauvegardés
        saved = self.settings.load_settings()

        # Lister les tâches NI MAX disponibles
        try:
            tasks = list_available_tasks()
        except Exception:
            tasks = []
            print("[Controller] NI-DAQmx non disponible — mode simulation")

        self.view.set_task_list(tasks)

        # Restaurer les préférences sauvegardées
        saved_task = saved.get("task_name", "")
        if saved_task and saved_task in tasks:
            self.view.set_task(saved_task)

        self.view.set_period(saved.get("record_period", 60))
        self.view.set_prefix(saved.get("file_prefix", "data"))
        self.view.set_comment(saved.get("file_comment", ""))
        self.view.set_directory(saved.get("last_save_folder", "data"))

        # Info périphériques (debug console)
        try:
            devices = list_available_devices()
            if devices:
                print(f"[Controller] Périphériques NI détectés: {devices}")
        except Exception:
            pass

        self.view.set_status("● Prêt", "info")

        # Démarrer le thread du Model (en état IDLE, attend des commandes)
        # → Thread 3 (DAQ) est maintenant actif
        # → Thread 2 (QMH Consumer) a déjà été démarré dans __init__
        self.daq_model.start()

        print("[Controller] Initialisation terminée — 3 threads actifs")
        print("  Thread 1 : Qt Event Loop + Display refresh (QTimer 100ms)")
        print("  Thread 2 : QMH Consumer (Dequeue bloquant)")
        print("  Thread 3 : DAQ Acquisition (State Machine)")
