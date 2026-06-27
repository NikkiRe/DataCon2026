"""Tests for verify guard."""

from chemx_extract.config import NOT_DETECTED
from chemx_extract.merge.verify_guard import guard_verify_output, should_skip_verify


def _fur_caf_row(photostability: str = "increases") -> dict:
    return {
        "name_cocrystal": "FUR-CAF",
        "ratio_cocrystal": "1 : 1",
        "name_drug": "Furosemide",
        "SMILES_drug": NOT_DETECTED,
        "name_coformer": "caffeine",
        "SMILES_coformer": NOT_DETECTED,
        "photostability_change": photostability,
    }


def test_should_skip_verify_when_table_and_text_agree():
    table = [_fur_caf_row()]
    text = [_fur_caf_row()]
    assert should_skip_verify(table, table + text, "cocrystals") is True


def test_should_not_skip_when_photostability_disagrees():
    table = [_fur_caf_row("increases")]
    text = [_fur_caf_row("decreases")]
    assert should_skip_verify(table, table + text, "cocrystals") is False


def test_guard_restores_table_photostability():
    table = [_fur_caf_row("increases")]
    before = table + [_fur_caf_row("increases")]
    verified = [_fur_caf_row("does not change")]
    out, notes = guard_verify_output(verified, table, before, "cocrystals")
    assert out[0]["photostability_change"] == "increases"
    assert notes
