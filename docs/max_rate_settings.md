# Max rate and max O2

The app reports two numbers per experiment:

- **Max rate** (umol/s): the largest O2 evolution rate sustained over a short window (about 7 s), taken from a smoothed version of the O2 trace in the first half of the O2 rise.
- **Max O2** (umol): the maximum of the smoothed O2 trace during irradiation.

Both come from pyKES `extract_max_rate`. Its result is used in two passes, set up so that the same procedure works for two kinds of robot experiments:

- **Short O2 bursts** (e.g. the BC series): O2 rises within 10–40 s and then decays.
- **Pulsed irradiation** (e.g. BA-10 to BA-13): the trace rises over minutes but scatters strongly. The scatter grows with the O2 level, by 7–19 % of the level in these runs.

The code is in [`general_processing_functions.py`](../src/pykes_robot_app/data_parsing/general_processing_functions.py) (`processing_data`, `build_max_rate_options`, `find_rising_part`, `find_early_max_rate`).

## Why the pyKES defaults are not used

pyKES smooths the trace with a Gaussian process. A Gaussian process is a statistical model of a smooth curve. Its *lengthscale* is the time over which the curve can change noticeably, and pyKES fits it to the data. The rate is then read off the smoothed curve over a *window*.

With the defaults the window is about 60 s, and the lengthscale may not drop below 20 sampling intervals (about 70 s). This caused three problems on the robot data:

1. **Bursts are missed.** A 60 s window cannot resolve a 20 s burst, and the curve cannot follow it. pyKES then even treats 4–7 samples around the burst peak as artifacts. In the benchmark below the defaults recovered 4–7 % of the burst rates (median).
2. **Rises are flattened.** On the whole trace, one lengthscale has to describe both the fast rise and the slow decay after the peak. The fit settles at 100–300 s, which flattens the rise. Continuous runs came out at 70 % of the true rate, pulsed runs at 56 %.
3. **The measured maximum is inflated by pulse scatter.** The largest *measured* O2 value of a pulsed run is mostly scatter: on continuous runs it was 22–64 % above the true maximum in the benchmark.

## Pipeline

All times are counted from irradiation start (plus the offset: `parameters.py`, default 0 s, or the optional `Offset` column of the overview). The O2 trace is re-zeroed at its first sample there. "Sampling interval" means the median time between samples, about 3.5 s on the robot.

### 1. Pass 1: smooth the whole irradiation window

`extract_max_rate` runs on the whole irradiation window with:

- lengthscale between **5 sampling intervals** (about 18 s) and half the window's duration;
- a window of 2 sampling intervals. The window does not matter here, because only the smoothed curve of this pass is used.

From the smoothed curve:

- **Max O2** is its maximum. Smoothing averages the scatter out, unlike the largest measured value.
- **Half-rise time** is the time at which it first reaches half its maximum.

### 2. Pass 2: fit the rising part only

`extract_max_rate` runs again, on the data up to **1.5 × the half-rise time**, but at least 20 sampling intervals (about 70 s). The settings are the same:

- lengthscale between 5 sampling intervals and half the length of this part;
- a window of **2 sampling intervals** (about 7 s).

Without the slow decay and without most of the high-level scatter, the fitted lengthscale is much shorter: 20–60 s on the robot runs instead of 100–300 s. The fit can then follow the rise.

On continuous runs (all eight BA runs) the pass-2 lengthscale sits at its upper bound, half the length of the rising part. There the length of the rising part, and so the factor 1.5, sets how strongly the rise is smoothed; with a factor of 3 the rates came out up to 22 % lower. Bursts stay below the bound.

The minimum of 20 sampling intervals is pyKES's own: `extract_max_rate` refuses series with fewer than 20 points. For bursts the rising part therefore reaches past the peak into the decay, which does no harm, since the rate search stops at the half-rise time.

### 3. Max rate: search the first half of the rise

For every window position pyKES's windowed rate is computed from the smoothed curve of pass 2 (`calculate_windowed_rates`). It is the O2 difference across the window divided by its length. The **max rate** is the largest of these among windows centred at or before the half-rise time; the first window is always included.

Why not search the whole rising part?

