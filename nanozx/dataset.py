from pathlib import Path

import pandas as pd

from .schema import NUMERIC_FIELDS

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "nanozymes_train.parquet"
PARQUET_URL = (
    "https://huggingface.co/api/datasets/ai-chem/Nanozymes/parquet/default/train/0.parquet"
)


def _convert_comma(x):
    try:
        return str(x.replace(",", "."))
    except AttributeError:
        return str(x)


def _download():
    import requests

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(PARQUET_URL, allow_redirects=True, timeout=120)
    response.raise_for_status()
    CACHE.write_bytes(response.content)


def load_raw() -> pd.DataFrame:
    if not CACHE.exists():
        _download()
    return pd.read_parquet(CACHE)


def ground_truth() -> pd.DataFrame:
    df = load_raw()
    for col in NUMERIC_FIELDS:
        df[col] = df[col].apply(_convert_comma)
    df = df.fillna("NOT_DETECTED")
    df = df[df["access"] == 1].copy()
    df["pdf"] = df["pdf"].str.lower()
    return df
