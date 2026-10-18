#!/usr/bin/env python3
"""Compare two GitHub repo trees through the API, without cloning.

Built for proprietary vendor repos (~1 GB) where a fetch is not an option.

usage: vendor-tree-diff.py OWNER/REPO@REF OWNER/REPO@REF [--prefix proprietary/] [--all]

Prints files only in A, only in B, and files at the same path whose blobs
differ. Needs an authenticated `gh`.
"""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor


def gh(path):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"gh api {path}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def walk(repo, sha, prefix=""):
    """Non-recursive walk for trees the recursive endpoint truncates."""
    data = gh(f"repos/{repo}/git/trees/{sha}")
    files, subdirs = {}, []
    for e in data["tree"]:
        if e["type"] == "blob":
            files[prefix + e["path"]] = e["sha"]
        elif e["type"] == "tree":
            subdirs.append((e["sha"], prefix + e["path"] + "/"))
    with ThreadPoolExecutor(8) as pool:
        for sub in pool.map(lambda s: walk(repo, *s), subdirs):
            files.update(sub)
    return files


def tree(spec):
    if "@" not in spec:
        sys.exit(f"expected OWNER/REPO@REF, got {spec}")
    repo, ref = spec.rsplit("@", 1)
    sha = gh(f"repos/{repo}/commits/{ref}")["sha"]
    data = gh(f"repos/{repo}/git/trees/{sha}?recursive=1")
    if data.get("truncated"):
        print(f"{spec}: tree truncated by the API, walking it", file=sys.stderr)
        return sha, walk(repo, sha)
    return sha, {e["path"]: e["sha"] for e in data["tree"] if e["type"] == "blob"}


def show(title, paths, limit):
    print(f"\n== {title}: {len(paths)}")
    for p in paths[: None if limit is None else limit]:
        print(f"  {p}")
    if limit is not None and len(paths) > limit:
        print(f"  ... {len(paths) - limit} more (--all)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--prefix", default="", help="only compare paths under this prefix")
    ap.add_argument("--all", action="store_true", help="print every path")
    args = ap.parse_args()

    sha_a, ta = tree(args.a)
    sha_b, tb = tree(args.b)
    ta = {p: s for p, s in ta.items() if p.startswith(args.prefix)}
    tb = {p: s for p, s in tb.items() if p.startswith(args.prefix)}
    limit = None if args.all else 40

    print(f"A {args.a} @ {sha_a[:12]}: {len(ta)} files")
    print(f"B {args.b} @ {sha_b[:12]}: {len(tb)} files")
    show("only in A", sorted(ta.keys() - tb.keys()), limit)
    show("only in B", sorted(tb.keys() - ta.keys()), limit)
    show("same path, different content", sorted(p for p in ta.keys() & tb.keys() if ta[p] != tb[p]), limit)


if __name__ == "__main__":
    main()
