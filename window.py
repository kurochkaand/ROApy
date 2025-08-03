# window.py
import os
from PyQt6.QtWidgets import QToolBar, QFileDialog, QMessageBox, QMainWindow, QCheckBox, QListWidgetItem
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QSettings, Qt
import math
from ui import SpectraViewerUI
from file_loader import load_data_files
from plotter import SpectraPlotter
from data_processor import merge_a_b, baseline_als
from baseline_manager import BaselineManager, BaselineParams
from exporter import export_combined, export_separately
from selection_cycles import SelectionOfCyclesWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectra Viewer")
        self.setWindowIcon(QIcon("app_icon.ico")) 
        self.resize(900, 900)
        self.baseline_mgr = BaselineManager(self._uid_for_entry, baseline_als)
        self.normalized = False
        self.main_toolbar = QToolBar("Main")
        self.addToolBar(self.main_toolbar)
        self.select_cycles_action = QAction("Create selection of measurement cycles", self)
        self.main_toolbar.addAction(self.select_cycles_action)
        self.select_cycles_action.triggered.connect(self.open_selection_window)

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
        self._update_modalities()
        self._populate_individual_list()
        self._connect_signals()

        self.on_selection_changed()

    def _populate_experiment_combo(self):
        names = sorted({e['name'] for e in self.data_entries})
        self.ui.exp_combo.clear()
        self.ui.exp_combo.addItems(names)
        if names:
            default = max(self.data_entries, key=lambda e: e['file_index'])['name']
            idx = names.index(default)
            self.ui.exp_combo.setCurrentIndex(idx)

    def get_selected_entries(self):
        # Otherwise use explicit selection in the list
        items = self.ui.indiv_list.selectedItems()
        if not items and self.ui.indiv_list.count() > 0:
            # Auto-select last row if nothing is selected
            last_row = self.ui.indiv_list.count() - 1
            self.ui.indiv_list.setCurrentRow(last_row)
            items = [self.ui.indiv_list.item(last_row)]

        selected = []
        for it in items:
            raw = it.data(Qt.ItemDataRole.UserRole)
            if isinstance(raw, list):
                selected.extend(raw)
            else:
                selected.append(raw)
        return selected

    def _normalize_copy(self, entries):
        """Return a NEW list of entries with data normalized if needed."""
        if not self.normalized:
            return entries
        out = []
        for e in entries:
            e2 = e.copy()
            df = e['data']
            norm_df = df.copy()
            total_time = e['info'].get('total_time', [1.0])
            duration = float(total_time[0]) if isinstance(total_time, (list, tuple)) else float(total_time)
            for col in norm_df.columns:
                if col != "Wavenumber":
                    norm_df[col] = norm_df[col] / duration
            e2['data'] = norm_df
            # mark the copy so the UID reflects normalization
            e2['__norm__'] = True
            out.append(e2)
        return out
    
    def _current_work_selection(self):
        """Selection as it is *processed* (avg + normalization)."""
        raw = self.get_selected_entries()
        return self._normalize_copy(raw)

    def _uid_for_entry(self, entry):
        """
        Build a stable key for a spectrum (file or averaged) including normalization state.
        """
        if entry.get('__kind__') == 'avg':
            lo, hi = entry['range']
            base = f"AVG::{entry['name']}::{entry['camera']}::{lo}-{hi}"
        else:
            # real file spectrum
            base = f"FILE::{entry.get('path', id(entry))}"
        norm_flag = "1" if entry.get('__norm__', False) else "0"
        return f"{base}::norm={norm_flag}"


    def _connect_signals(self):
        ui = self.ui
        ui.exp_combo.currentIndexChanged.connect(self._on_experiment_changed)
        for w in (ui.mod_scp, ui.mod_dcpi, ui.mod_dcpii, ui.mod_scpc):
            w.stateChanged.connect(self.on_selection_changed)
        for rb in (ui.radio_cam_a, ui.radio_cam_b, ui.radio_both):
            rb.toggled.connect(self._on_camera_mode_changed)            
        ui.btn_export_comb.clicked.connect(self.on_export_combined)
        ui.btn_export_sep.clicked.connect(self.on_export_separate)
        ui.btn_toggle_norm.clicked.connect(self.on_toggle_normalization)
        ui.btn_create_baseline.clicked.connect(self.on_create_baseline)
        ui.btn_subtract_created.clicked.connect(self.on_subtract_baseline)
        ui.btn_delete_baseline.clicked.connect(self.on_delete_baseline)
        ui.indiv_list.itemSelectionChanged.connect(self.on_selection_changed)

    def _on_experiment_changed(self):
        self._update_modalities()
        self._populate_individual_list()
        self.on_selection_changed()

    def get_modalities(self):
        return {k:cb.isChecked() for k,cb in {
            'SCP': self.ui.mod_scp, 'DCPI': self.ui.mod_dcpi,
            'DCPII': self.ui.mod_dcpii, 'SCPc': self.ui.mod_scpc
        }.items()}

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
        sel = self._normalize_copy(raw_sel)

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
        sel = self._current_work_selection()
        if not sel:
            QMessageBox.warning(self, "Create Baseline", "No spectra selected.")
            return

        params = BaselineParams(
            lam=1e5,
            p=self.ui.pressure_spin.value(),
            niter=self.ui.max_iter_spin.value(),
            start_wavenumber=self.ui.start_wav_spin.value()
        )
        mods = self.get_modalities()

        self.baseline_mgr.create(sel, mods, params)

        # replot spectra, then overlay baselines
        self.plotter.update_plot(sel, mods)
        self.plotter.draw_baselines(sel)

        QMessageBox.information(self, "Create Baseline", "Baseline(s) created and overlaid.")

    def on_subtract_baseline(self):
        sel = self._current_work_selection()
        if not sel:
            QMessageBox.warning(self, "Subtract Background", "No spectra selected.")
            return

        if not self.baseline_mgr.has_any(sel):
            QMessageBox.warning(self, "Subtract Background", "No baselines found. Please 'Create Baseline' first.")
            return

        new_entries = []
        for e in sel:
            # Deep copy the spectrum entry (so we don't change the original)
            import copy
            new_entry = copy.deepcopy(e)
            # Actually subtract the baseline on the copy
            self.baseline_mgr.subtract([new_entry], from_zero=self.ui.radio_zero.isChecked())
            # Modify the name/file_index to indicate baseline-corrected
            old_name = new_entry.get('name', '')
            old_index = new_entry.get('file_index', '')
            new_entry['name'] = old_name
            new_entry['file_index'] = f"{old_index}_blcorr"
            # Optionally: add a tag in metadata
            new_entry['info'] = dict(new_entry['info'])  # make a shallow copy if needed
            new_entry['info']['baseline_corrected'] = True
            new_entries.append(new_entry)

        # Insert new entries
        self.data_entries.extend(new_entries)
        self._populate_individual_list()
        self.on_selection_changed()
        QMessageBox.information(self, "Subtract Background", "Created baseline subtracted from spectra.")

    def on_delete_baseline(self):
        self.baseline_mgr.clear()
        for e in self.data_entries:
            e.pop("baselines", None)
        self.on_selection_changed()
        QMessageBox.information(self, "Delete Baseline", "Baselines cleared from the canvas.")


    def _populate_individual_list(self):
        """List only cycle numbers, filtered by Cam A/B/Both."""
        self.ui.indiv_list.clear()
        name = self.ui.exp_combo.currentText()
        entries = [e for e in self.data_entries if e['name']==name]

        # group by cycle → cameras
        by_cycle = {}
        for e in entries:
            by_cycle.setdefault(e['file_index'], {})[e['camera']] = e

        # decide mode
        if self.ui.radio_cam_a.isChecked():
            mode = 'A'
        elif self.ui.radio_cam_b.isChecked():
            mode = 'B'
        else:
            mode = 'Both'

        def cycle_sort_key(c):
            # ints sort before strings, and ints sort numerically
            return (isinstance(c, str), c)
        for cycle in sorted(by_cycle, key=cycle_sort_key):
            cams = by_cycle[cycle]
            if mode in ('A','B'):
                if mode not in cams:
                    continue
                data = cams[mode]
            else:  # Both
                if 'A' not in cams or 'B' not in cams:
                    continue
                data = [cams['A'], cams['B']]

            item = QListWidgetItem(f"Cycle {cycle}")
            # store either a single entry or a list of two
            item.setData(Qt.ItemDataRole.UserRole, data)
            self.ui.indiv_list.addItem(item)
        # Automatically select the last cycle in the list
        self.ui.indiv_list.clearSelection()
        count = self.ui.indiv_list.count()
        if count > 0:
            last_item = self.ui.indiv_list.item(count - 1)
            last_item.setSelected(True)
        if count:
            self.ui.indiv_list.setCurrentRow(count - 1)

    def _on_camera_mode_changed(self):
        self._populate_individual_list()
        self.on_selection_changed()

    def open_selection_window(self):
        # avoid opening duplicates
        if hasattr(self, 'selection_window') and self.selection_window.isVisible():
            self.selection_window.raise_()
            self.selection_window.activateWindow()
        else:
            self.selection_window = SelectionOfCyclesWindow(self)
            self.selection_window.show()

    def add_spectrum_entries(self, entries: list[dict]):
        # Called by SelectionOfCyclesWindow after summation
        self.data_entries.extend(entries)
        self._populate_individual_list()
        self.on_selection_changed()