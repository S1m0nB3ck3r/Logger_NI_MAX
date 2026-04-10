"""
Utilitaires DAQmx - Fonctions pour lister et gérer les tâches
"""
import nidaqmx
from nidaqmx.system import System


def list_available_tasks():
    """
    Liste toutes les tâches DAQmx disponibles dans le système
    
    Returns:
        list: Liste des noms de tâches disponibles
    """
    try:
        system = System.local()
        tasks = system.tasks
        task_names = [task.name for task in tasks]
        print(f"✓ {len(task_names)} tâche(s) DAQmx trouvée(s): {task_names}")
        return task_names
    except Exception as e:
        print(f"⚠ Erreur lors de la liste des tâches: {e}")
        return []


def get_task_channels(task_name):
    """
    Récupère les canaux d'une tâche DAQmx
    
    Args:
        task_name: Nom de la tâche
    
    Returns:
        list: Liste des noms de canaux
    """
    try:
        with nidaqmx.Task(task_name) as task:
            channels = [channel.name for channel in task.ai_channels]
            return channels
    except Exception as e:
        print(f"⚠ Erreur lors de la récupération des canaux: {e}")
        return []


def list_available_devices():
    """
    Liste tous les périphériques DAQ disponibles
    
    Returns:
        list: Liste des noms de périphériques
    """
    try:
        system = System.local()
        devices = system.devices
        device_names = [device.name for device in devices]
        return device_names
    except Exception as e:
        print(f"⚠ Erreur lors de la liste des périphériques: {e}")
        return []
