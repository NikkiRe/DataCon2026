from __future__ import annotations

try:
    from chemx_extract.config import NOT_DETECTED
except ImportError:
    NOT_DETECTED = "NOT_DETECTED"

try:
    from chemx_extract.schemas import NUMERIC_COLUMNS, get_columns
except ImportError:
    from chemx_extract.extraction.base import NUMERIC_COLUMNS, get_columns

PROMPT_DESCRIPTION = (
    "You are a domain-specific chemical information extraction assistant."
)

_DOMAIN_HINTS: dict[str, str] = {
    "cocrystals": (
        "Focus on co-crystal entries: drug and coformer names, stoichiometric ratios, "
        "and photostability changes after co-crystal formation."
    ),
    "oxazolidinone": (
        "Focus on antibacterial activity: compound identifiers, MIC/pMIC values, "
        "target relation and units, and bacterial strains tested."
    ),
    "cytotoxicity": (
        "Focus on nanomaterial cytotoxicity: cell lines and sources, exposure time, "
        "concentration, viability percentages, and assay details."
    ),
}


def _column_type(column: str, domain: str) -> str:
    numeric_cols = NUMERIC_COLUMNS.get(domain, [])
    return "numeric" if column in numeric_cols else "text"


def build_system_prompt(domain: str) -> str:
    """Build a system prompt with schema columns, types, and output rules."""
    columns = get_columns(domain)
    if not columns:
        raise ValueError(f"Unknown domain: {domain}")

    column_lines = [
        f"- {column} ({_column_type(column, domain)})"
        for column in columns
    ]
    hint = _DOMAIN_HINTS.get(domain, "")

    return f"""{PROMPT_DESCRIPTION}

Domain: {domain}

Extract structured data rows from the provided content. Each row must use exactly these columns:
{chr(10).join(column_lines)}

Rules:
- Return a JSON array of objects. Each object is one extracted row.
- Use column names exactly as listed above.
- If a value is missing or not found in the source, set it to "{NOT_DETECTED}".
- Do not invent values; extract only what is explicitly stated.
- Numeric values may use comma or dot as decimal separator in the source; preserve the value as a string.
{hint}
"""


def build_compress_prompt(domain: str) -> str:
    """System prompt for cheap-model fact compression (not summarization)."""
    columns = get_columns(domain)
    hint = _DOMAIN_HINTS.get(domain, "")
    column_list = ", ".join(columns)
    return f"""{PROMPT_DESCRIPTION}

Domain: {domain}

Compress the article text into a dense fact sheet for downstream structured extraction.
Target schema columns: {column_list}

Rules:
- Do NOT write a narrative summary. Extract only experimentally relevant facts.
- Preserve exact values: compound IDs, numbers, units, bacterial strains, names, ratios.
- Copy table-like values verbatim when they appear in prose.
- Include section references when helpful (e.g. "Table 2", "Figure 1").
- Omit introduction, references, and generic background.
- If a field is absent, omit it (do not write "{NOT_DETECTED}" here).
{hint}
"""
