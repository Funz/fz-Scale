#!/usr/bin/env python3
"""Generate the fz model files .fz/models/Scale-*.json.

The outputs are python:// expressions, evaluated by fz itself (no shell, same
behavior on Linux, macOS and Windows). They read the SCALE output line by line
with fz's lines() helper (which accepts LF and CRLF line endings) and use only
str methods (startswith, split, strip): no regular expressions. They are long
one-line expressions: writing them here, as plain Python strings, avoids JSON
escaping mistakes. Edit this file, run it from the repository root, and commit
both:

    python tools/build_models.py

tests/test_models_sync.py fails if the JSON files are not up to date.

Constraints:
- fz evaluates an expression with eval(expr, globals, helpers): the helpers
  (lines, base_dir, ...) are locals of eval, so on Python < 3.12 they are NOT
  visible inside a lambda, generator or comprehension body. Each expression is
  therefore a lambda called with the lines of the file as argument; inside it,
  only its parameters and builtins are used.
- The input (comment and title lines) is copied to the .out file: every test
  is tied to the SCALE layout (fixed columns, 6-space indented echo, comment
  lines starting with "'"), so that echoed text never matches
  (tests/fixtures/scale6.2.4/trap_echo).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / ".fz" / "models"

#: lines of the main SCALE output file (scalerte names it <input basename>.out)
OUT_LINES = "lines(next(base_dir.glob('*.out')))"

# ---------------------------------------------------------------- run status
#: First error message, in priority order (t: .out lines, m: .msg lines):
#: - .msg "error:  Sequence: csas5 failed to run with assertion: ..."
#: - "***** error ***** keno message number k5-131 follows:" + the next line
#:   (.msg, else .out); an echoed comment starts with "'" and does not match
#: - "line:10 column:26 - Parse Error: ..." (.out, column 1)
#: - "KENO failed to execute. error code 33536" (.out, column 1)
#: - "    execution terminated due to errors. completion code 127" (.out)
#: - "error: ..." / "***Error: ..." (.out, column 1)
#: else "CHECK ONLY" for a '=csas6 parm=check' run (data checked, no transport:
#: "This problem will not be run because parm=check was entered ..."),
#: else "NORMAL END" if "    SCALE is finished on <date>." is present,
#: else "NO END BANNER", followed by the crash message of the .msg file if any
#: (e.g. "double free or corruption (out)", tests/fixtures/scale6.2.4/err_array_undefined).
CRASH = ('free(): ', 'double free', 'malloc(): ', 'munmap_chunk', 'corrupted ', 'Segmentation fault',
         'Program received signal', 'Fortran runtime error', 'Backtrace')
STATUS = """(lambda outs, lines: 'NO OUTPUT' if not outs else (lambda t, m: next(
    ('ERROR: ' + ' '.join(e.split()) for e in [
        next((l[7:] for l in m if l.startswith('error: ')), None),
        next((l.split('*****', 2)[2] + ' ' + n for l, n in zip(m, m[1:] + ['']) if l.lstrip().startswith('***** error ***** ')), None),
        next((l.split('*****', 2)[2] + ' ' + n for l, n in zip(t, t[1:] + ['']) if l.lstrip().startswith('***** error ***** ')), None),
        next((l for l in t if l.startswith('line:') and ' - Parse Error:' in l), None),
        next((l for l in t if l[:1].strip() and ' failed to execute. error code ' in l), None),
        next((l.split('. cpu time')[0] for l in t if l.lstrip().startswith(('terminated due to errors. completion code', 'execution terminated due to errors. completion code'))), None),
        next((l.split(':', 1)[1] for l in t if l.startswith(('error: ', '***Error: '))), None),
    ] if e), None)
    or ('CHECK ONLY' if any(l.startswith('This problem will not be run because parm=check') for l in t)
        else 'NORMAL END' if any(l.lstrip().startswith('SCALE is finished on ') for l in t)
        else 'NO END BANNER' + next((': ' + l.strip() for l in m if l.startswith(%r)), '')))
  (lines(outs[0]), lines(outs[0].with_suffix('.msg')) if outs[0].with_suffix('.msg').exists() else []))
