import requests
import time

PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/property/IsomericSMILES/JSON"


def name_to_smiles(name: str) -> str | None:
    """Look up canonical SMILES from compound name via PubChem."""
    if not name or name.strip() == "":
        return None
    try:
        url = PUBCHEM_URL.format(requests.utils.quote(name.strip()))
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            props = data["PropertyTable"]["Properties"][0]
            return props.get("IsomericSMILES") or props.get("SMILES")
    except Exception:
        pass
    return None


def enrich_smiles(records: list[dict], name_field: str, smiles_field: str) -> list[dict]:
    """Fill smiles_field by looking up name_field in PubChem for each record."""
    for rec in records:
        name = rec.get(name_field, "")
        if name and not rec.get(smiles_field):
            smiles = name_to_smiles(name)
            if smiles:
                rec[smiles_field] = smiles
            time.sleep(0.2)  # PubChem rate limit
    return records
