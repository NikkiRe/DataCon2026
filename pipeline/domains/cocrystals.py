SCHEMA = {
    "name_cocrystal": "Common name or abbreviation of the co-crystal (e.g. 'CBZ-SAC', 'ACT-4,4-BPY')",
    "ratio_cocrystal": "Molar ratio of drug to co-former (e.g. '1:1', '2:1')",
    "name_drug": "Full name of the active pharmaceutical ingredient (API / drug molecule)",
    "name_coformer": "Full name of the co-former molecule",
    "photostability_change": (
        "How photostability of the co-crystal compares to the pure drug. "
        "MUST be exactly one of these three strings: "
        "\"increases\" | \"decreases\" | \"does not change\". "
        "If not mentioned in the paper, omit the field."
    ),
}

FEW_SHOT = """
Example output for a paper describing two co-crystals:
[
  {
    "name_cocrystal": "ACT-4,4'-BPY",
    "ratio_cocrystal": "2:1",
    "name_drug": "Acacetin",
    "name_coformer": "4,4'-Bipyridine",
    "photostability_change": "does not change"
  },
  {
    "name_cocrystal": "CBZ-SAC",
    "ratio_cocrystal": "1:1",
    "name_drug": "Carbamazepine",
    "name_coformer": "Saccharin",
    "photostability_change": "increases"
  }
]
"""

SYSTEM_PROMPT = """You are an expert chemist specializing in pharmaceutical co-crystals.
Your task is to extract structured data from scientific papers.
Always return valid JSON and nothing else."""

SMILES_PAIRS = [("name_drug", "SMILES_drug"), ("name_coformer", "SMILES_coformer")]

OUTPUT_COLUMNS = [
    "name_cocrystal",
    "ratio_cocrystal",
    "name_drug",
    "SMILES_drug",
    "name_coformer",
    "SMILES_coformer",
    "photostability_change",
]


def build_extraction_prompt(markdown_text: str) -> str:
    schema_desc = "\n".join(f"- {k}: {v}" for k, v in SCHEMA.items())
    return f"""Extract all pharmaceutical co-crystals from the paper below.

For each co-crystal, extract these fields:
{schema_desc}

Return a JSON array of objects. Extract ALL co-crystals mentioned in the paper.
{FEW_SHOT}

--- PAPER START ---
{markdown_text}
--- PAPER END ---

JSON array:"""


class CocrystalsDomain:
    name = "cocrystals"
    system_prompt = SYSTEM_PROMPT
    smiles_pairs = SMILES_PAIRS
    output_columns = OUTPUT_COLUMNS

    @staticmethod
    def build_prompt(markdown_text: str) -> str:
        return build_extraction_prompt(markdown_text)
