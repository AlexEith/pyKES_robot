from pyKES.streamlit_app.config_interface import (
    PyKESStreamlitConfig,
    HomeConfig,
    DataUploadConfig,
    FileUploadHandler,
)

from pyKES.utilities.version_information import get_project_version

from pykes_robot_app.data_parsing.general_processing_functions import metadata_retrival_function

from pykes_robot_app.data_parsing.processing_functions_O2_liquid import (
    raw_data_reading_function_O2_liquid,
    processing_function_O2_liquid
)

from pykes_robot_app.parameters import (
    PROCESSING_PARAMETERS,
    GROUP_MAPPING,
    PLOTTING_INSTRUCTIONS,
)

# -----------------------------------------------------------------------------
# Provenance of this app, stored in every dataset it processes
# -----------------------------------------------------------------------------

# Recorded in dataset.version['external_version'], so the processed data can be
# traced back to the code that produced it. get_project_version reads the
# version declared in this repository's own pyproject.toml.
EXTERNAL_VERSION = {
    "app": "pykes_robot_app",
    "version": get_project_version(__file__),
}

# -----------------------------------------------------------------------------
# File Handler Config
# -----------------------------------------------------------------------------

file_handler_O2_liquid =  FileUploadHandler(
                            label = "📊 O2 (liquid phase) - Upload Robot Raw Data",
                            file_type = ["csv"],
                            help_text = "Upload the robot log files named in the 'File name O2' column of the overview.",
                            overview_df_experiment_column = "Experiment",
                            metadata_retrival_function = metadata_retrival_function,
                            raw_data_reading_function = raw_data_reading_function_O2_liquid,
                            processing_function = processing_function_O2_liquid,
                            )

# -----------------------------------------------------------------------------
# Data Upload and Home Configuration
# -----------------------------------------------------------------------------

DATA_UPLOAD_CONFIG = DataUploadConfig(

    file_handlers = [file_handler_O2_liquid],
    # First sheet of the overview, whatever its name (Tabelle1, Sheet1, ...)
    metadata_excel_sheet_name=0,
    metadata_excel_experiment_column="Experiment",
    group_mapping=GROUP_MAPPING,
    plotting_instruction=PLOTTING_INSTRUCTIONS,
    processing_parameters=PROCESSING_PARAMETERS,
    external_version=EXTERNAL_VERSION,
)

HOME_CONFIG = HomeConfig(
    page_title = "pyKES Robot Analysis",
    main_title = "pyKES Robot Analysis",
)

# -----------------------------------------------------------------------------
# Top-level app configuration
# -----------------------------------------------------------------------------

PYKES_CONFIG = PyKESStreamlitConfig(
    home_config = HOME_CONFIG,
    data_upload_config = DATA_UPLOAD_CONFIG,
    app_title = "Photocatalysis Robot Data Analysis System",
    app_icon = ":test_tube:",
)
