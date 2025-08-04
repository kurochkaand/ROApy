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


def baseline_als(
    y: np.ndarray,
    lam: float = 1e5,
    p: float = 0.01,
    niter: int = 10,
    tol: float = 1e-6,             # relative convergence tolerance on ||Δz|| / ||z||
    min_delta: float = 0.0,       # absolute minimum change to consider (optional)
    redraw_each: int = None,
    callback=None
) -> np.ndarray:
    """
    Eilers & Boelens Asymmetric Least Squares baseline.
    Stops early if the change in baseline is below tolerance.
    """
    L = len(y)
    D = diags([1, -2, 1], [0, -1, -2], shape=(L, L-2))
    D = lam * (D @ D.T)
    w = np.ones(L)
    last_z = np.zeros_like(y)
    last_z_norm = np.linalg.norm(last_z)
    eps = 1e-8
    for i in range(niter):
        W = diags(w, 0)
        Z = W + D
        try:
            Z = Z.tocsc()
            rhs = w * y
            z = spsolve(Z, rhs)
        except Exception as exc:
            z = last_z.copy()
        z_norm = np.linalg.norm(z)

        w_new = np.where(y > z, p, 1 - p)
        w = np.clip(w_new, eps, 1 - eps)
        if callback and redraw_each and (i % redraw_each == 0):
            callback(i, z)
        if i > 0:
            delta_z = np.linalg.norm(z - last_z)
            rel_change = delta_z / (last_z_norm + eps)
            if (rel_change < tol) or (delta_z < min_delta):
                print(f"Convergence reached at iteration {i+1}")
                last_z = z.copy()
                break
        last_z = z.copy()
        last_z_norm = z_norm
    return last_z

