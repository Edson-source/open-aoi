import os
from dotenv import load_dotenv

assert load_dotenv(".env")

DEFAULT_DEFECT_TYPES = {
    "missing_component": {
        "title": "Missing component",
        "description": "Component is present on template, but is missing on tested image.",
    },
    "automatic_rejection": {
        "title": "Automatic rejection",
        "description": "Inspection zone is automatically rejected.",
    },
    "automatic_acceptance": {
        "title": "Automatic acceptance",
        "description": "Inspection zone is automatically accepted.",
    },
    "print_quality": {
        "title": "Print quality",
        "description": "Print quality issue.",
    },
    "capacitor_opposite_orientation": {
        "title": "Capacitor opposite orientation",
        "description": "Capacitor orientation is opposite to template.",
    },
}

MODULES_PATH = "./src/open_aoi_core/open_aoi_core/content/modules"
DEFAULT_MODULES = {
    f"{MODULES_PATH}/component_presence_discrete_wavelet_transformation.py": {
        "title": "Component presence detection (wavelet transformation, default module)",
        "description": "Module provide component presence inspection with wavelet transformation.",
        "type": "missing_component",
    },
    f"{MODULES_PATH}/component_presence_histogram_backprojection.py": {
        "title": "Component presence detection (histogram backprojection, default module)",
        "description": "Module provide component presence inspection with histogram backprojection.",
        "type": "missing_component",
    },
    f"{MODULES_PATH}/print_quality_xor_morphology.py": {
        "title": "Print quality inspection (classical image processing, default module)",
        "description": "Module inspect print quality with classical image processing approach",
        "type": "print_quality",
    },
    f"{MODULES_PATH}/automatic_rejection.py": {
        "title": "Auto rejection module (default module)",
        "description": "This module automatically reject all inspection zones.",
        "type": "automatic_rejection",
    },
    f"{MODULES_PATH}/automatic_acceptance.py": {
        "title": "Auto acceptance module (default module)",
        "description": "This module automatically accepts all inspection zones.",
        "type": "automatic_acceptance",
    },
    f"{MODULES_PATH}/capacitor_orientation_opposite_orientation.py": {
        "title": "Capacitor opposite orientation inspection (classical image processing, default module)",
        "description": "Module provide capacitor orientation inspection to detect opposite orientation compared to template.",
        "type": "capacitor_opposite_orientation",
    },
}


SIMULATION = int(os.environ["SIMULATION"])
assert SIMULATION

MYSQL_DATABASE = os.environ["MYSQL_DATABASE"]
assert MYSQL_DATABASE

MYSQL_USER = os.environ["MYSQL_USER"]
assert MYSQL_USER

MYSQL_PASSWORD = os.environ["MYSQL_PASSWORD"]
assert MYSQL_PASSWORD

MYSQL_HOST = os.environ["MYSQL_HOST"]
assert MYSQL_HOST

MYSQL_PORT = os.environ["MYSQL_PORT"]
assert MYSQL_PORT

AOI_OPERATOR_INITIAL_PASSWORD = os.environ["AOI_OPERATOR_INITIAL_PASSWORD"]
assert AOI_OPERATOR_INITIAL_PASSWORD

AOI_ADMINISTRATOR_INITIAL_PASSWORD = os.environ["AOI_ADMINISTRATOR_INITIAL_PASSWORD"]
assert AOI_ADMINISTRATOR_INITIAL_PASSWORD

STORAGE_SECRET = os.environ["STORAGE_SECRET"]
assert STORAGE_SECRET and len(STORAGE_SECRET) > 10

MINIO_ROOT_USER = os.environ["MINIO_ROOT_USER"]
assert MINIO_ROOT_USER

MINIO_ROOT_PASSWORD = os.environ["MINIO_ROOT_PASSWORD"]
assert MINIO_ROOT_PASSWORD

MINIO_HOST = os.environ["MINIO_HOST"]
assert MINIO_HOST

MINIO_PORT = os.environ["MINIO_PORT"]
assert MINIO_PORT
