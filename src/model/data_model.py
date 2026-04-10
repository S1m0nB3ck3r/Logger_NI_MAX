"""
DataModel — Gestion de l'écriture des données sur disque.

Responsabilité unique : ouvrir/fermer les fichiers TSV, écrire les en-têtes
et les lignes de données. Aucune logique d'acquisition ou d'interface.

Équivalent LabVIEW :
    Sous-VI de logging fichier, appelé depuis la boucle d'acquisition :
    ┌──────────────────────────────────────┐
    │  File I/O SubVI                      │
    │  ├─ Open/Create File                 │
    │  ├─ Write Delimited Spreadsheet.vi   │
    │  └─ Close File                       │
    └──────────────────────────────────────┘

    Le fichier est ouvert une fois (open_file), écrit ligne par ligne
    (write_row, appelé N fois), puis fermé proprement (close_file).
    Toutes les opérations sont effectuées depuis le thread d'acquisition
    (DAQModel) pour éviter les accès concurrents.
"""

import csv
import os
from datetime import datetime


class DataModel:
    """
    Gère l'écriture des données acquises dans des fichiers TSV (tab-separated).

    Cycle de vie :
        1. open_file()  → crée le fichier, écrit l'en-tête
        2. write_row()  → écrit une ligne de données (appelé N fois)
        3. close_file() → ferme le fichier, retourne un résumé

    Toutes les opérations fichier sont effectuées depuis le thread d'acquisition
    (DAQModel) pour éviter les accès concurrents — jamais depuis le thread UI.
    """

    def __init__(self):
        self._file = None
        self._writer = None
        self._filepath = None
        self._sample_count = 0

    # ─── Propriétés (lecture seule) ───

    @property
    def is_open(self) -> bool:
        """Le fichier est-il actuellement ouvert pour écriture ?"""
        return self._file is not None

    @property
    def filepath(self) -> str | None:
        """Chemin complet du fichier en cours d'écriture."""
        return self._filepath

    @property
    def sample_count(self) -> int:
        """Nombre de lignes de données écrites depuis l'ouverture."""
        return self._sample_count

    # ─── Opérations fichier ───

    def open_file(self, directory: str, prefix: str, comment: str,
                  channel_names: list[str]) -> str:
        """
        Ouvre un nouveau fichier TSV pour l'enregistrement.

        Équivalent LabVIEW : Open/Create/Replace File.vi + Write To Text File (header)

        Args:
            directory:     Dossier de destination (créé si nécessaire)
            prefix:        Préfixe du nom de fichier
            comment:       Commentaire optionnel (écrit en 1ère ligne avec #)
            channel_names: Noms des canaux pour l'en-tête

        Returns:
            Chemin complet du fichier créé
        """
        os.makedirs(directory, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.txt"
        self._filepath = os.path.join(directory, filename)

        self._file = open(self._filepath, 'w', newline='', encoding='utf-8')
        self._writer = csv.writer(self._file, delimiter='\t')

        # Commentaire optionnel en première ligne
        if comment:
            self._writer.writerow([f"# {comment}"])

        # En-tête : Temps + noms des canaux
        header = ["Temps"] + channel_names
        self._writer.writerow(header)
        self._file.flush()

        self._sample_count = 0
        return self._filepath

    def write_row(self, timestamp: float, channel_values: list[float]):
        """
        Écrit une ligne de données [temps, ch0, ch1, ...].

        Équivalent LabVIEW : Write Delimited Spreadsheet.vi (append mode, TAB delimiter)

        Args:
            timestamp:      Temps précis en secondes (basé sur compteur d'échantillons)
            channel_values: Valeurs des canaux pour cet instant
        """
        if self._writer is None:
            return
        row = [timestamp] + channel_values
        self._writer.writerow(row)
        self._file.flush()
        self._sample_count += 1

    def close_file(self) -> dict:
        """
        Ferme le fichier en cours et retourne un résumé.

        Équivalent LabVIEW : Close File.vi + Bundle (filepath, count)

        Returns:
            dict avec 'filepath' et 'sample_count' pour le message de résultat
        """
        result = {
            "filepath": self._filepath,
            "sample_count": self._sample_count
        }
        if self._file:
            self._file.close()
        self._file = None
        self._writer = None
        self._filepath = None
        self._sample_count = 0
        return result
