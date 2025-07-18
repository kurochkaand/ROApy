
import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QCheckBox, QGroupBox, QSpinBox, QListWidget, QMessageBox,
    QComboBox
)
from file_loader    import load_data_files
from plotter        import SpectraPlotter
from data_processor import merge_a_b, average_spectra
from exporter       import export_combined, export_separately
from PyQt6.QtCore import QSettings

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectra Viewer")
        self.resize(900, 600)

        self._init_ui()

        self.settings = QSettings("MyOrg", "SpectraViewer")
        last = self.settings.value("lastWorkingDir", os.getcwd())
        self.working_dir = QFileDialog.getExistingDirectory(
            self, "Select Working Directory", last,
            QFileDialog.Option.ShowDirsOnly
        )
        if not self.working_dir:
            self.close()
            return
        self.settings.setValue("lastWorkingDir", self.working_dir)

        # load data entries…
        self.data_entries = load_data_files(self.working_dir)
        if not self.data_entries:
            QMessageBox.warning(
                self, "No Data",
                f"No valid spectra files found in:\n{self.working_dir}"
            )
            self.close()
            return

        self._populate_experiment_combo()
        self._update_range_bounds()
        self._connect_signals()
        self._update_range_bounds()
        self._first_draw = True
        self.on_selection_changed()
        self._first_draw = False

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_l = QHBoxLayout(central)

        # ── control panel ──
        ctrl = QVBoxLayout()
        main_l.addLayout(ctrl, 1)

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
            QLabel("Cycle range:"), self.range_start, self.range_end
        ):
            l_spec.addWidget(w)
        grp_spec.setLayout(l_spec)
        ctrl.addWidget(grp_spec)

        # Modality selection
        self.mod_scp   = QCheckBox("SCP")
        self.mod_dcpi  = QCheckBox("DCPI")
        self.mod_dcpii = QCheckBox("DCPII")
        self.mod_scpc  = QCheckBox("SCPc")
        self.mod_scp.setChecked(True)

        grp_mod = QGroupBox("Modalities")
        l_mod = QVBoxLayout()
        for cb in (self.mod_scp, self.mod_dcpi, self.mod_dcpii, self.mod_scpc):
            l_mod.addWidget(cb)
        grp_mod.setLayout(l_mod)
        ctrl.addWidget(grp_mod)

        # Export buttons
        self.btn_export_comb = QPushButton("Export Combined")
        self.btn_export_sep  = QPushButton("Export Separate")
        ctrl.addWidget(self.btn_export_comb)
        ctrl.addWidget(self.btn_export_sep)

        # Metadata list
        ctrl.addWidget(QLabel("Metadata"))
        self.meta_list = QListWidget()
        ctrl.addWidget(self.meta_list)

        # ── plot area ──
        self.plotter = SpectraPlotter(self)
        plot_container = QWidget()
        plot_l = QVBoxLayout(plot_container)
        plot_l.setContentsMargins(0, 0, 0, 0)
        plot_l.addWidget(self.plotter.toolbar)
        plot_l.addWidget(self.plotter.canvas)

        main_l.addWidget(plot_container, 2)

    def _populate_experiment_combo(self):
        names = sorted({e["name"] for e in self.data_entries})
        self.exp_combo.clear()
        self.exp_combo.addItems(names)
        if names:
            max_entry = max(self.data_entries, key=lambda e: e["cycle"])
            default = max_entry["name"]
            idx = names.index(default)
            self.exp_combo.setCurrentIndex(idx)


    def _connect_signals(self):
        self.exp_combo.currentIndexChanged.connect(self._on_experiment_changed)

        widgets = (
            self.first_cb, self.last_cb, self.avg_cb,
            self.mod_scp, self.mod_dcpi,
            self.mod_dcpii, self.mod_scpc
        )
        for w in widgets:
            w.stateChanged.connect(self.on_selection_changed)
        for sb in (self.range_start, self.range_end):
            sb.valueChanged.connect(self.on_selection_changed)

        self.btn_export_comb.clicked.connect(self.on_export_combined)
        self.btn_export_sep.clicked.connect(self.on_export_separate)

    def _on_experiment_changed(self):
        self._update_range_bounds()
        self.on_selection_changed()

    def _update_range_bounds(self):
        name = self.exp_combo.currentText()
        cycles = sorted({
            e["cycle"] for e in self.data_entries
            if e["name"] == name
        })
        if not cycles:
            return
        lo, hi = cycles[0], cycles[-1]
        for sb in (self.range_start, self.range_end):
            sb.setRange(lo, hi)
        self.range_start.setValue(lo)
        self.range_end.setValue(hi)

    def get_selected_entries(self):
        # filter to the chosen experiment
        name = self.exp_combo.currentText()
        entries = [e for e in self.data_entries if e["name"] == name]

        # then the rest of your logic stays the same, e.g.:
        by_cycle = {}
        for e in entries:
            by_cycle.setdefault(e["cycle"], []).append(e)

        cycles = []
        if self.first_cb.isChecked():
            cycles.append(min(by_cycle))
        if self.last_cb.isChecked():
            cycles.append(max(by_cycle))
        if self.avg_cb.isChecked():
            lo, hi = self.range_start.value(), self.range_end.value()
            sel = [c for c in by_cycle if lo <= c <= hi]
            out = []
            for cam in ("A","B"):
                subset = [e for e in entries
                          if e["camera"]==cam and e["cycle"] in sel]
                avg = average_spectra(subset)
                if avg: out.append(avg)
            return out

         # if the user hasn’t chosen First, Last or Average, return nothing
        if not cycles and not self.avg_cb.isChecked():
            if self._first_draw:
                cycles = [max(by_cycle)]
            else:
                return []

        # collect A&B for each chosen cycle
        out = []
        for c in sorted(cycles):
            out += by_cycle[c]
        return out

    def get_modalities(self):
        return {
            "SCP":   self.mod_scp.isChecked(),
            "DCPI":  self.mod_dcpi.isChecked(),
            "DCPII": self.mod_dcpii.isChecked(),
            "SCPc":  self.mod_scpc.isChecked(),
        }

    def on_selection_changed(self):
        sel = self.get_selected_entries()
        mods = self.get_modalities()
        # update plot
        self.plotter.update_plot(sel, mods)
        # update metadata panel
        self.meta_list.clear()
        for e in sel:
            info = e["info"]
            self.meta_list.addItem(
                f"{e['name']} | Cam {e['camera']} | Cycle {e['cycle']}  "
                f"Gain={info.get('gain')}  Power={info.get('power')}mW  "
                f"Times={info.get('total_time')}"
            )

    def on_export_combined(self):
        sel = self.get_selected_entries()
        if len(sel) != 2:
            QMessageBox.warning(self, "Export Combined",
                                "Need exactly two spectra (A & B) to combine.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Combined Spectrum",
            os.path.join(self.working_dir, "combined.txt"),
            "Text Files (*.txt)"
        )
        if not path:
            return

        df = merge_a_b(sel[0]["data"], sel[1]["data"])
        export_combined(path, df)
        QMessageBox.information(self, "Export Combined",
                                f"Combined spectrum written to:\n{path}")

    def on_export_separate(self):
        sel = self.get_selected_entries()
        if not sel:
            QMessageBox.warning(self, "Export Separate", "No spectra selected.")
            return

        # build list of checked modalities
        mods = [m for m, on in self.get_modalities().items() if on]
        if not mods:
            QMessageBox.warning(self, "Export Separate", "No modalities selected.")
            return

        out_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.working_dir
        )
        if not out_dir:
            return

        base = os.path.join(out_dir, sel[0]["name"])
        export_separately(base, sel, mods)

        QMessageBox.information(
            self, "Export Separate",
            f"Exported {2*len(sel)*len(mods)} files (one Raman + one ROA per modality) to:\n{out_dir}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
