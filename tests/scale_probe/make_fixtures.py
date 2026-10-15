"""Copy probe results (run_probe.sh) to tests/fixtures/<label>/, anonymized.

Usage: python tests/scale_probe/make_fixtures.py <results dir> <label> [case ...]

Copies <case>.inp, <case>.out and <case>.msg of each case, replacing the user
name, host name, home directory, SCALE installation and run directory by
neutral values. Check afterwards with:  grep -ri "$USER\\|$(hostname)" tests/fixtures
"""
import getpass
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replacements(results):
    home = str(Path.home())
    user = getpass.getuser()
    fqdn = socket.getfqdn()
    host = socket.gethostname().split(".")[0]
    scale_home = os.environ.get("SCALE_HOME", "")
    reps = [(str(Path(results).resolve()), "/work")]
    if scale_home:
        reps.append((str(Path(scale_home).resolve()), "/opt/scale"))
    reps += [(home, "/home/user"), (fqdn, "host.example.org"), (host, "host"), (user, "user")]
    # SCALE truncates the user name in some fields (first characters only)
    reps += [(user[:n], "user") for n in range(len(user) - 1, 5, -1)]
    return [(a, b) for a, b in reps if a]


def main(results, label, cases):
    results = Path(results)
    dest_root = ROOT / "tests" / "fixtures" / label
    reps = replacements(results)
    dirs = [results / c for c in cases] if cases else sorted(p for p in results.iterdir() if p.is_dir())
    for d in dirs:
        dest = dest_root / d.name
        dest.mkdir(parents=True, exist_ok=True)
        for ext in (".inp", ".out", ".msg"):
            src = d / (d.name + ext)
            if not src.exists():
                continue
            text = src.read_text(errors="replace")
            for a, b in reps:
                text = text.replace(a, b)
            (dest / src.name).write_text(text)
        print(f"{d.name} -> {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
