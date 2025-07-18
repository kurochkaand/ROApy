# ROApy

This is a desk top app written in Python with PyQt6.
It helps scientists to process data from Raman optical activity spectrometer.

This spectrometer measures summ (Raman) and difference (ROA) of scatered light.
There are differnet spectral modalities: SCP (default), DCPI (optional), DCPII (optional), SCPc (optional).
All the spectra have wavenumber as an X axis and intensity as Y axis.
Spectra are accomulated by new cycle to previous ones.
Each spectra goes in pairs since A and B camera output have different (slightly overlaping) wavenumber range,

To do:

1.
2. Add a toggle button to normalize by accomulation time.
3. Add a button to remove fluorescence baseline with difuse function.
4. Fix not working average by range by making time range instead.
5. In UI, make time range to be a range slider.
6. When exporting, add a radio button to export as two (prn) or as 3 column file (plt).
7. Make a minimal functional export combined A and B function.
8. If different modalities are not present disable the checkboxes.

To get updated code:
"""
rm code.txt
cat README.md > code.txt
for i in \*.py; do cat $i >> code.txt; done
"""
