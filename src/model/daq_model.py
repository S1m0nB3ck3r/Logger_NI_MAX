"""
DAQModel — Thread d'acquisition avec State Machine.

Équivalent LabVIEW :
    Boucle While parallèle avec State Machine (Case Structure sur Enum)
    + file de commandes pour recevoir les ordres du controller.

    ┌──────────────────────────────────────────────────────────────┐
    │  QThread.run()  ←  Équivalent : While Loop (parallel)       │
    │                                                              │
    │  ┌─ Shift Registers (attributs d'instance) ───────────────┐  │
    │  │  state, buffers, counters, recording flag              │  │
    │  └────────────────────────────────────────────────────────┘  │
    │                                                              │
    │  while running:               ← While Loop condition         │
    │    process_commands()          ← Dequeue Element (timeout=0) │
    │    match state:                ← Case Structure (Enum)       │
    │      IDLE        → sleep                                     │
    │      CONFIGURING → load NI MAX task                          │
    │      ACQUIRING   → read DAQ + if recording → write file      │
    │      STOPPING    → close task + file                         │
    │      ERROR       → handle + return to IDLE                   │
    └──────────────────────────────────────────────────────────────┘

Communication :
    Controller → DAQModel : command_queue (queue.Queue de MessagePacket)
    DAQModel → Controller : Signaux Qt (cross-thread, auto-marshalled par Qt)

Thread Safety :
    Les buffers de données sont protégés par un QMutex.
    Équivalent LabVIEW : Data Value Reference (DVR) ou Semaphore.
"""

import queue
import time
import numpy as np

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from utils.messages import AcquisitionState, MessagePacket, Message
from model.data_model import DataModel

# ─── Import conditionnel de nidaqmx (permet le mode simulation) ───
try:
    import nidaqmx
    import nidaqmx.system.storage as storage
    from nidaqmx.constants import AcquisitionType
    NIDAQMX_AVAILABLE = True
except ImportError:
    NIDAQMX_AVAILABLE = False
    print("[DAQModel] nidaqmx non disponible — mode simulation activé")


