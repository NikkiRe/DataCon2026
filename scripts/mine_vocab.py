import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nanozx import dataset
from nanozx.schema import FIELDS, NUMERIC_FIELDS

CATEGORICAL = ["formula", "activity", "syngony", "surface", "reaction_type"]
UNIT_FIELDS = ["km_unit", "vmax_unit", "c_const_unit", "ccat_unit"]
OUT = Path(__file__).resolve().parents[1] / "data" / "cache" / "vocab.json"


def main() -> None:
    df = dataset.load_raw()
    present = df[df["access"] == 1]

    vocab = {}
    for field in CATEGORICAL + UNIT_FIELDS:
        counts = present[field].dropna().astype(str).value_counts()
        vocab[field] = counts.to_dict()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(vocab, ensure_ascii=False, indent=2))

    for field in CATEGORICAL + UNIT_FIELDS:
        items = list(vocab[field].items())
        head = ", ".join(f"{k}({v})" for k, v in items[:10])
        print(f"{field:14} [{len(items)} distinct]  {head}")


if __name__ == "__main__":
    main()
