# data_processor.py
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve

def merge_a_b(a_df, b_df):
    """Interpolates and combines two spectra."""
    common_x = sorted(set(a_df["Wavenumber"]).union(b_df["Wavenumber"]))
    merged = pd.DataFrame({"Wavenumber": common_x})
    for col in a_df.columns[1:]:
        f_a = interp1d(a_df["Wavenumber"], a_df[col], bounds_error=False, fill_value=0)
        f_b = interp1d(b_df["Wavenumber"], b_df[col], bounds_error=False, fill_value=0)
        merged[col] = (f_a(common_x) + f_b(common_x)) / 2
    return merged

def average_spectra(entries):
    """
    Given a list of entries (all same camera & same columns),
    average their intensities point-by-point. Assumes same Wavenumber grid.
    """
    if not entries:
        return None
    # stack all dataframes on third dimension
    dfs = [e["data"].set_index("Wavenumber") for e in entries]
    # concat into a 3D array (n_spectra × n_points × n_columns)
    combined = pd.concat(dfs, axis=1, keys=range(len(dfs)))
    # compute mean along the spectra axis
    mean_df = combined.groupby(level=1, axis=1).mean()
    mean_df.reset_index(inplace=True)
    # build a new entry dict (copy metadata from first one)
    avg = entries[0].copy()
    avg["data"] = mean_df
    avg['file_index'] = f"{min(e['file_index'] for e in entries)}–{max(e['file_index'] for e in entries)}"
    return avg

def baseline_als(
    y: np.ndarray,
    lam: float = 1e5,
    p: float = 0.01,
    niter: int = 10,
    redraw_each: int = None,
    callback=None
) -> np.ndarray:
    """
    Eilers & Boelens Asymmetric Least Squares baseline.

    Parameters
    ----------
    y : raw intensity array
    lam : smoothness parameter (higher → smoother baseline)
    p : asymmetry parameter (0 - 1, typical 1e-4 - 1e-2)
    niter : max iterations
    redraw_each : if provided, every redraw_each iterations invokes callback(i, baseline)
    callback : function(iteration, baseline_array)

    Returns
    -------
    baseline z as an array of same shape as y
    """
    L = len(y)
    # second‐difference matrix
    D = diags([1, -2, 1], [0, -1, -2], shape=(L, L-2))
    D = lam * (D @ D.T)
    w = np.ones(L)
    for i in range(niter):
        W = diags(w, 0)
        Z = W + D
        # convert to CSC (or .tocsr()) to avoid SparseEfficiencyWarning
        Z = Z.tocsc()
        z = spsolve(Z, w * y)
        w = p * (y > z) + (1 - p) * (y < z)
        if callback and redraw_each and (i % redraw_each == 0):
            callback(i, z)
    return z
