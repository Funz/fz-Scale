"""Calculator script .fz/calculators/Scale.sh, with a fake scalerte that
replays the real SCALE 6.2.4 outputs of tests/fixtures/scale6.2.4."""
import os
import shutil
import signal
import subprocess
import time

import pytest

from conftest import CALCULATOR, FAKE_SCALERTE, SCALE624, needs_bash

pytestmark = needs_bash

GODIVA = SCALE624 / "ok_csas5_mg" / "ok_csas5_mg.inp"


def run(workdir, *args, case=None, env=None, **kw):
    e = {k: v for k, v in os.environ.items() if not k.startswith("SCALE_")}
    e["SCALE_CMD"] = str(FAKE_SCALERTE)
    if case:
        e["FAKE_SCALE_CASE"] = str(SCALE624 / case)
    e.update(env or {})
    return subprocess.run(["bash", str(CALCULATOR), *args], cwd=workdir, env=e,
                          capture_output=True, text=True, **kw)


def setup_case(tmp_path, name="godiva.inp"):
    shutil.copy(GODIVA, tmp_path / name)
    return tmp_path


#: fixture -> expected exit code (0 normal end, 6 SCALE errors, 7 no end banner)
EXIT_CODES = {
    "ok_csas5_mg": 0, "ok_csas6_ce": 0, "ok_csas5_ce_legacy_alias": 0, "ok_two_sequences": 0,
    "ok_tsunami3d_k5": 0, "ok_tsunami1d": 0, "ok_t_xsdrn": 0,
    "var_short_run": 0, "trap_echo": 0, "var_negative_radius": 0,
    "err_geometry": 6, "err_library": 6, "err_nuclide": 6, "err_syntax": 6,
    "err_unknown_sequence": 6, "err_tsunami3d_adjoint": 6,
    "killed_sigterm": 7, "err_array_undefined": 7,
    "var_parm_check": 0, "err_nsk_ge_gen": 6, "err_overlap": 6,
}


def test_all_fixtures_have_an_expected_exit_code():
    assert sorted(p.name for p in SCALE624.iterdir() if p.is_dir()) == sorted(EXIT_CODES)


@pytest.mark.parametrize("case", sorted(EXIT_CODES))
def test_exit_code(case, tmp_path):
    r = run(setup_case(tmp_path), "godiva.inp", case=case)
    assert r.returncode == EXIT_CODES[case], r.stderr
    assert (tmp_path / "godiva.out").exists()
    if EXIT_CODES[case]:
        assert r.stderr.strip()


@pytest.mark.parametrize("case", sorted(EXIT_CODES))
def test_exit_code_agrees_with_scale_status(case, tmp_path):
    """the script and the models' scale_status output apply the same rules"""
    fz = pytest.importorskip("fz")
    r = run(setup_case(tmp_path), "godiva.inp", case=case)
    status = fz.fzo(str(tmp_path), "Scale-keno").iloc[0]["scale_status"]
    assert (r.returncode == 0) == (status in ("NORMAL END", "CHECK ONLY")), (status, r.stderr)


def test_error_message_on_stderr(tmp_path):
    r = run(setup_case(tmp_path), "godiva.inp", case="err_library")
    assert "Failed to load Ampx Library: v7-999zz" in r.stderr
    r = run(setup_case(tmp_path), "godiva.inp", case="err_tsunami3d_adjoint")
    assert "k5-131" in r.stderr and "no fissions were generated" in r.stderr
    r = run(setup_case(tmp_path), "godiva.inp", case="err_array_undefined")
    assert "double free or corruption (out)" in r.stderr


def test_input_selection(tmp_path):
    """*.inp first, whatever the argument order; fz files are never inputs"""
    setup_case(tmp_path)
    for f in ("aaa.txt", "out.txt", "data.dat"):
        (tmp_path / f).write_text("x")
    r = run(tmp_path, "aaa.txt", "data.dat", "godiva.inp", case="ok_csas5_mg")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "fake_scalerte_args.txt").read_text().split() == ["godiva.inp"]


