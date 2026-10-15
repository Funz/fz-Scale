"""Output extraction (model python:// expressions) on real SCALE outputs.

tests/fixtures/scale6.2.4/<case>/ are real SCALE 6.2.4 outputs of the probe
cases tests/scale_probe/cases/<case>.inp (anonymized); tests/fixtures/Scale-keno
is a KENO-V.a excerpt from idaholab/raven (see tests/fixtures/README.md).
"""
import math
import shutil

import pytest

fz = pytest.importorskip("fz")

from conftest import FIXTURES, SCALE624  # noqa: E402

NAN = float("nan")


@pytest.fixture(params=["lf", "crlf"])
def eol(request):
    """line endings of the parsed outputs: as produced (LF), or converted to
    CRLF (Windows), which must give the same results"""
    return request.param


def parse(case_dir, model, tmp_path, eol="lf"):
    """fzo on a copy of a fixture directory (fzo may write next to the outputs)."""
    work = tmp_path / case_dir.name
    shutil.copytree(case_dir, work)
    if eol == "crlf":
        for f in list(work.glob("*.out")) + list(work.glob("*.msg")):
            f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    return fz.fzo(str(work), model).iloc[0].to_dict()


def check(row, expected):
    for key, value in expected.items():
        assert key in row, f"missing output {key!r}"
        got = row[key]
        if value is None:
            assert got is None or (isinstance(got, float) and math.isnan(got)), f"{key}: expected None, got {got!r}"
        elif isinstance(value, float):
            assert isinstance(got, (int, float)) and math.isclose(got, value, rel_tol=1e-9), f"{key}: expected {value}, got {got!r}"
        else:
            assert got == value, f"{key}: expected {value!r}, got {got!r}"


GODIVA_MG = {
    "scale_status": "NORMAL END",
    "scale_version": "6.2.4",
    "mean_keff": 1.0032,
    "sigma_keff": 0.0019,
    "mean_E_lethargy": 822011.0,
    "sigma_E_lethargy": 2547.37,
    "mean_nubar": 2.5992,
    "sigma_nubar": 0.000516435,
    "mean_free_path": 2.56119,
    "sigma_free_path": 0.00113668,
    "n_warnings": 3,
    "n_errors": 0,
    "keff_normality": "pass_95",
    "source_convergence": "failed",
}

KENO_CASES = {
    "ok_csas5_mg": GODIVA_MG,
    "ok_csas6_ce": {"scale_status": "NORMAL END", "mean_keff": 1.0004, "sigma_keff": 0.0024,
                    "mean_E_lethargy": 819777.0, "n_warnings": 4},
    "ok_csas5_ce_legacy_alias": {"scale_status": "NORMAL END", "mean_keff": 1.0012, "sigma_keff": 0.0022},
    "var_short_run": {"scale_status": "NORMAL END", "mean_keff": 0.995, "sigma_keff": 0.017},
    # KENO-VI accepts a negative sphere radius (|r| is used): not an error for SCALE
    "var_negative_radius": {"scale_status": "NORMAL END", "mean_keff": 0.12116, "n_warnings": 14},
    # two sequences in one input: the first one is reported
    "ok_two_sequences": {"scale_status": "NORMAL END", "mean_keff": 0.9854, "sigma_keff": 0.0025},
    # input comments/title imitate SCALE messages and results: must be ignored
    "trap_echo": {"scale_status": "NORMAL END", "mean_keff": 1.0034, "sigma_keff": 0.0025},
    "err_geometry": {
        "scale_status": "ERROR: csas message number cs-091 follows: unit 1 contains the following geometry inconsistencies:",
        "mean_keff": None,
    },
    "err_library": {
        "scale_status": "ERROR: Sequence: csas5 failed to run with assertion: Failed to load Ampx Library: v7-999zz",
        "mean_keff": None,
    },
    "err_nuclide": {
        "scale_status": "ERROR: Sequence: csas5 failed to run with assertion: "
                        "Nuclide unobtainium not found in the standard composition library",
    },
    "err_syntax": {
        "scale_status": "ERROR: line:10 column:26 - Parse Error: expected a parameters terminator, found 'notakeyword'",
        "scale_version": None,
    },
    "err_unknown_sequence": {"scale_status": "ERROR: execution terminated due to errors. completion code 127"},
    # forward KENO succeeded ('Congratulations!') but the adjoint KENO failed
    "err_tsunami3d_adjoint": {
        "scale_status": "ERROR: keno message number k5-131 follows: no fissions were generated",
        "mean_keff": 1.0008,
    },
    # SIGTERM during the KENO generations: no end banner (the echoed comment
    # mentions 'SCALE is finished')
    "killed_sigterm": {"scale_status": "NO END BANNER", "mean_keff": None},
    # cases from the SCALE-skill v0.2 notice
    "var_parm_check": {"scale_status": "CHECK ONLY", "mean_keff": None},
    "err_nsk_ge_gen": {
        "scale_status": "ERROR: csas message number cs-333 follows: "
                        "The number of generations skipped is not less than the number of generations to be run.",
    },
    "err_overlap": {
        "scale_status": "ERROR: keno message number k6-106 follows: posit error --- unit 1 has multiply defined space at",
        "mean_keff": None,
    },
    # crash of the KENO-VI data processing (glibc abort), no end banner
    "err_array_undefined": {"scale_status": "NO END BANNER: double free or corruption (out)", "mean_keff": None},
}


