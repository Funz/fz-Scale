import os
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
SCALE624 = FIXTURES / "scale6.2.4"
FAKE_SCALERTE = ROOT / "tests" / "fake" / "scalerte"
CALCULATOR = ROOT / ".fz" / "calculators" / "Scale.sh"

needs_bash = pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="the calculator script needs bash (not run on Windows)",
)


@pytest.fixture(autouse=True)
def _repo_root(monkeypatch):
    """fz looks for models and calculators in ./.fz: run from the repository root."""
    monkeypatch.chdir(ROOT)


def real_scalerte():
    """Path of a real scalerte, or None (SCALE_HOME, PATH, ~/opt/SCALE*)."""
    home = os.environ.get("SCALE_HOME")
    candidates = [Path(home) / "bin" / "scalerte"] if home else []
    which = shutil.which("scalerte")
    if which:
        candidates.append(Path(which))
    candidates += sorted(Path.home().glob("opt/SCALE*/bin/scalerte"), reverse=True)
    return next((str(c) for c in candidates if c.is_file() and os.access(c, os.X_OK)), None)