class DAQModel(QThread):
    """
    Thread d'acquisition NI-DAQmx avec State Machine.

    Communication :
        Controller → DAQModel : command_queue (file de MessagePacket)
        DAQModel → Controller : Signaux Qt (cross-thread, auto-queued par Qt)

    Équivalent LabVIEW :
        - QThread.run()    = While Loop parallèle (exécution dans un autre thread)
        - command_queue     = Queue refnum partagée (Obtain Queue / Enqueue / Dequeue)
        - Signal Qt         = User Event ou Notifier (notification cross-loop)
        - QMutex            = DVR (Data Value Reference) pour accès thread-safe
    """

    # ─── Signaux (équiv. LabVIEW : User Events / Notifiers) ───
    # Émis depuis le thread d'acquisition, reçus dans le thread principal.
    # Qt gère automatiquement le marshalling cross-thread (QueuedConnection).
    state_changed  = Signal(object)   # Nouvel état AcquisitionState
    error_occurred = Signal(str)      # Message d'erreur

    def __init__(self, config, data_model: DataModel):
        super().__init__()
        self.config = config
        self.data_model = data_model

        # ─── File de commandes (Controller → Thread) ───
        # Équiv. LabVIEW : Queue refnum créée avec Obtain Queue
        self.command_queue: queue.Queue[MessagePacket] = queue.Queue()

        # ─── State Machine ───
        # Équiv. LabVIEW : Enum dans le shift register de la boucle While
        self._state = AcquisitionState.IDLE
        self._running = True          # False = quitter le thread (While Loop condition)
        self._quit_requested = False  # Flag pour arrêt différé via STOPPING

        # ─── Mutex pour accès thread-safe aux buffers ───
        # Équiv. LabVIEW : DVR (Data Value Reference) ou Semaphore
        self._mutex = QMutex()

        # ─── Hardware DAQ ───
        self._task = None
        self._task_name = ""
        self._channel_names: list[str] = []
        self._n_channels = 0
        self._sample_rate = config.SAMPLE_RATE  # 10 Hz

        # ─── Buffers de données (protégés par mutex) ───
        # Équiv. LabVIEW : Shift Registers de la boucle While
        self._buffer_instant = np.empty((0, 0))       # shape: (n_channels, n_samples)
        self._timestamps_instant: list[float] = []
        self._max_instant_samples = config.INSTANT_MAX_SAMPLES  # 600

        self._buffer_longduration = np.empty((0, 0))  # shape: (n_channels, n_samples)
        self._timestamps_longduration: list[float] = []
        self._max_longduration_samples = config.MAX_LONGUE_DUREE_SAMPLES  # 100000

        # ─── Compteurs pour timestamps précis ───
        # t = total_samples / sample_rate → pas de dérive, pas de jitter
        self._total_samples = 0
        self._acquisition_start_time: float | None = None
        self._buffer_available = 0

        # ─── Recording (flag interne à l'état ACQUIRING) ───
        # Équiv. LabVIEW : Booléen dans le shift register, testé par un Case
        #                  Structure "Recording?" à l'intérieur du Case ACQUIRING
        self._is_recording = False
        self._record_period = config.DEFAULT_RECORD_PERIOD
        self._last_save_sample = 0
        self._record_directory = ""
        self._record_prefix = ""
        self._record_comment = ""

        # ─── Résultat du dernier enregistrement ───
        self._last_recording_result: dict | None = None

        # ─── Dernière erreur ───
        self._last_error = ""

    # ═══════════════════════════════════════════════════════════════
    # Propriétés thread-safe (lecture depuis le thread principal)
    # ═══════════════════════════════════════════════════════════════

    def get_state(self) -> AcquisitionState:
        """État courant de la State Machine."""
        return self._state

    def get_channel_names(self) -> list[str]:
        """Noms des canaux de la tâche DAQ courante."""
        return self._channel_names.copy()

    def get_elapsed_time_str(self) -> str:
        """Temps écoulé depuis le début de l'acquisition (HH:MM:SS)."""
        if self._acquisition_start_time is None:
            return "00:00:00"
        elapsed = int(time.time() - self._acquisition_start_time)
        h, remainder = divmod(elapsed, 3600)
        m, s = divmod(remainder, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def get_buffer_available(self) -> int:
        """Nombre d'échantillons en attente dans le buffer hardware."""
        return self._buffer_available

    def get_instant_data(self) -> tuple[list[float], np.ndarray]:
        """
        Retourne (timestamps, data) du buffer instantané de façon thread-safe.

        Équiv. LabVIEW : In Place Element Structure sur DVR → lire → sortir
        """
        with QMutexLocker(self._mutex):
            if len(self._timestamps_instant) == 0:
                return [], np.empty((0, 0))
            return (
                list(self._timestamps_instant),
                self._buffer_instant.copy()
            )

    def get_longduration_data(self) -> tuple[list[float], np.ndarray]:
        """Retourne (timestamps, data) du buffer longue durée (thread-safe)."""
        with QMutexLocker(self._mutex):
            if len(self._timestamps_longduration) == 0:
                return [], np.empty((0, 0))
            return (
                list(self._timestamps_longduration),
                self._buffer_longduration.copy()
            )

    def get_last_recording_result(self) -> dict | None:
        """Résultat du dernier enregistrement arrêté (filepath + sample_count)."""
        return self._last_recording_result

    # ═══════════════════════════════════════════════════════════════
    # API publique : envoyer des commandes au thread
    # Équiv. LabVIEW : Enqueue Element (file de commandes)
    # ═══════════════════════════════════════════════════════════════

    def send_command(self, message: Message, **payload):
        """
        Envoie une commande au thread via la file.

        Équiv. LabVIEW : Enqueue Element(queue_ref, cluster(message, data))
        Appelé depuis le thread principal (Controller).

        Args:
            message: Type de message (Message enum)
            **payload: Données associées au message (optionnel)
        """
        self.command_queue.put(MessagePacket(message, payload))

    # ═══════════════════════════════════════════════════════════════
    # Boucle principale du thread (State Machine)
    # Équiv. LabVIEW : While Loop + Case Structure
    # ═══════════════════════════════════════════════════════════════

    def run(self):
        """
        Point d'entrée du QThread — boucle infinie avec State Machine.

        Chaque itération :
          1. Dépiler les commandes de la file (Dequeue Element, timeout=0)
          2. Exécuter l'état courant (Case Structure sur Enum)

        Le shift register "state" détermine quel Case est exécuté.
        Les transitions d'état se font via _change_state().
        """
        print("[DAQModel] Thread démarré — état: IDLE")

        while self._running:
            # ── 1. Traiter les commandes en attente ──
            # Équiv. LabVIEW : Dequeue Element (timeout=0) dans un While
            self._process_commands()

            # ── 2. Exécuter l'état courant ──
            # Équiv. LabVIEW : Case Structure alimenté par le shift register "state"
            match self._state:

                case AcquisitionState.IDLE:
                    time.sleep(0.05)   # Attente passive, faible CPU

                case AcquisitionState.CONFIGURING:
                    self._do_configure()

                case AcquisitionState.ACQUIRING:
                    self._do_acquire()

                case AcquisitionState.STOPPING:
                    self._do_stop()

                case AcquisitionState.ERROR:
                    self._do_error()

        print("[DAQModel] Thread terminé")

    def _change_state(self, new_state: AcquisitionState):
        """
        Transition d'état de la State Machine.

        Équiv. LabVIEW : écriture dans le shift register "next state"
                         + Generate User Event pour notifier l'UI.
        """
        old = self._state
        self._state = new_state
        print(f"[DAQModel] État: {old.name} → {new_state.name}")
        self.state_changed.emit(new_state)

    # ═══════════════════════════════════════════════════════════════
    # Traitement des commandes
    # Équiv. LabVIEW : Dequeue Element (timeout=0) en boucle
    # ═══════════════════════════════════════════════════════════════

    def _process_commands(self):
        """
        Dépile et traite toutes les commandes en attente dans la file.

        Équiv. LabVIEW :
            While (Queue Not Empty):
                Dequeue Element (timeout=0)
                Case Structure sur le message
        """
        while not self.command_queue.empty():
            try:
                packet: MessagePacket = self.command_queue.get_nowait()
            except queue.Empty:
                break

            match packet.message:

                case Message.START_ACQUISITION:
                    self._task_name = packet.payload.get("task_name", "")
                    if self._state == AcquisitionState.IDLE:
                        self._change_state(AcquisitionState.CONFIGURING)

                case Message.STOP_ACQUISITION:
                    if self._state == AcquisitionState.ACQUIRING:
                        self._change_state(AcquisitionState.STOPPING)

                case Message.START_RECORDING:
                    self._record_directory = packet.payload.get("directory", "")
                    self._record_prefix = packet.payload.get("prefix", "")
                    self._record_comment = packet.payload.get("comment", "")
                    self._record_period = packet.payload.get("period", 60)
                    self._start_recording()

                case Message.STOP_RECORDING:
                    self._stop_recording()

                case Message.CHANGE_PERIOD:
                    self._record_period = packet.payload.get("period", 60)
                    print(f"[DAQModel] Période mise à jour: {self._record_period}s")

                case Message.QUIT:
                    self._quit_requested = True
                    if self._state == AcquisitionState.ACQUIRING:
                        self._change_state(AcquisitionState.STOPPING)
                    elif self._state == AcquisitionState.IDLE:
                        self._running = False

    # ═══════════════════════════════════════════════════════════════
    # Implémentation des états (Cases de la State Machine)
    # ═══════════════════════════════════════════════════════════════

    def _do_configure(self):
        """
        État CONFIGURING : charge la tâche NI MAX et configure le timing.

        Équiv. LabVIEW :
            DAQmx Load Persisted Task.vi
            DAQmx Timing.vi (Sample Clock, Continuous, 10 Hz)
            → next state = ACQUIRING
        """
        try:
            if not NIDAQMX_AVAILABLE:
                # ── Mode simulation ──
                self._channel_names = [f"Sim_CH{i}" for i in range(4)]
                self._n_channels = len(self._channel_names)
                print(f"[DAQModel] Mode simulation : {self._n_channels} canaux")
                self._init_buffers()
                self._acquisition_start_time = time.time()
                self._change_state(AcquisitionState.ACQUIRING)
                return

            # ── Charger la tâche persistée depuis NI MAX ──
            # Équiv. LabVIEW : DAQmx Load Task (persisted task from MAX)
            persisted = storage.PersistedTask(self._task_name)
            self._task = persisted.load()

            # Lire les canaux configurés
            self._channel_names = [ch.name for ch in self._task.ai_channels]
            self._n_channels = len(self._channel_names)

            if self._n_channels == 0:
                raise Exception(
                    f"La tâche '{self._task_name}' ne contient aucun canal AI.\n"
                    f"Configurez des canaux d'entrée analogique dans NI MAX."
                )

            # Reconfigurer le timing hardware
            # Équiv. LabVIEW : DAQmx Timing.vi (Sample Clock, Continuous)
            self._task.timing.samp_quant_samp_mode = AcquisitionType.CONTINUOUS
            self._task.timing.samp_clk_rate = float(self._sample_rate)
            self._task.timing.samp_quant_samp_per_chan = self.config.SAMPLES_PER_CHANNEL

            print(f"[DAQModel] Tâche '{self._task_name}' : "
                  f"{self._n_channels} canaux @ {self._sample_rate} Hz")

            self._init_buffers()
            self._acquisition_start_time = time.time()
            self._change_state(AcquisitionState.ACQUIRING)

        except Exception as e:
            self._last_error = str(e)
            self._change_state(AcquisitionState.ERROR)

    def _init_buffers(self):
        """Réinitialise tous les buffers de données."""
        with QMutexLocker(self._mutex):
            self._buffer_instant = np.empty((self._n_channels, 0))
            self._timestamps_instant = []
            self._buffer_longduration = np.empty((self._n_channels, 0))
            self._timestamps_longduration = []
        self._total_samples = 0
        self._last_save_sample = 0
        self._last_recording_result = None

    def _do_acquire(self):
        """
        État ACQUIRING : lit 1 échantillon par canal depuis le DAQ.
        Si le flag _is_recording est actif, écrit dans le fichier
        et alimente le buffer longue durée.

        Équiv. LabVIEW :
            DAQmx Read.vi (Analog, 1D DBL, N Channels, 1 Sample)
            ├─ Shift Register : buffer instantané (fenêtre glissante)
            ├─ Case Structure "Recording?"
            │   ├─ True  : Write Delimited Spreadsheet + buffer longue durée
            │   └─ False : (passer)
            └─ Wire → Shift Register (itération suivante)

        Timestamps : t = n / fs (basé sur compteur, pas sur horloge système)
                     → élimine jitter et dérive de l'horloge logicielle
        """
        try:
            if NIDAQMX_AVAILABLE and self._task:
                # ── Lecture hardware ──
                # Équiv. LabVIEW : DAQmx Read.vi (Analog 1D DBL, N chan, 1 samp)
                try:
                    self._buffer_available = self._task.in_stream.avail_samp_per_chan
                except Exception:
                    self._buffer_available = 0

                raw = self._task.read(
                    number_of_samples_per_channel=self.config.SAMPLES_PER_READ,
                    timeout=self.config.TIMEOUT
                )

                # Convertir en numpy 2D (n_channels, n_samples)
                if not isinstance(raw, np.ndarray):
                    raw = np.array(raw)
                if raw.ndim == 1:
                    raw = raw.reshape(-1, 1)
                data = raw

            else:
                # ── Mode simulation : sinusoïdes déphasées ──
                t = self._total_samples / self._sample_rate
                data = np.array([
                    [self.config.SIMULATION_AMPLITUDE * np.sin(
                        2 * np.pi * 0.1 * t + i * np.pi / max(1, self._n_channels)
                    )]
                    for i in range(self._n_channels)
                ])
                self._buffer_available = 0

            n_new = data.shape[1]

            # ── Timestamp précis basé sur compteur d'échantillons ──
            # t = n / fs → pas de dérive, pas de jitter
            base_time = self._total_samples / self._sample_rate
            new_timestamps = [base_time + j / self._sample_rate for j in range(n_new)]
            self._total_samples += n_new

            # ── Buffer instantané (fenêtre glissante de 60s) ──
            # Équiv. LabVIEW : Shift Register + Array Subset (garder les N derniers)
            with QMutexLocker(self._mutex):
                if self._buffer_instant.shape[1] == 0:
                    self._buffer_instant = data
                else:
                    self._buffer_instant = np.concatenate(
                        [self._buffer_instant, data], axis=1
                    )
                self._timestamps_instant.extend(new_timestamps)

                # Trimmer si dépassement de la fenêtre
                overflow = self._buffer_instant.shape[1] - self._max_instant_samples
                if overflow > 0:
                    self._buffer_instant = self._buffer_instant[:, overflow:]
                    self._timestamps_instant = self._timestamps_instant[overflow:]

            # ── Si recording actif : écrire fichier + buffer longue durée ──
            # Équiv. LabVIEW : Case Structure "Recording?" dans le Case ACQUIRING
            if self._is_recording and self.data_model.is_open:
                # Décimation par période :
                #   period > 0 → 1 point tous les (period × sample_rate) échantillons
                #   period = 0 → chaque échantillon
                if self._record_period > 0:
                    samples_per_record = max(1, int(self._record_period * self._sample_rate))
                else:
                    samples_per_record = 1

                samples_since_last = self._total_samples - self._last_save_sample

                if samples_since_last >= samples_per_record:
                    precise_time = self._total_samples / self._sample_rate
                    channel_values = data[:, -1].tolist()

                    # Écrire dans le fichier TSV
                    self.data_model.write_row(precise_time, channel_values)
                    self._last_save_sample = self._total_samples

                    # Buffer longue durée (pour le graphique)
                    with QMutexLocker(self._mutex):
                        point = data[:, -1:].copy()
                        if self._buffer_longduration.shape[1] == 0:
                            self._buffer_longduration = point
                        else:
                            self._buffer_longduration = np.concatenate(
                                [self._buffer_longduration, point], axis=1
                            )
                        self._timestamps_longduration.append(precise_time)

                        # Trimmer si > max
                        overflow = (self._buffer_longduration.shape[1]
                                    - self._max_longduration_samples)
                        if overflow > 0:
                            self._buffer_longduration = self._buffer_longduration[:, overflow:]
                            self._timestamps_longduration = self._timestamps_longduration[overflow:]

            # ── Temporisation ──
            if NIDAQMX_AVAILABLE and self._task:
                time.sleep(0.01)  # CPU relief (task.read bloque déjà ~100ms à 10Hz)
            else:
                time.sleep(1.0 / self._sample_rate)  # Simuler le timing hardware

        except Exception as e:
            self._last_error = str(e)
            self._change_state(AcquisitionState.ERROR)

    def _start_recording(self):
        """
        Démarre l'enregistrement fichier (appelé dans le thread d'acquisition).

        Équiv. LabVIEW : Open/Create File + initialisation shift registers recording
        """
        if self._state != AcquisitionState.ACQUIRING:
            return

        try:
            filepath = self.data_model.open_file(
                directory=self._record_directory,
                prefix=self._record_prefix,
                comment=self._record_comment,
                channel_names=self._channel_names
            )
            self._is_recording = True
            self._last_save_sample = self._total_samples

            # Réinitialiser le buffer longue durée
            with QMutexLocker(self._mutex):
                self._buffer_longduration = np.empty((self._n_channels, 0))
                self._timestamps_longduration = []

            print(f"[DAQModel] Enregistrement démarré : {filepath}")

        except Exception as e:
            self._last_error = f"Erreur ouverture fichier: {e}"
            self.error_occurred.emit(self._last_error)

    def _stop_recording(self):
        """
        Arrête l'enregistrement fichier.

        Équiv. LabVIEW : Close File + Bundle résultat
        """
        self._is_recording = False
        if self.data_model.is_open:
            self._last_recording_result = self.data_model.close_file()
            print(f"[DAQModel] Enregistrement arrêté : "
                  f"{self._last_recording_result['sample_count']} points")

    def _do_stop(self):
        """
        État STOPPING : ferme proprement la tâche DAQ et les fichiers.

        Équiv. LabVIEW :
            DAQmx Stop Task.vi
            DAQmx Clear Task.vi
            Close File.vi
            → next state = IDLE
        """
        # Arrêter l'enregistrement si actif
        if self._is_recording:
            self._stop_recording()

        # Fermer la tâche DAQ
        if self._task and NIDAQMX_AVAILABLE:
            try:
                self._task.stop()
                self._task.close()
            except Exception as e:
                print(f"[DAQModel] Erreur fermeture tâche: {e}")
            self._task = None

        self._acquisition_start_time = None
        self._change_state(AcquisitionState.IDLE)

        # Si QUIT a été demandé, arrêter le thread après le nettoyage
        if self._quit_requested:
            self._running = False

    def _do_error(self):
        """
        État ERROR : signale l'erreur et revient à IDLE.

        Équiv. LabVIEW : General Error Handler.vi → next state = IDLE
        """
        error_msg = self._last_error or "Erreur inconnue"
        print(f"[DAQModel] ERREUR: {error_msg}")
        self.error_occurred.emit(error_msg)

        # Nettoyage
        if self._is_recording:
            self._stop_recording()
        if self._task and NIDAQMX_AVAILABLE:
            try:
                self._task.stop()
                self._task.close()
            except Exception:
                pass
            self._task = None

        self._acquisition_start_time = None
        self._change_state(AcquisitionState.IDLE)

        if self._quit_requested:
            self._running = False

    # ═══════════════════════════════════════════════════════════════
    # Arrêt propre (appelé depuis le thread principal)
    # ═══════════════════════════════════════════════════════════════

    def shutdown(self):
        """
        Arrêt propre du thread. Appelé par le Controller lors de la fermeture.

        Équiv. LabVIEW : Enqueue "QUIT" + Wait on Asynchronous Call
        """
        self.send_command(Message.QUIT)
        if not self.wait(5000):  # Attend max 5 secondes
            print("[DAQModel] Warning: arrêt forcé du thread")
            self.terminate()
