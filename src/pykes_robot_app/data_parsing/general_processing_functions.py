import dataclasses

import numpy as np
import pandas as pd

from pyKES.utilities.offset_correction import offset_correction
from pyKES.utilities.unit_handler import Quantity
from pyKES.utilities.max_rate import (
    extract_max_rate,
    calculate_windowed_rates,
    calculate_rolling_slopes,
    collect_quality_flags,
)

from pykes_robot_app.parameters import PROCESSING_PARAMETERS, GROUP_MAPPING

# -----------------------------------------------------------------------------
# Overview sheet
# -----------------------------------------------------------------------------

EXPERIMENT_COLUMN = 'Experiment'
FILE_NAME_COLUMN = 'File name O2'
ACTIVE_COLUMN = 'Active'
ACTIVE_VALUES = {'true': True, '1.0': True, '1': True, 'false': False, '0.0': False, '0': False}

# Columns that need an entry for every experiment (group, Active and color are read by pyKES)
NON_EMPTY_COLUMNS = [FILE_NAME_COLUMN, 'group', ACTIVE_COLUMN, 'color']
# ... and every column GROUP_MAPPING splits groups by has to exist
REQUIRED_COLUMNS = NON_EMPTY_COLUMNS + [metadata_path.split('/', 1)[1]
                                        for metadata_path in GROUP_MAPPING.values()
                                        if metadata_path is not None]

# -----------------------------------------------------------------------------
# Max rate and max O2 (see docs/max_rate_settings.md)
# -----------------------------------------------------------------------------

MAX_RATE_WINDOW_STEPS = 2              # default max-rate window, in sampling intervals
LENGTHSCALE_MIN_STEPS = 5              # default lower bound of the smoothing lengthscale, in sampling intervals
LENGTHSCALE_MAX_SPAN_FRACTION = 0.5    # default upper bound, as a fraction of the fitted duration (pyKES default)
HALF_RISE_FRACTION = 0.5               # half-rise time: the smoothed curve first reaches this fraction of its maximum
RISING_PART_FACTOR = 1.5               # pass 2 fits the data up to this multiple of the half-rise time ...
RISING_PART_MIN_STEPS = 20             # ... but over at least this many sampling intervals (pyKES needs 20 points)
NOT_APPLICABLE_FLAGS = ['window_duration_limited']   # pyKES flag about its default window, which is not used

def metadata_retrival_function(experiment_name: str,
                               overview_df):
    """
    Retrieve the metadata of an experiment from the overview sheet.

    Parameters
    ----------
    experiment_name : str
        Name of the experiment, as listed in the 'Experiment' column.
    overview_df : pd.DataFrame
        Overview sheet with one row per experiment.

    Returns
    -------
    metadata_dict : dict
        All columns of the experiment's row plus its name.
    """

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in overview_df.columns]
    if missing_columns:
        raise ValueError(f"Overview sheet is missing the columns {missing_columns}")

    experiment_row = overview_df[overview_df[EXPERIMENT_COLUMN] == experiment_name]

    if experiment_row.empty:
        raise ValueError(f"No experiment found with name: {experiment_name}")

    if len(experiment_row) > 1:
        raise ValueError(f"Multiple experiments found with name: {experiment_name}")

    metadata_dict = experiment_row.iloc[0].to_dict()
    metadata_dict['experiment_name'] = metadata_dict[EXPERIMENT_COLUMN]

    empty_columns = [column for column in NON_EMPTY_COLUMNS if pd.isna(metadata_dict[column])]
    if empty_columns:
        raise ValueError(f"Experiment {experiment_name} has no entry in the columns {empty_columns}")

    metadata_dict[ACTIVE_COLUMN] = parse_active_flag(metadata_dict[ACTIVE_COLUMN], experiment_name)

    return metadata_dict

def parse_active_flag(value, experiment_name: str) -> bool:
    """
    Interpret an entry of the 'Active' column.

    Parameters
    ----------
    value : bool, float or str
        Excel boolean (read as 1.0/0.0 if the column has empty cells), or the
        text TRUE/FALSE in any capitalization.
    experiment_name : str
        Experiment the entry belongs to, named in the error message.

    Returns
    -------
    bool
        Whether the experiment is shown on the Analysis Results page.
    """

    # pyKES tests the value's truth, so a text cell reading 'FALSE' would count as active
    text = str(value).strip().lower()

    if text not in ACTIVE_VALUES:
        raise ValueError(f"Experiment {experiment_name} has '{value}' in the '{ACTIVE_COLUMN}' column, expected TRUE or FALSE")

    return ACTIVE_VALUES[text]

