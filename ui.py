# ui.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox,
    QCheckBox, QGroupBox, QSpinBox, QPushButton, QListWidget,
    QDoubleSpinBox, QRadioButton, QFormLayout, QAbstractItemView,
)

class SpectraViewerUI:
    def setup_ui(self, parent, plotter):
        central = QWidget()
        parent.setCentralWidget(central)
        main_l = QHBoxLayout(central)

        # ── control panel ──
        ctrl = QVBoxLayout()
        main_l.addLayout(ctrl, 1)

        # Experiment selector
        ctrl.addWidget(QLabel("Experiment"))
        self.exp_combo = QComboBox()
        ctrl.addWidget(self.exp_combo)

        # Individual‐spectrum selector
        grp_list = QGroupBox("Spectra List")
        l_list = QVBoxLayout()

        # Cam-A / Cam-B / Both radio row
        row = QHBoxLayout()
        self.radio_cam_a = QRadioButton("Cam. A")
        self.radio_cam_b = QRadioButton("Cam. B")
        self.radio_both  = QRadioButton("Both")
        self.radio_both.setChecked(True)
        
        for rb in (self.radio_cam_a, self.radio_cam_b, self.radio_both):
            row.addWidget(rb)
        l_list.addLayout(row)

        self.indiv_list = QListWidget()
        # allow multiple selection
        self.indiv_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        l_list.addWidget(self.indiv_list)
        l_list.addWidget(QLabel("Range of exported files:"))
        grp_list.setLayout(l_list)
        ctrl.addWidget(grp_list)

        # Modalities
        self.mod_scp   = QCheckBox("SCP")
        self.mod_dcpi  = QCheckBox("DCPI")
        self.mod_dcpii = QCheckBox("DCPII")
        self.mod_scpc  = QCheckBox("SCPc")
        self.mod_scp.setChecked(True)

        grp_mod = QGroupBox("Modalities")
        l_mod = QHBoxLayout()
        for cb in (self.mod_scp, self.mod_dcpi,
                   self.mod_dcpii, self.mod_scpc):
            l_mod.addWidget(cb)
        grp_mod.setLayout(l_mod)
        ctrl.addWidget(grp_mod)

        # Export buttons & metadata
        self.btn_export_comb = QPushButton("Export Combined")
        self.btn_export_sep  = QPushButton("Export Separate")
        ctrl.addWidget(self.btn_export_comb)
        ctrl.addWidget(self.btn_export_sep)

        # Normalization toggle
        self.btn_toggle_norm = QPushButton("Normalize by TotalTime")
        ctrl.addWidget(self.btn_toggle_norm)

        # Fluorescence background removal
        grp_bg = QGroupBox("Fluorescence Removal")
        form = QFormLayout()

        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(1, 1_000)
        self.max_iter_spin.setValue(100)
        form.addRow("Max iterations:", self.max_iter_spin)

        self.pressure_spin = QDoubleSpinBox()
        self.pressure_spin.setDecimals(8)
        self.pressure_spin.setRange(0.0, 1.0)
        self.pressure_spin.setSingleStep(1e-5)
        self.pressure_spin.setValue(1e-5)
        form.addRow("Pressure (p):", self.pressure_spin)

        # baseline mode radio buttons
        self.radio_zero     = QRadioButton("From zero")
        self.radio_spectrum = QRadioButton("To spectrum")
        self.radio_zero.setChecked(True)
        h = QHBoxLayout()
        h.addWidget(self.radio_zero)
        h.addWidget(self.radio_spectrum)
        form.addRow("Mode:", h)

        # starting wavenumber for baseline
        self.start_wav_spin = QDoubleSpinBox()
        self.start_wav_spin.setRange(-50, 4000)
        self.start_wav_spin.setValue(100.0)
        self.start_wav_spin.setSuffix(" cm⁻¹")
        form.addRow("Baseline start (cm⁻¹):", self.start_wav_spin)

        # new baseline‐related buttons
        self.btn_create_baseline       = QPushButton("Create Baseline")
        self.btn_subtract_created      = QPushButton("Subtract Baseline")
        self.btn_delete_baseline       = QPushButton("Delete Baseline")
        form.addRow(self.btn_create_baseline)
        form.addRow(self.btn_subtract_created)
        form.addRow(self.btn_delete_baseline)
        
        grp_bg.setLayout(form)
        ctrl.addWidget(grp_bg)

        ctrl.addWidget(QLabel("Metadata"))
        self.meta_list = QListWidget()
        ctrl.addWidget(self.meta_list)

        # ── plot area ──
        plot_container = QWidget()
        plot_l = QVBoxLayout(plot_container)
        plot_l.setContentsMargins(0, 0, 0, 0)
        plot_l.addWidget(plotter.toolbar)
        plot_l.addWidget(plotter.canvas)
        main_l.addWidget(plot_container, 2)