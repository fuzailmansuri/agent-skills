#!/usr/bin/env python3
"""Find upstream commits that came after a commit and revert, fix or touch it.

Run this before picking anything: a commit that was later reverted, or needs a
follow-up fix, must not be picked alone.

usage: followups.py OWNER/REPO SHA [--branch BRANCH] [--max-files N]

Flags per later commit:
  REVERT   reverts it ("This reverts commit <sha>" or Revert "<subject>")
  MENTION  names its SHA or its subject (often "Fixes:" or follow-ups)
  FIX      subject says fix/fixup/follow-up and touches the same files
  TOUCH    only touches the same files
GitHub only (uses `gh api`).
"""
import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote


def gh(path):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"gh api {path}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("sha")
    ap.add_argument("--branch", help="branch to search (default: the repo's default branch)")
    ap.add_argument("--max-files", type=int, default=20)
    a = ap.parse_args()

    R = f"repos/{a.repo}"
    c = gh(f"{R}/commits/{a.sha}")
    sha, msg = c["sha"], c["commit"]["message"]
    subject = msg.splitlines()[0]
    since = c["commit"]["committer"]["date"]
    files = [f["filename"] for f in c.get("files", [])]
    branch = a.branch or gh(R)["default_branch"]
    print(f"{sha[:12]} {subject}")
    print(f"branch {branch}, after {since}, {len(files)} file(s)"
          + (f", checking the first {a.max_files}" if len(files) > a.max_files else ""))

    def later(path):
        return gh(f"{R}/commits?sha={quote(branch)}&path={quote(path)}&since={since}&per_page=100")

    hits = {}
    with ThreadPoolExecutor(6) as pool:
        for path, commits in zip(files[: a.max_files], pool.map(later, files[: a.max_files])):
            for x in commits:
                if x["sha"] == sha:
                    continue
                h = hits.setdefault(x["sha"], {"c": x, "files": set()})
                h["files"].add(path)

    rows = []
    for s, h in hits.items():
        m = h["c"]["commit"]["message"]
        subj = m.splitlines()[0]
        if re.search(rf"reverts commit {sha[:7]}", m) or subj == f'Revert "{subject}"':
            flag = "REVERT"
        elif sha[:7] in m or subject in m:
            flag = "MENTION"
        elif re.search(r"\b(fix|fixup|follow[- ]?up|regression|crash)", subj, re.I):
            flag = "FIX"
        else:
            flag = "TOUCH"
        rows.append((h["c"]["commit"]["committer"]["date"], flag, s, subj, len(h["files"])))

    if not rows:
        print("no later commits touch these files")
        return
    order = {"REVERT": 0, "MENTION": 1, "FIX": 2, "TOUCH": 3}
    rows.sort(key=lambda r: (order[r[1]], r[0]))
    print(f"\n{'FLAG':8} {'DATE':10} {'COMMIT':12} {'FILES':>5}  SUBJECT")
    for date, flag, s, subj, nf in rows:
        print(f"{flag:8} {date[:10]:10} {s[:12]:12} {nf:>5}  {subj}")
    if any(r[1] == "REVERT" for r in rows):
        print("\nreverted upstream: do not pick it alone")


if __name__ == "__main__":
    main()
