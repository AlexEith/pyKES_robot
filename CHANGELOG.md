# Changelog

## [Unreleased]

- Upload handler for photocat-hte robot logs, named in the overview column `File name O2`: logistic baseline correction ported from hte_streamlit, max rate with pyKES `extract_max_rate`.
- Max rate and max O2 from two `extract_max_rate` passes, for short O2 bursts and for the scattered traces of pulsed irradiation alike:
  - pass 1 smooths the whole irradiation window and gives max O2 (maximum of the smoothed curve);
  - pass 2 fits the rising part only and gives the max rate over 2 sampling intervals (about 7 s), searched in the first half of the rise;
  - lengthscale floor of 5 sampling intervals instead of pyKES's 20;
  - quality flags recomputed for the selected window.
- Method and benchmark in [docs/max_rate_settings.md](docs/max_rate_settings.md).
- Configurable max-rate window and smoothing lengthscale (`max_rate_window_s`, `max_rate_lengthscale_bounds_s`).
- Max O2 amount in the results table. The smoothing-free cross-check is not shown, since it needs at least 10 samples per window.
- Tests in `tests/` on synthetic traces with known ground truth; pytest as development dependency.
- Overview columns `Photosensitizer`, `c(photosensitizer) [M]`, `Catalyst` and `c(catalyst) [M]` replace `c([Ru(bpy(3]Cl2) [M]`.
- Groups, active flags and colors are set in the overview columns `group`, `Active` and `color`, as in the other pyKES apps, and must be filled for every experiment; `GROUP_MAPPING` defines the group names.
- Optional overview column `Offset` (s) overrides the offset of `parameters.py` per experiment, as in pyKES-O2-H2-App; empty cells use the default.
- The overview is read from its first sheet, so German (`Tabelle1`) and English (`Sheet1`) Excel files both work.
- Overview columns `Duty cycle [%]` and `Frequency [Hz]` for pulsed irradiation, available as groups `Duty cycle` and `Frequency`.
- Overview template `data/overview_template.xlsx` with all required and optional columns.
- `deploy/build.py` writes POSIX module paths and reads/writes UTF-8, so the browser bundle can be built on Windows.
