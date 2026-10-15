"""fz end to end (fzi, fzc, fzr) with the fake scalerte replaying real outputs."""
import os
import shutil

import pytest

fz = pytest.importorskip("fz")

from conftest import FAKE_SCALERTE, ROOT, SCALE624, needs_bash  # noqa: E402

EXAMPLES = ROOT / "examples"


@pytest.mark.parametrize("model", ["Scale-keno", "Scale-shift", "Scale-tsunami", "Scale-xsdrnpm"])
def test_examples_variables(model):
    variables = fz.fzi(str(EXAMPLES / model / "godiva.inp"), model)
    assert "r" in variables


def test_fzc_variables_formulas_and_format(tmp_path):
    inp = tmp_path / "t.inp"
    inp.write_text(
        "'test\n"
        "' mass = @{round(4/3*3.14159265*r**3*18.742/1000, 3)} kg\n"
        " sphere 10 &(r)\n"
        " h-1 3 0 @{6.686E-2*&(dens)|0.00000E00} 300 end\n"
    )
    assert set(fz.fzi(str(inp), "Scale-keno")) >= {"r", "dens"}
    fz.fzc(str(inp), {"r": 8.741, "dens": 0.01}, "Scale-keno", output_dir=str(tmp_path / "out"))
    text = next((tmp_path / "out").rglob("t.inp")).read_text()
    assert " sphere 10 8.741\n" in text
    assert "mass = 52.431 kg" in text
    assert " h-1 3 0 6.68600E-04 300 end" in text
    assert "&(" not in text and "@{" not in text


@needs_bash
def test_fzr_fake_scale(tmp_path, monkeypatch):
    monkeypatch.setenv("SCALE_CMD", str(FAKE_SCALERTE))
    monkeypatch.setenv("FAKE_SCALE_CASE", str(SCALE624 / "ok_csas5_mg"))
    for k in ("SCALE_HOME", "SCALE_THREADS", "SCALE_MPI", "SCALE_OPTS", "SCALE_TMPDIR"):
        monkeypatch.delenv(k, raising=False)
    res = fz.fzr(str(EXAMPLES / "Scale-keno" / "godiva.inp"), {"r": [8.5, 9.0]}, "Scale-keno",
                 calculators="localhost_Scale", results_dir=str(tmp_path / "res"))
    assert list(res["status"]) == ["done", "done"]
    assert list(res["scale_status"]) == ["NORMAL END"] * 2
    assert list(res["mean_keff"]) == [1.0032] * 2


@needs_bash
def test_fzr_fake_scale_error(tmp_path, monkeypatch):
    monkeypatch.setenv("SCALE_CMD", str(FAKE_SCALERTE))
    monkeypatch.setenv("FAKE_SCALE_CASE", str(SCALE624 / "err_library"))
    res = fz.fzr(str(EXAMPLES / "Scale-keno" / "godiva.inp"), {"r": 8.5}, "Scale-keno",
                 calculators="localhost_Scale", results_dir=str(tmp_path / "res"))
    assert res["status"].iloc[0] == "failed"
    assert res["scale_status"].iloc[0].startswith("ERROR: Sequence: csas5 failed to run with assertion")


@needs_bash
def test_fzr_without_calculators_argument(tmp_path, monkeypatch):
    """the calculator is found in .fz/calculators for the model"""
    monkeypatch.setenv("SCALE_CMD", str(FAKE_SCALERTE))
    monkeypatch.setenv("FAKE_SCALE_CASE", str(SCALE624 / "ok_csas5_mg"))
    res = fz.fzr(str(EXAMPLES / "Scale-keno" / "godiva.inp"), {"r": 8.7}, "Scale-keno",
                 results_dir=str(tmp_path / "res"))
    assert res["status"].iloc[0] == "done"
    assert res["mean_keff"].iloc[0] == 1.0032