def convert_umol_L_to_mol(data_umol_L: np.ndarray,
                          liquid_phase_volume_ml: float):
    """
    Convert liquid phase measurement in umol/L to an amount of substance.

    Parameters
    ----------
    data_umol_L : np.ndarray
        Liquid phase measurement in umol/L.
    liquid_phase_volume_ml : float
        Liquid phase volume in mL.

    Returns
    -------
    amount : Quantity
        Amount of substance (quantity object, substance)
    """

    data_quantity = Quantity(data_umol_L, 'umol/L')
    liquid_phase_volume_quantity = Quantity(liquid_phase_volume_ml, 'mL')

    amount = Quantity(data_quantity.unit['umol/L']
                      * liquid_phase_volume_quantity.unit['L'],
                      'umol')

    return amount

def build_max_rate_options(time_s: np.ndarray) -> dict:
    """
    Resolve the max-rate settings of PROCESSING_PARAMETERS for the trace that is fitted.

    Parameters
    ----------
    time_s : np.ndarray
        Time of the fitted trace, in s.

    Returns
    -------
    dict
        Window and lengthscale bounds as keyword arguments for extract_max_rate.
    """

    parameters = PROCESSING_PARAMETERS['processing_parameters']
    time_step = np.median(np.diff(time_s))

    window = parameters['max_rate_window_s']
    if window is None:
        window = MAX_RATE_WINDOW_STEPS * time_step

    lengthscale_bounds = parameters['max_rate_lengthscale_bounds_s']
    if lengthscale_bounds is None:
        lengthscale_bounds = (LENGTHSCALE_MIN_STEPS * time_step,
                              LENGTHSCALE_MAX_SPAN_FRACTION * (time_s[-1] - time_s[0]))

    return {'window': Quantity(window, 's'),
            'lengthscale_bounds': tuple(Quantity(bound, 's') for bound in lengthscale_bounds)}

def find_rising_part(time_s: np.ndarray, smoothed: np.ndarray) -> tuple:
    """
    Find the half-rise time and the end of the rising part of the O2 trace.

    Parameters
    ----------
    time_s : np.ndarray
        Time of the reaction window, in s, starting at 0.
    smoothed : np.ndarray
        Smoothed O2 curve of the whole reaction window.

    Returns
    -------
    half_rise_time : float
        Time at which the smoothed curve first reaches half its maximum, in s.
    rising_part_end : float
        End of the part of the trace the max rate is fitted on, in s.
    """

    time_step = np.median(np.diff(time_s))
    half_rise_time = time_s[np.argmax(smoothed >= HALF_RISE_FRACTION * smoothed.max())]

    rising_part_end = min(time_s[-1], max(RISING_PART_FACTOR * half_rise_time,
                                          RISING_PART_MIN_STEPS * time_step))

    return float(half_rise_time), float(rising_part_end)

def find_early_max_rate(time_s: np.ndarray,
                        data_mol: np.ndarray,
                        result,
                        search_end_s: float,
                        lengthscale_bounds_s: tuple):
    """
    Find the largest windowed rate among the windows centred up to a given time.

    Parameters
    ----------
    time_s : np.ndarray
        Time of the fitted trace, in s.
    data_mol : np.ndarray
        Measured O2 of the fitted trace, in mol.
    result : MaxRateResult
        Result of extract_max_rate on this trace.
    search_end_s : float
        Latest window centre, in s. The first window is always included.
    lengthscale_bounds_s : tuple of float
        Lengthscale bounds of the fit, in s, needed for the quality flags.

    Returns
    -------
    MaxRateResult
        Copy of the result with the max rate, its uncertainty, time, cross-check
        and quality flags of the selected window.
    """

    window = result.window.unit['s']
    # pyKES's robustness weights are internal; its outlier mask marks weights below 1/2
    weights = (~result.outlier_mask).astype(float)

    centers, windowed_rates, windowed_rate_stds = calculate_windowed_rates(time_s,
                                                                           result.smooth.unit['mol'],
                                                                           result.rate_std.unit['mol/s'] ** 2,
                                                                           window,
                                                                           weights)

    searched = centers <= max(search_end_s, centers[0])
    best_window = int(np.argmax(np.where(searched, windowed_rates, -np.inf)))

    rolling_slopes = calculate_rolling_slopes(time_s, data_mol, weights, window, np.median(np.diff(time_s)))
    crosscheck = rolling_slopes[int(np.argmin(np.abs(time_s - centers[best_window])))]

    early_result = dataclasses.replace(result,
                                       max_rate = Quantity(float(windowed_rates[best_window]), 'mol/s'),
                                       max_rate_std = Quantity(float(windowed_rate_stds[best_window]), 'mol/s'),
                                       t_max_rate = Quantity(float(centers[best_window]), 's'),
                                       max_rate_crosscheck = Quantity(float(crosscheck), 'mol/s'))

    early_result.flags = [flag for flag in collect_quality_flags(early_result, time_s, lengthscale_bounds_s)
                          if flag not in NOT_APPLICABLE_FLAGS]

    return early_result

