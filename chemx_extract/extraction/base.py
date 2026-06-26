from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

try:
    from chemx_extract.config import NOT_DETECTED
except ImportError:
    NOT_DETECTED = "NOT_DETECTED"

try:
    from chemx_extract.schemas import EXTRACTED_COLUMNS, NUMERIC_COLUMNS, get_columns
except ImportError:
    EXTRACTED_COLUMNS = {
        "cocrystals": [
            "name_cocrystal",
            "ratio_cocrystal",
            "name_drug",
            "SMILES_drug",
            "name_coformer",
            "SMILES_coformer",
            "photostability_change",
        ],
        "oxazolidinone": [
            "compound_id",
            "smiles",
            "target_type",
            "target_relation",
            "target_value",
            "target_units",
            "bacteria",
        ],
        "cytotoxicity": [
            "material",
            "shape",
            "coat_functional_group",
            "synthesis_method",
            "surface_charge",
            "core_nm",
            "size_in_medium_nm",
            "hydrodynamic_nm",
            "potential_mv",
            "zeta_in_medium_mv",
            "no_of_cells_cells_well",
            "human_animal",
            "cell_source",
            "cell_tissue",
            "cell_morphology",
            "cell_age",
            "time_hr",
            "concentration",
            "test",
            "test_indicator",
            "viability_%",
        ],
    }
    NUMERIC_COLUMNS = {
        "oxazolidinone": ["target_value"],
        "cytotoxicity": [
            "core_nm",
            "size_in_medium_nm",
            "hydrodynamic_nm",
            "potential_mv",
            "zeta_in_medium_mv",
            "no_of_cells_cells_well",
            "time_hr",
            "concentration",
            "viability_%",
        ],
    }

    def get_columns(domain: str) -> list[str]:
        return EXTRACTED_COLUMNS.get(domain, [])


def _unwrap_json_array(data: Any) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("rows", "data", "results", "extractions", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _strip_json_fences(content: str) -> str:
    """Remove markdown code fences often wrapping LLM JSON output."""
    text = content.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def call_llm_json(client: OpenAI, system: str, user: str, model: str) -> list[dict]:
    """Call OpenAI chat completions and parse a JSON array of row dicts."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            return []
        data = json.loads(_strip_json_fences(content))
        return _unwrap_json_array(data)
    except Exception:
        logger.exception("Failed to parse LLM JSON response")
        return []


def normalize_row(row: dict, domain: str) -> dict:
    """Ensure all schema columns are present; missing values become NOT_DETECTED."""
    columns = get_columns(domain)
    normalized: dict[str, str] = {}
    for column in columns:
        value = row.get(column, NOT_DETECTED)
        if value is None or (isinstance(value, str) and not value.strip()):
            normalized[column] = NOT_DETECTED
        else:
            normalized[column] = str(value)
    return normalized