def test_input_without_inp_extension(tmp_path):
    shutil.copy(GODIVA, tmp_path / "godiva")
    (tmp_path / "out.txt").write_text("")
    r = run(tmp_path, "out.txt", "godiva", case="ok_csas5_mg")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "godiva.out").exists()


def test_directory_argument(tmp_path):
    setup_case(tmp_path)
    r = run(tmp_path.parent, str(tmp_path), case="ok_csas5_mg")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "godiva.out").exists()


def test_usage_and_no_input(tmp_path):
    assert run(tmp_path).returncode == 2
    (tmp_path / "out.txt").write_text("")
    assert run(tmp_path, "out.txt").returncode == 1


def test_scalerte_not_found(tmp_path):
    setup_case(tmp_path)
    r = run(tmp_path, "godiva.inp", env={"SCALE_CMD": str(tmp_path / "nope")})
    assert r.returncode == 4 and "scalerte not found" in r.stderr
    e = {"SCALE_HOME": str(tmp_path / "no-scale"), "PATH": "/usr/bin:/bin"}
    r = subprocess.run(["bash", str(CALCULATOR), "godiva.inp"], cwd=tmp_path, capture_output=True, text=True,
                       env={**{k: v for k, v in os.environ.items() if not k.startswith("SCALE_")}, **e})
    assert r.returncode == 4


def test_scale_home(tmp_path):
    home = tmp_path / "scale"
    (home / "bin").mkdir(parents=True)
    shutil.copy(FAKE_SCALERTE, home / "bin" / "scalerte")
    work = tmp_path / "work"
    work.mkdir()
    setup_case(work)
    e = {k: v for k, v in os.environ.items() if not k.startswith("SCALE_")}
    e.update(SCALE_HOME=str(home), FAKE_SCALE_CASE=str(SCALE624 / "ok_csas5_mg"))
    r = subprocess.run(["bash", str(CALCULATOR), "godiva.inp"], cwd=work, env=e, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_no_out_produced(tmp_path):
    r = run(setup_case(tmp_path), "godiva.inp")  # fake scalerte without a case writes nothing
    assert r.returncode == 5


def test_previous_output_removed(tmp_path):
    """a stale <input>.out from a previous run must not be parsed"""
    setup_case(tmp_path)
    shutil.copy(SCALE624 / "ok_csas5_mg" / "ok_csas5_mg.out", tmp_path / "godiva.out")
    assert run(tmp_path, "godiva.inp").returncode == 5
    assert not (tmp_path / "godiva.out").exists()


def test_options(tmp_path):
    setup_case(tmp_path)
    r = run(tmp_path, "godiva.inp", case="ok_csas5_mg",
            env={"SCALE_THREADS": "4", "SCALE_MPI": "2", "SCALE_TMPDIR": "/scratch/x", "SCALE_OPTS": "-r -m"})
    assert r.returncode == 0, r.stderr
    args = (tmp_path / "fake_scalerte_args.txt").read_text().split()
    assert args == ["-I", "4", "-N", "2", "-T", "/scratch/x", "-r", "-m", "godiva.inp"]


def test_sigterm_is_relayed_to_scalerte(tmp_path):
    """fz stops a run by SIGTERM to the shell: scalerte must get it too"""
    setup_case(tmp_path)
    e = {k: v for k, v in os.environ.items() if not k.startswith("SCALE_")}
    e.update(SCALE_CMD=str(FAKE_SCALERTE), FAKE_SCALE_SLEEP="30")
    p = subprocess.Popen(["bash", str(CALCULATOR), "godiva.inp"], cwd=tmp_path, env=e)
    for _ in range(50):
        if (tmp_path / "fake_scalerte_args.txt").exists():
            break
        time.sleep(0.1)
    time.sleep(0.3)
    p.send_signal(signal.SIGTERM)
    assert p.wait(timeout=10) == 143
    for _ in range(50):
        if (tmp_path / "fake_scalerte_terminated.txt").exists():
            break
        time.sleep(0.1)
    assert (tmp_path / "fake_scalerte_terminated.txt").exists()
