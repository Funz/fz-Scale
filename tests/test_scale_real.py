"""fz + real SCALE (skipped when no scalerte is found: SCALE_HOME, PATH, ~/opt/SCALE*).

Runs the examples with small parameter lists; about one minute on 4 cores.
"""
import os

import pytest

fz = pytest.importorskip("fz")

from conftest import ROOT, needs_bash, real_scalerte  # noqa: E402

SCALERTE = real_scalerte()
pytestmark = [needs_bash, pytest.mark.skipif(SCALERTE is None, reason="SCALE (scalerte) not found")]


@pytest.fixture(autouse=True)
def _scale(monkeypatch):
    monkeypatch.setenv("SCALE_CMD", SCALERTE)


def run(model, values, tmp_path):
    return fz.fzr(str(ROOT / "examples" / model / "godiva.inp"), {"r": values}, model,
                  calculators=["localhost_Scale"] * 4, results_dir=str(tmp_path / "res"))


def test_keno_godiva(tmp_path):
    res = run("Scale-keno", [8.5, 8.741, 9.0], tmp_path).sort_values("r")
    assert list(res["status"]) == ["done"] * 3, res.get("error")
    assert list(res["scale_status"]) == ["NORMAL END"] * 3
    k = list(res["mean_keff"])
    assert k[0] < k[1] < k[2]
    assert abs(k[1] - 1.0) < 0.01  # critical radius, ce_v7.1
    assert all(0 < s < 0.005 for s in res["sigma_keff"])


def test_xsdrnpm_godiva(tmp_path):
    res = run("Scale-xsdrnpm", [8.5, 8.741, 9.0], tmp_path).sort_values("r")
    assert list(res["status"]) == ["done"] * 3, res.get("error")
    lam = list(res["lambda"])
    assert lam[0] < lam[1] < lam[2] and abs(lam[1] - 1.0) < 0.01


def test_tsunami_godiva(tmp_path):
    res = run("Scale-tsunami", [8.741], tmp_path)
    row = res.iloc[0]
    assert row["status"] == "done", row.get("error")
    assert 0.7 < row["mean_sens_u235_total"] < 1.0
    assert row["sigma_sens_u235_total"] > 0


def test_error_reported(tmp_path):
    """unknown cross-section library: scalerte exits 0, the case must fail"""
    inp = tmp_path / "godiva.inp"
    inp.write_text((ROOT / "examples" / "Scale-keno" / "godiva.inp").read_text().replace("ce_v7.1", "&(lib)"))
    res = fz.fzr(str(inp), {"lib": "v7-999zz"}, "Scale-keno", calculators="localhost_Scale",
                 results_dir=str(tmp_path / "res"))
    row = res.iloc[0]
    assert row["status"] == "failed"
    assert row["scale_status"].endswith("Failed to load Ampx Library: v7-999zz")
