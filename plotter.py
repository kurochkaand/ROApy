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
            prefix = f"{entry['name']} (Cam {entry['camera']})"
            for mod, (raman_col, roa_col) in modality_keys.items():
                if modalities.get(mod):
                    # Raman on top
                    self.ax_raman.plot(
                        df["Wavenumber"], df[raman_col],
                        label=f"{prefix} {mod} Raman"
                    )
                    # ROA on bottom
                    self.ax_roa.plot(
                        df["Wavenumber"], df[roa_col],
                        label=f"{prefix} {mod} ROA"
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
        if self.ax_roa.lines:
            self.ax_roa.legend(loc="upper right", fontsize="small")

        # tighten up spacing so labels don’t overlap
        self.figure.tight_layout()
        self.canvas.draw()