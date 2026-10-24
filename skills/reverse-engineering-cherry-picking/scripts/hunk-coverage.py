#!/usr/bin/env python3
"""Which upstream commits explain a bulk commit? Added-line coverage per patch.

Usage: hunk-coverage.py COMMIT PATCH_DIR [-C REPO] [--min PCT]

COMMIT is a commit in REPO (default: cwd) that imported many changes at once. PATCH_DIR holds
upstream commits as mbox/diff files (fetch-patch.py output, `git format-patch`, or `git show`).
For every patch, prints how many of its added lines also appear as added lines of the same
file in COMMIT, plus the residue of COMMIT that no patch explains. Use it to split an
"import" commit into per-upstream commits with their original authors.
"""
import argparse
import collections
import os
import re
import subprocess
import sys


def added_by_file(diff):
    out, cur = collections.defaultdict(list), None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            cur = None if line.endswith("/dev/null") else re.sub(r"^\+\+\+ [^/]*/", "", line)
        elif cur and line.startswith("+") and line[1:].strip():
            out[cur].append(line[1:].strip())
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("commit")
    ap.add_argument("patch_dir")
    ap.add_argument("-C", dest="repo", default=".")
    ap.add_argument("--min", type=float, default=50.0, help="hide patches below this %% (default 50)")
    a = ap.parse_args()

    show = subprocess.run(["git", "-C", a.repo, "show", "--format=", "--no-color", a.commit],
                          capture_output=True, text=True, check=True).stdout
    ours = added_by_file(show)
    left = {f: collections.Counter(v) for f, v in ours.items()}
    total = sum(len(v) for v in ours.values())
    rows = []
    for name in sorted(os.listdir(a.patch_dir)):
        path = os.path.join(a.patch_dir, name)
        if not os.path.isfile(path):
            continue
        with open(path, errors="replace") as fh:
            theirs = added_by_file(fh.read())
        n = sum(len(v) for v in theirs.values())
        if not n:
            continue
        hit = sum(1 for f, v in theirs.items() for l in v if f in ours and l in left[f])
        rows.append((100.0 * hit / n, hit, n, name, theirs))
    rows.sort(key=lambda r: -r[0])
    covered = 0
    for pct, hit, n, name, theirs in rows:
        if pct < a.min:
            continue
        for f, v in theirs.items():
            for l in v:
                if f in left and left[f][l] > 0:
                    left[f][l] -= 1
                    covered += 1
        print(f"{pct:5.1f}%  {hit:4d}/{n:<4d}  {name}")
    rest = sum(sum(c.values()) for c in left.values())
    print(f"\nexplained {total - rest}/{total} added lines; {rest} unexplained (your own work or a missing source)",
          file=sys.stderr)
    for f, c in sorted(left.items()):
        if sum(c.values()):
            print(f"  unexplained: {f} ({sum(c.values())} lines)", file=sys.stderr)


if __name__ == "__main__":
    main()
