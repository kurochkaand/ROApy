# ui.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox,
    QCheckBox, QGroupBox, QSpinBox, QPushButton, QListWidget
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

        # Spectra selection
        self.first_cb = QCheckBox("First")
        self.last_cb  = QCheckBox("Last")
        self.avg_cb   = QCheckBox("Average over range")
        self.range_start = QSpinBox()
        self.range_end   = QSpinBox()
        self.last_cb.setChecked(True)

        grp_spec = QGroupBox("Spectra Selection")
        l_spec = QVBoxLayout()
        for w in (
            self.first_cb, self.last_cb, self.avg_cb,
            QLabel("Range of exported files:"), self.range_start, self.range_end
        ):
            l_spec.addWidget(w)
        grp_spec.setLayout(l_spec)
        ctrl.addWidget(grp_spec)

        # Modalities
        self.mod_scp   = QCheckBox("SCP")
        self.mod_dcpi  = QCheckBox("DCPI")
        self.mod_dcpii = QCheckBox("DCPII")
        self.mod_scpc  = QCheckBox("SCPc")
        self.mod_scp.setChecked(True)

        grp_mod = QGroupBox("Modalities")
        l_mod = QVBoxLayout()
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