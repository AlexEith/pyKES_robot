# Parameters used during data processing
PROCESSING_PARAMETERS = {
    'processing_parameters': {
                        'offset': 0,
                        'baseline_polynomial_order': 4,
                        'liquid_phase_volume_ml': 8.5, # 5.1 mL water + 4 x 0.85 mL stock solutions
                        # Max-rate window and (min, max) smoothing lengthscale in s, None: see docs/max_rate_settings.md
                        'max_rate_window_s': None,
                        'max_rate_lengthscale_bounds_s': None,
                    },
}

# Mapping of metadata columns to dataset groups (for visualisation)
GROUP_MAPPING = {
        'Reference': None,
        'Intensity': 'metadata/Power output [W/m^2]',
        'Duty cycle': 'metadata/Duty cycle [%]',
        'Frequency': 'metadata/Frequency [Hz]',
        'Photosensitizer':'metadata/Photosensitizer',
        'Photosensitizer concentration': 'metadata/c(photosensitizer) [M]',
        'Catalyst': 'metadata/Catalyst',
        'Catalyst concentration': 'metadata/c(catalyst) [M]',
        'Persulfate concentration': 'metadata/c(Na2S2O8) [M]',
        'pH': 'metadata/pH [-]',
        }

# Instruction for time series plotting (mapping of plot labels to dataset paths)
# and kinetic results plotting (mapping of result labels to dataset paths and units)
PLOTTING_INSTRUCTIONS = {
    'time_series_instructions': {
                    'Raw': {
                        'x': 'raw_data/time_s',
                        'y': 'raw_data/measurement_raw',
                        'unit_x': 'raw_data/time_unit',
                        'unit_y': 'raw_data/measurement_unit',
                        },
                    'Baseline': {
                        'x': 'raw_data/time_s',
                        'y': 'processed_data/baseline_umol_L',
                        'unit_x': 'raw_data/time_unit',
                        'unit_y': 'processed_data/baseline_unit',
                        },
                    'Baseline corrected': {
                        'x': 'raw_data/time_s',
                        'y': 'processed_data/data_corrected_umol_L',
                        'unit_x': 'raw_data/time_unit',
                        'unit_y': 'processed_data/baseline_unit',
                        },
                    'Reaction': {
                        'x': 'processed_data/time_reaction_s',
                        'y': 'processed_data/data_reaction_umol',
                        'unit_x': 'processed_data/time_unit',
                        'unit_y': 'processed_data/data_unit',
                        },
                    'Smoothed': {
                        'x': 'processed_data/time_reaction_s',
                        'y': 'processed_data/smoothed_gaussian_umol',
                        'x_point': 'processed_data/max_oxygen_time_s',
                        'y_point': 'processed_data/max_oxygen_umol',
                        'unit_x': 'processed_data/time_unit',
                        'unit_y': 'processed_data/smoothed_gaussian_unit',
                        },
                    'Rate': {
                        'x': 'processed_data/time_rising_part_s',
                        'y': 'processed_data/rate_gaussian_umol_s',
                        'x_point': 'processed_data/max_rate_time_s',
                        'y_point': 'processed_data/max_rate_umol_s',
                        'unit_x': 'processed_data/time_unit',
                        'unit_y': 'processed_data/rate_gaussian_unit',
                        },
                },

    'kinetic_results_instructions': {
        'Max rate': {'Value': 'processed_data/max_rate_umol_s',
                     'Unit': 'Rate / umol/s'},
        'Max O2': {'Value': 'processed_data/max_oxygen_umol',
                   'Unit': 'O2 / umol'},
    },

    'results_table_instructions': {
        'Max. rate (umol/s)': {'result': 'processed_data/max_rate_umol_s',
                               'format': '.5f'},
        'Max. rate window (s)': {'result': 'processed_data/max_rate_window_s',
                                 'format': '.1f'},
        'Max. O2 (umol)': {'result': 'processed_data/max_oxygen_umol',
                           'format': '.4f'},
        'Max. rate flags': {'result': 'processed_data/max_rate_flags'},
    },
}
