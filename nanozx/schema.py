DATASET_ID = "ai-chem/Nanozymes"

FIELDS = [
    "formula",
    "activity",
    "syngony",
    "length",
    "width",
    "depth",
    "surface",
    "km_value",
    "km_unit",
    "vmax_value",
    "vmax_unit",
    "reaction_type",
    "c_min",
    "c_max",
    "c_const",
    "c_const_unit",
    "ccat_value",
    "ccat_unit",
    "ph",
    "temperature",
]

FLOAT_FIELDS = {
    "km_value",
    "vmax_value",
    "c_min",
    "c_max",
    "c_const",
    "ccat_value",
    "ph",
    "temperature",
}

RAW_NUMERIC_FIELDS = {"length", "width", "depth"}

NUMERIC_FIELDS = FLOAT_FIELDS | RAW_NUMERIC_FIELDS

STRING_FIELDS = {f for f in FIELDS if f not in NUMERIC_FIELDS}

STRING_MISSING = "NOT_DETECTED"
NUMERIC_MISSING = "nan"

ACTIVITY_VOCAB = {"peroxidase", "oxidase", "catalase", "laccase"}
SYNGONY_VOCAB = {
    "cubic",
    "hexagonal",
    "tetragonal",
    "monoclinic",
    "orthorhombic",
    "trigonal",
    "amorphous",
    "triclinic",
}
