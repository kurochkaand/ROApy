import pandas as pd

def export_combined(filename, df):
    df.to_csv(filename, sep="\t", index=False)

def export_separately(base_filename, spectra):
    for entry in spectra:
        df = entry["data"]
        name = f"{base_filename}_{entry['camera']}_{entry['cycle']}.txt"
        df.to_csv(name, sep="\t", index=False)
