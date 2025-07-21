# data_processor.py
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d

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
    average their intensities point‐by‐point. Assumes same Wavenumber grid.
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
