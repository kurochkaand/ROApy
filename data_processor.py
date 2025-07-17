import pandas as pd
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
