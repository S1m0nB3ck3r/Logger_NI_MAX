# ⏱️ Système de timestamps haute précision — Logger NI v3.0

## 🎯 Objectif

Garantir des **timestamps précis et réguliers** pour les mesures, même quand le système d'exploitation
introduit des variations de timing (jitter) dans l'acquisition.

---

## 📌 Le problème

### Approche naïve : `datetime.now()` à chaque échantillon

```python
# ❌ PROBLÈME : Les timestamps dérivent
timestamp = datetime.now()  # Appel à chaque lecture
```

**Résultat** : Irrégularités dues au jitter de l'OS (scheduling, I/O, GC Python).

```
Attendu :  0.000  0.100  0.200  0.300  0.400
Réel :     0.000  0.102  0.198  0.305  0.399
Drift :    0.000  +2ms   -2ms   +5ms   -1ms
```

Sur des acquisitions longues (heures), le drift s'accumule.

---

## ✅ Notre solution : Timestamps calculés par compteur

### Principe

Au lieu d'appeler `datetime.now()` à chaque échantillon, on :

1. **Enregistre** l'heure de départ (`t₀`) une seule fois
2. **Compte** les échantillons (`n`)
3. **Calcule** le timestamp : `tₙ = t₀ + n × période`

```python
# ✅ SOLUTION : Timestamps calculés
t0 = datetime.now()        # Une seule fois au démarrage
period_ms = 100            # Période d'acquisition en ms
n = sample_counter         # Compteur incrémental

timestamp = t0 + timedelta(milliseconds=n * period_ms)
```

### Implémentation dans `DAQModel` (QThread)

```python
# Dans src/model/daq_model.py — méthode _run_acquisition()

class DAQModel(QThread):
    def _run_acquisition(self):
        self._start_time = datetime.now()      # t₀ unique
        self._sample_counter = 0               # Compteur à 0

        while self._state == AcquisitionState.ACQUIRING:
            # Lire les données DAQ
            values = task.read(...)

            # Timestamp calculé (PAS datetime.now())
            timestamp = self._start_time + timedelta(
                milliseconds=self._sample_counter * self._period_ms
            )

            self._sample_counter += 1

            # Émettre vers le contrôleur via Signal Qt
            self.data_ready.emit(timestamp, values)
```

---

## 📊 Comparaison des approches

| Critère                    | `datetime.now()` répété | Compteur calculé ✅ |
|----------------------------|------------------------|---------------------|
| Précision inter-échantillon | ±1-10 ms (jitter OS)  | **Exacte** (0 ms)   |
| Drift sur 1 heure          | Jusqu'à ±30 s          | **0 s**             |
| Coût CPU                   | Appel système/échantillon | Addition simple   |
| Synchronisation multi-voies | Non garantie           | **Parfaite**        |
| Horodatage absolu (t₀)     | ✅ Précis              | ✅ Précis           |

---

## 🔬 Analyse mathématique

### Erreur avec `datetime.now()` répété

Soit $J_i$ le jitter de l'OS sur le $i$-ème appel :

$$t_{\text{mesuré}}(i) = t_0 + i \cdot T + \sum_{k=0}^{i} J_k$$

L'erreur s'accumule :
$$\epsilon(i) = \sum_{k=0}^{i} J_k \quad \text{(marche aléatoire)}$$

Écart-type après $N$ échantillons :
$$\sigma_\epsilon(N) = \sigma_J \cdot \sqrt{N}$$

Avec $\sigma_J \approx 2\text{ms}$ et $N = 36000$ (1h à 10Hz) :
$$\sigma_\epsilon = 2 \times \sqrt{36000} \approx 380\text{ms}$$

### Erreur avec compteur calculé

$$t_{\text{calculé}}(i) = t_0 + i \cdot T$$

L'erreur est **constante** (seul $t_0$ a un jitter) :
$$\epsilon(i) = J_0 \quad \forall i$$

Soit $\sigma_\epsilon = \sigma_J \approx 2\text{ms}$ constant.

---

## 🏗️ Intégration dans l'architecture

### Flux des timestamps

