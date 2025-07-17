import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QFileDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QCheckBox, QGroupBox, QSpinBox, QListWidget
)
from PyQt6.QtCore import Qt

from file_loader import load_data_files
from plotter import SpectraPlotter

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectra Viewer")
        self.resize(900, 600)

        self._init_ui()

        self.working_dir = QFileDialog.getExistingDirectory(
            self, "Select Working Directory", os.getcwd(),
            QFileDialog.Option.ShowDirsOnly
        )
        if not self.working_dir:
            self.close()
            return

        self.data = load_data_files(self.working_dir)
        
        if not self.data:
            self.meta_display.addItem("No valid spectra files found.")
            return

        self._update_range_bounds()

        # ✅ Fix here: provide default modalities when first plotting
        modalities = {
            "SCP": True,
            "DCPI": False,
            "DCPII": False,
            "SCPc": False
        }
        self.plotter.update_plot(self.data, modalities)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()
        central_widget.setLayout(layout)

        # Control panel (left)
        control_panel = QVBoxLayout()
        layout.addLayout(control_panel, 1)

        # Spectra selection
        self.first_cb = QCheckBox("First")
        self.last_cb = QCheckBox("Last")
        self.avg_cb = QCheckBox("Average over range")
        self.range_start = QSpinBox()
        self.range_end = QSpinBox()
        spectra_box = QGroupBox("Spectra Selection")
        spectra_layout = QVBoxLayout()
        spectra_layout.addWidget(self.first_cb)
        spectra_layout.addWidget(self.last_cb)
        spectra_layout.addWidget(self.avg_cb)
        spectra_layout.addWidget(QLabel("Range:"))
        spectra_layout.addWidget(self.range_start)
        spectra_layout.addWidget(self.range_end)
        spectra_box.setLayout(spectra_layout)

        # Modality selection
        self.mod_scp = QCheckBox("SCP")
        self.mod_dcpi = QCheckBox("DCPI")
        self.mod_dcpii = QCheckBox("DCPII")
        self.mod_scpc = QCheckBox("SCPc")
        self.mod_scp.setChecked(True)
        mod_box = QGroupBox("Modality Selection")
        mod_layout = QVBoxLayout()
        for box in [self.mod_scp, self.mod_dcpi, self.mod_dcpii, self.mod_scpc]:
            mod_layout.addWidget(box)
        mod_box.setLayout(mod_layout)

        # Export buttons
        self.export_comb_btn = QPushButton("Export Combined")
        self.export_separate_btn = QPushButton("Export Separate")

        # Metadata
        self.meta_display = QListWidget()

        # Add to control panel
        control_panel.addWidget(spectra_box)
        control_panel.addWidget(mod_box)
        control_panel.addWidget(self.export_comb_btn)
        control_panel.addWidget(self.export_separate_btn)
        control_panel.addWidget(QLabel("Metadata"))
        control_panel.addWidget(self.meta_display)

        # Plot area (right)
        self.plotter = SpectraPlotter(self)
        layout.addWidget(self.plotter.canvas, 2)
    def _update_range_bounds(self):
        all_cycles = [entry["cycle"] for entry in self.data]
        if not all_cycles:
           return
        min_cycle = min(all_cycles)
        max_cycle = max(all_cycles)
        self.range_start.setRange(min_cycle, max_cycle)
        self.range_end.setRange(min_cycle, max_cycle)
        self.range_start.setValue(min_cycle)
        self.range_end.setValue(max_cycle)

