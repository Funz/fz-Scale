# Test fixtures

## `scale6.2.4/<case>/`

Real SCALE 6.2.4 outputs (Linux x86_64) of the probe inputs
`tests/scale_probe/cases/<case>.inp`, produced by `tests/scale_probe/run_probe.sh`
and copied by `tests/scale_probe/make_fixtures.py`: user name, host name, home
directory and SCALE installation path replaced by `user`, `host`,
`/home/user`, `/opt/scale`, run directory by `/work`. Nothing else edited.

Exception: `killed_sigterm` is a real run of `ok_csas5_mg.inp` with 5000
generations, stopped by SIGTERM during the KENO generations (no end banner);
its echoed comment line mentions `SCALE is finished`.

See `tests/scale_probe/README.md` for what each case shows. The inputs
`var_parm_check`, `err_nsk_ge_gen`, `err_overlap`, `err_array_undefined` test
claims of the SCALE-skill notice; they are written for this probe (no text
of the notice is copied).

## `Scale-keno/godiva.out`

Excerpt (final results table and end of run) of a KENO-V.a output from
another SCALE version: `csas5_example.out` of idaholab/raven's
CodeInterfaceTests (https://github.com/idaholab/raven). Kept to check that an
older output layout still parses.
