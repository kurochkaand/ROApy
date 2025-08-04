# ui.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTreeWidget, 
    QCheckBox, QGroupBox, QSpinBox, QPushButton, QListWidget,
    QDoubleSpinBox, QRadioButton, QFormLayout, QAbstractItemView,
    QSizePolicy
)

class SpectraViewerUI:
    def setup_ui(self, parent, plotter):
        central = QWidget()
        parent.setCentralWidget(central)
        main_l = QHBoxLayout(central)

        # ── control panel ──
        ctrl = QVBoxLayout()
        main_l.addLayout(ctrl, 1)

        self.btn_add_working_dir = QPushButton("Add Working Directory")
        self.btn_add_working_dir.setToolTip("Load spectra from an additional working directory (merges with current).")
        ctrl.addWidget(self.btn_add_working_dir)

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

        # Tree list of spectra
        hint = QLabel("Press CTRL for multiple selection.")
        # make it slightly smaller / subdued if you want
        font = hint.font()
        font.setPointSize(font.pointSize() - 1)
        hint.setFont(font)
        hint.setStyleSheet("color: gray;")
        l_list.addWidget(hint)

        # Tree list of spectra
        self.tree_list = QTreeWidget()
        self.tree_list.setHeaderHidden(True)
        self.tree_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        l_list.addWidget(self.tree_list)

        self.btn_create_selection = QPushButton("Create selection of measurement cycles")
        l_list.addWidget(self.btn_create_selection)

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

        # Raman Baseline removal
        grp_bg = QGroupBox("Raman Baseline Removal")
        form = QFormLayout()

        self.max_iter_spin = QSpinBox()
        self.max_iter_spin.setRange(1, 1_000)
        self.max_iter_spin.setValue(100)
        form.addRow("Max iterations:", self.max_iter_spin)

        self.pressure_spin = QDoubleSpinBox()
        self.pressure_spin.setDecimals(1)
        self.pressure_spin.setRange(0.0, 10.0)
        self.pressure_spin.setSingleStep(1e-1)
        self.pressure_spin.setValue(1e-1)
        form.addRow("Pressure (scaled):", self.pressure_spin)

        # baseline mode radio buttons
        self.radio_zero     = QRadioButton("From zero")
        self.radio_spectrum = QRadioButton("To spectrum")
        self.radio_zero.setChecked(True)
        h = QHBoxLayout()
        h.addWidget(self.radio_zero)
        h.addWidget(self.radio_spectrum)
        form.addRow("Mode:", h)

        # starting wavenumber for baseline
        self.start_wav_spin = QSpinBox()
        self.start_wav_spin.setRange(-50, 4000)
        self.start_wav_spin.setValue(100)
        self.start_wav_spin.setSuffix(" cm⁻¹")
        form.addRow("Baseline start:", self.start_wav_spin)


        # new baseline‐related buttons
        self.btn_create_baseline       = QPushButton("Create")
        self.btn_subtract_created      = QPushButton("Subtract")
        self.btn_delete_baseline       = QPushButton("Delete")
        for btn in (self.btn_create_baseline, self.btn_subtract_created, self.btn_delete_baseline):
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.addWidget(self.btn_create_baseline)
        buttons_layout.addWidget(self.btn_subtract_created)
        buttons_layout.addWidget(self.btn_delete_baseline)
        form.addRow("", buttons_layout)  # empty label so buttons span the row

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