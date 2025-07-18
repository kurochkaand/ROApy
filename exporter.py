# exporter.py
import os

def export_combined(filename, df):
    df.to_csv(filename, sep="\t", index=False)

def export_separately(base_filename: str, spectra: list, modalities: list[str]):
    """
    For each spectrum entry and for each selected modality, export TWO
    TSVs: one with Wavenumber + <Modality> Raman, and one with
    Wavenumber + <Modality> ROA.

    Parameters
    ----------
    base_filename : str
        Path+prefix to use for each output file (without extension).
    spectra : list of dict
        Each dict has keys "camera", "cycle", and a pandas DataFrame under "data".
    modalities : list of str
        Which modalities to export, e.g. ["SCP", "DCPI", "DCPII", "SCPc"].
    """
    for entry in spectra:
        df    = entry["data"]
        cam   = entry["camera"]
        cycle = entry["cycle"]

        for mod in modalities:
            r_col = f"{mod} Raman"
            o_col = f"{mod} ROA"

            # Raman-only file
            if r_col in df.columns:
                subr = df[["Wavenumber", r_col]]
                fname_r = f"{base_filename}_{cam}_{cycle}_{mod}_Raman.txt"
                os.makedirs(os.path.dirname(fname_r), exist_ok=True)
                subr.to_csv(fname_r, sep="\t", index=False)

            # ROA-only file
            if o_col in df.columns:
                subo = df[["Wavenumber", o_col]]
                fname_o = f"{base_filename}_{cam}_{cycle}_{mod}_ROA.txt"
                os.makedirs(os.path.dirname(fname_o), exist_ok=True)
                subo.to_csv(fname_o, sep="\t", index=False)


