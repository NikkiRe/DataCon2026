"""
ChemX-compatible evaluation: Precision, Recall, Macro-F1 per domain field.
Usage:
    python evaluate.py --pred predictions.csv --gt data/cocrystals/data/train-00000-of-00001.parquet --domain cocrystals
"""

import argparse
import re
import pandas as pd
import numpy as np

try:
    from rdkit import Chem
    RDKIT_OK = True
except ImportError:
    RDKIT_OK = False


DOMAIN_FIELDS = {
    "cocrystals": [
        "name_cocrystal", "ratio_cocrystal", "name_drug",
        "SMILES_drug", "name_coformer", "SMILES_coformer", "photostability_change",
    ],
}


SMILES_FIELDS = {"SMILES_drug", "SMILES_coformer", "smiles", "SMILES"}


def canonical_smiles(s: str) -> str:
    """Return canonical SMILES via RDKit, or lowercased original if RDKit unavailable."""
    if not RDKIT_OK:
        return s.strip().lower()
    try:
        mol = Chem.MolFromSmiles(s.strip())
        if mol:
            return Chem.MolToSmiles(mol)
    except Exception:
        pass
    return s.strip().lower()


def normalize(val, field: str = "") -> str:
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if field in SMILES_FIELDS:
        return canonical_smiles(s)
    # normalize dashes and whitespace, lowercase
    s = re.sub(r"[–—−]", "-", s)   # em-dash, en-dash → hyphen
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def score_field(pred_vals: list[str], gt_vals: list[str], field: str = "") -> tuple[float, float, float]:
    """Compute precision/recall/f1 for one field across one paper."""
    pred = [normalize(v, field) for v in pred_vals if normalize(v, field)]
    gt = [normalize(v, field) for v in gt_vals if normalize(v, field)]

    if not gt and not pred:
        return 1.0, 1.0, 1.0
    if not gt:
        return 0.0, 1.0, 0.0
    if not pred:
        return 1.0, 0.0, 0.0

    matched_gt = set()
    tp = 0
    for p in pred:
        for i, g in enumerate(gt):
            if i not in matched_gt and p == g:
                tp += 1
                matched_gt.add(i)
                break

    precision = tp / len(pred)
    recall = tp / len(gt)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def evaluate(pred_df: pd.DataFrame, gt_df: pd.DataFrame, domain: str) -> pd.DataFrame:
    fields = DOMAIN_FIELDS[domain]
    results = []

    doi_col = "doi"
    if doi_col in pred_df.columns:
        pred_dois = set(pred_df[doi_col].unique())
        papers = [d for d in gt_df[doi_col].unique() if d in pred_dois]
    else:
        papers = gt_df[doi_col].unique()

    for field in fields:
        precisions, recalls, f1s = [], [], []
        for doi in papers:
            gt_rows = gt_df[gt_df[doi_col] == doi]
            pred_rows = pred_df[pred_df[doi_col] == doi] if doi_col in pred_df.columns else pd.DataFrame()

            gt_vals = gt_rows[field].tolist() if field in gt_rows.columns else []
            pred_vals = pred_rows[field].tolist() if (not pred_rows.empty and field in pred_rows.columns) else []

            p, r, f = score_field(pred_vals, gt_vals, field)
            precisions.append(p)
            recalls.append(r)
            f1s.append(f)

        results.append({
            "field": field,
            "precision": np.mean(precisions),
            "recall": np.mean(recalls),
            "f1": np.mean(f1s),
        })

    result_df = pd.DataFrame(results)
    macro_f1 = result_df["f1"].mean()
    print(result_df.to_string(index=False))
    print(f"\nMacro-F1: {macro_f1:.4f}  (baseline: 0.296)")
    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred", required=True, help="Predictions CSV")
    parser.add_argument("--gt", required=True, help="Ground truth parquet/csv")
    parser.add_argument("--domain", default="cocrystals")
    args = parser.parse_args()

    pred_df = pd.read_csv(args.pred)
    gt_df = pd.read_parquet(args.gt) if args.gt.endswith(".parquet") else pd.read_csv(args.gt)
    evaluate(pred_df, gt_df, args.domain)
