# window.py
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QMainWindow, QCheckBox, QListWidgetItem
from PyQt6.QtCore import QSettings, Qt
import math
from ui import SpectraViewerUI
from file_loader import load_data_files
from plotter import SpectraPlotter
from data_processor import merge_a_b, average_spectra, baseline_als
from exporter import export_combined, export_separately
import numpy as np


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectra Viewer")
        self.resize(900, 900)
        self.baselines = {}
        self.normalized = False

        # Plotter instantiation
        self.plotter = SpectraPlotter(self)

        # UI setup
        self.ui = SpectraViewerUI()
        self.ui.setup_ui(self, self.plotter)

        # Settings & directory
        self.settings = QSettings("MyOrg", "SpectraViewer")
        last = self.settings.value("lastWorkingDir", os.getcwd())
        self.working_dir = QFileDialog.getExistingDirectory(
            self, "Select Working Directory", last,
            QFileDialog.Option.ShowDirsOnly
        )
        if not self.working_dir:
            self.close(); return
        self.settings.setValue("lastWorkingDir", self.working_dir)

        # Load data
        self.data_entries = load_data_files(self.working_dir)
        if not self.data_entries:
            QMessageBox.warning(
                self, "No Data",
                f"No valid spectra files found in:\n{self.working_dir}"
            )
            self.close(); return

        # Initial population & signals
        self._populate_experiment_combo()
        self._update_range_bounds()
        self._update_modalities()
        self._populate_individual_list()
        self._connect_signals()

        # First draw
        self._first_draw = True
        self.on_selection_changed()
        self._first_draw = False

    def _populate_experiment_combo(self):
        names = sorted({e['name'] for e in self.data_entries})
        self.ui.exp_combo.clear()
        self.ui.exp_combo.addItems(names)
        if names:
            default = max(self.data_entries, key=lambda e: e['file_index'])['name']
            idx = names.index(default)
            self.ui.exp_combo.setCurrentIndex(idx)

    def _populate_individual_list(self):
        """Fill the QListWidget with every (camera, cycle) entry for the current experiment."""
        self.ui.indiv_list.clear()
        name = self.ui.exp_combo.currentText()
        # all entries for this experiment
        entries = [e for e in self.data_entries if e['name'] == name]
        # sort by cycle then camera
        entries.sort(key=lambda e: (e['file_index'], e['camera']))
        for e in entries:
            text = f"Cycle {e['file_index']} | Cam {e['camera']}"
            item = QListWidgetItem(text)
            # stash the actual entry dict so we can grab it later
            item.setData(Qt.ItemDataRole.UserRole, e)
            self.ui.indiv_list.addItem(item)

    def _update_range_bounds(self):
        name = self.ui.exp_combo.currentText()
        cycles = sorted({e['file_index'] for e in self.data_entries if e['name']==name})
        if not cycles: return
        lo, hi = cycles[0], cycles[-1]
        for sb in (self.ui.range_start, self.ui.range_end):
            sb.setRange(lo, hi)
        self.ui.range_start.setValue(lo)
        self.ui.range_end.setValue(hi)

    def get_selected_entries(self):
        items = self.ui.indiv_list.selectedItems()
        if items:
            return [item.data(Qt.ItemDataRole.UserRole) for item in items]

        name = self.ui.exp_combo.currentText()
        entries = [e for e in self.data_entries if e['name']==name]
        by_cycle = {}
        for e in entries:
            by_cycle.setdefault(e['file_index'], []).append(e)
        cycles = []
        if self.ui.first_cb.isChecked(): cycles.append(min(by_cycle))
        if self.ui.last_cb.isChecked():  cycles.append(max(by_cycle))
        if self.ui.avg_cb.isChecked():
            lo, hi = self.ui.range_start.value(), self.ui.range_end.value()
            sel = [c for c in by_cycle if lo <= c <= hi]
            out=[]
            for cam in ('A','B'):
                avg = average_spectra([e for e in entries if e['camera']==cam and e['file_index'] in sel])
                if avg: out.append(avg)
            return out
        if not cycles and not self._first_draw:
            return []
        if not cycles:
            cycles=[max(by_cycle)]
        out=[]
        for c in sorted(cycles): out+=by_cycle[c]
        return out

    def _connect_signals(self):
        ui = self.ui
        ui.exp_combo.currentIndexChanged.connect(self._on_experiment_changed)
        for w in (ui.first_cb, ui.last_cb, ui.avg_cb,
                  ui.mod_scp, ui.mod_dcpi, ui.mod_dcpii, ui.mod_scpc):
            w.stateChanged.connect(self.on_selection_changed)
        for sb in (ui.range_start, ui.range_end):
            sb.valueChanged.connect(self.on_selection_changed)
        ui.btn_export_comb.clicked.connect(self.on_export_combined)
        ui.btn_export_sep.clicked.connect(self.on_export_separate)
        ui.btn_toggle_norm.clicked.connect(self.on_toggle_normalization)
        ui.btn_create_baseline.clicked.connect(self.on_create_baseline)
        ui.btn_subtract_created.clicked.connect(self.on_subtract_baseline)
        ui.btn_delete_baseline.clicked.connect(self.on_delete_baseline)
        ui.indiv_list.itemSelectionChanged.connect(self.on_selection_changed)

    def _on_experiment_changed(self):
        self._update_range_bounds()
        self._update_modalities()
        self._populate_individual_list()
        self.on_selection_changed()

    def get_modalities(self):
        return {k:cb.isChecked() for k,cb in {
            'SCP': self.ui.mod_scp, 'DCPI': self.ui.mod_dcpi,
            'DCPII': self.ui.mod_dcpii, 'SCPc': self.ui.mod_scpc
        }.items()}

    def on_selection_changed(self):
        sel  = self.get_selected_entries()
        mods = self.get_modalities()
        self.plotter.update_plot(sel, mods)
        self.ui.meta_list.clear()
        for e in sel:
            info = e['info']
            num_cycles = info.get("num_cycles", "N/A")
            self.ui.meta_list.addItem(
                f"{e['name']} | Cam {e['camera']} | File#{e['file_index']} | "
                f"Cycles={num_cycles}  Gain={info.get('gain')}  "
                f"Power={info.get('power')}mW  TotalTime={info.get('total_time')} s"
            )

    def on_export_combined(self):
        sel=self.get_selected_entries()
        if len(sel)!=2:
            QMessageBox.warning(self,"Export Combined",
                                "Need exactly two spectra (A & B) to combine.")
            return
        path,_=QFileDialog.getSaveFileName(
            self,"Save Combined Spectrum",
            os.path.join(self.working_dir,"combined.txt"),
            "Text Files (*.txt)"
        )
        if not path: return
        df=merge_a_b(sel[0]['data'],sel[1]['data'])
        export_combined(path,df)
        QMessageBox.information(self,"Export Combined",
                                f"Combined spectrum written to:\n{path}")

    def on_export_separate(self):
        sel=self.get_selected_entries()
        if not sel:
            QMessageBox.warning(self,"Export Separate","No spectra selected.")
            return
        mods=[m for m,on in self.get_modalities().items() if on]
        if not mods:
            QMessageBox.warning(self,"Export Separate","No modalities selected.")
            return
        out_dir=QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.working_dir
        )
        if not out_dir: return
        base=os.path.join(out_dir,sel[0]['name'])
        export_separately(base,sel,mods)
        QMessageBox.information(
            self,"Export Separate",
            f"Exported {2*len(sel)*len(mods)} files (…) to:\n{out_dir}"
        )

    def _update_modalities(self):
        """
        Enable/disable each modality checkbox based on whether the FIRST
        data point in that modality is non-zero—treating NaN or missing
        as zero.
        """
        name = self.ui.exp_combo.currentText()
        if not name:
            return
        entries = [e for e in self.data_entries if e['name'] == name]
        modality_info = {
            'DCPI':  ('mod_dcpi',  "DCPI Raman",  "DCPI ROA"),
            'DCPII': ('mod_dcpii', "DCPII Raman", "DCPII ROA"),
            'SCPc':  ('mod_scpc',  "SCPc Raman",  "SCPc ROA")
        }
        for mod, (attr, r_col, o_col) in modality_info.items():
            cb: QCheckBox = getattr(self.ui, attr)
            present = False
            for e in entries:
                df = e['data']
                if len(df) > 0 and r_col in df.columns:
                    r0 = df[r_col].iat[0]
                    if math.isnan(r0): r0 = 0
                else:
                    r0 = 0
                if len(df) > 0 and o_col in df.columns:
                    o0 = df[o_col].iat[0]
                    if math.isnan(o0): o0 = 0
                else:
                    o0 = 0
                if r0 != 0 or o0 != 0:
                    present = True
                    break
            cb.setEnabled(present)
            if not present:
                cb.setChecked(False)

    def on_toggle_normalization(self):
        """
        Toggle normalization on/off and update button text.
        """
        self.normalized = not self.normalized
        if self.normalized:
            self.ui.btn_toggle_norm.setText("Undo normalization")
        else:
            self.ui.btn_toggle_norm.setText("Normalize by TotalTime")
        self.on_selection_changed()

    def on_selection_changed(self):
        """
        Gather selected entries, apply normalization if requested,
        then plot and update metadata.
        """
        raw_sel = self.get_selected_entries()
        if self.normalized:
            sel = []
            for e in raw_sel:
                e_copy = e.copy()
                df = e['data']
                norm_df = df.copy()
                total_time = e['info'].get('total_time', [1.0])
                duration = float(total_time[0]) if isinstance(total_time, (list, tuple)) else float(total_time)
                for col in norm_df.columns:
                    if col != "Wavenumber":
                        norm_df[col] = norm_df[col] / duration
                e_copy['data'] = norm_df
                sel.append(e_copy)
        else:
            sel = raw_sel
        mods = self.get_modalities()
        self.plotter.update_plot(sel, mods)
        self.ui.meta_list.clear()
        for e in raw_sel:
            info = e['info']
            num_cycles = info.get("num_cycles", "N/A")
            t = info.get("total_time")
            self.ui.meta_list.addItem(
                f"{e['name']} | Cam {e['camera']} | File#{e['file_index']} | "
                f"Cycles={num_cycles}  Gain={info.get('gain')}  "
                f"Power={info.get('power')}mW  TotalTime={t} s"
            )
            
    def on_create_baseline(self):
        sel = self.get_selected_entries()
        if not sel:
            QMessageBox.warning(self, "Create Baseline", "No spectra selected.")
            return
        mods = self.get_modalities()
        niter = self.ui.max_iter_spin.value()
        p     = self.ui.pressure_spin.value()
        start = self.ui.start_wav_spin.value()
        for e in sel:
            e.pop("baselines", None)
        mod_to_col = {
            'SCP':   'SCP Raman',
            'DCPI':  'DCPI Raman',
            'DCPII': 'DCPII Raman',
            'SCPc':  'SCPc Raman'
        }
        for entry in sel:
            df    = entry["data"]
            x     = df["Wavenumber"].to_numpy()
            idx0 = np.searchsorted(x, start)
            raman_cols = [
                col
                for mod, on in mods.items()
                if on and (col := mod_to_col[mod]) in df.columns
            ]
            bas_dict = {}
            for col in raman_cols:
                y      = df[col].to_numpy()
                y_tail = y[idx0:]
                z_tail = baseline_als(
                    y_tail,
                    lam=1e5,
                    p=p,
                    niter=niter
                )
                z = np.zeros_like(y)
                z[idx0:] = z_tail
                bas_dict[col] = z

            entry["baselines"] = bas_dict
        self.plotter.update_plot(sel, mods)
        for entry in sel:
            x = entry["data"]["Wavenumber"].to_numpy()
            for col, z in entry["baselines"].items():
                self.plotter.ax_raman.plot(
                    x, z,
                    linestyle="--",
                    label=f"(Cam {entry['camera']}) {col} baseline"
                )
        self.plotter.canvas.draw()

        QMessageBox.information(
            self, "Create Baseline",
            "Baseline(s) created and overlaid."
        )


    def on_subtract_baseline(self):
        """Subtract the previously created baseline from the spectra."""
        sel = self.get_selected_entries()
        if not sel:
            QMessageBox.warning(self, "Subtract Background", "No spectra selected.")
            return

        any_baseline = any("baselines" in e for e in sel)
        if not any_baseline:
            QMessageBox.warning(self, "Subtract Background", "No baselines found. Please 'Create Baseline' first.")
            return

        from_zero = self.ui.radio_zero.isChecked()

        for entry in sel:
            df = entry["data"]
            bas = entry.get("baselines", {})
            for col, z in bas.items():
                y = df[col].to_numpy()
                if from_zero:
                    new = y - z
                else:
                    new = y - z + z.min()
                df[col] = new

        # refresh the plot with the subtracted data
        self.on_selection_changed()
        QMessageBox.information(self, "Subtract Background", "Created baseline subtracted from spectra.")

    def on_delete_baseline(self):
        """Remove all baseline overlays (and cached baselines)."""
        for e in self.data_entries:
            e.pop("baselines", None)
        self.on_selection_changed()
        QMessageBox.information(self, "Delete Baseline", "Baselines cleared from the canvas.")