"""
Configuration - Paramètres de l'application Logger NI
"""


class Config:
    """
    Classe de configuration pour l'application
    """
    
    # ========== PARAMÈTRES DAQ ==========
    
    # Fréquence d'échantillonnage (Hz)
    SAMPLE_RATE = 10  # 10 Hz pour la cuve expérimentale
    
    # Nombre d'échantillons par canal dans le buffer
    SAMPLES_PER_CHANNEL = 1000
    
    # Nombre d'échantillons à lire à chaque fois
    SAMPLES_PER_READ = 1  # Lire 1 point à la fois à 10Hz
    
    # Timeout pour la lecture (secondes)
    TIMEOUT = 1.0
    
    # Historique du graphique instantané (en secondes)
    INSTANT_HISTORY_SECONDS = 60  # 1 minute
    INSTANT_MAX_SAMPLES = SAMPLE_RATE * INSTANT_HISTORY_SECONDS  # 600 points à 10Hz
    
    # Historique du graphique longue durée (nombre de points maximum)
    MAX_LONGUE_DUREE_SAMPLES = 100000  # 100 000 points max (évite la saturation mémoire)
    
    # Plage de tension
    MIN_VOLTAGE = -10.0
    MAX_VOLTAGE = 10.0
    
    # ========== PARAMÈTRES INTERFACE ==========
    
    # Taille de la fenêtre
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 700
    
    # Couleurs
    COLOR_BACKGROUND = '#e8f4f8'
    COLOR_PLOT_BG = '#808080'
    COLOR_PLOT_FRAME = '#d3d3d3'
    
    # ========== PARAMÈTRES D'ENREGISTREMENT ==========
    
    # Période d'enregistrement par défaut (secondes)
    # 0 = pas d'enregistrement automatique
    DEFAULT_RECORD_PERIOD = 60  # 60 secondes par défaut
    
    # ========== PARAMÈTRES D'AFFICHAGE ==========
    
    # Durée d'affichage du graphique instantané (secondes)
    INSTANT_DISPLAY_DURATION = 1.0
    
    # Facteur de décimation pour l'affichage longue durée
    DECIMATION_FACTOR = 10
    
    # ========== PARAMÈTRES DE SAUVEGARDE ==========
    
    # Format de sauvegarde
    SAVE_FORMAT = "CSV"  # Options: "CSV", "TDMS"
    
    # Dossier de sauvegarde par défaut
    DEFAULT_SAVE_FOLDER = "data"
    
    # Fichier de configuration des paramètres
    CONFIG_FILE = "logger_config.json"
    
    # ========== MODE SIMULATION ==========
    
    # Activer le mode simulation si aucune carte DAQ n'est détectée
    ENABLE_SIMULATION = True
    
    # Fréquence du signal simulé (Hz)
    SIMULATION_FREQUENCY = 10.0
    
    # Amplitude du signal simulé
    SIMULATION_AMPLITUDE = 5.0


# Instance globale de configuration
config = Config()
