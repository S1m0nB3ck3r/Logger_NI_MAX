"""
MainView — Interface graphique PySide6 + pyqtgraph.

Rôle : affichage uniquement, aucune logique métier.
Émet des signaux Qt pour communiquer avec le Controller.

Équivalent LabVIEW : Front Panel
    - Les contrôles (boutons, combobox, entries) → événements vers l'Event Structure
    - Les indicateurs (graphiques, labels) → mis à jour par le diagramme
    - Aucune logique dans le Front Panel lui-même

Communication :
    View → Controller : Signaux Qt (start_requested, stop_requested, etc.)
    Controller → View : Appels directs de méthodes (set_status, update_plot, etc.)
"""

import os
import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QLineEdit, QTabWidget, QCheckBox, QFileDialog, QDialog,
    QFrame, QGridLayout, QSizePolicy, QApplication,
)
from PySide6.QtGui import QFont, QCloseEvent


# ═══════════════════════════════════════════════════════════════
# Constantes de thème (Catppuccin Mocha)
# ═══════════════════════════════════════════════════════════════

COLORS = {
    "bg_dark":       "#1e1e2e",
    "bg_medium":     "#2b2b3c",
    "bg_light":      "#363654",
    "accent_blue":   "#89b4fa",
    "accent_green":  "#a6e3a1",
    "accent_red":    "#f38ba8",
    "accent_yellow": "#f9e2af",
    "accent_purple": "#cba6f7",
    "text_white":    "#cdd6f4",
    "text_gray":     "#a6adc8",
    "plot_bg":       "#1a1a2e",
    "border":        "#45475a",
}

CHANNEL_COLORS = [
    "#89b4fa",   # Bleu
    "#cba6f7",   # Violet
    "#a6e3a1",   # Vert
    "#f9e2af",   # Jaune
    "#f38ba8",   # Rouge
    "#ff6b9d",   # Rose
    "#00d4ff",   # Cyan
    "#ffaa00",   # Orange
]

# Configuration globale pyqtgraph
pg.setConfigOptions(antialias=True)


