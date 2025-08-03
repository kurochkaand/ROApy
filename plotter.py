# plotter.py
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
from matplotlib.figure import Figure

class SpectraPlotter:
    def __init__(self, parent):
        # create figure with two rows, shared X
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self.canvas)
        self.ax_raman = self.figure.add_subplot(211)
        self.ax_roa   = self.figure.add_subplot(212, sharex=self.ax_raman)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    def update_plot(self, spectra_entries, modalities):
        # clear both axes
        self.ax_raman.clear()
        self.ax_roa.clear()
        modality_keys = {
            "SCP":   ("SCP Raman",  "SCP ROA"),
            "DCPI":  ("DCPI Raman", "DCPI ROA"),
            "DCPII": ("DCPII Raman","DCPII ROA"),
            "SCPc":  ("SCPc Raman", "SCPc ROA")
        }

        # plot each trace into the appropriate axis
        for entry in spectra_entries:
            df = entry["data"]
            cam = f"(Cam. {entry['camera']})"
            name = f"Cyc. {entry['file_index']}"
            for mod, (raman_col, roa_col) in modality_keys.items():
                if modalities.get(mod):
                    # Raman on top
                    self.ax_raman.plot(
                        df["Wavenumber"], df[raman_col],
                        label=f"{name} {cam} {mod}"
                    )
                    # ROA on bottom
                    self.ax_roa.plot(
                        df["Wavenumber"], df[roa_col],
                    )

        # annotate axes
        self.ax_raman.set_ylabel("Raman Intensity")
        self.ax_roa.set_xlabel("Wavenumber (1/cm)")
        self.ax_roa.set_ylabel("ROA Intensity")

        # optional grids
        self.ax_raman.grid(True, linestyle='--', alpha=0.3)
        self.ax_roa.grid(True,   linestyle='--', alpha=0.3)

        # legends (only if there are lines)
        if self.ax_raman.lines:
            self.ax_raman.legend(loc="upper right", fontsize="small")

        # tighten up spacing so labels don’t overlap
        self.figure.tight_layout()
        self.canvas.draw()
    def _on_mouse_move(self, event):
        # remove old cursor-annotations
        for ax in (self.ax_raman, self.ax_roa):
            for txt in list(ax.texts):
                if txt.get_gid() == "cursor":
                    txt.remove()

        # if over one of our axes, show new annotation
        if event.inaxes in (self.ax_raman, self.ax_roa) and event.xdata is not None:
            x, y = event.xdata, event.ydata
            event.inaxes.annotate(
                f"{x:.2f}, {y:.2f}",
                xy=(x, y), xytext=(10, 10), textcoords="offset points",
                bbox=dict(boxstyle="round", fc="white", alpha=0.7),
                fontsize="small", gid="cursor"
            )

        # schedule a redraw
        self.canvas.draw_idle()
        
    def draw_baselines(self, entries):
        for e in entries:
            bas = e.get("baselines") or {}
            if not bas:
                continue
            x = e["data"]["Wavenumber"].to_numpy()
            for col, z in bas.items():
                self.ax_raman.plot(
                    x, z, linestyle="--",
                    label=f"(Cam {e['camera']}) {col} baseline"
                )
        self.canvas.draw_idle()