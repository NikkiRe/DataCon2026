"""SMILES resolution: RDKit canonicalization and PubChem name lookup."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import requests
from rdkit import Chem

from chemx_extract.config import NOT_DETECTED, PUBCHEM_USER_AGENT
from chemx_extract.schemas import SMILES_COLS

logger = logging.getLogger(__name__)

try:
    from decimer import predict_smiles  # type: ignore[import-untyped]

    _HAS_DECIMER = True
except ImportError:
    _HAS_DECIMER = False

    def predict_smiles(_image_path: str) -> str | None:
        return None

NAME_TO_SMILES_FIELDS: dict[str, dict[str, str]] = {
    "cocrystals": {
        "SMILES_drug": "name_drug",
        "SMILES_coformer": "name_coformer",
    },
    "complexes": {
        "SMILES": "compound_name",
    },
}

PUBCHEM_NAME_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/"
    "CanonicalSMILES/JSON"
)


def canonicalize_smiles(s: str) -> str:
    """Return RDKit-canonical SMILES, or NOT_DETECTED if invalid."""
    if s in (None, "", NOT_DETECTED):
        return NOT_DETECTED if s in (None, "") else str(s)
    text = str(s).strip()
    mol = Chem.MolFromSmiles(text)
    if mol is None:
        return NOT_DETECTED
    return Chem.MolToSmiles(mol)


def name_to_smiles(name: str) -> str | None:
    """Resolve a compound name to SMILES via PubChem PUG REST."""
    if not name or name == NOT_DETECTED:
        return None
    url = PUBCHEM_NAME_URL.format(name=quote(str(name).strip()))
    try:
        response = requests.get(
            url,
            headers={"User-Agent": PUBCHEM_USER_AGENT},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        props = payload.get("PropertyTable", {}).get("Properties", [])
        if not props:
            return None
        smiles = props[0].get("CanonicalSMILES") or props[0].get("ConnectivitySMILES")
        return str(smiles) if smiles else None
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.debug("PubChem lookup failed for %r: %s", name, exc)
        return None


def smiles_from_image(image_path: str) -> str | None:
    """Optional DECIMER image-to-SMILES; returns None if DECIMER is unavailable."""
    if not _HAS_DECIMER:
        return None
    try:
        result = predict_smiles(image_path)
        return str(result) if result else None
    except Exception as exc:  # noqa: BLE001 - optional dependency
        logger.debug("DECIMER failed for %s: %s", image_path, exc)
        return None


def _is_missing(value: Any) -> bool:
    return value in (None, "", NOT_DETECTED)


def resolve_smiles_fields(row: dict, domain: str) -> dict:
    """Fill SMILES columns from names and canonicalize existing SMILES values."""
    resolved = dict(row)
    smiles_cols = SMILES_COLS.get(domain, [])
    name_map = NAME_TO_SMILES_FIELDS.get(domain, {})

    for col in smiles_cols:
        current = resolved.get(col, NOT_DETECTED)
        name_field = name_map.get(col)
        if name_field:
            name_value = resolved.get(name_field, NOT_DETECTED)
            if not _is_missing(name_value) and str(name_value).strip().lower() == "nanosponge":
                resolved[col] = NOT_DETECTED
                continue
        if _is_missing(current):
            name_field = name_map.get(col)
            if name_field:
                name_value = resolved.get(name_field, NOT_DETECTED)
                if not _is_missing(name_value):
                    looked_up = name_to_smiles(str(name_value))
                    if looked_up:
                        resolved[col] = canonicalize_smiles(looked_up)
                        continue
            if _is_missing(resolved.get(col)):
                resolved[col] = NOT_DETECTED
        else:
            resolved[col] = canonicalize_smiles(str(current))

    return resolved
