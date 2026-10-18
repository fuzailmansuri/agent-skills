#!/usr/bin/env python3
"""Fetch commits from any git host as an mbox for `git am`, without cloning.

usage: fetch-patch.py REF [REF ...] [-o OUT] [--map OLD=NEW ...]
                      [--include GLOB ...] [--exclude GLOB ...] [-C REPO (--check | --am)]

REF can be:
  https://github.com/O/R/commit/SHA      O/R@SHA      O/R@A..B (range)
  https://github.com/O/R/pull/N          (whole PR as a series)
  https://gitlab.com/O/R/-/commit/SHA    any GitLab, incl. git.codelinaro.org
  https://HOST/PROJECT/+/SHA             googlesource (android, chromium, ...)
  https://review.lineageos.org/c/P/+/N[/PS]   any Gerrit change (or HOST/#/c/N)
  https://git.kernel.org/.../commit/?id=SHA   cgit
  a local .patch / .mbox file, or any URL that serves a patch

--map aidl/lights/=lights/   move files to another directory (repeatable; the
                             upstream path is matched, first map wins)
--include / --exclude GLOB   keep or drop files by upstream path (fnmatch)
-C REPO --check              trial `git am -3` in a throwaway worktree of REPO
-C REPO --am                 `git am -3` onto REPO's current branch

Authorship stays the upstream author's. GitHub refs go through `gh api`, so
private repos work; everything else is fetched anonymously.
"""
import argparse
import base64
import datetime
import email.utils
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

MBOX_SEP = re.compile(r"^From [0-9a-f]{40} ", re.M)
UA = {"User-Agent": "fetch-patch/1"}


def http(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def gh_patch(path):
    out = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github.patch", path],
                         capture_output=True)
    if out.returncode:
        sys.exit(f"gh api {path}: {out.stderr.decode().strip()}")
    return out.stdout.decode("utf-8", "replace")


def gerrit_json(url):
    return json.loads(re.sub(r"^\)\]\}'\n", "", http(url)))


def mbox_from(sha, name, mail, when, message, diff):
    subject, _, body = message.strip("\n").partition("\n")
    body = body.strip("\n")
    return (f"From {sha} Mon Sep 17 00:00:00 2001\nFrom: {name} <{mail}>\n"
            f"Date: {email.utils.format_datetime(when)}\nSubject: [PATCH] {subject}\n\n"
            + (body + "\n" if body else "") + "---\n" + diff.rstrip("\n") + "\n-- \n2\n\n")


