# fz-Scale

A [Funz/fz](https://github.com/Funz/fz) plugin to run parametric studies with
[SCALE](https://www.ornl.gov/scale) (ORNL): substitute variables in a SCALE
input, run `scalerte` for each case (locally, over SSH or SLURM), and collect
k-eff, eigenvalues or sensitivity coefficients in a pandas DataFrame.

| Model | Sequences | Main outputs | Validated on |
|---|---|---|---|
| `Scale-keno` | `=csas5`, `=csas6` (multigroup or continuous energy) | `mean_keff`, `sigma_keff` + KENO final results table | SCALE 6.2.4 |
| `Scale-tsunami` | `=tsunami-3d-k5`, `=tsunami-3d-k6`, `=tsunami-1d` | k-eff (forward, adjoint), `lambda`, sensitivity coefficients | SCALE 6.2.4 (TSUNAMI-3D-K5 multigroup, TSUNAMI-1D) |
| `Scale-xsdrnpm` | `=t-xsdrn`, `=xsdrn` (any sequence printing the XSDRNPM `lambda` line) | `lambda` | SCALE 6.2.4 (`=t-xsdrn`) |
| `Scale-shift` | `=csas5-shift`, `=csas6-shift` (SCALE >= 6.3) | same as `Scale-keno` | **not validated** (no Shift in SCALE 6.2) |

All models share one calculator, `.fz/calculators/Scale.sh`, and report a
`scale_status` output (see [Run status](#run-status)).

## Installation

```bash
pip install git+https://github.com/Funz/fz.git
fz install Scale            # or: python -c "import fz; fz.install('Scale')"
```

SCALE itself is found, in this order, from `SCALE_CMD` (path of `scalerte`),
`SCALE_HOME` (`$SCALE_HOME/bin/scalerte`), `scalerte` on `PATH`, then the newest
of `/SCALE/scale6*`, `/opt/scale*`, `/opt/SCALE*`, `~/opt/SCALE*`, `~/opt/scale*`.

```bash
export SCALE_HOME=/opt/SCALE-6.2.4
```

## Usage

```python
import fz

results = fz.fzr(
    "examples/Scale-keno/godiva.inp",
    {"r": [8.4, 8.6, 8.741, 8.9, 9.1]},
    model="Scale-keno",
    calculators=["localhost_Scale"] * 4,   # 4 cases in parallel
    results_dir="results/godiva",
)
print(results[["r", "status", "scale_status", "mean_keff", "sigma_keff"]])
```

Command line:

```bash
fzr examples/Scale-keno/godiva.inp --model Scale-keno \
    --input_variables '{"r": [8.4, 8.741, 9.1]}' --calculators localhost_Scale --results_dir results/godiva
fzo 'results/godiva/*' --model Scale-keno --format csv    # re-parse existing results
```

`calculators` may be omitted: fz then uses `.fz/calculators/localhost_Scale.json`.

Result with SCALE 6.2.4 (`examples/Scale-keno/godiva.inp`, CSAS6, ce_v7.1,
250 generations of 2000 neutrons; see `example_usage.ipynb`):

```
       r status scale_status  mean_keff  sigma_keff
0  8.400   done   NORMAL END     0.9701      0.0013
1  8.600   done   NORMAL END     0.9859      0.0014
2  8.741   done   NORMAL END     0.9990      0.0013
3  8.900   done   NORMAL END     1.0165      0.0012
4  9.100   done   NORMAL END     1.0355      0.0013
```

## Input syntax

| Syntax | Meaning | Example |
|---|---|---|
| `&(name)` | variable | `sphere 10 &(r)` |
| `&(name~value)` | variable with default value | `&(r~8.741)` |
| `@{expression}` | formula (Python), evaluated after substitution | `@{round(4/3*3.14159265*r**3*18.742/1000, 2)}` |
| `@{expression\|format}` | formula with number format | `@{6.686E-2*&(dens)\|0.00000E00}` → `6.68600E-04` |
| `'` | SCALE comment line | `' r = &(r) cm` |

Variables (`()`) and formulas (`{}`) use different delimiters, so they can be
mixed on one line. In a formula, a name that is used nowhere else as a
variable must be written with its prefix (`&(dens)` or `&dens`); a plain name
(`r`) works once `&(r)` appears in the input.

The comment and title lines are copied to the SCALE output: a variable in a
comment (e.g. `' r = &(r) cm`) documents each case in its output.

## Outputs

`Scale-keno` and `Scale-shift` (KENO final results table, first sequence of
the input when it contains several):

| Output | Content |
|---|---|
| `scale_status` | `NORMAL END`, `CHECK ONLY` (`parm=check`), `ERROR: <first SCALE error message>`, `NO END BANNER[: <crash message>]`, `NO OUTPUT` |
| `scale_version` | e.g. `6.2.4` |
| `mean_keff`, `sigma_keff` | best estimate system k-eff and its standard deviation |
| `mean_E_lethargy`, `sigma_E_lethargy` | energy (eV) of the average lethargy causing fission |
| `mean_nubar`, `sigma_nubar` | system nu bar |
| `mean_free_path`, `sigma_free_path` | system mean free path (cm) |
| `n_warnings`, `n_errors` | numbers of KENO warning / error messages |
| `keff_normality` | chi**2 normality test of k-eff: `pass_95`, `pass_99` (fails at 95 %, passes at 99 %), `fail_99` |
| `source_convergence` | KENO source convergence tests: `passed`, `failed`, `not valid` |

`Scale-tsunami`: the outputs above, plus

| Output | Content |
|---|---|
| `mean_keff_adjoint`, `sigma_keff_adjoint` | adjoint k-eff (TSUNAMI-3D; the 2nd KENO final table) |
| `lambda` | eigenvalue (TSUNAMI-1D) |
| `mean_sens_<nuclide>_<reaction>`, `sigma_sens_<nuclide>_<reaction>` | energy-, region- and mixture-integrated sensitivity coefficients (first table of the output), e.g. `mean_sens_u235_total`, `mean_sens_u238_nnp` (`n,n'`), `mean_sens_h1_capture`; no `sigma_sens_*` for TSUNAMI-1D |

`Scale-xsdrnpm`: `scale_status`, `scale_version`, `lambda` (first XSDRNPM eigenvalue).

## Run status

The `scalerte` exit code is 0 even when the calculation failed (input error,
unknown library or nuclide, KENO failure), and `Congratulations!` can be
printed although a later step failed (TSUNAMI-3D adjoint KENO). The calculator
and `scale_status` therefore read `<input>.out` and `<input>.msg`:

- an error message (`error: ...`, `***** error ***** ...`, `Parse Error`,
  `<module> failed to execute`, `terminated due to errors`) gives
  `ERROR: <message>` and a failed case (`status = failed`, message in `error`
  and in the case's `err.txt`);
- a `parm=check` run (data check, no transport) gives `CHECK ONLY` (case done);
- no `SCALE is finished on ...` line (run killed, crashed) gives `NO END BANNER`,
  followed by the crash message of the `.msg` file when there is one
  (e.g. `double free or corruption (out)`);
- otherwise `NORMAL END`.

`NORMAL END` does not mean that the result is physically meaningful: SCALE
accepts, for instance, a negative sphere radius in KENO-VI. Look at
`source_convergence`, `keff_normality` and the warnings.

## Calculator settings

Environment variables read by `.fz/calculators/Scale.sh`:

| Variable | Effect |
|---|---|
| `SCALE_HOME`, `SCALE_CMD` | SCALE location (see Installation) |
| `SCALE_THREADS` | `scalerte -I N` (threads) |
| `SCALE_MPI` | `scalerte -N N` (MPI processes, MPI builds only) |
| `SCALE_TMPDIR` | `scalerte -T DIR` (temporary directory, default `/tmp/scale.<user>.<pid>`) |
| `SCALE_OPTS` | other `scalerte` options, e.g. `-r` (keep the temporary directory) |

The input file is the first `*.inp` file of the case, else the first file
that is not an output. Exit codes: 0 normal end or `parm=check`, 1 no input, 2 usage,
4 scalerte not found, 5 no `.out` produced, 6 SCALE errors, 7 no end banner.

fz stops a case after `FZ_RUN_TIMEOUT` seconds (default 3600 for local runs;
`0` for none), or after the model's `"timeout"` entry. On timeout or
interrupt, the calculator relays the signal to `scalerte`, which stops all
SCALE processes and removes its temporary directory.

Remote execution: install the plugin and SCALE on the remote host, then e.g.
`calculators="ssh://user@host/bash .fz/calculators/Scale.sh"` (see the fz
documentation for SSH/SLURM calculators).

## Limits

- `Scale-shift` has not been run: SCALE 6.2 has no Shift. The SCALE 6.3 manual
  describes a CSAS-Shift "final results table" with the best-estimate system
  k-eff, but its exact layout was not checked; run `tests/scale_probe` with a
  `=csas5-shift` input before relying on it.
- SCALE 6.3 outputs, CE-TSUNAMI, MPI builds and Windows were not tested.
- With several sequences in one input, only the first final results table is
  reported.

## Tests

```bash
pip install pytest git+https://github.com/Funz/fz.git
pytest tests/                    # ~10 s without SCALE; tests/test_scale_real.py runs SCALE if found (~1 min)
python tools/build_models.py     # regenerate .fz/models/*.json after editing the generator
```

- `tests/fixtures/scale6.2.4/`: real SCALE 6.2.4 outputs (normal ends, input
  errors, failed adjoint, killed run, echo traps), from `tests/scale_probe`;
- `tests/test_outputs.py`: output extraction on these outputs;
- `tests/test_calculator.py`: `Scale.sh` with a fake `scalerte` replaying them;
- `tests/test_fz_e2e.py`: `fzi`, `fzc`, `fzr` with the fake `scalerte`;
- `tests/test_scale_real.py`: `fzr` with the real SCALE (skipped without it);
- `tests/scale_probe/`: the SCALE probe and its findings (`README.md`).

## Links

- [Funz/fz](https://github.com/Funz/fz)
- [Funz/plugin-scale](https://github.com/Funz/plugin-scale) (former Java Funz plugin)
- [SCALE manual](https://scale-manual.ornl.gov)

## License

BSD 3-Clause, see [LICENSE](LICENSE).
