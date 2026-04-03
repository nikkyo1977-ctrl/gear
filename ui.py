import sys
import os
import math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QFormLayout,
    QGroupBox, QSplitter, QMessageBox, QFileDialog, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QAction, QKeySequence

import numpy as np
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from gears import (
    create_spur_gear, create_helical_gear, create_rack_gear, create_worm_zi,
    list_materials, get_material,
    calculate_lewis_bending, calculate_hertz_contact, tangential_force_from_power,
    calculate_gear_pair, pair_from_center_distance,
    save_project, load_project,
    iso1328_tolerances,
    list_presets, get_preset,
    gear_profile_points, rack_profile_points, export_svg, export_dxf,
)
from gears.involute import calculate_gear_parameters
from gears import report as rpt


class GearApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Gear Generator Pro")
        self.resize(1280, 860)
        self.current_part  = None
        self._gear2_part   = None          # seconda ruota coppia (3D)
        self._pair_aw      = None          # interasse di lavoro coppia
        self._2d_points    = None          # profilo 2D ruota 1 per SVG/DXF
        self._2d_points2   = None          # profilo 2D ruota 2 per vista 2D
        self._2d_shaft     = 0.0           # diametro foro albero per export 2D
        self.last_results  = None          # ultimi risultati calcolati
        self._undo_stack = []             # stack undo (max 20)
        self._redo_stack = []             # stack redo
        self._init_menu()
        self._init_ui()

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------
    def _init_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")

        act_new = QAction("Nuovo progetto", self)
        act_new.setShortcut(QKeySequence("Ctrl+N"))
        act_new.triggered.connect(self._new_project)
        file_menu.addAction(act_new)

        act_open = QAction("Apri progetto…", self)
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self._open_project)
        file_menu.addAction(act_open)

        act_save = QAction("Salva progetto…", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self._save_project)
        file_menu.addAction(act_save)

        file_menu.addSeparator()

        act_quit = QAction("Esci", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        edit_menu = menu_bar.addMenu("Modifica")

        act_undo = QAction("Annulla", self)
        act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        act_undo.triggered.connect(self._undo)
        edit_menu.addAction(act_undo)

        act_redo = QAction("Ripeti", self)
        act_redo.setShortcut(QKeySequence("Ctrl+Y"))
        act_redo.triggered.connect(self._redo)
        edit_menu.addAction(act_redo)

    # ------------------------------------------------------------------
    # Layout principale
    # ------------------------------------------------------------------
    def _init_ui(self):
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # ---------- Pannello sinistro ----------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(6, 6, 6, 6)

        # Preset
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:"))
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(list_presets())
        self.combo_preset.currentTextChanged.connect(self._apply_preset)
        preset_row.addWidget(self.combo_preset, 1)
        left_layout.addLayout(preset_row)

        # Tab ingranaggi
        self.tabs = QTabWidget()
        left_layout.addWidget(self.tabs, 1)

        self._setup_spur_tab()
        self._setup_helical_tab()
        self._setup_rack_tab()
        self._setup_worm_tab()

        # Pulsanti azione
        btn_calc = QPushButton("CALCOLA GEOMETRIA E MOSTRA 3D")
        btn_calc.setStyleSheet("background-color:#3498db;color:white;font-weight:bold;padding:10px;")
        btn_calc.clicked.connect(self.generate_gear)
        left_layout.addWidget(btn_calc)

        btn_row = QHBoxLayout()
        self.btn_export_stp = QPushButton("ESPORTA .STP")
        self.btn_export_stp.setStyleSheet("background-color:#2ecc71;color:white;font-weight:bold;padding:8px;")
        self.btn_export_stp.clicked.connect(self.export_step)

        self.btn_export_pdf = QPushButton("ESPORTA PDF")
        self.btn_export_pdf.setStyleSheet("background-color:#e67e22;color:white;font-weight:bold;padding:8px;")
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.btn_export_pdf.setEnabled(False)

        self.btn_export_csv = QPushButton("ESPORTA CSV")
        self.btn_export_csv.setStyleSheet("background-color:#8e44ad;color:white;font-weight:bold;padding:8px;")
        self.btn_export_csv.clicked.connect(self._export_csv)
        self.btn_export_csv.setEnabled(False)

        btn_row.addWidget(self.btn_export_stp)
        btn_row.addWidget(self.btn_export_pdf)
        btn_row.addWidget(self.btn_export_csv)
        left_layout.addLayout(btn_row)

        btn_row2 = QHBoxLayout()
        self.btn_export_svg = QPushButton("ESPORTA SVG")
        self.btn_export_svg.setStyleSheet("background-color:#16a085;color:white;font-weight:bold;padding:8px;")
        self.btn_export_svg.clicked.connect(self._export_svg)
        self.btn_export_svg.setEnabled(False)

        self.btn_export_dxf = QPushButton("ESPORTA DXF")
        self.btn_export_dxf.setStyleSheet("background-color:#2c3e50;color:white;font-weight:bold;padding:8px;")
        self.btn_export_dxf.clicked.connect(self._export_dxf)
        self.btn_export_dxf.setEnabled(False)

        btn_row2.addWidget(self.btn_export_svg)
        btn_row2.addWidget(self.btn_export_dxf)
        left_layout.addLayout(btn_row2)

        # ---------- Pannello destro ----------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)

        # 3D canvas
        self._fig = Figure(facecolor='#1a1a2e')
        self._canvas = FigureCanvas(self._fig)
        self._ax3d = self._fig.add_subplot(111, projection='3d')
        self._ax3d.set_facecolor('#1a1a2e')
        self._ax3d.set_title("Vista 3D", color='white', fontsize=9)

        # 2D profile canvas
        self._fig2d = Figure(facecolor='#1a1a2e')
        self._canvas2d = FigureCanvas(self._fig2d)
        self._ax2d = self._fig2d.add_subplot(111, aspect='equal')
        self._ax2d.set_facecolor('#0d1117')
        self._ax2d.set_title("Profilo 2D", color='white', fontsize=9)
        self._ax2d.tick_params(colors='#888', labelsize=6)
        for sp in self._ax2d.spines.values():
            sp.set_edgecolor('#333')

        view_split = QSplitter(Qt.Horizontal)
        view_split.addWidget(self._canvas)
        view_split.addWidget(self._canvas2d)
        right_layout.addWidget(view_split, 3)

        # Pannello risultati a tab
        self.result_tabs = QTabWidget()
        self.result_tabs.setMaximumHeight(260)

        self._tbl_geom = self._make_result_table(["Parametro", "Valore", "Unità"])
        self._tbl_pair = self._make_result_table(["Parametro", "Valore", "Unità"])
        self._tbl_str  = self._make_result_table(["Parametro", "Valore", "Unità"])

        self.result_tabs.addTab(self._tbl_geom, "Geometria")
        self.result_tabs.addTab(self._tbl_pair, "Coppia")
        self.result_tabs.addTab(self._tbl_str,  "Resistenza")

        right_layout.addWidget(self.result_tabs, 1)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([420, 860])

    # ------------------------------------------------------------------
    # Helper tabella risultati
    # ------------------------------------------------------------------
    @staticmethod
    def _make_result_table(headers):
        tbl = QTableWidget(0, len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        if len(headers) > 2:
            tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        return tbl

    def _fill_table(self, tbl, rows, color_col=None, color_fn=None):
        """
        rows: lista di tuple (parametro, valore, unità)
        color_col: indice colonna da colorare in base a color_fn(val) -> QColor
        """
        tbl.setRowCount(0)
        for row_data in rows:
            r = tbl.rowCount()
            tbl.insertRow(r)
            for c, val in enumerate(row_data):
                item = QTableWidgetItem(str(val))
                if c == 1:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if color_col is not None and c == color_col and color_fn:
                    try:
                        col = color_fn(float(str(val)))
                        item.setBackground(col)
                    except (ValueError, TypeError):
                        pass
                tbl.setItem(r, c, item)

    # ------------------------------------------------------------------
    # Tab setup
    # ------------------------------------------------------------------
    def _strength_group(self, prefix):
        """Crea il QGroupBox 'Analisi Resistenza' comune a tutti i tab."""
        grp = QGroupBox("Analisi Resistenza (opzionale)")
        form = QFormLayout()

        mat_combo = QComboBox()
        mat_combo.addItem("-- nessuno --")
        mat_combo.addItems(list_materials())
        setattr(self, f"{prefix}_mat", mat_combo)
        form.addRow("Materiale:", mat_combo)

        p_edit = QLineEdit("")
        p_edit.setPlaceholderText("es. 5.0")
        setattr(self, f"{prefix}_P", p_edit)
        form.addRow("Potenza P [kW]:", p_edit)

        n_edit = QLineEdit("")
        n_edit.setPlaceholderText("es. 1500")
        setattr(self, f"{prefix}_n", n_edit)
        form.addRow("Velocità n [rpm]:", n_edit)

        KA_edit = QLineEdit("1.25")
        setattr(self, f"{prefix}_KA", KA_edit)
        form.addRow("Fattore appl. KA:", KA_edit)

        z2_edit = QLineEdit("")
        z2_edit.setPlaceholderText("es. 40 (per analisi coppia)")
        setattr(self, f"{prefix}_z2", z2_edit)
        form.addRow("Denti ruota z₂:", z2_edit)

        x2_edit = QLineEdit("0.0")
        setattr(self, f"{prefix}_x2", x2_edit)
        form.addRow("Spost. ruota x₂:", x2_edit)

        aw_edit = QLineEdit("")
        aw_edit.setPlaceholderText("es. 62.5 (calcola x1,x2 automatici)")
        setattr(self, f"{prefix}_aw", aw_edit)
        form.addRow("Interasse imposto a_w [mm]:", aw_edit)

        grp.setLayout(form)
        return grp

    def _iso_grade_group(self, prefix):
        grp = QGroupBox("Tolleranze ISO 1328")
        form = QFormLayout()
        combo = QComboBox()
        combo.addItems([str(g) for g in range(3, 13)])
        combo.setCurrentText("6")
        setattr(self, f"{prefix}_grade", combo)
        form.addRow("Grado qualità:", combo)
        grp.setLayout(form)
        return grp

    def _setup_spur_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        grp_base = QGroupBox("Parametri Base (ISO)")
        form = QFormLayout()
        self.spur_m     = QLineEdit("2.0")
        self.spur_z     = QLineEdit("20")
        self.spur_w     = QLineEdit("10.0")
        self.spur_alpha = QLineEdit("20.0")
        form.addRow("Modulo (m) [mm]:", self.spur_m)
        form.addRow("Num. Denti (z):", self.spur_z)
        form.addRow("Fascia (b) [mm]:", self.spur_w)
        form.addRow("Angolo Pressione (α) [°]:", self.spur_alpha)
        grp_base.setLayout(form)

        grp_adv = QGroupBox("Parametri Avanzati")
        form2 = QFormLayout()
        self.spur_x = QLineEdit("0.0")
        self.spur_backlash = QLineEdit("0.0")
        self.spur_backlash.setPlaceholderText("gioco totale es. 0.05")
        self.spur_shaft_dia = QLineEdit("0.0")
        self.spur_shaft_dia.setPlaceholderText("0 = nessun foro")
        form2.addRow("Spost. Profilo (x):", self.spur_x)
        form2.addRow("Gioco (backlash) [mm]:", self.spur_backlash)
        form2.addRow("Ø foro albero [mm]:", self.spur_shaft_dia)
        grp_adv.setLayout(form2)

        layout.addWidget(grp_base)
        layout.addWidget(grp_adv)
        layout.addWidget(self._strength_group("spur"))
        layout.addWidget(self._iso_grade_group("spur"))
        layout.addStretch()

        scroll.setWidget(inner)
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.tabs.addTab(tab, "Denti Dritti")

    def _setup_helical_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        grp_base = QGroupBox("Parametri Base (ISO)")
        form = QFormLayout()
        self.hel_m    = QLineEdit("2.0")
        self.hel_z    = QLineEdit("20")
        self.hel_beta = QLineEdit("15.0")
        self.hel_w    = QLineEdit("15.0")
        self.hel_alpha = QLineEdit("20.0")
        form.addRow("Modulo Norm. (mn) [mm]:", self.hel_m)
        form.addRow("Num. Denti (z):", self.hel_z)
        form.addRow("Angolo Elica (β) [°]:", self.hel_beta)
        form.addRow("Fascia (b) [mm]:", self.hel_w)
        form.addRow("Angolo Pressione (α) [°]:", self.hel_alpha)
        grp_base.setLayout(form)

        grp_adv = QGroupBox("Parametri Avanzati")
        form2 = QFormLayout()
        self.hel_x = QLineEdit("0.0")
        self.hel_backlash = QLineEdit("0.0")
        self.hel_backlash.setPlaceholderText("gioco totale es. 0.05")
        self.hel_shaft_dia = QLineEdit("0.0")
        self.hel_shaft_dia.setPlaceholderText("0 = nessun foro")
        form2.addRow("Spost. Profilo (x):", self.hel_x)
        form2.addRow("Gioco (backlash) [mm]:", self.hel_backlash)
        form2.addRow("Ø foro albero [mm]:", self.hel_shaft_dia)
        grp_adv.setLayout(form2)

        layout.addWidget(grp_base)
        layout.addWidget(grp_adv)
        layout.addWidget(self._strength_group("hel"))
        layout.addWidget(self._iso_grade_group("hel"))
        layout.addStretch()

        scroll.setWidget(inner)
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.tabs.addTab(tab, "Denti Elicoidali")

    def _setup_rack_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        grp_base = QGroupBox("Parametri Base")
        form = QFormLayout()
        self.rack_m     = QLineEdit("3.0")
        self.rack_z     = QLineEdit("20")
        self.rack_w     = QLineEdit("20.0")
        self.rack_alpha = QLineEdit("20.0")
        form.addRow("Modulo (m) [mm]:", self.rack_m)
        form.addRow("Num. Denti (z):", self.rack_z)
        form.addRow("Fascia (b) [mm]:", self.rack_w)
        form.addRow("Angolo Pressione (α) [°]:", self.rack_alpha)
        grp_base.setLayout(form)

        layout.addWidget(grp_base)
        layout.addWidget(self._iso_grade_group("rack"))
        layout.addStretch()

        scroll.setWidget(inner)
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.tabs.addTab(tab, "Cremagliera")

    def _setup_worm_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        grp_base = QGroupBox("Parametri Base (ZI Profile)")
        form = QFormLayout()
        self.worm_mx     = QLineEdit("2.0")
        self.worm_z1     = QLineEdit("1")
        self.worm_q      = QLineEdit("10.0")
        self.worm_length = QLineEdit("60.0")
        form.addRow("Modulo assiale (mx) [mm]:", self.worm_mx)
        form.addRow("Num. principi (z₁):", self.worm_z1)
        form.addRow("Quoziente diam. (q):", self.worm_q)
        form.addRow("Lunghezza (L) [mm]:", self.worm_length)
        grp_base.setLayout(form)

        layout.addWidget(grp_base)
        layout.addStretch()

        scroll.setWidget(inner)
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.tabs.addTab(tab, "Vite Senza Fine")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def _vf(self, text, default=0.0):
        """Valida e converte stringa in float."""
        try:
            return float(str(text).replace(',', '.'))
        except (ValueError, AttributeError):
            return default

    def _vi(self, text, default=0):
        try:
            return int(float(str(text).replace(',', '.')))
        except (ValueError, AttributeError):
            return default

    # ------------------------------------------------------------------
    # Genera ingranaggio
    # ------------------------------------------------------------------
    def generate_gear(self):
        # Push undo prima di procedere
        current_state = self.get_state()
        if self._undo_stack[-1:] != [current_state]:
            self._undo_stack.append(current_state)
            if len(self._undo_stack) > 20:
                self._undo_stack.pop(0)
            self._redo_stack.clear()

        idx = self.tabs.currentIndex()
        try:
            if idx == 0:
                self._calc_spur()
            elif idx == 1:
                self._calc_helical()
            elif idx == 2:
                self._calc_rack()
            elif idx == 3:
                self._calc_worm()

            self._generate_gear2(idx)
            self._update_3d_view()
            self._update_2d_view()
            if self.last_results:
                self.btn_export_pdf.setEnabled(True)
                self.btn_export_csv.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Errore di Generazione", str(e))

    def _calc_spur(self):
        m         = self._vf(self.spur_m.text(), 2.0)
        z         = self._vi(self.spur_z.text(), 20)
        b         = self._vf(self.spur_w.text(), 10.0)
        alpha     = self._vf(self.spur_alpha.text(), 20.0)
        x         = self._vf(self.spur_x.text(), 0.0)
        backlash  = self._vf(self.spur_backlash.text(), 0.0)
        shaft_dia = self._vf(self.spur_shaft_dia.text(), 0.0)

        params = calculate_gear_parameters(m, z, alpha, x)
        self._fill_geom_table(params, b)
        self._run_strength_and_pair("spur", params, b, alpha, x)
        self._fill_tol_table("spur", params, b)

        self._2d_points = gear_profile_points(m, z, alpha, x, backlash)
        self._2d_shaft  = shaft_dia
        self.btn_export_svg.setEnabled(True)
        self.btn_export_dxf.setEnabled(True)

        self.current_part = create_spur_gear(m, z, b, alpha, x)

    def _calc_helical(self):
        mn        = self._vf(self.hel_m.text(), 2.0)
        z         = self._vi(self.hel_z.text(), 20)
        beta      = self._vf(self.hel_beta.text(), 15.0)
        b         = self._vf(self.hel_w.text(), 15.0)
        alpha     = self._vf(self.hel_alpha.text(), 20.0)
        x         = self._vf(self.hel_x.text(), 0.0)
        backlash  = self._vf(self.hel_backlash.text(), 0.0)
        shaft_dia = self._vf(self.hel_shaft_dia.text(), 0.0)

        # Modulo trasversale
        mt = mn / math.cos(math.radians(beta))
        alpha_t = math.degrees(math.atan(math.tan(math.radians(alpha)) / math.cos(math.radians(beta))))
        params = calculate_gear_parameters(mt, z, alpha_t, x)
        params['mn'] = mn
        params['beta'] = beta
        self._fill_geom_table(params, b)
        self._run_strength_and_pair("hel", params, b, alpha, x, beta=beta)
        self._fill_tol_table("hel", params, b)

        # 2D export uses the transverse profile
        self._2d_points = gear_profile_points(mt, z, alpha_t, x, backlash)
        self._2d_shaft  = shaft_dia
        self.btn_export_svg.setEnabled(True)
        self.btn_export_dxf.setEnabled(True)

        self.current_part = create_helical_gear(mn, z, b, beta)

    def _calc_rack(self):
        m     = self._vf(self.rack_m.text(), 3.0)
        z     = self._vi(self.rack_z.text(), 20)
        b     = self._vf(self.rack_w.text(), 20.0)
        alpha = self._vf(self.rack_alpha.text(), 20.0)

        # Geometria semplificata cremagliera
        pitch = math.pi * m
        h_a   = m
        h_f   = 1.25 * m
        h_tot = h_a + h_f
        geom_rows = [
            ("Modulo (m)", f"{m:.3f}", "mm"),
            ("Num. denti (z)", str(z), ""),
            ("Angolo pressione (α)", f"{alpha:.1f}", "°"),
            ("Passo (p = π·m)", f"{pitch:.4f}", "mm"),
            ("Addendum (ha)", f"{h_a:.3f}", "mm"),
            ("Dedendum (hf)", f"{h_f:.3f}", "mm"),
            ("Altezza dente (h)", f"{h_tot:.3f}", "mm"),
            ("Larghezza fascia (b)", f"{b:.2f}", "mm"),
        ]
        self._fill_table(self._tbl_geom, geom_rows)
        self._fill_table(self._tbl_pair, [])
        self._fill_table(self._tbl_str,  [])
        self._fill_tol_table("rack", {"d": m * z, "m": m}, b)

        self.last_results = {
            "gear_params": {"m": m, "z": z, "alpha": alpha, "d": m*z, "db": 0,
                             "da": 0, "df": 0, "s": pitch/2, "x_shift": 0},
            "pair": None, "strength": None, "Ft": None,
        }
        self.current_part = create_rack_gear(m, z, b)

    def _calc_worm(self):
        mx     = self._vf(self.worm_mx.text(), 2.0)
        z1     = self._vi(self.worm_z1.text(), 1)
        q      = self._vf(self.worm_q.text(), 10.0)
        length = self._vf(self.worm_length.text(), 60.0)

        d1     = q * mx
        gamma  = math.degrees(math.atan(z1 / q))
        beta_w = 90.0 - gamma
        mn_w   = mx * math.cos(math.radians(gamma))
        lead   = math.pi * mx * z1

        geom_rows = [
            ("Modulo assiale (mx)", f"{mx:.3f}", "mm"),
            ("Num. principi (z₁)", str(z1), ""),
            ("Quoziente diametrale (q)", f"{q:.2f}", ""),
            ("Diametro riferimento (d₁=q·mx)", f"{d1:.3f}", "mm"),
            ("Angolo di passo (γ)", f"{gamma:.3f}", "°"),
            ("Angolo di elica (β)", f"{beta_w:.3f}", "°"),
            ("Modulo normale (mn)", f"{mn_w:.4f}", "mm"),
            ("Passo assiale (pz=π·mx·z₁)", f"{lead:.4f}", "mm"),
            ("Lunghezza (L)", f"{length:.1f}", "mm"),
        ]
        self._fill_table(self._tbl_geom, geom_rows)
        self._fill_table(self._tbl_pair, [])
        self._fill_table(self._tbl_str,  [])

        self.last_results = {
            "gear_params": {"m": mx, "z": z1, "alpha": 20, "d": d1, "db": 0,
                             "da": 0, "df": 0, "s": 0, "x_shift": 0},
            "pair": None, "strength": None, "Ft": None,
        }
        self.current_part = create_worm_zi(mx, z1, q, length)

    # ------------------------------------------------------------------
    # Riempimento tabelle
    # ------------------------------------------------------------------
    def _fill_geom_table(self, params, b):
        rows = [
            ("Modulo (m)",              f"{params.get('m', 0):.3f}",     "mm"),
            ("Num. denti (z)",          str(params.get('z', 0)),         ""),
            ("Angolo pressione (α)",    f"{params.get('alpha', 0):.2f}", "°"),
            ("Spost. profilo (x)",      f"{params.get('x_shift', 0):.3f}", ""),
            ("Diametro primitivo (d)",  f"{params.get('d', 0):.4f}",     "mm"),
            ("Diametro base (db)",      f"{params.get('db', 0):.4f}",    "mm"),
            ("Diametro punta (da)",     f"{params.get('da', 0):.4f}",    "mm"),
            ("Diametro piede (df)",     f"{params.get('df', 0):.4f}",    "mm"),
            ("Spessore dente (s)",      f"{params.get('s', 0):.5f}",     "mm"),
            ("Larghezza fascia (b)",    f"{b:.2f}",                       "mm"),
        ]
        if 'mn' in params:
            rows.insert(1, ("Modulo normale (mn)", f"{params['mn']:.3f}", "mm"))
            rows.insert(3, ("Angolo elica (β)",    f"{params.get('beta',0):.2f}", "°"))
        self._fill_table(self._tbl_geom, rows)

    def _fill_tol_table(self, prefix, params, b):
        grade_widget = getattr(self, f"{prefix}_grade", None)
        if grade_widget is None:
            return
        grade = int(grade_widget.currentText())
        d = params.get('d', 1.0)
        m = params.get('m', 1.0)
        try:
            tol = iso1328_tolerances(grade, d, m, b)
            extra = [
                ("--- Tolleranze ISO 1328 ---", f"Grado {grade}", ""),
                ("Dev. totale profilo (Ff)",   f"{tol['Ff']:.1f}", "µm"),
                ("Dev. totale elica (Fb)",     f"{tol['Fb']:.1f}", "µm"),
                ("Dev. passo singolo (fp)",    f"{tol['fp']:.1f}", "µm"),
                ("Dev. cumul. passo (Fp)",     f"{tol['Fp']:.1f}", "µm"),
            ]
            current = []
            for r in range(self._tbl_geom.rowCount()):
                row_data = tuple(self._tbl_geom.item(r, c).text() if self._tbl_geom.item(r, c) else "" for c in range(3))
                current.append(row_data)
            self._fill_table(self._tbl_geom, current + extra)
        except Exception:
            pass

    def _run_strength_and_pair(self, prefix, params, b, alpha=20.0, x=0.0, beta=0.0):
        mat_widget = getattr(self, f"{prefix}_mat", None)
        P_widget   = getattr(self, f"{prefix}_P", None)
        n_widget   = getattr(self, f"{prefix}_n", None)
        KA_widget  = getattr(self, f"{prefix}_KA", None)
        z2_widget  = getattr(self, f"{prefix}_z2", None)
        x2_widget  = getattr(self, f"{prefix}_x2", None)

        if mat_widget is None or P_widget is None:
            return

        mat_name = mat_widget.currentText()
        P_txt = P_widget.text().strip()
        n_txt = n_widget.text().strip()
        z2_txt = z2_widget.text().strip() if z2_widget else ""
        x2 = self._vf(x2_widget.text() if x2_widget else "0.0", 0.0)

        pair_result = None
        str_result  = None
        Ft_val      = None

        aw_widget  = getattr(self, f"{prefix}_aw", None)
        aw_txt     = aw_widget.text().strip() if aw_widget else ""

        # Analisi coppia
        if z2_txt:
            z2 = self._vi(z2_txt, 0)
            z1 = params['z']
            m  = params['m']
            if z2 > 0:
                try:
                    # Se interasse imposto → calcola spostamenti automatici
                    if aw_txt:
                        a_w_target = self._vf(aw_txt, 0.0)
                        pair_result = pair_from_center_distance(a_w_target, m, z1, z2, alpha, beta)
                        # Aggiorna i campi x1 e x2 con i valori calcolati
                        x_field = getattr(self, f"{prefix}_x", None)
                        x2_field = getattr(self, f"{prefix}_x2", None)
                        if x_field:
                            x_field.setText(f"{pair_result['x1']:.5f}")
                        if x2_field:
                            x2_field.setText(f"{pair_result['x2']:.5f}")
                        x  = pair_result['x1']
                        x2 = pair_result['x2']
                    else:
                        pair_result = calculate_gear_pair(m, z1, z2, alpha, x, x2, beta)

                    def color_eps(v):
                        if v >= 1.2: return QColor("#a8e6a3")
                        if v >= 1.0: return QColor("#ffe0a3")
                        return QColor("#f5a3a3")

                    pair_rows = []
                    if pair_result.get('warning'):
                        pair_rows.append(("Avviso", pair_result['warning'], ""))
                    if 'x1' in pair_result:
                        pair_rows += [
                            ("Interasse imposto (a_w)",  f"{pair_result.get('a_w_target', pair_result['a_w']):.3f}", "mm"),
                            ("Spost. profilo calcolato x₁", f"{pair_result['x1']:.5f}", ""),
                            ("Spost. profilo calcolato x₂", f"{pair_result['x2']:.5f}", ""),
                        ]
                    pair_rows += [
                        ("Rapporto trasmiss. (i)",      f"{pair_result['i']:.3f}", ""),
                        ("Interasse standard (a)",       f"{pair_result['a_std']:.3f}", "mm"),
                        ("Interasse di lavoro (a_w)",    f"{pair_result['a_w']:.3f}", "mm"),
                        ("Ang. press. lavoro (α_wt)",    f"{pair_result['alpha_wt']:.3f}", "°"),
                        ("Rapporto contatto (ε_α)",      f"{pair_result['epsilon_alpha']:.4f}", ""),
                        ("Diam. punta max pignone",      f"{pair_result['da1_max']:.3f}", "mm"),
                        ("Diam. punta max ruota",        f"{pair_result['da2_max']:.3f}", "mm"),
                        ("Rischio sottoq. pignone",      "SI ⚠" if pair_result['undercut_risk_1'] else "No", ""),
                        ("Rischio sottoq. ruota",        "SI ⚠" if pair_result['undercut_risk_2'] else "No", ""),
                        ("Denti min. senza spost.",      str(pair_result['z_min']), ""),
                    ]
                    self._fill_table(self._tbl_pair, pair_rows, color_col=1,
                                     color_fn=lambda v: color_eps(v) if abs(v - pair_result['epsilon_alpha']) < 0.001 else None)
                    # Colora la riga ε_α
                    for r in range(self._tbl_pair.rowCount()):
                        it = self._tbl_pair.item(r, 0)
                        if it and "ε_α" in it.text():
                            val_item = self._tbl_pair.item(r, 1)
                            if val_item:
                                val_item.setBackground(color_eps(pair_result['epsilon_alpha']))
                except Exception as e:
                    self._fill_table(self._tbl_pair, [("Errore coppia", str(e), "")])
            else:
                self._fill_table(self._tbl_pair, [])
        else:
            self._fill_table(self._tbl_pair, [("z₂ non inserito", "—", "")])

        # Analisi resistenza
        if mat_name != "-- nessuno --" and P_txt and n_txt:
            try:
                P   = self._vf(P_txt, 0.0)
                n   = self._vf(n_txt, 0.0)
                KA  = self._vf(KA_widget.text() if KA_widget else "1.25", 1.25)
                mat = get_material(mat_name)
                Ft_val = tangential_force_from_power(P, n, params['d'])

                bend = calculate_lewis_bending(params, b, Ft_val, mat, KA=KA,
                                               epsilon_alpha=pair_result['epsilon_alpha'] if pair_result else None)

                # Per Hertz serve una seconda ruota — se z2 disponibile usiamo i suoi parametri
                if pair_result and z2_txt:
                    m2 = params['m']
                    z2 = self._vi(z2_txt, 0)
                    p2 = calculate_gear_parameters(m2, z2, alpha, x2)
                    contact = calculate_hertz_contact(params, p2, b, Ft_val, mat, mat, KA=KA)
                else:
                    contact = {}

                def color_SF(v):
                    if v >= 1.4: return QColor("#a8e6a3")
                    if v >= 1.1: return QColor("#ffe0a3")
                    return QColor("#f5a3a3")

                str_rows = [
                    ("Forza tangenziale (Ft)",        f"{Ft_val:.1f}", "N"),
                    ("--- FLESSIONE ---",              "", ""),
                    ("Fattore forma (YF)",             f"{bend.get('YF',0):.3f}", ""),
                    ("Fattore corr. tens. (YS)",       f"{bend.get('YS',0):.3f}", ""),
                    ("Tensione flessione (σ_F)",       f"{bend.get('sigma_F',0):.2f}", "MPa"),
                    ("Tensione ammiss. fless.",        f"{bend.get('sigma_F_perm',0):.2f}", "MPa"),
                    ("Sicurezza flessione (SF)",       f"{bend.get('SF',0):.3f}", ""),
                ]
                if contact:
                    str_rows += [
                        ("--- CONTATTO ---",           "", ""),
                        ("Fattore elastico (ZE)",      f"{contact.get('ZE',0):.2f}", "√MPa"),
                        ("Fattore zona (ZH)",          f"{contact.get('ZH',0):.3f}", ""),
                        ("Tensione contatto (σ_H)",    f"{contact.get('sigma_H',0):.2f}", "MPa"),
                        ("Tensione ammiss. cont.",     f"{contact.get('sigma_H_perm',0):.2f}", "MPa"),
                        ("Sicurezza contatto (SH)",    f"{contact.get('SH',0):.3f}", ""),
                    ]

                self._fill_table(self._tbl_str, str_rows)

                # Colora SF
                for r in range(self._tbl_str.rowCount()):
                    it = self._tbl_str.item(r, 0)
                    if it and "SF" in it.text():
                        vi = self._tbl_str.item(r, 1)
                        if vi:
                            try:
                                vi.setBackground(color_SF(float(vi.text())))
                            except ValueError:
                                pass
                    if it and "SH" in it.text():
                        vi = self._tbl_str.item(r, 1)
                        if vi:
                            try:
                                vi.setBackground(color_SF(float(vi.text())))
                            except ValueError:
                                pass

                str_result = {"bending": bend, "contact": contact}

            except Exception as e:
                self._fill_table(self._tbl_str, [("Errore resistenza", str(e), "")])
        else:
            self._fill_table(self._tbl_str, [("Inserire P, n e materiale", "—", "")])

        self.last_results = {
            "gear_params": params,
            "pair": pair_result,
            "strength": str_result,
            "Ft": Ft_val,
            "material": mat_widget.currentText() if mat_widget else "",
        }

    # ------------------------------------------------------------------
    # Vista 3D
    # ------------------------------------------------------------------
    @staticmethod
    def _read_stl_binary(path):
        """Legge un file STL binario e ritorna array (N,3,3) di triangoli."""
        # Binary STL record: 3×float32 normal + 3×3×float32 vertices + uint16 attr = 50 bytes
        _dt = np.dtype([
            ('normal',   np.float32, (3,)),
            ('vertices', np.float32, (3, 3)),
            ('attr',     np.uint16,  (1,)),
        ])
        with open(path, 'rb') as f:
            f.read(80)   # 80-byte header
            count = np.frombuffer(f.read(4), dtype=np.uint32)[0]
            raw = f.read(count * 50)
        records = np.frombuffer(raw, dtype=_dt)
        return records['vertices']   # shape (N, 3, 3)

    @staticmethod
    def _stl_export(part, path):
        try:
            part.export_stl(path)
        except AttributeError:
            from build123d import export_stl
            export_stl(part, path)

    def _update_3d_view(self):
        if self.current_part is None:
            return
        base = os.path.dirname(__file__)
        stl1 = os.path.join(base, "temp_g1.stl")
        stl2 = os.path.join(base, "temp_g2.stl")
        try:
            self._stl_export(self.current_part, stl1)
        except Exception as e:
            print("STL1 export error:", e)
            return
        try:
            tris1 = self._read_stl_binary(stl1)
        except Exception as e:
            print("STL1 read error:", e)
            return

        # Gear 2 (coppia)
        tris2 = None
        if self._gear2_part is not None and self._pair_aw is not None:
            try:
                self._stl_export(self._gear2_part, stl2)
                tris2 = self._read_stl_binary(stl2).copy()
                tris2[:, :, 0] += float(self._pair_aw)   # offset lungo X
            except Exception as e:
                print("STL2 error:", e)

        self._ax3d.cla()
        self._ax3d.set_facecolor('#1a1a2e')

        poly1 = Poly3DCollection(tris1, alpha=0.85, linewidth=0.1)
        poly1.set_facecolor('#5dade2')
        poly1.set_edgecolor('#1a5276')
        self._ax3d.add_collection3d(poly1)
        all_pts = tris1.reshape(-1, 3)

        if tris2 is not None:
            poly2 = Poly3DCollection(tris2, alpha=0.85, linewidth=0.1)
            poly2.set_facecolor('#e74c3c')
            poly2.set_edgecolor('#922b21')
            self._ax3d.add_collection3d(poly2)
            all_pts = np.vstack([all_pts, tris2.reshape(-1, 3)])

        mn, mx = all_pts.min(axis=0), all_pts.max(axis=0)
        mid  = (mn + mx) / 2
        half = (mx - mn).max() / 2 * 1.1
        self._ax3d.set_xlim(mid[0] - half, mid[0] + half)
        self._ax3d.set_ylim(mid[1] - half, mid[1] + half)
        self._ax3d.set_zlim(mid[2] - half, mid[2] + half)
        self._ax3d.set_xlabel('X', color='white', fontsize=7)
        self._ax3d.set_ylabel('Y', color='white', fontsize=7)
        self._ax3d.set_zlabel('Z', color='white', fontsize=7)
        self._ax3d.tick_params(colors='white', labelsize=6)
        title = "Vista 3D — Coppia" if tris2 is not None else "Vista 3D"
        self._ax3d.set_title(title, color='white', fontsize=9)
        self._fig.tight_layout(pad=0.5)
        self._canvas.draw()

    # ------------------------------------------------------------------
    # Vista 2D profilo
    # ------------------------------------------------------------------
    def _update_2d_view(self):
        ax = self._ax2d
        ax.cla()
        ax.set_facecolor('#0d1117')
        ax.set_aspect('equal')
        ax.tick_params(colors='#888', labelsize=6)
        for sp in ax.spines.values():
            sp.set_edgecolor('#333')

        theta = np.linspace(0, 2 * np.pi, 300)

        def _draw_circles(cx, cy, params):
            for r_key, col, ls in [('r', '#f0e68c', '--'), ('ra', '#7fb3d3', ':'), ('rb', '#888', ':')]:
                rv = params.get(r_key, 0)
                if rv > 0:
                    ax.plot(cx + rv * np.cos(theta), cy + rv * np.sin(theta),
                            color=col, linewidth=0.5, linestyle=ls, alpha=0.6)

        # Ruota 1
        if self._2d_points is not None:
            p = self._2d_points
            ax.fill(p[:, 0], p[:, 1], color='#5dade2', alpha=0.80,
                    linewidth=0.4, edgecolor='#1a5276')
            if self.last_results:
                _draw_circles(0, 0, self.last_results.get('gear_params', {}))

        # Ruota 2 (coppia)
        if self._2d_points2 is not None and self._pair_aw is not None:
            p2 = self._2d_points2.copy()
            p2[:, 0] += float(self._pair_aw)
            ax.fill(p2[:, 0], p2[:, 1], color='#e74c3c', alpha=0.80,
                    linewidth=0.4, edgecolor='#922b21')
            if self.last_results and self.last_results.get('pair'):
                pr = self.last_results['pair']
                # disegna cerchio primitivo ruota 2
                gp = self.last_results.get('gear_params', {})
                m  = gp.get('m', 0)
                z2 = pr.get('i', 1) * gp.get('z', 0)
                r2 = m * z2 / 2
                if r2 > 0:
                    ax.plot(float(self._pair_aw) + r2 * np.cos(theta),
                            r2 * np.sin(theta),
                            color='#f0e68c', linewidth=0.5, linestyle='--', alpha=0.6)

        if self._2d_points is None:
            ax.set_title("Profilo 2D — calcola prima la geometria", color='#888', fontsize=8)
        elif self._2d_points2 is not None:
            ax.set_title("Profilo 2D — Coppia", color='white', fontsize=9)
        else:
            ax.set_title("Profilo 2D", color='white', fontsize=9)

        ax.autoscale_view()
        self._fig2d.tight_layout(pad=0.5)
        self._canvas2d.draw()

    # ------------------------------------------------------------------
    # Genera seconda ruota della coppia
    # ------------------------------------------------------------------
    def _generate_gear2(self, idx):
        self._gear2_part  = None
        self._pair_aw     = None
        self._2d_points2  = None

        if not self.last_results:
            return
        pair = self.last_results.get('pair')
        if pair is None:
            return

        a_w = pair.get('a_w', 0)
        x2  = pair.get('x2', 0.0)
        i   = pair.get('i', 0)
        gp  = self.last_results.get('gear_params', {})
        z1  = gp.get('z', 0)
        z2  = round(i * z1)
        if z2 <= 0:
            return

        try:
            if idx == 0:   # denti dritti
                m     = self._vf(self.spur_m.text(), 2.0)
                b     = self._vf(self.spur_w.text(), 10.0)
                alpha = self._vf(self.spur_alpha.text(), 20.0)
                bl    = self._vf(self.spur_backlash.text(), 0.0)
                self._gear2_part = create_spur_gear(m, z2, b, alpha, x2)
                self._2d_points2 = gear_profile_points(m, z2, alpha, x2, bl)
            elif idx == 1:  # denti elicoidali
                mn    = self._vf(self.hel_m.text(), 2.0)
                b     = self._vf(self.hel_w.text(), 15.0)
                beta  = self._vf(self.hel_beta.text(), 15.0)
                alpha = self._vf(self.hel_alpha.text(), 20.0)
                bl    = self._vf(self.hel_backlash.text(), 0.0)
                import math as _m
                mt    = mn / _m.cos(_m.radians(beta))
                at    = _m.degrees(_m.atan(_m.tan(_m.radians(alpha)) / _m.cos(_m.radians(beta))))
                self._gear2_part = create_helical_gear(mn, z2, b, beta, alpha_n=alpha, x_shift=x2)
                self._2d_points2 = gear_profile_points(mt, z2, at, x2, bl)
            else:
                return

            self._pair_aw = a_w
        except Exception as e:
            print("Gear2 generation error:", e)

    # ------------------------------------------------------------------
    # Export STEP
    # ------------------------------------------------------------------
    def export_step(self):
        if self.current_part is None:
            QMessageBox.warning(self, "Attenzione", "Genera prima una geometria!")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salva STEP", "", "STEP Files (*.stp *.step)")
        if not path:
            return
        try:
            try:
                self.current_part.export_step(path)
            except AttributeError:
                from build123d import export_step
                export_step(self.current_part, path)
            QMessageBox.information(self, "Export", f"File salvato:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore Export STEP", str(e))

    # ------------------------------------------------------------------
    # Export PDF / CSV
    # ------------------------------------------------------------------
    def _export_pdf(self):
        if not self.last_results:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salva PDF", "", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            rpt.export_pdf(
                path,
                self.last_results.get("gear_params", {}),
                self.last_results.get("pair"),
                self.last_results.get("strength"),
                self.last_results.get("material", ""),
            )
            if self.last_results.get("Ft"):
                # Aggiunge Ft ai risultati strength per il PDF
                if self.last_results.get("strength"):
                    self.last_results["strength"]["Ft"] = self.last_results["Ft"]
            QMessageBox.information(self, "Export PDF", f"Report salvato:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore Export PDF", str(e))

    def _export_csv(self):
        if not self.last_results:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salva CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            rpt.export_csv(
                path,
                self.last_results.get("gear_params", {}),
                self.last_results.get("pair"),
                self.last_results.get("strength"),
            )
            QMessageBox.information(self, "Export CSV", f"File salvato:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore Export CSV", str(e))

    # ------------------------------------------------------------------
    # Export SVG / DXF (profilo 2D)
    # ------------------------------------------------------------------
    def _export_svg(self):
        if self._2d_points is None:
            QMessageBox.warning(self, "Attenzione", "Genera prima una geometria (Denti Dritti o Elicoidali).")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salva SVG", "", "SVG Files (*.svg)")
        if not path:
            return
        try:
            shaft = getattr(self, '_2d_shaft', 0.0)
            gp    = self.last_results.get("gear_params", {}) if self.last_results else {}
            title = f"m={gp.get('m','')} z={gp.get('z','')} α={gp.get('alpha','')}°"
            export_svg(path, self._2d_points, shaft_dia=shaft, title=title)
            QMessageBox.information(self, "Export SVG", f"File salvato:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore Export SVG", str(e))

    def _export_dxf(self):
        if self._2d_points is None:
            QMessageBox.warning(self, "Attenzione", "Genera prima una geometria (Denti Dritti o Elicoidali).")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salva DXF", "", "DXF Files (*.dxf)")
        if not path:
            return
        try:
            shaft = getattr(self, '_2d_shaft', 0.0)
            export_dxf(path, self._2d_points, shaft_dia=shaft)
            QMessageBox.information(self, "Export DXF", f"File salvato:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore Export DXF", str(e))

    # ------------------------------------------------------------------
    # Salva / Carica progetto
    # ------------------------------------------------------------------
    def get_state(self):
        idx = self.tabs.currentIndex()
        gear_map = {0: "spur", 1: "helical", 2: "rack", 3: "worm"}
        gear_type = gear_map.get(idx, "spur")

        params = {}
        pair   = {}
        strength = {}

        if idx == 0:
            params = {"m": self.spur_m.text(), "z": self.spur_z.text(),
                      "b": self.spur_w.text(), "alpha": self.spur_alpha.text(), "x": self.spur_x.text()}
            pair     = {"z2": self.spur_z2.text(), "x2": self.spur_x2.text(), "aw": self.spur_aw.text()}
            strength = {"material": self.spur_mat.currentText(),
                        "P_kW": self.spur_P.text(), "n_rpm": self.spur_n.text(), "KA": self.spur_KA.text()}
        elif idx == 1:
            params = {"m": self.hel_m.text(), "z": self.hel_z.text(), "beta": self.hel_beta.text(),
                      "b": self.hel_w.text(), "alpha": self.hel_alpha.text(), "x": self.hel_x.text()}
            pair     = {"z2": self.hel_z2.text(), "x2": self.hel_x2.text(), "aw": self.hel_aw.text()}
            strength = {"material": self.hel_mat.currentText(),
                        "P_kW": self.hel_P.text(), "n_rpm": self.hel_n.text(), "KA": self.hel_KA.text()}
        elif idx == 2:
            params = {"m": self.rack_m.text(), "z": self.rack_z.text(),
                      "b": self.rack_w.text(), "alpha": self.rack_alpha.text()}
        elif idx == 3:
            params = {"mx": self.worm_mx.text(), "z1": self.worm_z1.text(),
                      "q": self.worm_q.text(), "length": self.worm_length.text()}

        return {"version": 1, "gear_type": gear_type, "tab_index": idx,
                "params": params, "pair": pair, "strength": strength}

    def set_state(self, state):
        idx = state.get("tab_index", 0)
        self.tabs.setCurrentIndex(idx)
        params   = state.get("params", {})
        pair     = state.get("pair", {})
        strength = state.get("strength", {})

        def _set(widget, key, d=params):
            if key in d and widget:
                widget.setText(str(d[key]))

        if idx == 0:
            _set(self.spur_m, "m"); _set(self.spur_z, "z"); _set(self.spur_w, "b")
            _set(self.spur_alpha, "alpha"); _set(self.spur_x, "x")
            _set(self.spur_z2, "z2", pair); _set(self.spur_x2, "x2", pair); _set(self.spur_aw, "aw", pair)
            if strength.get("material") and strength["material"] in list_materials():
                self.spur_mat.setCurrentText(strength["material"])
            _set(self.spur_P, "P_kW", strength); _set(self.spur_n, "n_rpm", strength)
            _set(self.spur_KA, "KA", strength)
        elif idx == 1:
            _set(self.hel_m, "m"); _set(self.hel_z, "z"); _set(self.hel_beta, "beta")
            _set(self.hel_w, "b"); _set(self.hel_alpha, "alpha"); _set(self.hel_x, "x")
            _set(self.hel_z2, "z2", pair); _set(self.hel_x2, "x2", pair); _set(self.hel_aw, "aw", pair)
            if strength.get("material") and strength["material"] in list_materials():
                self.hel_mat.setCurrentText(strength["material"])
            _set(self.hel_P, "P_kW", strength); _set(self.hel_n, "n_rpm", strength)
            _set(self.hel_KA, "KA", strength)
        elif idx == 2:
            _set(self.rack_m, "m"); _set(self.rack_z, "z")
            _set(self.rack_w, "b"); _set(self.rack_alpha, "alpha")
        elif idx == 3:
            _set(self.worm_mx, "mx"); _set(self.worm_z1, "z1")
            _set(self.worm_q, "q"); _set(self.worm_length, "length")

    def _new_project(self):
        self.tabs.setCurrentIndex(0)
        defaults = {"version": 1, "gear_type": "spur", "tab_index": 0,
                    "params": {"m": "2.0", "z": "20", "b": "10.0", "alpha": "20.0", "x": "0.0"},
                    "pair": {}, "strength": {}}
        self.set_state(defaults)
        self.last_results = None
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_csv.setEnabled(False)
        self._fill_table(self._tbl_geom, [])
        self._fill_table(self._tbl_pair, [])
        self._fill_table(self._tbl_str,  [])

    def _save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salva Progetto", "",
                                               "Gear Project (*.gear.json)")
        if path:
            try:
                save_project(path, self.get_state())
                QMessageBox.information(self, "Salvataggio", f"Progetto salvato:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Errore Salvataggio", str(e))

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Apri Progetto", "",
                                               "Gear Project (*.gear.json);;JSON (*.json)")
        if path:
            try:
                state = load_project(path)
                self.set_state(state)
            except Exception as e:
                QMessageBox.critical(self, "Errore Apertura", str(e))

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------
    def _undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(self.get_state())
        self.set_state(self._undo_stack.pop())

    def _redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(self.get_state())
        self.set_state(self._redo_stack.pop())

    # ------------------------------------------------------------------
    # Preset
    # ------------------------------------------------------------------
    def _apply_preset(self, name):
        preset = get_preset(name)
        if preset is None:
            return
        gear_type = preset.get("gear_type", "spur")
        tab_map = {"spur": 0, "helical": 1, "rack": 2, "worm": 3}
        state = {
            "version": 1,
            "gear_type": gear_type,
            "tab_index": tab_map.get(gear_type, 0),
            "params": preset.get("params", {}),
            "pair": preset.get("pair", {}),
            "strength": preset.get("strength", {}),
        }
        self.set_state(state)
        # Reset combo a placeholder per evitare loop
        self.combo_preset.blockSignals(True)
        self.combo_preset.setCurrentIndex(0)
        self.combo_preset.blockSignals(False)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GearApp()
    window.show()
    sys.exit(app.exec())
