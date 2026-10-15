"""Plugin layout: files fz needs, executable calculator, examples."""
import json
import os

from conftest import CALCULATOR, FAKE_SCALERTE, ROOT

MODELS = ["Scale-keno", "Scale-shift", "Scale-tsunami", "Scale-xsdrnpm"]


def test_model_files():
    for m in MODELS:
        model = json.loads((ROOT / ".fz" / "models" / f"{m}.json").read_text())
        assert model["id"] == m and model["output"]


def test_calculator_files():
    calc = json.loads((ROOT / ".fz" / "calculators" / "localhost_Scale.json").read_text())
    assert calc["uri"] == "sh://"
    assert sorted(calc["models"]) == MODELS


def test_scripts_executable():
    for script in (CALCULATOR, FAKE_SCALERTE):
        assert script.exists()
        if os.name != "nt":
            assert os.access(script, os.X_OK), f"{script} is not executable"


def test_examples():
    for m in MODELS:
        assert (ROOT / "examples" / m / "godiva.inp").exists()


def test_docs():
    for f in ("README.md", "LICENSE", "tests/fixtures/README.md", "tests/scale_probe/README.md"):
        assert (ROOT / f).exists(), f