- Pulse scatter grows with the O2 level, so the upper half of the rise is the noisiest part of the trace.
- In the benchmark, the inflated max rates (1.5–4.5× the true value) all lay there, at or after the half-rise time.
- The steepest part of a rising and levelling O2 trace lies before it reaches half its maximum, so nothing real is lost. On the 16 real runs the max rate lies at 7–30 s, before or (on one burst) at the half-rise time, and limiting the search changed none of their rates by more than 0.05 %.

### 4. Quality flags

The pyKES quality flags are recomputed for the selected window with pyKES's own rules (`collect_quality_flags`). pyKES's `window_duration_limited` is left out: it warns that pyKES's *default* window was capped by a short series, but here the window is set explicitly and the rising part is short by design.

The flags that occur on robot data:

- `max_rate_at_boundary`: the max rate is in the first window. The O2 rises at full speed right from irradiation start, as in fast bursts.
- `lengthscale_at_lower_bound`: the fit wanted an even shorter lengthscale. On noisy runs this often marks a rate inflated by scatter.
- `max_rate_not_significant`, `high_uncertainty`: the rate is not clearly above its uncertainty.
- `many_outliers_masked`: more than 5 % of the samples were treated as artifacts.

The smoothing-free cross-check of pyKES needs at least 10 samples per window. With a 7 s window it is therefore empty and is not shown.

## Outputs

| Key in `processed_data` | Meaning |
|---|---|
| `max_rate_umol_s`, `max_rate_time_s`, `max_rate_window_s` | Max rate, centre and length of its window |
| `max_rate_flags` | Quality flags (see above) |
| `max_rate_lengthscale_s` | Fitted lengthscale of pass 2 |
| `max_oxygen_umol`, `max_oxygen_time_s` | Max O2 and its time |
| `smoothed_gaussian_umol`, `smoothing_lengthscale_s` | Smoothed curve of pass 1 and its lengthscale |
| `half_rise_time_s` | Half-rise time (end of the max-rate search) |
| `time_rising_part_s`, `rate_gaussian_umol_s` | Time of the rising part and the instantaneous rate of pass 2 on it (the "Rate" plot) |

## Settings

In [`parameters.py`](../src/pykes_robot_app/parameters.py):

- `max_rate_window_s`: window in seconds. `None` (default) uses 2 sampling intervals. Longer windows lower the scatter of the rate but cannot resolve bursts shorter than the window.
- `max_rate_lengthscale_bounds_s`: `(min, max)` lengthscale in seconds for both passes. `None` (default) uses 5 sampling intervals and half the fitted duration.

Fixed in `general_processing_functions.py`, because the benchmark below was run with them:

- `LENGTHSCALE_MIN_STEPS = 5`;
- `RISING_PART_FACTOR = 1.5`;
- `RISING_PART_MIN_STEPS = 20`;
- `HALF_RISE_FRACTION = 0.5`.

**Process together what you compare.** Experiments that are compared must be processed with the same settings.

## Validation

### Benchmark

Synthetic traces with a known true curve, built like the robot data:

- **True curves:**
  - 12 real runs with little scatter, interpolated smoothly (PCHIP): continuous BA-06 to BA-09 and the eight BC bursts;
  - two simulated bursts of 10 s and 20 s O2 production, seen through a first-order sensor (3 s lag) with first-order O2 loss (0.03 1/s).
- **Sampling:** every 3.55 s, with a random start phase and ±2 % jitter.
- **Noise:**
  - "clean": white noise of 0.012 umol/L, as in the clean runs;
  - "pulsed": skewed noise with a standard deviation of 0.3 umol/L plus 7, 12 or 18 % of the O2 level, as measured on BA-10 to BA-13.
- **Size:** 10 noise realizations per curve and noise level, 560 traces in total.
- **Truth:** the steepest 10 s average slope of the true curve.

Recovered max rate in % of the truth. The columns show the median, the 10–90 % range, the share of traces more than 20 % too high, and the largest value:

