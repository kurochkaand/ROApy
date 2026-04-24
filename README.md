# ROApy

This is a desk top app written in Python with PyQt6, Numpy, Pandas and Matplotlib.
It helps scientists to process data from Raman optical activity spectrometer manufactured by Zebr.

This spectrometer measures sum (Raman) and difference (ROA) of scattered light.
There are different spectral modalities: SCP (default), DCPI (optional), DCPII (optional), SCPc (optional).
All the spectra have wavenumber as an X axis and intensity as Y axis.
Spectra are accumulated by new cycle to previous ones.
Each spectra goes in pairs since A and B camera output have different (slightly overlapping) wavenumber range.

To do:

1. Just after the program is launched and it's loading display program logo.
2. Pending state after you select a difector and spectra are loading.
3. In the plot, make right mouse button click and drag to zoom into a rectangle. (optionally, return arrows crossed and lense to plot manage bar and make arrows selected by default.)
4. In UI, add pending states (oppening of many files, select all pressed in selection,).
5. create new box combined spectra, button create combined which prompts to a new window. Below it a selection list with combinations.
6. After performing a selection of baseline removal plot the result.
7. Export separate as 2 column or a 3 column files
8. Button to Create combined spectra
9. In plot, add check box for stacked view of spectra.
10. change Normalization button to check box and move it to plot.
11. In selector tree, allow delition of custom spectra and experiments.
