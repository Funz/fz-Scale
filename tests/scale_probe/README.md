# SCALE probe

Small SCALE inputs, each testing one hypothesis the plugin relies on (exit
code, files produced, end banner, error messages, result table layout). Each
`cases/<case>.inp` states its hypothesis in its first comment lines.

```bash
SCALE_HOME=/path/to/SCALE-6.2.x SCALE_LABEL=scale624 JOBS=8 tests/scale_probe/run_probe.sh   # all cases
tests/scale_probe/run_probe.sh 'ok_*'                                                       # filter
SCALE_HOME=... python tests/scale_probe/make_fixtures.py tests/scale_probe/results-scale624-<date> scale6.2.4 [case ...]
```

`run_probe.sh` writes `results-<label>-<date>/<case>/` (input, `.out`, `.msg`,
scalerte stdout/stderr, `exit_code.txt`) and `summary.txt`. `make_fixtures.py`
copies the `.inp`/`.out`/`.msg` files to `tests/fixtures/<label>/`, replacing
user, host, home and SCALE paths. The results directories are not versioned.

## Findings (2026-10-15, SCALE 6.2.4, Linux x86_64, runtime dated Jun 9 2020)

| Id | Hypothesis | Result |
|---|---|---|
| H1 | Files: `scalerte <input>` writes `<basename>.out` and `<basename>.msg` next to the input, plus `.html` + `.htmd/` (KENO), `.sdf` (TSUNAMI); temporary directory `/tmp/scale.<user>.<pid>` removed at the end | Confirmed. `scalerte in out` does **not** name the output: the 2nd argument is taken as another input (`No input file associated with godiva.inp.out was found, skipping...`) — the former calculator scripts relied on it (`Scale-xsdrnpm` read a never-written `out.txt`). Option `-o` exists to rename. |
| H2 | Final results table, identical for csas5/csas6, multigroup/CE: `best estimate system k-eff`, lethargy, nu bar, mean free path, warnings/errors count, chi**2 normality, source convergence | Confirmed. Fortran layout `(8x,'***',t20,...)`, i.e. 8 spaces, `***`, 8 spaces. |
| H3 | Normal end: `SCALE is finished on <date>.` then `-------------------------- Summary --------------------------`, one `<sequence> finished. used N seconds.` line per sequence | Confirmed. `Congratulations!` is printed by KENO only (not by XSDRN, TSUNAMI-1D). |
| H4 | scalerte exit code reflects success | **Refuted**: exit code 0 in all cases, including input errors, unknown library/nuclide/sequence and failed adjoint KENO. Success must be read from the output. |
| H5 | Legacy library alias `ce_v7_endf` still accepted | Confirmed (alias of `ce_v7.0_endf`, FileNameAliases.txt). |
| H6 | Two sequences in one input | One `.out`, two final tables; the first one is reported by the models. |
| H7 | TSUNAMI-3D-K5 sensitivity table | `  u-235        total              8.4586E-01 +\- 3.4440E-02 (   4.07%)`; first table "Energy, Region and Mixture Integrated"; forward k-eff is the 1st `best estimate`, adjoint the 2nd. |
| H7b | A failed adjoint KENO is visible | `KENO failed to execute. error code 33536`, `SAMS failed to execute`, `.msg`: `***** error ***** keno message number k5-131 follows: / no fissions were generated` — **while** `Congratulations!` (forward KENO) and `tsunami-3d-k5 finished.` are printed. A "Congratulations" test (former scripts) accepts this failed run. |
| H8 | TSUNAMI-1D: `lambda` line, sensitivity table without standard deviation | Confirmed: `                   lambda    1.002794          production/absorption    2.340E+00`. |
| H9 | `=t-xsdrn` (XSDRNPM 1-D): `lambda` line | Confirmed (same layout as H8). `=csas1` with a `read model` block is a parse error (case dropped). The standalone `=xsdrn` sample of the SCALE distribution also printed it, but is not kept here (SCALE distribution content). |
| H10 | Input syntax error | `.out` and stdout: `line:10 column:26 - Parse Error: expected a parameters terminator, found 'notakeyword'`, `error:  Sequence: csas5 failed to initialize - see messages file for details.`, summary `csas5 failed.` |
| H11 | Unknown library | `.msg`: `error:  Sequence: csas5 failed to run with assertion: Failed to load Ampx Library: v7-999zz`; `.out`: `error:  Sequence: csas5 failed to execute - see messages file for details.` |
| H12 | Unknown nuclide | `.msg`: `error:  Sequence: csas5 failed to run with assertion: Nuclide unobtainium not found in the standard composition library` |
| H13 | KENO geometry error | `***** error ***** csas message number cs-091 follows:` (+ cs-092, cs-096) in `.msg`, `cs-55 *** errors were encountered in processing the keno data. execution is impossible.` — yet the summary says `csas5 finished.` |
| H14 | Unknown sequence (`=csas5-shift` on 6.2.4) | `.msg`: `sh: 1: csas5-shift: not found`; `.out`: `execution terminated due to errors. completion code 127`; summary `csas5-shift finished.` |
| H15 | Short run (20 generations) | Normal end, larger sigma; KENO source convergence tests `failed` also for the 150-generation reference runs: the indicator is strict. |
| H16 | Input echo | Comment and title lines are copied to the `.out` (6-space indent) and the title also in centered `***` boxes and page headers: an unanchored `best estimate system k-eff` regex returned the title value 9.9999. The models now read fixed columns of the SCALE layout (line by line, no regex), and the calculator uses anchored patterns. |
| H17 | Negative KENO-VI sphere radius | Accepted without error (k-eff 0.121 of a 1 cm sphere): SCALE does not validate such parameter values. |
| H18 | SIGTERM to the calculator shell (what fz does on timeout/interrupt) | scalerte, `scale` and `kenova` keep running (orphans). SIGTERM sent to scalerte stops the whole tree and removes its temporary directory: `Scale.sh` relays the signal. A killed run's `.out` has no `SCALE is finished on` line (fixture `killed_sigterm`, whose echoed comment mentions it). |
| H19 | `copy_graphic: not found` in `.msg` | Harmless (HTML report helpers in `cmds/`); `Scale.sh` adds `$SCALE_HOME/cmds` to PATH. |
| H20 | `=csas6 parm=check` (data check, no transport) | `This problem will not be run because parm=check was entered in the analytical sequence specification.`, end banner, no error: status `CHECK ONLY` (was reported `NORMAL END` before). |
| H21 | `nsk >= gen` | `***** error ***** csas message number cs-333 follows:` / `The number of generations skipped is not less than the number of generations to be run.`, `cs-55 ... execution is impossible`, `This problem will not be run because errors were detected in reading the input.` |
| H22 | Overlapping KENO-VI regions | `***** error ***** keno message number k6-106 follows:` / `posit error --- unit 1 has multiply defined space at` (13 error blocks in `.msg`), then `k6-117`, `KENO failed to execute. error code 33280`; summary `csas6 finished.` |
| H23 | `array N` record without `ara=N` | Crash during KENO-VI data processing: `.msg` ends with a glibc abort message (`double free or corruption (out)` for this input; the notice quotes `free(): invalid next size (fast)`), the `.out` has no end banner. Status `NO END BANNER: <abort message>`. |