@pytest.mark.parametrize("case", sorted(KENO_CASES))
def test_keno(case, tmp_path, eol):
    check(parse(SCALE624 / case, "Scale-keno", tmp_path, eol), KENO_CASES[case])


def test_keno_raven_excerpt(tmp_path, eol):
    """Older KENO-V.a output (other SCALE version) keeps parsing."""
    row = parse(FIXTURES / "Scale-keno", "Scale-keno", tmp_path, eol)
    check(row, {
        "scale_status": "NORMAL END",
        "mean_keff": 0.952, "sigma_keff": 0.020,
        "mean_E_lethargy": 0.280003, "sigma_E_lethargy": 0.00358169,
        "mean_free_path": 1.23628, "sigma_free_path": 0.00823879,
        "mean_nubar": 2.44645, "sigma_nubar": 0.000111459,
        "n_warnings": 3, "n_errors": 0, "keff_normality": "pass_95",
    })


def test_no_output(tmp_path):
    (tmp_path / "case").mkdir()
    (tmp_path / "case" / "godiva.inp").write_text("=csas5\n")
    row = fz.fzo(str(tmp_path / "case"), "Scale-keno").iloc[0].to_dict()
    assert row["scale_status"] == "NO OUTPUT"


def test_tsunami3d(tmp_path, eol):
    row = parse(SCALE624 / "ok_tsunami3d_k5", "Scale-tsunami", tmp_path, eol)
    check(row, {
        "scale_status": "NORMAL END",
        "mean_keff": 1.0008, "sigma_keff": 0.0013,
        "mean_keff_adjoint": 0.994, "sigma_keff_adjoint": 0.036,
        "mean_sens_u235_total": 0.84586, "sigma_sens_u235_total": 0.03444,
        "mean_sens_u235_nnp": 0.094985, "sigma_sens_u235_nnp": 0.016345,
        "mean_sens_u238_capture": -0.0013317, "sigma_sens_u238_capture": 4.7146e-05,
        "mean_sens_u234_chi": -1.2612e-09,
        "lambda": None,
    })
    # 3 nuclides x 10 reactions, from the first (energy-, region-, mixture-integrated) table only
    assert len([k for k in row if k.startswith("mean_sens_")]) == 30
    assert len([k for k in row if k.startswith("sigma_sens_")]) == 30


def test_tsunami1d(tmp_path, eol):
    row = parse(SCALE624 / "ok_tsunami1d", "Scale-tsunami", tmp_path, eol)
    check(row, {
        "scale_status": "NORMAL END",
        "lambda": 1.002794,
        "mean_keff": None,
        "mean_sens_u235_total": 0.80217,
        "mean_sens_u238_nnp": 0.0056351,
    })
    # deterministic: no standard deviations
    assert not [k for k in row if k.startswith("sigma_sens_") and row[k] == row[k] and row[k] is not None]


@pytest.mark.parametrize("case,value", [("ok_t_xsdrn", 0.996375)])
def test_xsdrn(case, value, tmp_path, eol):
    check(parse(SCALE624 / case, "Scale-xsdrnpm", tmp_path, eol), {"scale_status": "NORMAL END", "lambda": value})


def test_xsdrn_trap_echo(tmp_path, eol):
    """the 'lambda ... production/absorption' line in a comment is not taken"""
    check(parse(SCALE624 / "trap_echo", "Scale-xsdrnpm", tmp_path, eol), {"lambda": None})


def test_shift_same_extraction_as_keno(tmp_path, eol):
    """Scale-shift uses the KENO final results table expressions: NOT validated
    on a CSAS-Shift output (Shift is not part of SCALE 6.2)."""
    check(parse(SCALE624 / "ok_csas5_mg", "Scale-shift", tmp_path, eol), GODIVA_MG)
