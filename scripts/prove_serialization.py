import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from nanozx import dataset, metric, serialize
from nanozx.schema import FIELDS

BASELINE_URL = (
    "https://raw.githubusercontent.com/ai-chem/ChemX/main/"
    "LLM/result/from_single_agent/nanozymes/pred.csv"
)
LOCAL_BASELINE = Path(__file__).resolve().parents[2] / ".chemx_ref" / "nanozymes_single_agent_pred.csv"


def load_baseline() -> pd.DataFrame:
    if LOCAL_BASELINE.exists():
        return pd.read_csv(LOCAL_BASELINE)
    import requests

    text = requests.get(BASELINE_URL, timeout=60).text
    return pd.read_csv(io.StringIO(text))


def as_is(pred: pd.DataFrame) -> pd.DataFrame:
    frame = pred.copy()
    frame["pdf"] = frame["pdf"].astype(str).str.lower()
    return frame.drop_duplicates()


def reserialized(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, record in pred.iterrows():
        row = {field: serialize.serialize_value(field, record.get(field)) for field in FIELDS}
        row["pdf"] = str(record["pdf"]).lower()
        rows.append(row)
    return pd.DataFrame(rows).drop_duplicates()


def main() -> None:
    gt = dataset.ground_truth()
    base = load_baseline()
    print(f"ground-truth open-access articles: {gt['pdf'].nunique()} | rows: {len(gt)}")
    print(f"baseline prediction rows: {len(base)}\n")

    results = {}
    for label, pred in [("baseline as-is", as_is(base)), ("re-serialized", reserialized(base))]:
        metrics = metric.score(gt, pred)
        results[label] = metrics
        print(f"{label:>16}  macro-F1 = {metric.macro_f1(metrics):.4f}")

    print("\nper-field f1 (as-is -> re-serialized):")
    a = results["baseline as-is"]["f1"]
    b = results["re-serialized"]["f1"]
    order = (b - a).sort_values(ascending=False).index
    for field in order:
        delta = b[field] - a[field]
        mark = "  <==" if delta > 0.001 else ""
        print(f"  {field:14} {a[field]:.3f} -> {b[field]:.3f}  ({delta:+.3f}){mark}")

    print(f"\nbaseline published target macro-F1: 0.164")
    print(f"reproduced as-is macro-F1:           {metric.macro_f1(results['baseline as-is']):.4f}")
    print(f"format-only macro-F1:                {metric.macro_f1(results['re-serialized']):.4f}")


if __name__ == "__main__":
    main()