(sorted(base_dir.glob('*.out')), lines)""" % (CRASH,)

#: "*****                      version:  6.2.4 (602004)          *****"
VERSION = (
    "(lambda L: next((t[2] for t in (l.split() for l in L if l.startswith('*****')) "
    "if len(t) > 3 and t[1] == 'version:' and t[3].startswith('(')), None))(" + OUT_LINES + ")"
)

# ------------------------------------------------------- KENO final results
#: start of a KENO final results table line: Fortran format (8x,'***',t20,...)
#: (strings of libsmclib), i.e. 8 spaces, '***', 8 spaces. The run title is
#: also printed in '***' boxes, but centered: the fixed column plus 2 spaces
#: (at least) between the label and the value tell them apart.
ROW = " " * 8 + "***" + " " * 8


def fields(label):
    """generator of the split remainders of the final results lines `label`"""
    p = ROW + label
    return f"(l[{len(p)}:].split() for l in L if l.startswith({p!r}) and l[{len(p)}:{len(p) + 2}] == '  ')"


def value(label, index, n=0, cast="float"):
    """n-th (0-based) occurrence of the `index`-th field after `label`, or None.
    "best estimate system k-eff    1.0032 + or - 0.0019     ***"
    -> fields ['1.0032', '+', 'or', '-', '0.0019', '***']: value 0, sigma 4"""
    return (
        f"python://(lambda L: ([{cast}(t[{index}]) for t in {fields(label)}][{n}:] or [None])[0])"
        f"({OUT_LINES})"
    )


KEFF = "best estimate system k-eff"
LETHARGY = "Energy of average lethargy of Fission (eV)"
NUBAR = "system nu bar"
MFP = "system mean free path (cm)"

#: "k-effective satisfies the chi**2 test for normality at the 95 % level" /
#: "k-effective fails ... at the 95 % level, but satisfies it at the 99 % level" /
#: "k-effective fails ... at the 99 % level" (strings of libsmclib)
NORMALITY = (
    "python://(lambda L: next(('pass_95' if s.startswith('satisfies') else 'pass_99' if 'but satisfies' in s else 'fail_99' "
    f"for s in (l[{len(ROW + 'k-effective ')}:] for l in L if l.startswith({ROW + 'k-effective '!r}))), None))"
    f"({OUT_LINES})"
)

#: "source convergence tests passed|failed|not valid"
CONVERGENCE = (
    "python://(lambda L: next((l[{0}:].split('***')[0].strip() for l in L if l.startswith({1!r})), None))({2})"
).format(len(ROW + "source convergence tests "), ROW + "source convergence tests ", OUT_LINES)

COMMON = {
    "scale_status": "python://" + " ".join(s.strip() for s in STATUS.splitlines()),
    "scale_version": "python://" + VERSION,
}

KENO = {
    "mean_keff": value(KEFF, 0),
    "sigma_keff": value(KEFF, 4),
    "mean_E_lethargy": value(LETHARGY, 0),
    "sigma_E_lethargy": value(LETHARGY, 4),
    "mean_nubar": value(NUBAR, 0),
    "sigma_nubar": value(NUBAR, 4),
    "mean_free_path": value(MFP, 0),
    "sigma_free_path": value(MFP, 4),
    "n_warnings": value("number of warning messages", 0, cast="int"),
    "n_errors": value("number of error messages", 0, cast="int"),
    "keff_normality": NORMALITY,
    "source_convergence": CONVERGENCE,
}

#: XSDRNPM eigenvalue: "                    lambda    0.996375          production/absorption    2.340E+00"
#: (20-space indent; an echoed input line has a 6-space indent)
LAMBDA = (
    "python://(lambda L: next((float(t[1]) for t in (l.split() for l in L if not l[:12].strip()) "
    "if len(t) > 2 and t[0] == 'lambda' and t[2] == 'production/absorption'), None))"
    f"({OUT_LINES})"
)

# ------------------------------------------------------- TSUNAMI sensitivities
#: First table of the output (energy-, region- and mixture-integrated):
#:     Energy, Region and Mixture Integrated Sensitivity Coefficients for this Problem
#:  -------------------------------------------------------------------------------------
#:
#:     Nuclide       Reaction       Sensitivity      Std. Dev. % Std. Dev.
#:  ------------- ---------------   -----------     ---------- -----------
#:   u-235        total              8.4586E-01 +\- 3.4440E-02 (   4.07%)     <- TSUNAMI-3D
#:   u-235        total              8.4586E-01                               <- TSUNAMI-1D
#: rows start 5 lines after the title and end at the first blank line.
SENS_TITLE = "Energy, Region and Mixture Integrated Sensitivity Coefficients for this Problem"


def sens(sigma):
    """dict {'<nuclide>_<reaction>': value}, flattened by fz into
    <output name>_<key> columns; nuclide without '-', reaction without ','
    and with "'" -> 'p': u-235 total -> u235_total, u-238 n,n' -> u238_nnp."""
    pick = "float(t[4])" if sigma else "float(t[2])"
    keep = "len(t) > 4 and t[3] in ('+\\\\-', '+/-')" if sigma else "len(t) > 2"
    return (
        "python://(lambda L: (lambda i: {} if i is None else dict("
        "(t[0].replace('-', '') + '_' + t[1].replace(',', '').replace(\"'\", 'p'), " + pick + ") "
        "for t in (l.split() for l in L[i + 5:next((k for k in range(i + 5, len(L)) if not L[k].strip()), len(L))]) "
        "if " + keep + "))"
        f"(next((k for k, l in enumerate(L) if l.strip() == {SENS_TITLE!r}), None)))"
        f"({OUT_LINES})"
    )


TSUNAMI = {
    **KENO,
    "mean_keff_adjoint": value(KEFF, 0, n=1),
    "sigma_keff_adjoint": value(KEFF, 4, n=1),
    "lambda": LAMBDA,
    "mean_sens": sens(False),
    "sigma_sens": sens(True),
}

XSDRN = {"lambda": LAMBDA}

HEADER = {
    "varprefix": "&",
    "formulaprefix": "@",
    "var_delim": "()",
    "formula_delim": "{}",
    "commentline": "'",
}

MODEL_DEFS = {
    "Scale-keno": {**COMMON, **KENO},
    "Scale-shift": {**COMMON, **KENO},
    "Scale-tsunami": {**COMMON, **TSUNAMI},
    "Scale-xsdrnpm": {**COMMON, **XSDRN},
}


def models():
    return {mid: {"id": mid, **HEADER, "output": out} for mid, out in MODEL_DEFS.items()}


def render(model):
    return json.dumps(model, indent=4) + "\n"


if __name__ == "__main__":
    for mid, model in models().items():
        (MODELS / f"{mid}.json").write_text(render(model))
        print(f"wrote .fz/models/{mid}.json ({len(model['output'])} outputs)")
