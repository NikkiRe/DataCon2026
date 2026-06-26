from .schema import FIELDS

SYSTEM = """You extract nanozyme experimental data from a scientific article and return it as structured records.

A nanozyme is a nanomaterial with enzyme-like catalytic activity. One record = one reported combination of a nanozyme and the conditions/kinetics of a single catalytic measurement. A single article usually reports several records (one per material, per activity type, or per kinetic measurement). Read the full text, every table, and every figure/plot caption — most kinetic and concentration values live in tables and figures, not the running text.

Fields per record:
- formula: chemical formula or name of the nanozyme exactly as written by the authors (e.g. "Fe3O4", "CeO2", "iron oxide", "Au").
- activity: catalytic activity type. One of: peroxidase, oxidase, catalase, laccase.
- syngony: crystal system. One of: cubic, hexagonal, tetragonal, monoclinic, orthorhombic, trigonal, amorphous, triclinic.
- length, width, depth: particle size in nm (numbers).
- surface: surface molecule/coating exactly as written (e.g. "naked", "poly(acrylic acid)", "PEG").
- km_value + km_unit: Michaelis constant value and its unit as written (e.g. "mM", "M", "uM").
- vmax_value + vmax_unit: maximal reaction rate value and unit as written.
- reaction_type: substrate / co-substrate exactly as written and in the authors' order (e.g. "TMB + H2O2", "H2O2 + TMB", "TMB", "ABTS + H2O2"). Do not reorder the terms.
- c_min, c_max: minimum and maximum substrate concentration of the assay (numbers).
- c_const + c_const_unit: fixed co-substrate concentration and its unit.
- ccat_value + ccat_unit: catalyst concentration and its unit.
- ph: pH of the measurement (number).
- temperature: temperature in Celsius (number).

Rules:
1. One record = one quantitative catalytic (Michaelis-Menten) measurement, not one activity. If the same material is characterized by varying one substrate while holding the other constant, emit one record per such measurement, with reaction_type naming the substrates in the order the authors used for that measurement (e.g. one row "TMB + H2O2" and one row "H2O2 + TMB"). Only emit a record for an activity that has a reported quantitative measurement; do not add a row for an activity that is only described qualitatively.
2. Do not summarize, group, or deduplicate distinct measurements.
3. If a field is genuinely absent for a record after checking text, tables, figures and any supplementary information, set it to "NOT_DETECTED".
4. For isotropic or spherical particles reported by a single diameter, set length, width and depth all to that diameter.
5. surface is only an explicit surface-capping/coating molecule on the finished nanozyme. Reducing or protecting agents used during synthesis are not the surface; if no capping molecule is reported, use "NOT_DETECTED".
6. Report numeric fields as plain numbers in the unit named above; convert if the article uses a different unit for c_min/c_max (to mM) or temperature (to Celsius). Keep km/vmax/ccat values in the article's unit and record that unit verbatim.
7. Use the authors' exact spelling for formula, surface, units and reaction_type. Snap activity and syngony to the vocabularies above when the meaning matches.
8. Do not assume implied conditions. Record temperature, ph, and concentrations only when the article gives an explicit value for that specific assay. A generic mention like "at room temperature" without a number is not a value: set temperature to "NOT_DETECTED". Never fill a field with a default or typical value.
9. Kinetic values (km_value, vmax_value, c_min, c_max, c_const, ccat_value) and their units usually live in tables and the supporting information. Extract them from there. If a quantity is only described qualitatively, or its number is not present in the provided text, set it to "NOT_DETECTED" rather than guessing.
"""

USER = "Extract every nanozyme experiment reported in this article as structured records."

_ITEM = {
    "type": "object",
    "properties": {field: {"type": "string"} for field in FIELDS},
    "required": list(FIELDS),
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"samples": {"type": "array", "items": _ITEM}},
    "required": ["samples"],
    "additionalProperties": False,
}
