# ROApy

This is a desk top app written in Python with PyQt6.
It helps scientists to process data from Raman optical activity spectrometer.

This spectrometer measures summ (Raman) and difference (ROA) of scatered light.
There are differnet spectral modalities: SCP (default), DCPI (optional), DCPII (optional), SCPc (optional).
All the spectra have wavenumber as an X axis and intensity as Y axis.
Spectra are accomulated by new cycle to previous ones.
Each spectra goes in pairs since A and B camera output have different (slightly overlaping) wavenumber range,

To get updated code:
"""
rm code.txt
cat README.md > code.txt
for i in \*.py; do echo "#" $i >> code.txt; cat $i >> code.txt; done
"""
