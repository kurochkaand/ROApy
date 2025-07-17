import os

def export_combined(filename, df):
    df.to_csv(filename, sep="\t", index=False)

def export_separately(base_filename: str, spectra: list, modalities: list[str]):
    for entry in spectra:
        df     = entry["data"]
        cam    = entry["camera"]
        cycle  = entry["cycle"]
        for mod in modalities:
            r_col = f"{mod} Raman"
            o_col = f"{mod} ROA"
            # only export if both columns exist
            if r_col in df.columns and o_col in df.columns:
                sub = df[["Wavenumber", r_col, o_col]]
                filename = f"{base_filename}_{cam}_{cycle}_{mod}.txt"
                # ensure directory exists
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                sub.to_csv(filename, sep="\t", index=False)

