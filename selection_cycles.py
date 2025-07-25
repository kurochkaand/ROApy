from PyQt6.QtWidgets import (
    QWidget, QSplitter, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

class SelectionOfCyclesWindow(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Selection of measurement cycles")
        self.resize(800, 600)

        # Filter entries for current experiment
        exp_name = main_window.ui.exp_combo.currentText()
        entries = [e for e in main_window.data_entries if e['name'] == exp_name]
        # Group entries by cycle index
        self.cycles = {}  # cycle_index -> {'A': entryA, 'B': entryB}
        for e in entries:
            idx = e['file_index']
            cam = e['camera']
            self.cycles.setdefault(idx, {})[cam] = e
        self.sorted_cycles = sorted(self.cycles.keys(), key=lambda x: (isinstance(x, str), x))

        # Map each cycle to its previous cycle (for Δ calculation)
        self.prev_cycle = {
            cycle: (self.sorted_cycles[i-1] if i > 0 else None)
            for i, cycle in enumerate(self.sorted_cycles)
        }

        # Build UI: splitter with controls (left) and plot (right)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # ── Left panel: cycle list + buttons ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.list_widget = QListWidget()
        for cycle in self.sorted_cycles:
            item = QListWidgetItem(f"Cycle {cycle}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, cycle)
            self.list_widget.addItem(item)
        self.list_widget.itemChanged.connect(self.on_toggle_cycle)
        left_layout.addWidget(self.list_widget)

        btns = QHBoxLayout()
        self.btn_select_all = QPushButton("Select all")
        self.btn_clear = QPushButton("Clear selection")
        self.btn_help = QPushButton("Help")
        btns.addWidget(self.btn_select_all)
        btns.addWidget(self.btn_clear)
        btns.addWidget(self.btn_help)
        left_layout.addLayout(btns)

        self.btn_select_all.clicked.connect(self.select_all)
        self.btn_clear.clicked.connect(self.clear_selection)
        self.btn_help.clicked.connect(self.show_help)

        splitter.addWidget(left)

        # ── Right panel: Matplotlib canvas ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax_raman = self.figure.add_subplot(211)
        self.ax_roa = self.figure.add_subplot(212, sharex=self.ax_raman)
        self.ax_raman.set_ylabel("Raman Intensity")
        self.ax_roa.set_xlabel("Wavenumber")
        self.ax_roa.set_ylabel("ROA Intensity")
        right_layout.addWidget(self.canvas)
        splitter.addWidget(right)
        splitter.setSizes([int(0.3 * self.width()), int(0.7 * self.width())])

        # ── Summation button ──
        self.btn_summate = QPushButton("Summate selected cycles")
        self.btn_summate.clicked.connect(self.summate_selected)

        # ── Main layout ──
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.btn_summate)
        self.setLayout(main_layout)

    def select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def clear_selection(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def show_help(self):
        QMessageBox.information(
            self, "Help",
            "Check one or more cycles\n"
            "▶ cycles overlay their Δ signals as soon as they're toggled\n"
            "▶ click 'Summate selected cycles' to combine into a new spectrum"
        )

    def on_toggle_cycle(self, item: QListWidgetItem):
        cycle = item.data(Qt.ItemDataRole.UserRole)
        prev = self.prev_cycle[cycle]

        # Plot or remove Δ traces for both cameras
        for cam in ('A', 'B'):
            entry = self.cycles[cycle].get(cam)
            if not entry:
                continue
            df_curr = entry['data']
            # Determine previous spectrum
            if prev is None or cam not in self.cycles.get(prev, {}):
                df_prev = df_curr.copy()
                for c in df_prev.columns:
                    if c != 'Wavenumber':
                        df_prev[c] = 0
            else:
                df_prev = self.cycles[prev][cam]['data']
            # Compute Δ
            df_delta = df_curr.copy()
            for c in df_curr.columns:
                if c != 'Wavenumber':
                    df_delta[c] = df_curr[c] - df_prev[c]

            label_prefix = f"Δ Cycle {cycle} (Cam {cam})"
            # Add or remove lines
            if item.checkState() == Qt.CheckState.Checked:
                # Raman:
                for c in df_delta.columns:
                    if 'Raman' in c:
                        self.ax_raman.plot(df_delta['Wavenumber'], df_delta[c], label=f"{label_prefix} {c}")
                # ROA:
                for c in df_delta.columns:
                    if 'ROA' in c:
                        self.ax_roa.plot(df_delta['Wavenumber'], df_delta[c], label=f"{label_prefix} {c}")
            else:
                # Remove matching lines
                for ax in (self.ax_raman, self.ax_roa):
                    lines_to_remove = [ln for ln in ax.lines if f"Δ Cycle {cycle} (Cam" in ln.get_label()]
                    for ln in lines_to_remove:
                        ln.remove()
        # Refresh legend & canvas
        self.figure.tight_layout()
        self.canvas.draw()

    def summate_selected(self):
        # Collect selected cycles
        selected = [
            self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.list_widget.count())
            if self.list_widget.item(i).checkState() == Qt.CheckState.Checked
        ]
        if not selected:
            QMessageBox.warning(self, "No selection", "Please select at least one cycle.")
            return

        # Prepare metadata and Δ data lists
        gains, powers, times = [], [], []
        deltas_A, deltas_B = [], []
        import pandas as pd
        for cycle in selected:
            for cam, container in (('A', deltas_A), ('B', deltas_B)):
                entry = self.cycles[cycle].get(cam)
                if not entry:
                    continue
                info = entry['info']
                if cam == 'A':
                    gains.append(info['gain'])
                    powers.append(info['power'])
                    t = info['total_time']
                    times.append(sum(t) if isinstance(t, (list, tuple)) else t)
                # Δ computation same as on_toggle
                prev = self.prev_cycle[cycle]
                df_curr = entry['data']
                if prev is None or cam not in self.cycles.get(prev, {}):
                    df_prev = df_curr.copy()
                    for c in df_prev.columns:
                        if c != 'Wavenumber': df_prev[c] = 0
                else:
                    df_prev = self.cycles[prev][cam]['data']
                df_delta = df_curr.copy()
                for c in df_curr.columns:
                    if c != 'Wavenumber': df_delta[c] = df_curr[c] - df_prev[c]
                container.append(df_delta)

        # Sum pointwise
        def sum_dfs(dfs):
            df_sum = dfs[0].copy()
            for df in dfs[1:]:
                for c in df.columns:
                    if c != 'Wavenumber':
                        df_sum[c] += df[c]
            return df_sum

        sum_A = sum_dfs(deltas_A)
        sum_B = sum_dfs(deltas_B)

        # Build new spectrum entries
        name = self.main_window.ui.exp_combo.currentText()
        meta = {
            'Cycles': len(selected),
            'Gain': sum(gains) / len(gains),
            'Power': sum(powers) / len(powers),
            'TotalTime': sum(times),
        }
        new_entries = []
        for cam, df in (('A', sum_A), ('B', sum_B)):
            new_entries.append({
                'name': name,
                'camera': cam,
                'file_index': f"sum_{min(selected)}–{max(selected)}",
                'info': meta,
                'data': df,
                'path': None,
            })

        # Insert into main window and close
        self.main_window.add_spectrum_entries(new_entries)
        self.close()
