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
        "Focus on pharmaceutical co-crystals: drug and coformer names, stoichiometric ratios, "
        "and photostability_change compared to the pure drug (API) under the same conditions. "
        "photostability_change MUST be exactly one of: "
        '"increases", "decreases", "does not change", or NOT_DETECTED. '
        "Compare each co-crystal to its parent drug — if UV degradation is slower / stability "
        "is higher than pure drug, use \"increases\"; if faster degradation, \"decreases\". "
        "One row = one distinct co-crystal entity studied in THIS article. "
        "Do NOT summarize or merge distinct co-crystals. "
        "Do NOT extract co-crystals mentioned only in Introduction, References, or prior-work "
        "citations — only entities prepared and tested in this study. "
        "For drug-loaded nanosponge systems: use abbreviations RES-NS (resveratrol) and "
        "OXY-NS (oxyresveratrol); name_coformer = nanosponge; ratio_cocrystal = NOT_DETECTED; "
        "do NOT emit separate rows for each loading ratio (1:2, 1:4, 1:6)."
    ),
    "oxazolidinone": (
        "Focus on antibacterial activity: compound identifiers, MIC/pMIC values, "
        "target relation and units, and bacterial strains tested. "
        "One row = one compound × bacteria × measurement. Extract ALL rows from activity tables."
    ),
    "cytotoxicity": (
        "Focus on nanomaterial cytotoxicity experiments. "
        "One row = one experimental condition (material × cell line × concentration × time × assay). "
        "Extract EVERY row from cytotoxicity/viability tables — do NOT summarize to a few materials. "
        "human_animal: use H for human, A for animal sources. "
        "Typical articles have dozens of rows, not 2–3."
    ),
    "nanozymes": (
        "One row = one quantitative catalytic (Michaelis-Menten) measurement. "
        "Do not summarize, group, or deduplicate distinct measurements. "
        "activity: peroxidase | oxidase | catalase | laccase. "
        "Read all tables and figure captions for km/vmax/concentration values."
    ),
}

_FEW_SHOT: dict[str, str] = {
    "cocrystals": """
Example output:
[
  {
    "name_cocrystal": "ACT-4,4'-BPY",
    "ratio_cocrystal": "2:1",
    "name_drug": "Acacetin",
    "SMILES_drug": "NOT_DETECTED",
    "name_coformer": "4,4'-Bipyridine",
    "SMILES_coformer": "NOT_DETECTED",
    "photostability_change": "does not change"
  },
  {
    "name_cocrystal": "CBZ-SAC",
    "ratio_cocrystal": "1:1",
    "name_drug": "Carbamazepine",
    "SMILES_drug": "NOT_DETECTED",
    "name_coformer": "Saccharin",
    "SMILES_coformer": "NOT_DETECTED",
    "photostability_change": "increases"
  },
  {
    "name_cocrystal": "RES-NS",
    "ratio_cocrystal": "NOT_DETECTED",
    "name_drug": "resveratrol",
    "SMILES_drug": "NOT_DETECTED",
    "name_coformer": "nanosponge",
    "SMILES_coformer": "NOT_DETECTED",
    "photostability_change": "increases"
  }
]
""",
    "cytotoxicity": """
Example: a table with 3 materials × 4 concentrations = 12 rows, not 3.
Each row must include material, cell_source, time_hr, concentration, test, viability_% when present.
human_animal: "H" or "A" (not full words).
""",
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
    few_shot = _FEW_SHOT.get(domain, "")

    return f"""{PROMPT_DESCRIPTION}

Domain: {domain}

Extract structured data rows from the provided content. Each row must use exactly these columns:
{chr(10).join(column_lines)}

Rules:
- Return a JSON array of objects. Each object is one extracted row.
- Use column names exactly as listed above.
- If a value is missing or not found in the source, set it to "{NOT_DETECTED}".
- Do not invent values; extract only what is explicitly stated in text, tables, or figures.
- Do NOT summarize multiple table rows into one. One table row = one output row when applicable.
- Extract ALL relevant records from the entire article including every table and figure caption.
- Numeric values: use dot as decimal separator in output.
{hint}
{few_shot}
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
- List every distinct experimental condition separately (do not collapse table rows).
- Include section references when helpful (e.g. "Table 2", "Figure 1").
- Omit introduction, references, and generic background.
- If a field is absent, omit it (do not write "{NOT_DETECTED}" here).
{hint}
"""


def build_verify_prompt(domain: str) -> str:
    hint = _DOMAIN_HINTS.get(domain, "")
    cocrystals_extra = ""
    if domain == "cocrystals":
        cocrystals_extra = (
            "\n- Double-check photostability_change against photostability figures/tables "
            "(compare co-crystal vs pure drug).\n"
            "- Remove rows from cited prior work not studied in this article.\n"
            "- Collapse nanosponge loading-ratio variants into one RES-NS and one OXY-NS row.\n"
        )
    return f"""{PROMPT_DESCRIPTION}

Domain: {domain}

You verify and correct extracted JSON records against the source article.
Fix wrong values, remove duplicate rows, ensure correct row count from tables.
{cocrystals_extra}{hint}
Return ONLY a corrected JSON array."""


def build_document_user_prompt(domain: str, content: str) -> str:
    return (
        f"Extract ALL structured data rows for domain '{domain}' from the article below.\n"
        "Return ONLY a JSON array — one object per distinct experimental record.\n"
        "Include every table row. Do not summarize.\n"
        "Extract only data from experiments in THIS article — skip Introduction/References.\n\n"
        f"{content}"
    )


def build_chunk_user_prompt(domain: str, content: str, *, chunk_index: int, chunk_total: int) -> str:
    """User prompt for one chunk of a long article."""
    extra = ""
    if domain == "cocrystals":
        extra = (
            "Skip co-crystals mentioned only as literature examples. "
            "For nanosponge formulations use RES-NS / OXY-NS naming.\n"
        )
    return (
        f"Extract structured data rows for domain '{domain}' from section {chunk_index}/{chunk_total} "
        f"of the article below.\n"
        "Return ONLY a JSON array. Include table rows in this section. Do not summarize.\n"
        f"{extra}\n"
        f"{content}"
    )