## Confrontation with a SCALE usage notice (SCALE-skill v0.2, 2026-10-15)

The notice covers CSAS5/CSAS6 (not TSUNAMI, XSDRN, Shift). Its claims were
checked against the runs above (H20-H23 were written from its error table):

| Notice claim | Probe result |
|---|---|
| exit code 0 even when the input is rejected | Confirmed (H4). |
| SCALE "always ends with `Scale job ... is finished`" | **Inexact**: no such line in any run; `.msg` starts with `SCALE Job started on <date>`, `.out` ends with `    SCALE is finished on <date>.` — and a crashed or killed run has no end line at all (H18, H23). |
| success iff `best estimate system k-eff` and `number of error messages 0` in `.out` | **Insufficient**: the failed TSUNAMI-3D adjoint run (H7b) has both; sequences without KENO (XSDRN, TSUNAMI-1D) never have them. The plugin uses the error messages and the end banner instead. |
| extract k-eff with `grep "best estimate system k-eff"` (last occurrence) / `awk '{print $6, $10}'` | **Wrong for TSUNAMI-3D** (last occurrence = adjoint k-eff 0.994 ± 0.036 instead of forward 1.0008 ± 0.0013) and **fooled by the echoed title** (`trap_echo`: `k-eff -`, `+`, `9.9999 0.0001`). The plugin reads the fixed columns of the final results table, first occurrence. |
| failure markers: `error`, `Parse Error`, `will not be run`, `execution is impossible`, `terminated` | Confirmed as markers (H10-H14, H21); `will not be run` also appears for a successful `parm=check` (H20); the plain words `error`/`terminated` also match `number of error messages` and `execution terminated due to completion of the specified number of generations` of normal runs, hence the specific patterns used. |
| cs-333 (`nsk >= gen`), k6-106 (overlap), `free(): ...` crash, negative sphere radius accepted | Confirmed (H21, H22, H23 with another glibc message, H17). |
| run with `scalerte -m` | Not needed: without `-m` the same `.out`/`.msg` files are written (all runs above). |

Not covered: CSAS-Shift (SCALE >= 6.3 only), CE-TSUNAMI, MPI builds (`-N`),
Windows. SCALE 6.3 outputs may differ: rerun this probe before relying on the
plugin with another SCALE version.