class MainView(QMainWindow):
    """
    Interface graphique principale — PySide6 + pyqtgraph.

    Rôle : affichage uniquement. Aucune logique métier.
    Émet des signaux Qt pour communiquer avec le Controller.

    Équivalent LabVIEW : Front Panel
        - Contrôles → génèrent des événements (Signal)
        - Indicateurs → mis à jour par le Controller (méthodes set_*/update_*)
    """

    # ─── Signaux émis vers le Controller ───
    # Équiv. LabVIEW : événements du Front Panel détectés par l'Event Structure
    start_requested  = Signal()        # Clic sur "Démarrer"
    stop_requested   = Signal()        # Clic sur "Arrêter"
    task_changed     = Signal(str)     # Sélection d'une nouvelle tâche
    period_changed   = Signal(int)     # Changement de la période
    quit_requested   = Signal()        # Clic "Quitter" ou fermeture fenêtre

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._force_close = False

        # Courbes pyqtgraph (créées dynamiquement par setup_plot_channels)
        self._instant_curves: list[pg.PlotDataItem] = []
        self._longduration_curves: list[pg.PlotDataItem] = []

        # Construction de l'interface
        self._setup_window()
        self._build_ui()
        self._apply_stylesheet()
        self._connect_internal_signals()

    # ═══════════════════════════════════════════════════════════════
    # Configuration de la fenêtre
    # ═══════════════════════════════════════════════════════════════

    def _setup_window(self):
        self.setWindowTitle("🧪 Logger NI")
        self.resize(1400, 800)
        self.setMinimumSize(1000, 600)

    # ═══════════════════════════════════════════════════════════════
    # Construction de l'interface (équiv. LabVIEW : placement des contrôles)
    # ═══════════════════════════════════════════════════════════════

    def _build_ui(self):
        """Construit toute l'interface graphique."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(8)

        # ── Titre ──
        title = QLabel("🧪 LOGGER NI")
        title.setObjectName("title_label")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # ── Séparateur bleu ──
        main_layout.addWidget(self._create_separator("separator_blue"))

        # ── Corps : Left Panel + Right Panel ──
        body = QHBoxLayout()
        body.setSpacing(12)
        self._build_left_panel(body)
        self._build_right_panel(body)
        main_layout.addLayout(body, stretch=1)

    # ─── Panneau gauche (Configuration + Contrôles + Info) ───

    def _build_left_panel(self, parent_layout: QHBoxLayout):
        """Panneau gauche fixe (280px) : configuration, contrôles, info."""
        panel = QWidget()
        panel.setObjectName("left_panel")
        panel.setFixedWidth(280)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Section Configuration
        self._build_config_section(layout)

        # Séparateur violet
        layout.addWidget(self._create_separator("separator_purple"))

        # Section Contrôles
        self._build_controls_section(layout)

        # Espacement flexible
        layout.addStretch(1)

        # Section Info (bas du panneau)
        self._build_info_section(layout)

        parent_layout.addWidget(panel)

    def _build_config_section(self, parent_layout: QVBoxLayout):
        """Section ⚙️ CONFIGURATION."""
        # Titre de section
        lbl = QLabel("⚙️ CONFIGURATION")
        lbl.setObjectName("section_config")
        parent_layout.addWidget(lbl)

        # Cadre de configuration
        frame = QWidget()
        frame.setObjectName("config_frame")
        form = QVBoxLayout(frame)
        form.setContentsMargins(10, 10, 10, 10)
        form.setSpacing(6)

        # 📋 Tâche DAQmx
        form.addWidget(self._field_label("📋 Tâche DAQmx"))
        self.task_combo = QComboBox()
        self.task_combo.setObjectName("task_combo")
        form.addWidget(self.task_combo)

        # ⏱️ Période d'enregistrement
        form.addWidget(self._field_label("⏱️ Période d'enregistrement (s)"))
        period_row = QHBoxLayout()
        self.period_spinbox = QSpinBox()
        self.period_spinbox.setRange(0, 3600)
        self.period_spinbox.setValue(60)
        self.period_spinbox.setToolTip("0 = chaque échantillon")
        period_row.addWidget(self.period_spinbox, stretch=1)
        hint = QLabel("(0 = chaque éch.)")
        hint.setObjectName("info_detail")
        period_row.addWidget(hint)
        form.addLayout(period_row)

        # 📁 Préfixe nom fichier
        form.addWidget(self._field_label("📁 Préfixe nom fichier"))
        self.prefix_edit = QLineEdit("data")
        form.addWidget(self.prefix_edit)

        # 📂 Répertoire d'enregistrement
        form.addWidget(self._field_label("📂 Répertoire d'enregistrement"))
        dir_row = QHBoxLayout()
        self.directory_edit = QLineEdit("data")
        dir_row.addWidget(self.directory_edit, stretch=1)
        self.btn_browse = QPushButton("📁")
        self.btn_browse.setObjectName("btn_browse")
        self.btn_browse.setFixedWidth(36)
        dir_row.addWidget(self.btn_browse)
        form.addLayout(dir_row)

        # 💬 Commentaire
        form.addWidget(self._field_label("💬 Commentaire"))
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("Commentaire optionnel...")
        form.addWidget(self.comment_edit)

        parent_layout.addWidget(frame)

    def _build_controls_section(self, parent_layout: QVBoxLayout):
        """Section 🎮 CONTRÔLES."""
        lbl = QLabel("🎮 CONTRÔLES")
        lbl.setObjectName("section_controls")
        parent_layout.addWidget(lbl)

        # Bouton Démarrer
        self.btn_start = QPushButton("▶  Démarrer")
        self.btn_start.setObjectName("btn_start")
        parent_layout.addWidget(self.btn_start)

        # Bouton Arrêter
        self.btn_stop = QPushButton("◼  Arrêter enregistrement")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setEnabled(False)
        parent_layout.addWidget(self.btn_stop)

        # Espacement
        parent_layout.addSpacing(16)

        # Bouton Quitter
        self.btn_quit = QPushButton("✕  Quitter [Echap]")
        self.btn_quit.setObjectName("btn_quit")
        parent_layout.addWidget(self.btn_quit)

        # Bouton À propos
        self.btn_about = QPushButton("ℹ  À propos")
        self.btn_about.setObjectName("btn_about")
        parent_layout.addWidget(self.btn_about)

    def _build_info_section(self, parent_layout: QVBoxLayout):
        """Section info en bas du panneau gauche."""
        frame = QWidget()
        frame.setObjectName("info_frame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        lbl_title = QLabel("🔌 Périphérique")
        lbl_title.setObjectName("field_label")
        layout.addWidget(lbl_title)

        lbl_detail = QLabel("Configuré via NI MAX")
        lbl_detail.setObjectName("info_detail")
        layout.addWidget(lbl_detail)

        lbl_rate = QLabel(f"📡 {self.config.SAMPLE_RATE} Hz")
        lbl_rate.setObjectName("info_detail")
        layout.addWidget(lbl_rate)

        parent_layout.addWidget(frame)

    # ─── Panneau droit (Graphiques + Barre de statut) ───

    def _build_right_panel(self, parent_layout: QHBoxLayout):
        """Panneau droit extensible : onglets graphiques + barre de statut."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Onglets de graphiques ──
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("plot_tabs")

        # Tab 1 : Graphique instantané (pyqtgraph)
        self.instant_plot = self._create_plot_widget("Graphique Instantané (60s)")
        self.tab_widget.addTab(self.instant_plot, "📈 Graphique Instantané")

        # Tab 2 : Graphique longue durée (pyqtgraph)
        self.longduration_plot = self._create_plot_widget("Graphique Longue Durée")
        self.tab_widget.addTab(self.longduration_plot, "📊 Graphique Longue Durée")

        layout.addWidget(self.tab_widget, stretch=1)

        # ── Barre de statut ──
        self._build_status_bar(layout)

        parent_layout.addWidget(panel, stretch=1)

    def _create_plot_widget(self, title: str) -> pg.PlotWidget:
        """
        Crée un PlotWidget pyqtgraph stylisé.

        Équiv. LabVIEW : Waveform Chart avec configuration d'apparence
        """
        pw = pg.PlotWidget()
        pw.setBackground(COLORS["plot_bg"])
        pw.showGrid(x=True, y=True, alpha=0.15)
        pw.setLabel('left', 'Tension (V)', color=COLORS["text_gray"])
        pw.setLabel('bottom', 'Temps (s)', color=COLORS["text_gray"])

        # Style des axes
        for axis_name in ('left', 'bottom'):
            axis = pw.getAxis(axis_name)
            axis.setTextPen(COLORS["text_gray"])
            axis.setPen(pg.mkPen(color=COLORS["border"], width=1))

        # Légende
        legend = pw.addLegend(offset=(10, 10))
        legend.setBrush(pg.mkBrush(43, 43, 60, 180))
        legend.setPen(pg.mkPen(color=COLORS["border"]))

        return pw

    def _build_status_bar(self, parent_layout: QVBoxLayout):
        """Barre de statut en bas : statut, buffer, temps, échelle."""
        bar = QWidget()
        bar.setObjectName("status_bar")
        bar.setFixedHeight(70)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(20)

        # ── Statut ──
        col_status = QVBoxLayout()
        col_status.addWidget(self._field_label("⚡ Statut"))
        self.status_label = QLabel("● Prêt")
        self.status_label.setObjectName("status_value")
        self.status_label.setStyleSheet(f"color: {COLORS['accent_blue']};")
        col_status.addWidget(self.status_label)
        layout.addLayout(col_status)

        # ── Buffer ──
        col_buffer = QVBoxLayout()
        col_buffer.addWidget(self._field_label("📊 Buffer disponible"))
        self.buffer_label = QLabel("0")
        self.buffer_label.setObjectName("buffer_value")
        col_buffer.addWidget(self.buffer_label)
        layout.addLayout(col_buffer)

        # ── Temps écoulé ──
        col_elapsed = QVBoxLayout()
        col_elapsed.addWidget(self._field_label("⏱️ Temps écoulé"))
        self.elapsed_label = QLabel("00:00:00")
        self.elapsed_label.setObjectName("elapsed_value")
        col_elapsed.addWidget(self.elapsed_label)
        layout.addLayout(col_elapsed)

        # ── Espacement flexible ──
        layout.addStretch(1)

        # ── Contrôles d'échelle Y ──
        scale_layout = QHBoxLayout()
        scale_layout.setSpacing(6)

        self.auto_scale_checkbox = QCheckBox("Échelle auto")
        self.auto_scale_checkbox.setChecked(True)
        scale_layout.addWidget(self.auto_scale_checkbox)

        scale_layout.addWidget(QLabel("Min:"))
        self.min_spinbox = QDoubleSpinBox()
        self.min_spinbox.setRange(-1000, 1000)
        self.min_spinbox.setValue(-10.0)
        self.min_spinbox.setSingleStep(0.5)
        self.min_spinbox.setFixedWidth(75)
        self.min_spinbox.setEnabled(False)
        scale_layout.addWidget(self.min_spinbox)

        scale_layout.addWidget(QLabel("Max:"))
        self.max_spinbox = QDoubleSpinBox()
        self.max_spinbox.setRange(-1000, 1000)
        self.max_spinbox.setValue(10.0)
        self.max_spinbox.setSingleStep(0.5)
        self.max_spinbox.setFixedWidth(75)
        self.max_spinbox.setEnabled(False)
        scale_layout.addWidget(self.max_spinbox)

        layout.addLayout(scale_layout)
        parent_layout.addWidget(bar)

    # ─── Utilitaires de construction ───

    def _field_label(self, text: str) -> QLabel:
        """Crée un label de champ (style secondaire)."""
        lbl = QLabel(text)
        lbl.setObjectName("field_label")
        return lbl

    def _create_separator(self, object_name: str, height: int = 2) -> QFrame:
        """Crée une ligne de séparation horizontale."""
        sep = QFrame()
        sep.setObjectName(object_name)
        sep.setFixedHeight(height)
        sep.setFrameShape(QFrame.HLine)
        return sep

    # ═══════════════════════════════════════════════════════════════
    # Stylesheet (chargement du QSS)
    # ═══════════════════════════════════════════════════════════════

    def _apply_stylesheet(self):
        """Charge et applique le thème QSS Catppuccin."""
        qss_path = os.path.join(os.path.dirname(__file__), "style.qss")
        try:
            with open(qss_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print(f"[View] style.qss non trouvé : {qss_path}")

    # ═══════════════════════════════════════════════════════════════
    # Connexions internes (signaux widgets → signaux publics)
    # Équiv. LabVIEW : câblage des terminaux de contrôle vers l'Event Structure
    # ═══════════════════════════════════════════════════════════════

    def _connect_internal_signals(self):
        """Connecte les signaux des widgets aux signaux publics de la View."""
        # Boutons
        self.btn_start.clicked.connect(self.start_requested.emit)
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        self.btn_quit.clicked.connect(self._on_quit_clicked)
        self.btn_about.clicked.connect(self._show_about)
        self.btn_browse.clicked.connect(self._on_browse_directory)

        # ComboBox (tâche) — currentTextChanged émet task_changed(str)
        self.task_combo.currentTextChanged.connect(
            lambda text: self.task_changed.emit(text) if text else None
        )

        # Spinbox (période) — valueChanged émet period_changed(int)
        self.period_spinbox.valueChanged.connect(self.period_changed.emit)

        # Échelle Y (interne à la View, pas de signal vers le Controller)
        self.auto_scale_checkbox.toggled.connect(self._on_auto_scale_changed)
        self.min_spinbox.valueChanged.connect(self._apply_manual_scale)
        self.max_spinbox.valueChanged.connect(self._apply_manual_scale)

    # ═══════════════════════════════════════════════════════════════
    # Getters (lecture des valeurs des contrôles)
    # Équiv. LabVIEW : lire la valeur d'un contrôle du Front Panel
    # ═══════════════════════════════════════════════════════════════

    def get_task_name(self) -> str:
        return self.task_combo.currentText()

    def get_period(self) -> int:
        return self.period_spinbox.value()

    def get_prefix(self) -> str:
        return self.prefix_edit.text()

    def get_directory(self) -> str:
        return self.directory_edit.text()

    def get_comment(self) -> str:
        return self.comment_edit.text()

    # ═══════════════════════════════════════════════════════════════
    # Setters (mise à jour des contrôles depuis le Controller)
    # Équiv. LabVIEW : écrire dans un contrôle/indicateur via Property Node
    # ═══════════════════════════════════════════════════════════════

    def set_task_list(self, tasks: list[str]):
        """Remplit le combobox avec les tâches NI MAX disponibles."""
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItems(tasks)
        self.task_combo.blockSignals(False)

    def set_task(self, name: str):
        """Sélectionne une tâche dans le combobox (sans émettre de signal)."""
        self.task_combo.blockSignals(True)
        idx = self.task_combo.findText(name)
        if idx >= 0:
            self.task_combo.setCurrentIndex(idx)
        self.task_combo.blockSignals(False)

    def set_period(self, value: int):
        """Définit la période d'enregistrement (sans émettre de signal)."""
        self.period_spinbox.blockSignals(True)
        self.period_spinbox.setValue(value)
        self.period_spinbox.blockSignals(False)

    def set_prefix(self, text: str):
        self.prefix_edit.setText(text)

    def set_directory(self, path: str):
        self.directory_edit.setText(path)

    def set_comment(self, text: str):
        self.comment_edit.setText(text)

    # ═══════════════════════════════════════════════════════════════
    # Mise à jour des graphiques
    # Équiv. LabVIEW : Waveform Chart → Update Value
    # ═══════════════════════════════════════════════════════════════

    def setup_plot_channels(self, channel_names: list[str]):
        """
        Configure les courbes pour les canaux détectés.
        Appelé quand la tâche DAQ est configurée.

        Équiv. LabVIEW : configurer le nombre de plots dans un Waveform Chart
        """
        # Supprimer les anciennes courbes
        for curve in self._instant_curves:
            self.instant_plot.removeItem(curve)
        for curve in self._longduration_curves:
            self.longduration_plot.removeItem(curve)

        self._instant_curves = []
        self._longduration_curves = []

        # Nettoyer les légendes
        for pw in (self.instant_plot, self.longduration_plot):
            pi = pw.getPlotItem()
            if pi.legend is not None:
                pi.legend.clear()

        # Créer les nouvelles courbes
        for i, name in enumerate(channel_names):
            color = CHANNEL_COLORS[i % len(CHANNEL_COLORS)]
            pen = pg.mkPen(color=color, width=2)

            c1 = self.instant_plot.plot([], [], pen=pen, name=name)
            self._instant_curves.append(c1)

            c2 = self.longduration_plot.plot([], [], pen=pen, name=name)
            self._longduration_curves.append(c2)

    def update_instant_plot(self, timestamps: list[float], data: np.ndarray):
        """
        Met à jour le graphique instantané (fenêtre glissante 60s).

        Args:
            timestamps: liste de temps en secondes
            data: np.ndarray shape (n_channels, n_samples)
        """
        if data.size == 0:
            return

        x = np.array(timestamps)
        for i, curve in enumerate(self._instant_curves):
            if i < data.shape[0]:
                curve.setData(x, data[i])

        # Auto-scale Y si activé
        if self.auto_scale_checkbox.isChecked():
            self.instant_plot.enableAutoRange(axis='y')
        else:
            self.instant_plot.disableAutoRange(axis='y')

    def update_longduration_plot(self, timestamps: list[float], data: np.ndarray):
        """Met à jour le graphique longue durée."""
        if data.size == 0:
            return

        x = np.array(timestamps)
        for i, curve in enumerate(self._longduration_curves):
            if i < data.shape[0]:
                curve.setData(x, data[i])

        if self.auto_scale_checkbox.isChecked():
            self.longduration_plot.enableAutoRange(axis='y')
        else:
            self.longduration_plot.disableAutoRange(axis='y')

    # ═══════════════════════════════════════════════════════════════
    # Mise à jour des indicateurs
    # ═══════════════════════════════════════════════════════════════

    def set_status(self, text: str, level: str = "info"):
        """
        Met à jour l'indicateur de statut (texte + couleur automatique).

        Le Controller envoie un niveau sémantique, la View choisit la couleur.
        C'est la View qui maîtrise la présentation (conformité MVC).

        Args:
            text: Texte à afficher
            level: Niveau sémantique — "info", "warning", "recording",
                   "error", "stopped". Détermine la couleur.
        """
        level_colors = {
            "info":      COLORS["accent_blue"],
            "warning":   COLORS["accent_yellow"],
            "recording": COLORS["accent_red"],
            "error":     COLORS["accent_red"],
            "stopped":   COLORS["text_gray"],
        }
        color = level_colors.get(level, COLORS["text_white"])
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def show_error(self, title: str, message: str):
        """
        Affiche une boîte de dialogue d'erreur.

        C'est la View qui crée les widgets UI (conformité MVC).
        Le Controller appelle cette méthode sans manipuler de widget.
        """
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, title, message)

    def set_buffer_info(self, text: str):
        """Met à jour l'indicateur de buffer disponible."""
        self.buffer_label.setText(text)

    def set_elapsed_time(self, text: str):
        """Met à jour l'indicateur de temps écoulé."""
        self.elapsed_label.setText(text)

    def set_recording_state(self, recording: bool):
        """Bascule l'état visuel entre enregistrement et arrêté."""
        self.btn_start.setEnabled(not recording)
        self.btn_stop.setEnabled(recording)

    def set_controls_enabled(self, enabled: bool):
        """Active/désactive les contrôles de configuration pendant l'enregistrement."""
        self.task_combo.setEnabled(enabled)
        self.prefix_edit.setEnabled(enabled)
        self.directory_edit.setEnabled(enabled)
        self.btn_browse.setEnabled(enabled)
        self.comment_edit.setEnabled(enabled)
        # Note : le spinbox de période reste toujours actif (modifiable en cours)

    def show_recording_result(self, filepath: str, count: int):
        """Affiche un dialogue avec le résumé de l'enregistrement."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Enregistrement terminé")
        dialog.setFixedSize(500, 200)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("✅ Enregistrement terminé"))

        info = QLabel(
            f"📁 Fichier : {filepath}\n"
            f"📊 Échantillons enregistrés : {count}"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        btn_ok = QPushButton("✓ Fermer")
        btn_ok.setObjectName("btn_start")  # Réutilise le style vert
        btn_ok.clicked.connect(dialog.accept)
        layout.addWidget(btn_ok, alignment=Qt.AlignCenter)

        dialog.exec()

    # ═══════════════════════════════════════════════════════════════
    # Handlers internes (pas de logique métier — juste du UI)
    # ═══════════════════════════════════════════════════════════════

    def _on_auto_scale_changed(self, checked: bool):
        """Bascule entre échelle automatique et manuelle."""
        self.min_spinbox.setEnabled(not checked)
        self.max_spinbox.setEnabled(not checked)

        if checked:
            self.instant_plot.enableAutoRange(axis='y')
            self.longduration_plot.enableAutoRange(axis='y')
        else:
            self._apply_manual_scale()

    def _apply_manual_scale(self):
        """Applique l'échelle Y manuelle aux deux graphiques."""
        if self.auto_scale_checkbox.isChecked():
            return
        y_min = self.min_spinbox.value()
        y_max = self.max_spinbox.value()
        if y_min >= y_max:
            return  # Valeurs invalides
        self.instant_plot.setYRange(y_min, y_max, padding=0)
        self.longduration_plot.setYRange(y_min, y_max, padding=0)

    def _on_browse_directory(self):
        """Ouvre le sélecteur de dossier."""
        current = self.directory_edit.text()
        directory = QFileDialog.getExistingDirectory(
            self, "Sélectionner le répertoire d'enregistrement", current
        )
        if directory:
            self.directory_edit.setText(directory)

    def _on_quit_clicked(self):
        """Clic sur le bouton Quitter."""
        if self._confirm_quit():
            self.quit_requested.emit()

    def _confirm_quit(self) -> bool:
        """Dialogue de confirmation de fermeture."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Quitter")
        dialog.setFixedSize(400, 180)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(QLabel("⚠️ Êtes-vous sûr de vouloir quitter ?"))

        btn_layout = QHBoxLayout()
        btn_yes = QPushButton("✓ Oui, quitter")
        btn_yes.setObjectName("btn_stop")  # Style rouge
        btn_yes.clicked.connect(dialog.accept)
        btn_layout.addWidget(btn_yes)

        btn_no = QPushButton("✕ Non, rester")
        btn_no.setObjectName("btn_start")  # Style vert
        btn_no.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_no)

        layout.addLayout(btn_layout)

        return dialog.exec() == QDialog.Accepted

    def _show_about(self):
        """Dialogue À propos."""
        dialog = QDialog(self)
        dialog.setWindowTitle("À propos")
        dialog.setFixedSize(500, 380)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Titre
        title = QLabel("🧪 Logger NI")
        title.setStyleSheet(f"color: {COLORS['accent_blue']}; font-size: 20pt; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        version = QLabel("Version 2.5 • PySide6 Edition")
        version.setStyleSheet(f"color: {COLORS['text_gray']};")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(8)

        # Table d'informations
        info_data = [
            ("Architecture", "MVC + QMH + State Machine"),
            ("Framework UI", "PySide6 (Qt 6)"),
            ("Graphiques", "pyqtgraph (temps réel)"),
            ("DAQ", "NI-DAQmx (National Instruments)"),
            ("Langage", "Python 3.10+"),
            ("Design Pattern", "LabVIEW-inspired QMH"),
        ]
        grid = QGridLayout()
        grid.setSpacing(4)
        for row, (key, val) in enumerate(info_data):
            lbl_key = QLabel(f"  {key}")
            lbl_key.setStyleSheet(f"color: {COLORS['accent_purple']};")
            grid.addWidget(lbl_key, row, 0)
            grid.addWidget(QLabel(f":  {val}"), row, 1)
        layout.addLayout(grid)

        layout.addStretch(1)

        # Bouton Fermer
        btn_close = QPushButton("✓ Fermer")
        btn_close.setObjectName("btn_start")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignCenter)

        dialog.exec()

    # ═══════════════════════════════════════════════════════════════
    # Événements fenêtre
    # ═══════════════════════════════════════════════════════════════

    def closeEvent(self, event: QCloseEvent):
        """
        Interception de la fermeture de la fenêtre (clic ✕).
        Demande confirmation, puis délègue au Controller.

        Équiv. LabVIEW : Event "Panel Close?" → Discard event + demander à l'utilisateur
        """
        if self._force_close:
            event.accept()
            return
        event.ignore()
        if self._confirm_quit():
            self.quit_requested.emit()

    def keyPressEvent(self, event):
        """Raccourci Echap pour quitter."""
        if event.key() == Qt.Key_Escape:
            if self._confirm_quit():
                self.quit_requested.emit()
        else:
            super().keyPressEvent(event)

    def force_close(self):
        """Fermeture forcée (appelée par le Controller après nettoyage)."""
        self._force_close = True
        self.close()
