"""
Messages et états pour le pattern Queued Message Handler (QMH).

Équivalent LabVIEW :
    - Message (Enum)           → Type Def Enum pour le Case Structure du consumer loop
    - AcquisitionState (Enum)  → Type Def Enum pour la State Machine d'acquisition
    - MessagePacket (Cluster)  → Cluster {Message, Data} envoyé via Enqueue Element

En LabVIEW, vous utiliseriez un Type Def Enum partagé entre le producer et le consumer.
En Python, les Enums jouent exactement le même rôle : un ensemble fini de valeurs nommées.

    ┌────────────────────────────────────────────────────────┐
    │  Producer (View)                                       │
    │    Event Structure détecte un clic                     │
    │    → Enqueue Element(queue, {START_ACQUISITION, data}) │
    └──────────────────────┬─────────────────────────────────┘
                           │  Queue
    ┌──────────────────────▼─────────────────────────────────┐
    │  Consumer (Controller)                                 │
    │    Dequeue Element(queue, timeout=100ms)               │
    │    → Case Structure sur Message Enum                   │
    │       ├─ START_ACQUISITION : démarrer le DAQ           │
    │       ├─ STOP_ACQUISITION  : arrêter le DAQ            │
    │       ├─ CHANGE_TASK       : changer la tâche NI MAX   │
    │       └─ QUIT              : quitter proprement        │
    └────────────────────────────────────────────────────────┘
"""

from enum import Enum, auto
from dataclasses import dataclass, field


class Message(Enum):
    """
    Messages du Queued Message Handler (QMH) principal.

    Chaque valeur correspond à un "cas" du Case Structure dans le consumer loop.
    Le producer (View) enfile ces messages, le consumer (Controller) les traite.

    Équivalent LabVIEW : Enum Type Def → Enqueue Element → Dequeue Element → Case Structure
    """
    START_ACQUISITION = auto()   # Démarrer acquisition + enregistrement
    STOP_ACQUISITION  = auto()   # Arrêter acquisition + enregistrement
    START_RECORDING   = auto()   # Démarrer l'enregistrement fichier
    STOP_RECORDING    = auto()   # Arrêter l'enregistrement fichier uniquement
    CHANGE_TASK       = auto()   # Changer la tâche NI MAX sélectionnée
    CHANGE_PERIOD     = auto()   # Modifier la période d'enregistrement
    QUIT              = auto()   # Quitter l'application proprement
    ERROR             = auto()   # Signaler une erreur


class AcquisitionState(Enum):
    """
    États de la State Machine du thread d'acquisition.

    Équivalent LabVIEW : Enum dans le shift register de la boucle While,
                         alimentant un Case Structure pour chaque état.

    Diagramme d'états :

        IDLE ──START──► CONFIGURING ──ok──► ACQUIRING ──STOP──► STOPPING ──► IDLE
                              │                                      ▲
                              └──error──► ERROR ─────────────────────┘

    Note : ACQUIRING gère à la fois l'acquisition et l'enregistrement.
           L'enregistrement est un flag interne (_is_recording), pas un état séparé.
           C'est l'équivalent d'un "if recording?" dans le Case ACQUIRING en LabVIEW.
    """
    IDLE        = auto()   # En attente — pas de tâche DAQ ouverte
    CONFIGURING = auto()   # Chargement tâche NI MAX, configuration hardware
    ACQUIRING   = auto()   # Lecture continue (+ enregistrement si flag actif)
    STOPPING    = auto()   # Fermeture propre tâche + fichiers
    ERROR       = auto()   # Gestion d'erreur → retour à IDLE


@dataclass
class MessagePacket:
    """
    Paquet transporté dans la file du QMH : message + données optionnelles.

    Équivalent LabVIEW : Cluster {Message (Enum), Data (Variant)}
                         passé via Enqueue Element / Dequeue Element.

    En LabVIEW vous utiliseriez un Variant ou un Cluster de Clusters pour les données.
    En Python, le dataclass + dict offre la même flexibilité avec du typage.

    Exemples :
        MessagePacket(Message.START_ACQUISITION, {"task_name": "MaTache"})
        MessagePacket(Message.CHANGE_PERIOD, {"period": 30})
        MessagePacket(Message.QUIT)  # Pas de payload nécessaire
    """
    message: Message
    payload: dict = field(default_factory=dict)
