"""
Logger NI — Application d'acquisition de données National Instruments
Point d'entrée principal de l'application

Architecture PySide6 inspirée des design patterns LabVIEW :
    - Queued Message Handler (QMH) → Controller + message_queue
    - State Machine d'acquisition  → DAQModel QThread
    - Producer/Consumer             → View (producer) / Controller (consumer)
    - Event Structure               → QApplication.exec() (boucle d'événements Qt)

Équivalent LabVIEW :
    Ce fichier correspond au "main.vi" qui :
    1. Crée les références partagées (queues, notifiers)
    2. Lance les boucles parallèles (UI loop, acquisition loop)
    3. Attend la fin d'exécution

    En Python/Qt :
    1. QApplication → boucle d'événements (équiv. UI loop LabVIEW)
    2. DAQModel(QThread) → thread d'acquisition (équiv. acquisition loop)
    3. Controller(QTimer) → consumer loop du QMH (traitement des messages)
    4. app.exec() → bloque jusqu'à fermeture (équiv. While Loop + Event Structure)

Flux de données :
    ┌──────────┐  Signaux   ┌────────────┐  command_queue  ┌──────────┐
    │   View   │ ─────────► │ Controller │ ──────────────► │ DAQModel │
    │ (PySide6)│            │   (QMH)    │                 │ (QThread)│
    │          │ ◄───────── │            │ ◄────────────── │          │
    └──────────┘  méthodes  └────────────┘  Signal(state)  └──────────┘
         │                       │                              │
         │                       │                              │
    Boutons/Inputs          QTimer 100ms                    State Machine
    → emit Signal()         → process_messages()            IDLE → CONFIGURING
                            → poll buffers                  → ACQUIRING → STOPPING
                            → update plots
"""

import sys
import os

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from model.data_model import DataModel
from model.daq_model import DAQModel
from view.main_view import MainView
from controller.main_controller import MainController
from utils.config import config


def main():
    """
    Fonction principale — crée et connecte les composants MVC.

    Équiv. LabVIEW :
        1. Obtain Queue (créer les files de messages)
        2. Launch VIs (démarrer les boucles parallèles)
        3. Wait for Events (app.exec = boucle événementielle)
    """
    print("=" * 60)
    print("Logger NI — Acquisition de données National Instruments")
    print("Architecture MVC + QMH + State Machine (PySide6)")
    print("=" * 60)

    # ── 1. Créer l'application Qt ──
    # Équiv. LabVIEW : initialisation du runtime LabVIEW
    app = QApplication(sys.argv)

    # Attributs de l'application
    app.setApplicationName("Logger NI")
    app.setApplicationVersion("2.5")

    try:
        # ── 2. Créer les composants MVC ──
        print("\nInitialisation des composants...")

        # Modèles
        data_model = DataModel()
        daq_model = DAQModel(config, data_model)
        print("✓ Modèles créés (DataModel + DAQModel)")

        # Vue (Front Panel)
        view = MainView(config)
        print("✓ Vue créée (PySide6 + pyqtgraph)")

        # Contrôleur (QMH — connecte tout + lance le consumer thread)
        controller = MainController(daq_model, data_model, view)
        print("✓ Contrôleur créé (QMH + QMHWorker thread connecté)")

        print("\nDémarrage de l'application...")
        print("-" * 60)

        # ── 3. Afficher la fenêtre et lancer la boucle d'événements ──
        # Équiv. LabVIEW : le VI est maintenant "running"
        #   app.exec() = While Loop + Event Structure (bloque jusqu'à fermeture)
        view.show()
        sys.exit(app.exec())

    except Exception as e:
        print(f"\n❌ Erreur lors du démarrage de l'application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
