"""
Script de test pour vérifier l'installation et la configuration
Logger NI v3.0 — PySide6 + pyqtgraph + nidaqmx
"""
import sys
import os

# Ajouter le dossier src/ au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))


def test_imports():
    """Test des imports de dépendances externes"""
    print("Test des imports...")
    results = []

    try:
        from PySide6 import __version__ as pyside_ver
        print(f"  ✓ PySide6 {pyside_ver} disponible")
        results.append(True)
    except ImportError as e:
        print(f"  ✗ Erreur PySide6: {e}")
        results.append(False)

    try:
        import pyqtgraph
        print(f"  ✓ pyqtgraph {pyqtgraph.__version__} disponible")
        results.append(True)
    except ImportError as e:
        print(f"  ✗ Erreur pyqtgraph: {e}")
        results.append(False)

    try:
        import numpy as np
        print(f"  ✓ NumPy {np.__version__} disponible")
        results.append(True)
    except ImportError as e:
        print(f"  ✗ Erreur NumPy: {e}")
        results.append(False)

    try:
        import nidaqmx
        print(f"  ✓ NI-DAQmx Python disponible")
        results.append(True)
    except ImportError as e:
        print(f"  ✗ Erreur NI-DAQmx: {e}")
        results.append(False)

    return all(results)


def test_modules():
    """Test des modules de l'application (depuis src/)"""
    print("\nTest des modules de l'application...")
    results = []

    try:
        from model.daq_model import DAQModel
        print("  ✓ DAQModel importé (src/model/daq_model.py)")
        results.append(True)
    except ImportError as e:
        print(f"  ✗ Erreur DAQModel: {e}")
        results.append(False)

    try:
        from model.data_model import DataModel
        print("  ✓ DataModel importé (src/model/data_model.py)")
        results.append(True)
    except ImportError as e:
        print(f"  ✗ Erreur DataModel: {e}")
        results.append(False)

    try:
        from view.main_view import MainView
        print("  ✓ MainView importé (src/view/main_view.py)")
        results.append(True)
    except ImportError as e:
        print(f"  ✗ Erreur MainView: {e}")
        results.append(False)

    try:
        from controller.main_controller import MainController
        print("  ✓ MainController importé (src/controller/main_controller.py)")
        results.append(True)
    except ImportError as e:
        print(f"  ✗ Erreur MainController: {e}")
        results.append(False)

    try:
        from utils.config import config
        print("  ✓ Config importé (src/utils/config.py)")
        results.append(True)
    except ImportError as e:
        print(f"  ✗ Erreur Config: {e}")
        results.append(False)

    try:
        from utils.messages import Message, AcquisitionState, MessagePacket
        print("  ✓ Messages importé (src/utils/messages.py)")
        results.append(True)
    except ImportError as e:
        print(f"  ✗ Erreur Messages: {e}")
        results.append(False)

    return all(results)


def test_daq_devices():
    """Test de détection des périphériques DAQ"""
    print("\nTest de détection des périphériques DAQ...")

    try:
        import nidaqmx
        from nidaqmx.system import System

        system = System.local()
        devices = system.devices

        if len(devices) > 0:
            print(f"  ✓ {len(devices)} périphérique(s) détecté(s):")
            for device in devices:
                print(f"    - {device.name}: {device.product_type}")
        else:
            print("  ⚠ Aucun périphérique DAQ détecté")
            print("    L'application fonctionnera en mode simulation")

        return True

    except Exception as e:
        print(f"  ✗ Erreur lors de la détection: {e}")
        return False


def test_config():
    """Test de la configuration"""
    print("\nTest de la configuration...")

    try:
        from utils.config import config

        print(f"  ✓ SAMPLE_RATE = {config.SAMPLE_RATE} Hz")
        print(f"  ✓ INSTANT_MAX_SAMPLES = {config.INSTANT_MAX_SAMPLES}")
        print(f"  ✓ MAX_LONGUE_DUREE_SAMPLES = {config.MAX_LONGUE_DUREE_SAMPLES}")
        print(f"  ✓ ENABLE_SIMULATION = {config.ENABLE_SIMULATION}")

        return True

    except Exception as e:
        print(f"  ✗ Erreur Config: {e}")
        return False


def test_qss_stylesheet():
    """Test de la présence du fichier de style QSS"""
    print("\nTest du fichier de style...")

    qss_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "src", "view", "style.qss"
    )

    if os.path.exists(qss_path):
        size = os.path.getsize(qss_path)
        print(f"  ✓ style.qss trouvé ({size} octets)")
        return True
    else:
        print(f"  ✗ style.qss NON trouvé : {qss_path}")
        return False


def main():
    """Exécute tous les tests"""
    print("=" * 60)
    print("Logger NI — Test d'installation v3.0")
    print("Architecture : PySide6 + pyqtgraph + nidaqmx")
    print("Structure : src/ (code source)")
    print("=" * 60)
    print()

    all_ok = True
    all_ok &= test_imports()
    all_ok &= test_modules()
    all_ok &= test_daq_devices()
    all_ok &= test_config()
    all_ok &= test_qss_stylesheet()

    print()
    print("=" * 60)
    if all_ok:
        print("✅ TOUS LES TESTS PASSENT — L'installation est correcte !")
    else:
        print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ — Vérifiez les erreurs ci-dessus")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