def fetch(ref):
    if os.path.exists(ref):
        with open(ref, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    m = re.fullmatch(r"([\w.-]+/[\w.-]+)@([\w./~^-]+?)(?:\.\.\.?([\w./~^-]+))?", ref)
    if m and "://" not in ref:
        repo, a, b = m.groups()
        return gh_patch(f"repos/{repo}/compare/{a}...{b}" if b else f"repos/{repo}/commits/{a}")
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)/(commit|pull)/([^/?#]+)", ref)
    if m:
        repo, kind, ident = m.groups()
        return gh_patch(f"repos/{repo}/pulls/{ident}" if kind == "pull" else f"repos/{repo}/commits/{ident}")
    m = re.match(r"(https?://[^?#]+?/-/(?:commit|merge_requests)/[^/?#]+)", ref)
    if m:
        return http(m.group(1) + ".patch")
    m = re.match(r"(https?://[^/]+)/(?:c/(?:.+?/\+/)?|#/c/(?:.+?/\+/)?)(\d+)(?:/(\d+))?", ref)
    if m:
        host, num, ps = m.groups()
        rev = ps or "current"
        text = base64.b64decode(http(f"{host}/changes/{num}/revisions/{rev}/patch")).decode("utf-8", "replace")
        if MBOX_SEP.search(text) and "\nFrom: " in text:
            return text
        info = gerrit_json(f"{host}/changes/{num}/revisions/{rev}/commit")
        au = info["author"]
        when = datetime.datetime.strptime(au["date"][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        return mbox_from(info.get("commit", "0" * 40), au["name"], au["email"], when, info["message"], text)
    m = re.match(r"(https?://[^/]*googlesource\.com/.+?)/\+/([0-9a-f]{7,40})", ref)
    if m:
        base, sha = m.groups()
        info = gerrit_json(f"{base}/+/{sha}?format=JSON")
        diff = base64.b64decode(http(f"{base}/+/{sha}%5E%21/?format=TEXT")).decode("utf-8", "replace")
        au = info["author"]
        when = datetime.datetime.strptime(au["time"], "%a %b %d %H:%M:%S %Y %z")
        return mbox_from(info["commit"], au["name"], au["email"], when, info["message"], diff)
    if re.match(r"https?://.+/commit/\?id=", ref):
        return http(ref.replace("/commit/?id=", "/patch/?id="))
    if ref.startswith("http"):
        return http(ref)
    sys.exit(f"don't know how to fetch {ref}")


def split_mbox(text):
    starts = [m.start() for m in MBOX_SEP.finditer(text)] or [0]
    return [text[s:e] for s, e in zip(starts, starts[1:] + [len(text)])]


def rewrite(patch, maps, inc, exc):
    """Filter and move the per-file sections of one patch."""
    lines = patch.split("\n")
    sep = next((i for i, l in enumerate(lines) if l == "---"), None)
    first = next((i for i, l in enumerate(lines) if l.startswith("diff --git ") and (sep is None or i > sep)), None)
    if first is None:
        return patch, [], []
    tail = len(lines)
    for i in range(len(lines) - 1, first, -1):
        if lines[i] == "-- ":
            tail = i
            break
    head, body, trailer = lines[:first], lines[first:tail], lines[tail:]
    chunks, cur = [], []
    for line in body:
        if line.startswith("diff --git ") and cur:
            chunks.append(cur)
            cur = []
        cur.append(line)
    if cur:
        chunks.append(cur)

    def move(p):
        for old, new in maps:
            if p.startswith(old):
                return new + p[len(old):]
        return p

    kept_chunks, kept, dropped = [], [], []
    for ch in chunks:
        m = re.match(r'diff --git a/(\S+) b/(\S+)$', ch[0])
        if not m:
            sys.exit(f"cannot parse quoted/odd path: {ch[0]}")
        src = m.group(1)
        if (inc and not any(fnmatch.fnmatch(src, g) for g in inc)) or any(fnmatch.fnmatch(src, g) for g in exc):
            dropped.append(src)
            continue
        out = []
        for line in ch:
            for pre in ("diff --git ", "--- a/", "+++ b/", "rename from ", "rename to ", "copy from ", "copy to "):
                if line.startswith(pre):
                    if pre == "diff --git ":
                        mm = re.match(r'diff --git a/(\S+) b/(\S+)$', line)
                        line = f"diff --git a/{move(mm.group(1))} b/{move(mm.group(2))}"
                    else:
                        line = pre + move(line[len(pre):])
                    break
            out.append(line)
        kept_chunks.append(out)
        kept.append(move(src))
    if not kept_chunks:
        return None, kept, dropped
    return "\n".join(head + [l for ch in kept_chunks for l in ch] + trailer), kept, dropped


def _git_identity():
    name = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True).stdout.strip()
    email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True).stdout.strip()
    return name, email


def git_am(repo, mbox, trial):
    env = dict(os.environ)
    name, email = _git_identity()
    if not name or not email:
        sys.exit("git config user.name/user.email unset — set your own identity first")
    env.setdefault("GIT_COMMITTER_NAME", name)
    env.setdefault("GIT_COMMITTER_EMAIL", email)
    if not trial:
        r = subprocess.run(["git", "-C", repo, "am", "-3", mbox], env=env, capture_output=True, text=True)
        print(r.stdout + r.stderr)
        if r.returncode:
            print("stopped; resolve then `git am --continue`, or `git am --abort`")
        return r.returncode
    tmp = tempfile.mkdtemp(prefix="pickcheck.")
    wt = os.path.join(tmp, "wt")
    subprocess.run(["git", "-C", repo, "worktree", "add", "-q", "--detach", wt, "HEAD"], check=True)
    try:
        r = subprocess.run(["git", "-C", wt, "am", "-3", mbox], env=env, capture_output=True, text=True)
        if r.returncode == 0:
            n = len(re.findall(r"^Applying: ", r.stdout, re.M))
            print(f"check: all {n} patch(es) apply on {repo} HEAD")
        else:
            failed = re.search(r"Patch failed at (\d+) (.*)", r.stdout + r.stderr)
            files = subprocess.run(["git", "-C", wt, "diff", "--name-only", "--diff-filter=U"],
                                   capture_output=True, text=True).stdout.split()
            print(f"check: FAILS at patch {failed.group(1)} {failed.group(2)}" if failed else "check: FAILS")
            if files:
                print("  conflicts: " + " ".join(files))
            print("  " + "\n  ".join(l for l in (r.stdout + r.stderr).splitlines() if l.startswith(("error", "CONFLICT"))))
            subprocess.run(["git", "-C", wt, "am", "--abort"], capture_output=True)
        return r.returncode
    finally:
        subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", wt], capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("refs", nargs="+")
    ap.add_argument("-o", "--out")
    ap.add_argument("--map", action="append", default=[], metavar="OLD=NEW")
    ap.add_argument("--include", action="append", default=[], metavar="GLOB")
    ap.add_argument("--exclude", action="append", default=[], metavar="GLOB")
    ap.add_argument("-C", "--repo")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true")
    g.add_argument("--am", action="store_true")
    a = ap.parse_args()
    maps = [tuple(m.split("=", 1)) for m in a.map]
    if any(len(m) != 2 for m in maps):
        sys.exit("--map wants OLD=NEW")

    patches = []
    for ref in a.refs:
        patches += split_mbox(fetch(ref))
    out_patches = []
    print(f"{'#':>3}  {'AUTHOR':24}  {'DATE':10}  SUBJECT")
    for n, p in enumerate(patches, 1):
        au = re.search(r"^From: (.*)$", p, re.M)
        dt = re.search(r"^Date: (.*)$", p, re.M)
        sj = re.search(r"^Subject: (?:\[PATCH[^\]]*\] )?(.*)$", p, re.M)
        try:
            day = email.utils.parsedate_to_datetime(dt.group(1)).strftime("%Y-%m-%d") if dt else "?"
        except (TypeError, ValueError):
            day = "?"
        newp, kept, dropped = rewrite(p, maps, a.include, a.exclude)
        name = re.sub(r"\s*<.*", "", au.group(1)) if au else "?"
        print(f"{n:>3}  {name[:24]:24}  {day:10}  {sj.group(1) if sj else '?'}")
        for f in kept:
            print(f"{'':42}{f}")
        for f in dropped:
            print(f"{'':42}(excluded) {f}")
        if newp is None:
            print(f"{'':42}-> every file excluded, patch skipped")
            continue
        out_patches.append(newp.rstrip("\n") + "\n")
    if not out_patches:
        sys.exit("nothing left to write")

    out = a.out
    if not out:
        d = os.path.join(os.environ.get("TMPDIR") or os.path.join(os.environ.get("PREFIX", ""), "tmp"), "picks")
        os.makedirs(d, exist_ok=True)
        out = os.path.join(d, datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".mbox")
    with open(out, "w") as fh:
        fh.write("\n".join(out_patches))
    print(f"\nwrote {len(out_patches)} patch(es) to {out}")
    if a.repo and (a.check or a.am):
        sys.exit(git_am(a.repo, out, trial=a.check))
    if a.check or a.am:
        sys.exit("--check/--am need -C REPO")


if __name__ == "__main__":
    main()
