# window.py
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QMainWindow, QCheckBox, QTreeWidgetItem
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSettings, Qt
import math
from ui import SpectraViewerUI
from file_loader import load_data_files
from plotter import SpectraPlotter
from data_processor import merge_a_b, baseline_als
from baseline_manager import BaselineManager, BaselineParams
from exporter import export_combined, export_separately
from selection_cycles import SelectionOfCyclesWindow
import copy

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectra Viewer")
        self.setWindowIcon(QIcon("app_icon.ico")) 
        self.resize(900, 900)
        self.baseline_mgr = BaselineManager(self._uid_for_entry, baseline_als)
        self.normalized = False

        # Plotter instantiation
        self.plotter = SpectraPlotter(self)

        # UI setup
        self.ui = SpectraViewerUI()
        self.ui.setup_ui(self, self.plotter)
        self.ui.btn_create_selection.clicked.connect(self.open_selection_window)
        self.ui.btn_add_working_dir.clicked.connect(self.on_add_working_dir)

        # Connect the new button to opening selection window
        self.ui.btn_create_selection.clicked.connect(self.open_selection_window)

        # Settings & directory
        self.ui.btn_subtract_created.setEnabled(False)
        self.ui.btn_delete_baseline.setEnabled(False)
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
        self._update_modalities()
        self._populate_individual_list()
        self._connect_signals()
        self._select_last_spectrum()
        self.on_selection_changed()

    def get_selected_entries(self):
        items = self.ui.tree_list.selectedItems()
        selected = []
        for it in items:
            raw = it.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(raw, list):
                selected.extend(raw)
            elif raw:
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
            # real file spectrum — include camera so A vs B (or path=None duplicates) don’t collide
            base = f"FILE::{entry.get('path', id(entry))}::Cam{entry.get('camera', '?')}"
        norm_flag = "1" if entry.get('__norm__', False) else "0"
        return f"{base}::norm={norm_flag}"


    def _connect_signals(self):
        ui = self.ui
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
        ui.tree_list.itemSelectionChanged.connect(self.on_selection_changed)

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
            f"Exported {2*len(sel)*len(mods)} files to:\n{out_dir}"
        )

    def _update_modalities(self):
        """
        Enable/disable each modality checkbox based on whether any data entry
        contains non-zero values for that modality.
        """
        entries = self.data_entries
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
                if r_col in df.columns and not df[r_col].isna().all() and df[r_col].any():
                    present = True
                    break
                if o_col in df.columns and not df[o_col].isna().all() and df[o_col].any():
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
            self._update_baseline_buttons()
            num_cycles = info.get("num_cycles", "N/A")
            t = info.get("total_time")
            self.ui.meta_list.addItem(
                f"{e['name']} | Cam {e['camera']} | File#{e['file_index']} | "
                f"Cycles={num_cycles}  Gain={info.get('gain')}  "
                f"Power={info.get('power')}mW  TotalTime={t} s"
            )
            
    def on_create_baseline(self):
        sel = self._current_work_selection()
        params = BaselineParams(
            lam=1e5,
            p=self.ui.pressure_spin.value()*1e-4,
            niter=self.ui.max_iter_spin.value(),
            start_wavenumber=self.ui.start_wav_spin.value()
        )
        mods = self.get_modalities()

        self.baseline_mgr.create(sel, mods, params)

        # replot spectra, then overlay baselines
        self.plotter.update_plot(sel, mods)
        self.plotter.draw_baselines(sel)
        self._update_baseline_buttons()

    def on_subtract_baseline(self):
        sel = self._current_work_selection()
        new_entries = []
        for e in sel:
            # Deep copy the spectrum entry (so we don't change the original)
            new_entry = copy.deepcopy(e)
            # Actually subtract the baseline on the copy
            self.baseline_mgr.subtract([new_entry])
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
        self._update_baseline_buttons()

    def on_delete_baseline(self):
        self.baseline_mgr.clear()
        for e in self.data_entries:
            e.pop("baselines", None)
        self.on_selection_changed()
        self._update_baseline_buttons()

    def _update_baseline_buttons(self):
        """
        Enable the 'Subtract Baseline' and 'Delete Baseline' buttons
        only if there is at least one baseline for the current selection.
        """
        sel = self._current_work_selection()
        has_baseline = self.baseline_mgr.has_any(sel)
        self.ui.btn_subtract_created.setEnabled(has_baseline)
        self.ui.btn_delete_baseline.setEnabled(has_baseline)

    def _populate_individual_list(self):
        self.ui.tree_list.clear()
        cam_mode = (
            'A' if self.ui.radio_cam_a.isChecked() else
            'B' if self.ui.radio_cam_b.isChecked() else
            'Both'
        )

        # Group by experiment name
        by_experiment = {}
        for entry in self.data_entries:
            by_experiment.setdefault(entry['name'], []).append(entry)

        for exp_name, entries in sorted(by_experiment.items()):
            exp_item = QTreeWidgetItem([exp_name])
            exp_item.setFlags(exp_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)  # make experiment unselectable

            # Group entries by file_index (cycle)
            by_cycle = {}
            for e in entries:
                by_cycle.setdefault(e['file_index'], {})[e['camera']] = e

            def _cycle_sort_key(cycle):
                # Sort integers numerically first, then strings alphabetically
                return (isinstance(cycle, str), cycle)

            for cycle, cams in sorted(by_cycle.items(), key=lambda item: _cycle_sort_key(item[0])):
                if cam_mode in ('A', 'B'):
                    if cam_mode not in cams:
                        continue
                    data = cams[cam_mode]
                else:  # Both
                    if 'A' not in cams or 'B' not in cams:
                        continue
                    data = [cams['A'], cams['B']]

                item = QTreeWidgetItem([f"Cycle {cycle}"])
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                exp_item.addChild(item)

            if exp_item.childCount() > 0:
                self.ui.tree_list.addTopLevelItem(exp_item)
                exp_item.setExpanded(True)

    def _on_camera_mode_changed(self):
        self._populate_individual_list()
        self.on_selection_changed()

    def open_selection_window(self):
        # avoid opening duplicates
        if hasattr(self, 'selection_window') and self.selection_window.isVisible():
            self.selection_window.raise_()
            self.selection_window.activateWindow()
        else:
            sel = self.get_selected_entries()
            exp_name = sel[0]["name"] if sel else None
            self.selection_window = SelectionOfCyclesWindow(self, exp_name)
            self.selection_window.show()

    def add_spectrum_entries(self, entries: list[dict]):
        # Called by SelectionOfCyclesWindow after summation
        self.data_entries.extend(entries)
        self._populate_individual_list()
        self.on_selection_changed()
    def _select_last_spectrum(self):
        tree = self.ui.tree_list
        # no experiments? bail
        if tree.topLevelItemCount() == 0:
            return
        # pick the last experiment node
        last_exp = tree.topLevelItem(tree.topLevelItemCount() - 1)
        if last_exp.childCount() == 0:
            return
        # pick its last cycle
        last_cycle = last_exp.child(last_exp.childCount() - 1)
        tree.setCurrentItem(last_cycle)      # focus
        last_cycle.setSelected(True)         # actually select

    def on_add_working_dir(self):
        """Prompt for another directory and merge its data entries (skipping already-loaded files)."""
        last = self.settings.value("lastWorkingDir", os.getcwd())
        new_dir = QFileDialog.getExistingDirectory(
            self, "Select Additional Working Directory", last,
            QFileDialog.Option.ShowDirsOnly
        )
        if not new_dir:
            return

        new_entries = load_data_files(new_dir)
        if not new_entries:
            QMessageBox.warning(
                self, "No Data",
                f"No valid spectra files found in:\n{new_dir}"
            )
            return

        # Filter out duplicates based on path
        existing_paths = {e.get("path") for e in self.data_entries}
        added = [e for e in new_entries if e.get("path") not in existing_paths]
        if not added:
            QMessageBox.information(
                self, "Add Working Directory",
                "All spectra from the selected directory are already loaded."
            )
            return

        self.data_entries.extend(added)
        self.settings.setValue("lastWorkingDir", new_dir)

        # Refresh UI/state
        self._update_modalities()
        self._populate_individual_list()
        self.on_selection_changed()
