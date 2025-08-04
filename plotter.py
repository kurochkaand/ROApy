# plotter.py
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT
)
from matplotlib.figure import Figure

class SlimToolbar(NavigationToolbar2QT):
    # filter the toolitems to just the ones we want
    toolitems = [ti for ti in NavigationToolbar2QT.toolitems if ti[0] in ("Home", "Back", "Save")]

class SpectraPlotter:
    def __init__(self, parent):
        # create figure with two rows, shared X
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = SlimToolbar(self.canvas, self.canvas)
        self.ax_raman = self.figure.add_subplot(211)
        self.ax_roa   = self.figure.add_subplot(212, sharex=self.ax_raman)

        # pan state
        self._panning = False
        self._pan_press_event = None
        self._active_ax = None
        self._orig_xlim_raman = None
        self._orig_ylim_raman = None
        self._orig_xlim_roa = None
        self._orig_ylim_roa = None

        # flag to ensure initial view is pushed once
        self._initial_view_pushed = False

        # connect for pan and wheel zoom
        self.canvas.mpl_connect("button_press_event", self._on_button_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("button_release_event", self._on_button_release)
        self.canvas.mpl_connect("scroll_event", self._on_scroll)

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

        # push the initial view into the toolbar's stack once so "home" works
        if not self._initial_view_pushed:
            self.toolbar.push_current()
            self._initial_view_pushed = True

    # ---- event handlers for smooth pan and wheel Y-zoom ----
    def _on_button_press(self, event):
        if event.button == 1 and event.inaxes in (self.ax_raman, self.ax_roa):
            # start pan
            self._panning = True
            self._pan_press_event = event
            self._active_ax = event.inaxes
            # store original limits
            self._orig_xlim_raman = self.ax_raman.get_xlim()
            self._orig_ylim_raman = self.ax_raman.get_ylim()
            self._orig_xlim_roa = self.ax_roa.get_xlim()
            self._orig_ylim_roa = self.ax_roa.get_ylim()

    def _on_motion(self, event):
        if not self._panning or self._pan_press_event is None or event.inaxes is not self._active_ax:
            return
        # compute delta in data space using display->data inversion for smoothness
        inv = self._active_ax.transData.inverted()
        start_data = inv.transform((self._pan_press_event.x, self._pan_press_event.y))
        curr_data = inv.transform((event.x, event.y))
        dx = start_data[0] - curr_data[0]
        dy = start_data[1] - curr_data[1]

        # pan X for both (shared X)
        x0_r, x1_r = self._orig_xlim_raman
        self.ax_raman.set_xlim(x0_r + dx, x1_r + dx)
        x0_o, x1_o = self._orig_xlim_roa
        self.ax_roa.set_xlim(x0_o + dx, x1_o + dx)

        # pan Y only on active axis
        if self._active_ax is self.ax_raman:
            y0, y1 = self._orig_ylim_raman
            self.ax_raman.set_ylim(y0 + dy, y1 + dy)
        elif self._active_ax is self.ax_roa:
            y0, y1 = self._orig_ylim_roa
            self.ax_roa.set_ylim(y0 + dy, y1 + dy)

        self.canvas.draw_idle()

    def _on_button_release(self, event):
        if event.button == 1 and self._panning:
            # finish pan and record new view so toolbar can navigate/reset
            self._panning = False
            self._pan_press_event = None
            self._active_ax = None
            self.toolbar.push_current()

    def _on_scroll(self, event):
        if event.inaxes not in (self.ax_raman, self.ax_roa):
            return
        ax = event.inaxes
        if event.ydata is None:
            return
        # zoom factor: positive step -> zoom in
        base_scale = 1.1
        step = getattr(event, "step", None)
        if step is None:
            return
        if step > 0:
            scale = 1 / (base_scale ** step)
        else:
            scale = base_scale ** (-step)
        ymin, ymax = ax.get_ylim()
        ydata = event.ydata
        dy_low = ydata - ymin
        dy_high = ymax - ydata
        new_low = ydata - dy_low * scale
        new_high = ydata + dy_high * scale
        ax.set_ylim(new_low, new_high)
        self.canvas.draw_idle()
        # record the zoomed view
        self.toolbar.push_current()


    # def _on_mouse_move(self, event):
    #     for ax in (self.ax_raman, self.ax_roa):
    #         for txt in list(ax.texts):
    #             if txt.get_gid() == "cursor":
    #                 txt.remove()
    #     if event.inaxes in (self.ax_raman, self.ax_roa) and event.xdata is not None:
    #         x, y = event.xdata, event.ydata
    #         event.inaxes.annotate(
    #             f"{x:.2f}, {y:.2f}",
    #             xy=(x, y), xytext=(10, 10), textcoords="offset points",
    #             bbox=dict(boxstyle="round", fc="white", alpha=0.7),
    #             fontsize="small", gid="cursor"
    #         )
    #     self.canvas.draw_idle()
        
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