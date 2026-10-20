"""Max rate and max O2 of processing_data on synthetic O2 traces with known ground truth."""

import numpy as np
import pytest
from scipy.signal import lfilter

from pyKES.utilities.unit_handler import Quantity

from pykes_robot_app.data_parsing.general_processing_functions import (
    build_max_rate_options,
    processing_data,
)

# -----------------------------------------------------------------------------
# Synthetic robot traces: 600 s baseline, 600 s irradiation, 600 s baseline,
# sampled like the robot; O2 in umol/L in a 8.5 mL liquid phase
# -----------------------------------------------------------------------------

TIME_STEP = 3.5               # s
IRRADIATION_START = 600.      # s
IRRADIATION_END = 1200.       # s
TOTAL_TIME = 1800.            # s
LIQUID_VOLUME_L = 8.5e-3
FINE_TIME_STEP = 0.01         # s, grid of the noise-free curves

# Physical model: O2 production, first-order O2 loss, first-order sensor response
PRODUCTION_RATE = 0.5         # umol/L/s
LOSS_CONSTANT = 0.006         # 1/s
SENSOR_LAG = 3.               # s
BURST_DURATION = 20.          # s, O2 production time of the burst
BURST_PRODUCTION_RATE = 2.    # umol/L/s
BURST_LOSS_CONSTANT = 0.03    # 1/s

CLEAN_NOISE = 0.012           # umol/L, white noise of the clean robot runs
RELATIVE_PULSE_NOISE = 0.07   # scatter of pulsed runs, as a fraction of the O2 level
PULSE_NOISE_FLOOR = 0.3       # umol/L, level-independent part of that scatter
PULSE_NOISE_SEEDS = 5         # noise realizations of the pulse-noise test

def calculate_continuous_curve(time_since_start: np.ndarray) -> np.ndarray:
    """
    Sensor signal for constant O2 production with first-order loss.

    Parameters
    ----------
    time_since_start : np.ndarray
        Time since irradiation start, in s.

    Returns
    -------
    np.ndarray
        O2 in umol/L, 0 before irradiation start.
    """

    elapsed = np.clip(time_since_start, 0, None)
    plateau = PRODUCTION_RATE / LOSS_CONSTANT
    lag_ratio = LOSS_CONSTANT * SENSOR_LAG

    return plateau * (1
                      - np.exp(-LOSS_CONSTANT * elapsed) / (1 - lag_ratio)
                      + lag_ratio * np.exp(-elapsed / SENSOR_LAG) / (1 - lag_ratio))

def calculate_burst_curve(time_since_start: np.ndarray) -> np.ndarray:
    """
    Sensor signal for a short O2 burst with first-order loss.

    Parameters
    ----------
    time_since_start : np.ndarray
        Time since irradiation start, in s.

    Returns
    -------
    np.ndarray
        O2 in umol/L, 0 before irradiation start.
    """

    fine_time = np.arange(0, TOTAL_TIME, FINE_TIME_STEP)
    production = np.where(fine_time < BURST_DURATION, BURST_PRODUCTION_RATE, 0.)

    # Explicit Euler steps of dO2/dt = production - loss * O2 and of the sensor lag
    dissolved = lfilter([0, FINE_TIME_STEP], [1, -(1 - BURST_LOSS_CONSTANT * FINE_TIME_STEP)], production)
    sensor_weight = FINE_TIME_STEP / SENSOR_LAG
    sensor = lfilter([0, sensor_weight], [1, -(1 - sensor_weight)], dissolved)

    return np.interp(time_since_start, fine_time, sensor, left=0.)

def calculate_true_max_rate(curve_function, window: float) -> float:
    """
    Steepest window-averaged slope of a noise-free curve.

    Parameters
    ----------
    curve_function : callable
        Maps time since irradiation start (s) to O2 (umol/L).
    window : float
        Averaging window, in s.

    Returns
    -------
    float
        Max rate in umol/s.
    """

    fine_time = np.arange(0, IRRADIATION_END - IRRADIATION_START, FINE_TIME_STEP)
    windowed_slopes = (curve_function(fine_time + window / 2) - curve_function(fine_time - window / 2)) / window

    return windowed_slopes.max() * LIQUID_VOLUME_L

