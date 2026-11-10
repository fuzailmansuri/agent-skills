#!/usr/bin/env python3
"""Print the authorship and credit trailers for a commit built from upstream work.

usage: credit.py OWNER/REPO SHA [SHA ...] [--mirror] [--me "Name <email>"]

  default   adapted/squashed port: the upstream author becomes the commit author,
            the upstream commits are cited, you are Co-authored-by + Signed-off-by
  --mirror  your own follow-up that mirrors an upstream change (e.g. a vendor blob
            drop matching their device-tree commit): you stay author, the upstream
            author is Co-authored-by

Straight cherry-picks need none of this: `git cherry-pick -x SHA` keeps the
upstream author on its own.
"""
import argparse
import json
import re
import subprocess
import sys

def me():
    name = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True).stdout.strip()
    email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True).stdout.strip()
    if not name or not email:
        sys.exit("git config user.name/user.email unset — set your own identity first")
    return f"{name} <{email}>"

def gh(path):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"gh api {path}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("shas", nargs="+")
    ap.add_argument("--mirror", action="store_true")
    ap.add_argument("--me")
    a = ap.parse_args()
    a.me = a.me or me()

    commits = [gh(f"repos/{a.repo}/commits/{s}") for s in a.shas]
    people = []
    for c in commits:
        au = c["commit"]["author"]
        people.append(f"{au['name']} <{au['email']}>")
        people += re.findall(r"^Co-authored-by:\s*(.+?)\s*$", c["commit"]["message"], re.M | re.I)
    seen, ordered = set(), []
    for p in people:
        key = p.lower()
        if key not in seen and a.me.lower() != key:
            seen.add(key)
            ordered.append(p)

    primary = commits[0]["commit"]["author"]
    author = a.me if a.mirror else f"{primary['name']} <{primary['email']}>"
    co = [p for p in ordered if p.lower() != author.lower()]
    if not a.mirror and a.me.lower() != author.lower():
        co.append(a.me)

    print(f"author: {author}")
    if not a.mirror and len(commits) == 1:
        print(f"subject (keep upstream's when the change is the same): {commits[0]['commit']['message'].splitlines()[0]}")
    print("\n--- message footer ---")
    print("Based on" if not a.mirror else "Matches")
    for c in commits:
        print(c["html_url"])
    print()
    for p in co:
        print(f"Co-authored-by: {p}")
    print(f"Signed-off-by: {a.me}")
    print("--- end ---")
    if not a.mirror:
        print(f'\ngit commit --author="{author}" -F msg.txt   (or --amend)')
    else:
        print("\nvendor-api-commit.py ... " + " ".join(f'--co-author "{p}"' for p in ordered))


if __name__ == "__main__":
    main()
