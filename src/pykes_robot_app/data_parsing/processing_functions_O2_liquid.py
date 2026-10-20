from pathlib import Path

from pyKES.utilities.unit_handler import Quantity

from pykes_robot_app.data_parsing.raw_data_reading_functions import read_robot_log_file
from pykes_robot_app.data_parsing.baseline_correction import correct_baseline
from pykes_robot_app.data_parsing.general_processing_functions import (
    processing_data,
    convert_umol_L_to_mol,
    FILE_NAME_COLUMN,
)
from pykes_robot_app.parameters import PROCESSING_PARAMETERS

def raw_data_reading_function_O2_liquid(directory: Path, metadata_dict):
    """
    Read the robot log file named in the 'File name O2' column of an experiment.

    Parameters
    ----------
    directory : Path
        Directory containing the raw data files.
    metadata_dict : dict
        Metadata of the experiment, as returned by the metadata retrieval function.

    Returns
    -------
    raw_data_dict : dict
        Raw data, as returned by read_robot_log_file.
    """

    return read_robot_log_file(Path(directory) / metadata_dict[FILE_NAME_COLUMN])

def processing_function_O2_liquid(raw_data_dict, metadata_dict):
    """
    Process liquid phase O2 data given in umol/L: baseline correction, then max rate and max O2.

    Parameters
    ----------
    raw_data_dict : dict
        Raw data, as returned by the raw data reading function.
    metadata_dict : dict
        Metadata of the experiment, as returned by the metadata retrieval function.

    Returns
    -------
    processed_O2 : dict
        Processed data, max rate and max O2 amount, plus the baseline correction.
    """

    baseline, baseline_with_step, data_corrected = correct_baseline(
        raw_data_dict['time_s'],
        raw_data_dict['measurement_raw'],
        raw_data_dict['irradiation_start_s'],
        raw_data_dict['irradiation_end_s'],
        PROCESSING_PARAMETERS['processing_parameters']['baseline_polynomial_order'])

    data_quantity = convert_umol_L_to_mol(data_corrected,
                                          liquid_phase_volume_ml = PROCESSING_PARAMETERS['processing_parameters']['liquid_phase_volume_ml'])

    processed_O2 = processing_data(
        time = Quantity(raw_data_dict['time_s'], 's'),
        data = data_quantity,
        start = Quantity(raw_data_dict['irradiation_start_s'], 's'),
        end = Quantity(raw_data_dict['irradiation_end_s'], 's'),
        metadata_dict = metadata_dict,
    )

    processed_O2.update({'baseline_umol_L': baseline,
                         'lbc_fit_umol_L': baseline_with_step,
                         'data_corrected_umol_L': data_corrected,
                         'baseline_unit': 'umol/L',
                         })

    return processed_O2

def test_function():

    import tempfile
    import numpy as np
    import pandas as pd

    # Synthetic robot log: O2 rises at a known rate for 120 s of a 600 s irradiation
    oxygen_rate_umol_L_s = 0.5
    time_step = 3.5
    noise_umol_L = 0.012 # white noise of the clean robot runs
    phases = [('DEGASSING', 'FIRESTING-START', 300), ('PREREACTION-BASELINE', 'FIRESTING-START', 900),
              ('REACTION', 'LAMP-ON', 600), ('POSTREACTION-BASELINE', 'LAMP-OFF', 300)]

    rows = []
    phase_start = 0.
    for status, command, phase_duration in phases:
        for duration in np.arange(phase_start, phase_start + phase_duration, time_step):
            rows.append({'duration': duration, 'status': status, 'command': command})
        phase_start += phase_duration

    log = pd.DataFrame(rows)
    time_since_irradiation = log['duration'] - 1200
    log['uM_1'] = (5 - 1e-4 * log['duration']
                   + oxygen_rate_umol_L_s * np.clip(time_since_irradiation, 0, 120)
                   + np.random.default_rng(0).normal(0, noise_umol_L, len(log)))

    metadata_dict = {'experiment_name': 'SYNTHETIC-1', FILE_NAME_COLUMN: 'SYNTHETIC-1.csv'}

    with tempfile.TemporaryDirectory() as directory:
        log.to_csv(Path(directory) / metadata_dict[FILE_NAME_COLUMN], index = False)
        raw_data_dict = raw_data_reading_function_O2_liquid(directory, metadata_dict)

    processed = processing_function_O2_liquid(raw_data_dict, metadata_dict)

    liquid_volume_L = PROCESSING_PARAMETERS['processing_parameters']['liquid_phase_volume_ml'] * 1e-3
    print(f"True rate: {oxygen_rate_umol_L_s * liquid_volume_L:.5f} umol/s, "
          f"extracted: {processed['max_rate_umol_s']:.5f} umol/s")
    print(f"True max O2: {oxygen_rate_umol_L_s * 120 * liquid_volume_L:.4f} umol, "
          f"extracted: {processed['max_oxygen_umol']:.4f} umol")

if __name__ == "__main__":
    test_function()
