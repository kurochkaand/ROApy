# ROApy

This is a desk top app written in Python with PyQt6.
It helps scientists to process data from Raman optical activity spectrometer.

This spectrometer measures summ (Raman) and difference (ROA) of scatered light.
There are differnet spectral modalities: SCP (default), DCPI (optional), DCPII (optional), SCPc (optional).
All the spectra have wavenumber as an X axis and intensity as Y axis.
Spectra are accomulated by new cycle to previous ones.
Each spectra goes in pairs since A and B camera output have different (slightly overlaping) wavenumber range,

To do:

1. In UI, add pending states (oppening of many files, select all pressed in selection,).
2. create new box combined spectra, button create combined which prompts to a new window. Below it a selection list with combinations.
3. After performing a selection of baseline removal plot the result.

For later:

1. In plot, add check box for stacked view of spectra.
2. change Normalization button to check box and move it to plot.
3. In selector tree, allow delition of custom spectra and experiments.

My code:
"""
rm code.txt
cat README.md >> code.txt
cat main.py >> code.txt
cat ui.py >> code.txt
cat window.py >> code.txt
cat file_loader.py >> code.txt
cat plotter.py >> code.txt
cat data_processor.py >> code.txt
cat baseline_manager.py >> code.txt
cat exporter.py >> code.txt
cat selection_cycles.py >> code.txt
"""
