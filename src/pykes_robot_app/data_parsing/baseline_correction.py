"""Logistic baseline correction (LBC) of O2 traces, ported from hte_streamlit."""

import numpy as np

from pyKES.utilities.find_nearest import find_nearest

# Decay of the logistic step halfway between its midpoint and the reaction end, so it
# does not interfere with the baseline fit outside the reaction window
LOGISTIC_DECAY_RATIO = 1. / 9e6

def evaluate_logistic_step(time, midpoint, steepness, height = 1.):
    """
    Evaluate a logistic step that rises from zero to `height` around `midpoint`.

    Parameters
    ----------
    time : np.ndarray
        Time values.
    midpoint : float
        Time at which the step reaches half its height.
    steepness : float
        Negative growth rate of the step; larger magnitudes give sharper steps.
    height : float, optional
        Final height of the step.

    Returns
    -------
    np.ndarray
        Step values.
    """

    return height / (1 + np.exp(steepness * (time - midpoint)))

def fit_baseline_coefficients(normalized_time, signal, normalized_midpoint, normalized_steepness, polynomial_order):
    """
    Least-squares fit of a polynomial plus a logistic step to the baseline phases.

    Parameters
    ----------
    normalized_time : np.ndarray
        Time values of the baseline phases, normalized to order unity.
    signal : np.ndarray
        Measured values of the baseline phases.
    normalized_midpoint, normalized_steepness : float
        Midpoint and steepness of the logistic step on the normalized time axis.
    polynomial_order : int
        Order of the polynomial describing the baseline.

    Returns
    -------
    polynomial_coefficients : np.ndarray
        Polynomial coefficients on the normalized time axis, lowest order first.
    step_height : float
        Height of the logistic step.
    """

    design_matrix = np.c_[np.polynomial.polynomial.polyvander(normalized_time, polynomial_order),
                          evaluate_logistic_step(normalized_time, normalized_midpoint, normalized_steepness)]

    coefficients = np.linalg.lstsq(design_matrix, signal, rcond = None)[0]

    return coefficients[:-1], coefficients[-1]

def correct_baseline(time, signal, reaction_start, reaction_end, polynomial_order):
    """
    Fit a polynomial baseline plus a logistic step to the data outside of the
    reaction window and subtract the polynomial baseline.

    Parameters
    ----------
    time : np.ndarray
        Time values.
    signal : np.ndarray
        Measured values.
    reaction_start, reaction_end : float
        Start and end time of the reaction window.
    polynomial_order : int
        Order of the polynomial describing the baseline.

    Returns
    -------
    baseline : np.ndarray
        Polynomial baseline.
    baseline_with_step : np.ndarray
        Polynomial baseline plus logistic step.
    signal_corrected : np.ndarray
        Signal with the polynomial baseline subtracted.
    """

    start_index, end_index = find_nearest(time, (reaction_start, reaction_end))
    outside_reaction = np.r_[0:start_index, end_index:len(time)]

    midpoint = (time[start_index] + time[end_index]) / 2
    steepness = np.log(LOGISTIC_DECAY_RATIO) / ((time[end_index] - midpoint) / 2)

    # Normalized time keeps the polynomial terms of similar size (well-conditioned fit)
    time_scale = time[-1] - time[0]
    normalized_time = (time - midpoint) / time_scale

    polynomial_coefficients, step_height = fit_baseline_coefficients(normalized_time[outside_reaction],
                                                                     signal[outside_reaction],
                                                                     0.,
                                                                     steepness * time_scale,
                                                                     polynomial_order)

    baseline = np.polynomial.polynomial.polyval(normalized_time, polynomial_coefficients)
    baseline_with_step = baseline + evaluate_logistic_step(normalized_time, 0., steepness * time_scale, step_height)

    return baseline, baseline_with_step, signal - baseline

def test_function():

    import matplotlib.pyplot as plt

    time = np.linspace(3000, 3800, 400)
    reaction_start, reaction_end = 3200, 3600

    drift = 1 - 2e-4 * (time - 3000) + 1e-7 * (time - 3000)**2
    evolved_oxygen = np.clip((time - reaction_start) / (reaction_end - reaction_start), 0, 1) * 5
    signal = drift + evolved_oxygen + np.random.default_rng(0).normal(0, 0.02, len(time))

    baseline, baseline_with_step, signal_corrected = correct_baseline(time, signal, reaction_start, reaction_end, 4)

    print(f"Maximum baseline error: {np.max(np.abs(baseline - drift)):.4f}")

    fig, ax = plt.subplots()
    ax.plot(time, signal, '.', markersize = 2, label = 'Signal')
    ax.plot(time, baseline, label = 'Baseline')
    ax.plot(time, baseline_with_step, label = 'Baseline + step')
    ax.plot(time, signal_corrected, label = 'Corrected')
    ax.legend()
    plt.show()

if __name__ == "__main__":
    test_function()
