# ROApy

This is a desk top app written in Python with PyQt6, Numpy, Pandas and Matplotlib.
It helps scientists to process data from Raman optical activity spectrometer manufactured by Zebr.

This spectrometer measures sum (Raman) and difference (ROA) of scattered light.
There are different spectral modalities: SCP (default), DCPI (optional), DCPII (optional), SCPc (optional).
All the spectra have wavenumber as an X axis and intensity as Y axis.
Spectra are accumulated by new cycle to previous ones.
Each spectra goes in pairs since A and B camera output have different (slightly overlapping) wavenumber range.
