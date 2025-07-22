# baseline_manager.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, Callable
import numpy as np
import pandas as pd

# Map UI modality toggles → Raman column names
MOD_TO_COL = {
    "SCP":  "SCP Raman",
    "DCPI": "DCPI Raman",
    "DCPII":"DCPII Raman",
    "SCPc": "SCPc Raman",
}

@dataclass
class BaselineParams:
    lam: float = 1e5          # ALS lambda
    p: float = 0.01           # ALS asymmetry parameter
    niter: int = 10           # ALS iterations
    start_wavenumber: float = 0.0  # from which wavenumber to start fitting

class BaselineManager:
    """
    Pure 'model' layer for baselines:
    - stores cached baselines by a stable UID
    - computes / subtracts / deletes baselines on spectra entries
    No plotting, no UI.
    """
    def __init__(self,
                 uid_fn: Callable[[dict], str],
                 als_fn: Callable[..., np.ndarray]):
        self._uid_fn = uid_fn
        self._als_fn = als_fn
        self._cache: Dict[str, Dict[str, np.ndarray]] = {}

    # ---------- Public API ----------
    def create(self,
               entries: Iterable[dict],
               mods: Dict[str, bool],
               params: BaselineParams) -> None:
        """Compute and attach baselines to each entry in-place."""
        for e in entries:
            e.pop("baselines", None)  # reset
            uid = self._uid_fn(e)

            df: pd.DataFrame = e["data"]
            x = df["Wavenumber"].to_numpy()
            idx0 = np.searchsorted(x, params.start_wavenumber)

            bas_dict: Dict[str, np.ndarray] = {}
            for mod, on in mods.items():
                if not on:
                    continue
                col = MOD_TO_COL.get(mod)
                if col not in df.columns:
                    continue
                y = df[col].to_numpy()
                y_tail = y[idx0:]
                z_tail = self._als_fn(y_tail, lam=params.lam, p=params.p, niter=params.niter)
                z = np.zeros_like(y)
                z[idx0:] = z_tail
                bas_dict[col] = z

            e["baselines"] = bas_dict
            self._cache[uid] = bas_dict

    def subtract(self,
                 entries: Iterable[dict],
                 from_zero: bool = True) -> None:
        """Subtract cached/attached baselines from spectra in-place."""
        for e in entries:
            self._attach_cached_if_missing(e)
            bas = e.get("baselines", {})
            if not bas:
                continue
            df: pd.DataFrame = e["data"]
            for col, z in bas.items():
                if col not in df.columns:
                    continue
                y = df[col].to_numpy()
                new_y = (y - z) if from_zero else (y - z + z.min())
                df[col] = new_y
            # keep cache (baseline can be reused)

    def clear(self, entries: Iterable[dict] | None = None) -> None:
        """Remove baselines either globally or just for given entries."""
        if entries is None:
            self._cache.clear()
            return
        for e in entries:
            e.pop("baselines", None)
            self._cache.pop(self._uid_fn(e), None)

    def has_any(self, entries: Iterable[dict]) -> bool:
        return any(self._has_for_entry(e) for e in entries)

    # ---------- Internals ----------
    def _has_for_entry(self, entry: dict) -> bool:
        return ("baselines" in entry and entry["baselines"]) or \
               (self._uid_fn(entry) in self._cache)

    def _attach_cached_if_missing(self, entry: dict) -> None:
        if "baselines" not in entry:
            cached = self._cache.get(self._uid_fn(entry))
            if cached:
                entry["baselines"] = cached