def process_synthetic_trace(curve_function, noise_std, seed: int = 0, metadata_dict: dict = None) -> dict:
    """
    Sample a curve like the robot, add noise and run processing_data.

    Parameters
    ----------
    curve_function : callable
        Maps time since irradiation start (s) to O2 (umol/L).
    noise_std : callable
        Maps the noise-free O2 (umol/L) to the noise standard deviation (umol/L).
    seed : int, optional
        Seed of the noise realization.
    metadata_dict : dict, optional
        Overview row of the experiment; empty by default.

    Returns
    -------
    dict
        Output of processing_data.
    """

    time = np.arange(0, TOTAL_TIME, TIME_STEP)
    clean = curve_function(time - IRRADIATION_START)
    signal = clean + noise_std(clean) * np.random.default_rng(seed).standard_normal(time.size)

    return processing_data(Quantity(time, 's'),
                           Quantity(signal * LIQUID_VOLUME_L, 'umol'),
                           Quantity(IRRADIATION_START, 's'),
                           Quantity(IRRADIATION_END, 's'),
                           metadata_dict or {})

def calculate_clean_noise_std(clean: np.ndarray) -> np.ndarray:
    """
    Noise standard deviation of the clean robot runs.

    Parameters
    ----------
    clean : np.ndarray
        Noise-free O2, in umol/L.

    Returns
    -------
    np.ndarray
        Noise standard deviation, in umol/L.
    """

    return np.full_like(clean, CLEAN_NOISE)

def calculate_pulse_noise_std(clean: np.ndarray) -> np.ndarray:
    """
    Noise standard deviation of pulsed runs, growing with the O2 level.

    Parameters
    ----------
    clean : np.ndarray
        Noise-free O2, in umol/L.

    Returns
    -------
    np.ndarray
        Noise standard deviation, in umol/L.
    """

    return PULSE_NOISE_FLOOR + RELATIVE_PULSE_NOISE * np.abs(clean)

@pytest.mark.parametrize('curve_function, rate_tolerance, max_oxygen_tolerance',
                         [(calculate_continuous_curve, 0.03, 0.02),
                          (calculate_burst_curve, 0.08, 0.05)])
def test_clean_trace(curve_function, rate_tolerance, max_oxygen_tolerance):
    processed = process_synthetic_trace(curve_function, calculate_clean_noise_std)

    true_rate = calculate_true_max_rate(curve_function, processed['max_rate_window_s'])
    true_max_oxygen = curve_function(np.arange(0, 600, FINE_TIME_STEP)).max() * LIQUID_VOLUME_L

    assert processed['max_rate_umol_s'] == pytest.approx(true_rate, rel=rate_tolerance)
    assert processed['max_oxygen_umol'] == pytest.approx(true_max_oxygen, rel=max_oxygen_tolerance)

def test_pulse_noise_does_not_inflate_rate():
    rate_ratios = []
    for seed in range(PULSE_NOISE_SEEDS):
        processed = process_synthetic_trace(calculate_continuous_curve, calculate_pulse_noise_std, seed)
        true_rate = calculate_true_max_rate(calculate_continuous_curve, processed['max_rate_window_s'])
        rate_ratios.append(processed['max_rate_umol_s'] / true_rate)

    assert np.median(rate_ratios) == pytest.approx(1, abs=0.1)
    assert max(rate_ratios) < 1.15

def test_max_rate_is_searched_in_first_half_of_rise():
    processed = process_synthetic_trace(calculate_burst_curve, calculate_clean_noise_std)

    time_rising_part = processed['time_rising_part_s']
    first_window_end = time_rising_part[0] + processed['max_rate_window_s']

    assert len(time_rising_part) == len(processed['rate_gaussian_umol_s'])
    assert time_rising_part[-1] < processed['time_reaction_s'][-1]
    assert processed['max_rate_time_s'] <= max(processed['half_rise_time_s'], first_window_end)

def test_offset_column_overrides_default():
    default = process_synthetic_trace(calculate_continuous_curve, calculate_clean_noise_std)
    empty_cell = process_synthetic_trace(calculate_continuous_curve, calculate_clean_noise_std,
                                         metadata_dict = {'Offset': np.nan})
    shifted = process_synthetic_trace(calculate_continuous_curve, calculate_clean_noise_std,
                                      metadata_dict = {'Offset': 10 * TIME_STEP})

    assert len(empty_cell['time_reaction_s']) == len(default['time_reaction_s'])
    assert len(shifted['time_reaction_s']) == len(default['time_reaction_s']) - 10

def test_default_max_rate_options():
    time = np.arange(0, 600, TIME_STEP)

    options = build_max_rate_options(time)

    assert options['window'].unit['s'] == pytest.approx(2 * TIME_STEP)
    assert options['lengthscale_bounds'][0].unit['s'] == pytest.approx(5 * TIME_STEP)
    assert options['lengthscale_bounds'][1].unit['s'] == pytest.approx(0.5 * (time[-1] - time[0]))
