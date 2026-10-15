"""Summarize a SCALE probe results directory (see run_probe.sh)."""
import re
import sys
from pathlib import Path

MARKERS = [
    ("finished", r"SCALE is finished"),
    ("congratulations", r"Congratulations!"),
    ("terminated_due_to_errors", r"terminated due to errors"),
    ("error_lines", r"(?im)^.*\berror\b.*$"),
    ("best_estimate", r"best estimate system k-eff\s+(\S+)\s+\+ or -\s+(\S+)"),
    ("n_warnings", r"number of warning messages\s+(\d+)"),
    ("n_errors", r"number of error messages\s+(\d+)"),
    ("chi2", r"k-effective (\S+(?: not)?) satisf\S* the chi\*\*2 test|k-effective (.{0,40}chi\*\*2.{0,40})"),
    ("source_convergence", r"source convergence tests (\S+)"),
    ("lambda", r"(?m)^\s*lambda\s+(\S+)"),
]


def main(root):
    root = Path(root)
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        print(f"=== {d.name}")
        print("  exit code:", (d / "exit_code.txt").read_text().strip(),
              " seconds:", (d / "seconds.txt").read_text().strip())
        print("  files:", " ".join(sorted(p.name for p in d.iterdir())))
        outs = sorted(d.glob("*.out"))
        if not outs:
            print("  NO .out")
        for out in outs:
            text = out.read_text(errors="replace")
            for name, pat in MARKERS:
                ms = list(re.finditer(pat, text))
                if not ms:
                    continue
                if name == "error_lines":
                    print(f"  {name}: {len(ms)}")
                    for m in ms[:6]:
                        print("     |", m.group(0).strip()[:150])
                else:
                    vals = [" ".join(g for g in m.groups() if g) if m.groups() else m.group(0) for m in ms]
                    print(f"  {name} x{len(ms)}: {vals[:4]}")
        for f in ("stderr.txt", "stdout.txt"):
            t = (d / f).read_text(errors="replace").strip() if (d / f).exists() else ""
            if t:
                print(f"  {f}: {t[:300]!r}")


if __name__ == "__main__":
    main(sys.argv[1])