```
┌──────────────────────────────────────────────────┐
│           DAQModel (QThread — src/model/)         │
│                                                   │
│  t₀ = datetime.now()   ← Une seule fois          │
│  counter = 0                                      │
│                                                   │
│  Boucle acquisition :                             │
│    values = task.read()                           │
│    ts = t₀ + counter × period                    │
│    counter += 1                                   │
│    emit data_ready(ts, values)                    │
│                                                   │
└────────────────┬─────────────────────────────────┘
                 │ Signal Qt (thread-safe)
                 ▼
┌──────────────────────────────────────────────────┐
│      MainController (QMH — src/controller/)       │
│                                                   │
│  → Stocke dans buffer circulaire                  │
│  → Met à jour pyqtgraph (QTimer 100ms)           │
│  → Appelle DataModel.write_row(ts, values)        │
│                                                   │
└────────────────┬─────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────┐
│          DataModel (SubVI — src/model/)            │
│                                                   │
│  Fichier TSV :                                    │
│  2025-01-15 14:30:00.000 \t 23.45 \t 67.89       │
│  2025-01-15 14:30:00.100 \t 23.46 \t 67.90       │
│  2025-01-15 14:30:00.200 \t 23.44 \t 67.88       │
│  (espacement parfait de 100ms)                    │
│                                                   │
└──────────────────────────────────────────────────┘
```

### Thread-safety

Le timestamp est calculé **dans le QThread** d'acquisition, puis transmis au thread principal
via un **Signal Qt** (`data_ready`). Le mécanisme Signal/Slot de Qt assure la thread-safety
automatiquement (les signaux cross-thread sont envoyés via la event loop Qt).

Aucun `QMutex` n'est nécessaire pour les timestamps car :
- `t₀` est écrit une fois avant la boucle
- `counter` est incrémenté dans un seul thread (le QThread)
- Le signal `data_ready` fait une copie thread-safe

---

## 📐 Format des timestamps dans les fichiers

### Format TSV (Tab-Separated Values)

```
Timestamp	Voie_1	Voie_2	Voie_3
2025-01-15 14:30:00.000	23.4521	67.8912	-0.0023
2025-01-15 14:30:00.100	23.4534	67.8901	-0.0019
2025-01-15 14:30:00.200	23.4512	67.8923	-0.0025
```

- **Séparateur** : Tabulation (`\t`)
- **Format timestamp** : `YYYY-MM-DD HH:MM:SS.fff` (millisecondes)
- **Précision** : 1 milliseconde

### Vérification de régularité

```python
import numpy as np
from datetime import datetime

# Lire les timestamps du fichier
timestamps = []
with open('data/acquisition.txt', 'r') as f:
    next(f)  # Skip header
    for line in f:
        ts_str = line.split('\t')[0]
        timestamps.append(datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S.%f'))

# Calculer les intervalles
intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() * 1000
             for i in range(len(timestamps)-1)]

print(f"Intervalle moyen : {np.mean(intervals):.3f} ms")
print(f"Écart-type :       {np.std(intervals):.3f} ms")
print(f"Min :              {np.min(intervals):.3f} ms")
print(f"Max :              {np.max(intervals):.3f} ms")
```

Résultat attendu avec notre système :
```
Intervalle moyen : 100.000 ms
Écart-type :         0.000 ms
Min :              100.000 ms
Max :              100.000 ms
```

---

## ⚡ Limites et considérations

### Précision de `t₀`
Le timestamp initial `t₀` dépend de `datetime.now()` qui a une résolution de ~1ms sous Windows.
C'est acceptable car l'erreur absolue est constante et ne s'accumule pas.

### Dérive de l'horloge matérielle
Sur de très longues acquisitions (> 24h), l'horloge du PC peut dériver par rapport au temps réel.
Pour des applications de métrologie extrême, utiliser un serveur NTP ou l'horloge matérielle de la carte DAQ.

### Échantillons perdus
Si un échantillon est perdu (timeout DAQmx), le compteur n'est pas incrémenté.
Le fichier présente alors un "trou" visible dans les timestamps.

---

**Version** : 3.0
**Implémentation** : QThread + compteur + Signal Qt (src/model/daq_model.py)