def processing_data(time: Quantity,
                    data: Quantity,
                    start: Quantity,
                    end: Quantity,
                    metadata_dict: dict) -> dict:
    """
    Cut out the reaction window and determine the max O2 amount (pyKES
    extract_max_rate on the whole window) and the max rate (on the rising part).

    Parameters
    ----------
    time : Quantity
        Time data (quantity object, time)
    data : Quantity
        Measurement data (quantity object, substance [mol])
    start : Quantity
        Start time of the reaction (quantity object, time)
    end : Quantity
        End time of the reaction (quantity object, time)
    metadata_dict : dict
        Metadata of the experiment, as returned by the metadata retrieval function.

    Returns
    -------
    processed_data_dict : dict
        Dictionary containing the processed data, max rate and max O2 amount.
    """

    if 'Offset' in metadata_dict and pd.notna(metadata_dict['Offset']):
        offset = Quantity(metadata_dict['Offset'], 's')
    else:
        offset = Quantity(PROCESSING_PARAMETERS['processing_parameters']['offset'], 's')

    time_reaction, data_reaction = offset_correction(time.unit['s'],
                                                     data.unit['mol'],
                                                     offset.unit['s'],
                                                     start.unit['s'],
                                                     end.unit['s'])

    # Pass 1, whole reaction window: smoothed O2 curve and max O2
    full_result = extract_max_rate(Quantity(time_reaction, 's'),
                                   Quantity(data_reaction, 'mol'),
                                   **build_max_rate_options(time_reaction))

    smoothed_umol = full_result.smooth.unit['umol']
    max_oxygen_index = int(np.argmax(smoothed_umol))

    # Pass 2, rising part only: max rate in the first half of the rise
    half_rise_time, rising_part_end = find_rising_part(time_reaction, smoothed_umol)
    rising_part = time_reaction <= rising_part_end
    rising_options = build_max_rate_options(time_reaction[rising_part])

    rising_fit = extract_max_rate(Quantity(time_reaction[rising_part], 's'),
                                  Quantity(data_reaction[rising_part], 'mol'),
                                  **rising_options)

    rising_result = find_early_max_rate(time_reaction[rising_part],
                                        data_reaction[rising_part],
                                        rising_fit,
                                        half_rise_time,
                                        tuple(bound.unit['s'] for bound in rising_options['lengthscale_bounds']))

    processed_data_dict = {'time_reaction_s': time_reaction,
                           'time_unit': 's',
                           'data_reaction_umol': Quantity(data_reaction, 'mol').unit['umol'],
                           'data_unit': 'umol',
                           'smoothed_gaussian_umol': smoothed_umol,
                           'smoothed_gaussian_unit': 'umol',
                           'smoothing_lengthscale_s': full_result.hyperparameters['lengthscale'].unit['s'],
                           'half_rise_time_s': half_rise_time,
                           # The rate curve of pass 2 only covers the rising part
                           'time_rising_part_s': time_reaction[rising_part],
                           'rate_gaussian_umol_s': rising_result.rate.unit['umol/s'],
                           'rate_gaussian_unit': 'umol/s',
                           'max_rate_umol_s': rising_result.max_rate.unit['umol/s'],
                           'max_rate_unit': 'umol/s',
                           'max_rate_time_s': rising_result.t_max_rate.unit['s'],
                           'max_rate_time_unit': 's',
                           'max_rate_window_s': rising_result.window.unit['s'],
                           'max_rate_lengthscale_s': rising_result.hyperparameters['lengthscale'].unit['s'],
                           'max_rate_flags': ', '.join(rising_result.flags),
                           'max_oxygen_umol': float(smoothed_umol[max_oxygen_index]),
                           'max_oxygen_time_s': float(time_reaction[max_oxygen_index]),
                           'max_oxygen_unit': 'umol',
                           }

    return processed_data_dict