| Data | pyKES defaults, median | This method, median | 10–90 % | > +20 % | max |
|---|---|---|---|---|---|
| Continuous, clean | 70 | 100 | 89–101 | 0 % | 102 |
| Continuous, 7 % scatter | 56 (all pulsed) | 94 | 80–104 | 0 % | 110 |
| Continuous, 12 % scatter | | 93 | 83–110 | 0 % | 115 |
| Continuous, 18 % scatter | | 93 | 81–120 | 10 % | 205 |
| Burst, clean | 7 | 102 | 100–108 | 1 % | 122 |
| Burst, 7 % scatter | 4 (all pulsed) | 95 | 85–106 | 0 % | 119 |
| Burst, 12 % scatter | | 91 | 79–110 | 1 % | 123 |
| Burst, 18 % scatter | | 89 | 72–107 | 2 % | 126 |

The pyKES defaults were run on an earlier version of the same benchmark with 4 noise realizations per curve. The window of the method is about 7 s, but the truth is the 10 s slope. Values slightly above 100 % on clean bursts are therefore expected.

**How the method was chosen.** An earlier variant searched the whole rising part with a lengthscale floor of 3 sampling intervals. Its medians were within 4 % of the table, but under 12–18 % scatter up to 20 % of the traces were more than 20 % too high, by up to 4.5×. Both changes only matter on noisy data: on clean data and on the 16 real runs the two variants agree within 0.05 %.

Max O2, in % of the true maximum:

| Data | Smoothed maximum (reported) | Largest measured value |
|---|---|---|
| Continuous, clean | 99 | 100 |
| Continuous, 7 / 12 / 18 % scatter | 100 / 100 / 100 | 123 / 138 / 164 |
| Burst, clean | 100 | 100 |
| Burst, 7 / 12 / 18 % scatter | 95 / 90 / 88 | 106 / 111 / 120 |

The test suite ([`tests/test_max_rate.py`](../tests/test_max_rate.py)) repeats a smaller version of this check on every run. It uses a continuous trace and a 20 s burst, with clean and pulse-type noise.

### Synthetic curve shapes

The pipeline was also run on three idealized shapes, 24 noise realizations each, with the same pulse-type noise as above. All three pass through a 3 s sensor lag:

- a straight rise at constant rate;
- constant production with O2 loss;
- production that decays (catalyst deactivation) with O2 loss.

Recovered max rate in % of the steepest 10 s slope: median, share of traces more than 20 % too high, largest value.

| Shape | 7 % scatter | 12 % scatter | 18 % scatter |
|---|---|---|---|
| Production with loss | 99, 0 %, 107 | 97, 0 %, 107 | 94, 0 %, 109 |
| Decaying production with loss | 103, 4 %, 129 | 103, 12 %, 143 | 105, 17 %, 174 |
| Straight rise | 118, 42 %, 144 | 123, 54 %, 183 | 126, 54 %, 218 |

The flatter the rate is around its maximum, the more windows are nearly as steep as the steepest one. The more such windows there are, the more likely scatter pushes one of them up. A constant rate is the extreme case: every window of the rise is equally steep, so the reported maximum is always an upward fluctuation, and the **straight rise reads about 20 % too high**. The real runs do not look like that: their rate peaks within the first 7–30 s and then falls.

## Limits

- **Single noisy runs can be inflated.** In the benchmark, about 1 in 10 continuous traces under 18 % scatter read more than 20 % too high; under 7–12 % scatter, none did. On the synthetic decaying-production curve it was 4–17 % of the traces under 7–18 % scatter. Many of these runs carry `lengthscale_at_lower_bound` or `max_rate_not_significant`. Measure replicates of every pulsed condition and compare their medians.
- **Noisy runs read low on average.** The median is 5–11 % below the truth under pulse scatter, but correct on clean data. When pulsed (noisy) runs are compared with continuous (clean) runs, the method therefore favours the continuous ones by about 5–10 %. A small positive effect of pulsing can be hidden by this.
- **Constant-rate rises** read about 20 % too high under scatter (see above).
- **Rates that still increase after the half-rise time** are underestimated, because the search stops there. On synthetic accelerating bursts (production rate ramping up until it stops) the method gave 81–84 % of the true rate; slow catalyst activation followed by a constant rate and symmetric S-shaped curves were not affected. None of the 16 real runs has its steepest point after the half-rise time.
- **10 s bursts** are only a few samples long at 3.5 s sampling. Their rates scatter more, and their max O2 is underestimated under scatter.
