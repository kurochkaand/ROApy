from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class SpectraPlotter:
    def __init__(self, parent):
        self.canvas = FigureCanvas(Figure())
        self.ax = self.canvas.figure.add_subplot(111)

    def update_plot(self, spectra_entries, modalities):
        self.ax.clear()
        modality_keys = {
            "SCP": ("SCP Raman", "SCP ROA"),
            "DCPI": ("DCPI Raman", "DCPI ROA"),
            "DCPII": ("DCPII Raman", "DCPII ROA"),
            "SCPc": ("SCPc Raman", "SCPc ROA")
        }

        for entry in spectra_entries:
            df = entry["data"]
            label_prefix = f"{entry['name']} (Cam {entry['camera']})"
            for mod, (raman_col, roa_col) in modality_keys.items():
                if modalities.get(mod):
                    self.ax.plot(df["Wavenumber"], df[raman_col], label=f"{label_prefix} {mod} Raman")
                    self.ax.plot(df["Wavenumber"], df[roa_col], label=f"{label_prefix} {mod} ROA")

        self.ax.set_xlabel("Wavenumber (1/cm)")
        self.ax.set_ylabel("Intensity")
        self.ax.legend()
        self.canvas.figure.tight_layout()
        self.canvas.draw()
