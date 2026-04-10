"""
Gestionnaire de paramètres - Sauvegarde et chargement de la configuration
"""
import json
import os


class SettingsManager:
    """
    Classe pour gérer la sauvegarde et le chargement des paramètres
    """
    
    def __init__(self, config_file="logger_config.json"):
        """
        Initialise le gestionnaire de paramètres
        
        Args:
            config_file: Nom du fichier de configuration
        """
        self.config_file = config_file
        self.settings = {
            'task_name': '',
            'record_period': 60,
            'file_prefix': 'data',
            'file_comment': '',
            'last_save_folder': 'data',
            'window_geometry': '1400x800'
        }
    
    def load_settings(self):
        """
        Charge les paramètres depuis le fichier JSON
        
        Returns:
            dict: Dictionnaire des paramètres chargés
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
                    print(f"✓ Paramètres chargés depuis {self.config_file}")
            except Exception as e:
                print(f"⚠ Erreur lors du chargement des paramètres: {e}")
        else:
            print(f"ℹ Fichier de configuration non trouvé, utilisation des valeurs par défaut")
        
        return self.settings
    
    def save_settings(self, settings=None):
        """
        Sauvegarde les paramètres dans le fichier JSON
        
        Args:
            settings: Dictionnaire des paramètres à sauvegarder (optionnel)
        """
        if settings:
            self.settings.update(settings)
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            print(f"✓ Paramètres sauvegardés dans {self.config_file}")
        except Exception as e:
            print(f"⚠ Erreur lors de la sauvegarde des paramètres: {e}")
    
    def get(self, key, default=None):
        """
        Récupère un paramètre
        
        Args:
            key: Clé du paramètre
            default: Valeur par défaut si la clé n'existe pas
        
        Returns:
            Valeur du paramètre
        """
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """
        Définit un paramètre
        
        Args:
            key: Clé du paramètre
            value: Valeur du paramètre
        """
        self.settings[key] = value
    
    def update(self, **kwargs):
        """
        Met à jour plusieurs paramètres
        
        Args:
            **kwargs: Paramètres à mettre à jour
        """
        self.settings.update(kwargs)
