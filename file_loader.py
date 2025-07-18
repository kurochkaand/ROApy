# file_loader.py
import os
import glob
import re
import pandas as pd

def parse_header(header_line: str):
    info = {}
    parts = header_line.strip("# \n").split("#")
    for part in parts:
        if "Gain" in part:
            info["gain"] = float(re.search(r"Gain\s+([\d.]+)", part).group(1))
        if "Power at sample" in part:
            info["power"] = int(re.search(r"Power at sample\s+(\d+)", part).group(1))
        if "Cycles" in part:
            info["cycle"] = int(re.search(r"Cycles\s+(\d+)", part).group(1))
        if "Total times" in part:
            times = re.findall(r"([\d.]+)", part)
            info["total_time"] = list(map(float, times))
    return info

def load_data_files(directory):
    pattern = os.path.join(directory, "*_out.txt")
    files = glob.glob(pattern)
    data_entries = []

    for path in files:
        filename = os.path.basename(path)
        match = re.match(r"(.+)_([AB])-(\d+)_out\.txt", filename)
        if not match:
            continue
        name, cam, cycle = match.groups()

        with open(path, 'r') as f:
            header = f.readline()
            info = parse_header(header)
            df = pd.read_csv(f, delim_whitespace=True, names=[
                "Wavenumber", "SCP Raman", "SCP ROA",
                "DCPI Raman", "DCPI ROA",
                "DCPII Raman", "DCPII ROA",
                "SCPc Raman", "SCPc ROA"
            ])
            data_entries.append({
                "name": name,
                "camera": cam,
                "cycle": int(cycle),
                "info": info,
                "data": df,
                "path": path
            })

    return data_entries
