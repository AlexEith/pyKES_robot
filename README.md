# pyKES Robot App

This repository packages the Streamlit workflow used for analysing automated photocatalysis robot experiments. It is built on top of `pyKES` and focuses on ingesting experiment metadata plus raw measurement files, processing the time series, and visualizing the resulting dataset.

## What It Does

The app provides three main steps:

1. Upload experiment metadata and raw measurement files.
2. Inspect time-series plots for raw, smoothed, and rate-derived signals.
3. Review analysis results such as extracted maximum rates.

Uploads consist of the HTE experiment overview (Excel, read from its first sheet, one row per experiment keyed by the `Experiment` column) and the photocat-hte robot log files named in its `File name O2` column (columns `duration`, `status`, `command`, `uM_1`).

The overview must contain the columns `group`, `File name O2`, `Active` (TRUE/FALSE) and `color` (display color, e.g. `#1f77b4` or `red`), each filled for every experiment, and the condition columns `Power output [W/m^2]`, `Duty cycle [%]`, `Frequency [Hz]`, `Photosensitizer`, `c(photosensitizer) [M]`, `Catalyst`, `c(catalyst) [M]`, `c(Na2S2O8) [M]` and `pH [-]` (empty condition cells mean "none"). Liquid volume (8.5 mL) and offset (0 s) are set for all experiments in [`parameters.py`](src/pykes_robot_app/parameters.py); an optional `Offset` column (s) overrides the offset for the experiments where it is filled, as in pyKES-O2-H2-App.

The `group` names are defined in `GROUP_MAPPING` in [`parameters.py`](src/pykes_robot_app/parameters.py), which maps each group to the condition column that splits it into subsets on the Analysis Results page (e.g. `Catalyst` → `Catalyst`). Only experiments with `Active` set to TRUE appear on that page.

## Requirements

- Python 3.9 or newer
- `pyKES>=0.2.4`
- `numpy>=1.24.4`
- `pandas>=2.0.3`
- `scipy>=1.10.1`

## Install

From the repository root:

```bash
uv sync
```

## Run Locally

The Streamlit entrypoint is [`src/pykes_robot_app/streamlit_app/Home.py`](src/pykes_robot_app/streamlit_app/Home.py).

```bash
uv run streamlit run src/pykes_robot_app/streamlit_app/Home.py
```

The app configuration lives in [`src/pykes_robot_app/config.py`](src/pykes_robot_app/config.py). It wires together the metadata lookup, raw file readers, and processing functions used by the upload page.

## Static Deploy

The repository also includes a static deploy setup in [`deploy/`](deploy/). To rebuild the browser bundle and serve it locally:

```bash
uv run python deploy/build.py
cd deploy
uv run python -m http.server 8000
```

Then open `http://localhost:8000` in a browser.

## Versioning

pyKES version

* Raising floor for pyKES dependency in [`pyproject.toml`](pyproject.toml), then
```bash
uv lock --refresh
uv sync
```

App version

* Updating version in [`pyproject.toml`](pyproject.toml)
```bash
git tag v0.1.1
git push origin v0.1.1
```
* Creating release from tag in GitHub


## Repository Layout

- [`src/pykes_robot_app/data_parsing/`](src/pykes_robot_app/data_parsing/) contains the raw readers and signal-processing helpers.
- [`src/pykes_robot_app/streamlit_app/`](src/pykes_robot_app/streamlit_app/) contains the Streamlit entrypoint and pages.
- [`data/`](data/) holds the overview template [`overview_template.xlsx`](data/overview_template.xlsx) and the data used for local work.
- [`deploy/`](deploy/) contains the static browser bundle entrypoint and build script.
- [`docs/`](docs/) documents the max-rate and max-O2 method.
- [`tests/`](tests/) checks the max rate and max O2 on synthetic traces.

## Processing Overview

The robot log is reduced to the pre-reaction baseline, reaction and post-reaction baseline measurements, with time re-zeroed at the start of degassing. A polynomial baseline plus logistic step is fitted to the pre- and post-reaction phases and the polynomial baseline is subtracted (logistic baseline correction, ported from `hte_streamlit`). The corrected O2 concentration is converted to an amount using the liquid phase volume and cut to the irradiation window. Max O2 and max rate then come from two passes of pyKES `extract_max_rate`:

1. **Whole irradiation window.** The trace is smoothed; max O2 is the maximum of the smoothed curve.
2. **Rising part only** (up to 1.5 × the time at which the smoothed curve reaches half its maximum). The max rate is the largest rate sustained over about 7 s, searched in the first half of the rise. Each rate comes with pyKES quality flags.

This works for short O2 bursts as well as for the scattered traces of pulsed irradiation. The rate window and the smoothing time scale can be changed in [`parameters.py`](src/pykes_robot_app/parameters.py) (`max_rate_window_s`, `max_rate_lengthscale_bounds_s`). [docs/max_rate_settings.md](docs/max_rate_settings.md) explains the method and its accuracy on synthetic data with known ground truth.

## Tests

```bash
uv run pytest
```

## Contributing

Contributions are welcome. Please open a pull request if you want to propose a change.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
