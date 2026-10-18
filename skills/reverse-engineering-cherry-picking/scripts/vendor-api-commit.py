#!/usr/bin/env python3
"""Commit to a proprietary vendor repo through the GitHub API, without cloning it.

Drops prebuilt modules/files the way a setup-makefiles regen would (module block
in Android.bp, PRODUCT_PACKAGES / PRODUCT_COPY_FILES lines in <device>-vendor.mk,
the blob files themselves), or uploads replacement files. Dry run by default.

usage:
  vendor-api-commit.py --repo OWNER/REPO --branch BR
      [--drop-module NAME ...] [--drop-file proprietary/PATH ...] [--put LOCAL=REPO_PATH ...]
      [-m MSG | -F FILE] [--author "Name <email>"] [--co-author "Name <email>" ...]
      [--ref SHA] [--diff] [--apply]

Safety:
  * refuses when a remaining module still names a dropped module (shared_libs,
    required, ...) or a remaining module uses a file being deleted
  * verifies the module set, brace balance and the final file list before the
    ref update, and only fast-forwards the branch (never forces)
  * --ref lets a dry run target an older commit; --apply needs the branch head
"""
import argparse
import base64
import datetime
import difflib
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

ME = me()
BLOCK = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*) \{$")


def gh(path, method="GET", body=None, raw=False):
    cmd = ["gh", "api", "-X", method, path]
    if raw:
        cmd[2:2] = ["-H", "Accept: application/vnd.github.raw"]
    if body is not None:
        cmd += ["--input", "-"]
    out = subprocess.run(cmd, input=json.dumps(body).encode() if body is not None else None,
                         capture_output=True)
    if out.returncode:
        sys.exit(f"gh api {method} {path}: {out.stderr.decode().strip()}")
    return out.stdout if raw else json.loads(out.stdout)


def person(s):
    m = re.fullmatch(r"\s*(.+?)\s*<([^>]+)>\s*", s)
    if not m:
        sys.exit(f"expected 'Name <email>', got {s!r}")
    return m.group(1), m.group(2)


def bp_blocks(lines):
    blocks, i = [], 0
    while i < len(lines):
        m = BLOCK.match(lines[i])
        if not m:
            i += 1
            continue
        j = i + 1
        while j < len(lines) and lines[j] != "}":
            j += 1
        body = "\n".join(lines[i:j + 1])
        name = re.search(r'^    name: "([^"]+)"', body, re.M)
        blocks.append({"start": i, "end": j, "type": m.group(1),
                       "name": name.group(1) if name else None,
                       "srcs": re.findall(r'"(proprietary/[^"]+)"', body), "body": body})
        i = j + 1
    return blocks


def drop_mk_lines(lines, doomed):
    """Remove list items; fix the trailing backslash when the last item goes."""
    out = []
    for i, line in enumerate(lines):
        if i not in doomed:
            out.append(line)
            continue
        if not line.rstrip().endswith("\\"):
            for k in range(len(out) - 1, -1, -1):
                if out[k].strip():
                    if out[k].rstrip().endswith("\\"):
                        out[k] = out[k].rstrip()[:-1].rstrip()
                    break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--ref", help="base commit for a dry run (default: branch head)")
    ap.add_argument("--drop-module", action="append", default=[], metavar="NAME")
    ap.add_argument("--drop-file", action="append", default=[], metavar="PATH")
    ap.add_argument("--put", action="append", default=[], metavar="LOCAL=REPO_PATH")
    ap.add_argument("-m", "--message")
    ap.add_argument("-F", "--message-file")
    ap.add_argument("--author", default=ME)
    ap.add_argument("--co-author", action="append", default=[], metavar="'Name <email>'")
    ap.add_argument("--no-signoff", action="store_true")
    ap.add_argument("--diff", action="store_true", help="print unified diffs of edited makefiles")
    ap.add_argument("--apply", action="store_true", help="create the commit and fast-forward the branch")
    a = ap.parse_args()
    if not (a.drop_module or a.drop_file or a.put):
        sys.exit("nothing to do")

    R = f"repos/{a.repo}"
    head = gh(f"{R}/git/ref/heads/{a.branch}")["object"]["sha"]
    base = gh(f"{R}/commits/{a.ref}")["sha"] if a.ref else head
    if a.apply and base != head:
        sys.exit(f"--apply needs the branch head ({head[:12]}), not {base[:12]}")
    base_tree = gh(f"{R}/git/commits/{base}")["tree"]["sha"]
    tree = gh(f"{R}/git/trees/{base_tree}?recursive=1")
    if tree.get("truncated"):
        sys.exit("tree listing truncated; this repo is too big for the recursive tree endpoint")
    files = {e["path"] for e in tree["tree"] if e["type"] == "blob"}
    mk_names = sorted(p for p in files if "/" not in p and p.endswith("-vendor.mk"))
    if "Android.bp" not in files or len(mk_names) != 1:
        sys.exit(f"expected Android.bp and one *-vendor.mk at the root, found {mk_names}")
    mk_name = mk_names[0]

    def fetch(path):
        return gh(f"{R}/contents/{path}?ref={base}", raw=True).decode()

    bp_old, mk_old = fetch("Android.bp"), fetch(mk_name)
    amk = fetch("Android.mk") if "Android.mk" in files else ""
    bp_lines, mk_lines = bp_old.split("\n"), mk_old.split("\n")
    blocks = bp_blocks(bp_lines)
    by_name = {}
    for b in blocks:
        by_name.setdefault(b["name"], []).append(b)

    errors, deletes, bp_doomed, mk_doomed = [], set(), set(), set()
    for name in a.drop_module:
        if name not in by_name:
            errors.append(f"module {name} not in Android.bp")
            continue
        for b in by_name[name]:
            bp_doomed.update(range(b["start"], b["end"] + 1))
            if b["end"] + 1 < len(bp_lines) and bp_lines[b["end"] + 1] == "":
                bp_doomed.add(b["end"] + 1)
            deletes.update(b["srcs"])
        for i, line in enumerate(mk_lines):
            if line.strip() in (name, name + " \\"):
                mk_doomed.add(i)
    for path in a.drop_file:
        if path not in files:
            errors.append(f"{path} not in the tree")
            continue
        deletes.add(path)
        for i, line in enumerate(mk_lines):
            if f"/{path}:" in line:
                mk_doomed.add(i)

    puts = {}
    for spec in a.put:
        local, _, dest = spec.partition("=")
        if not dest:
            sys.exit(f"--put wants LOCAL=REPO_PATH, got {spec}")
        with open(local, "rb") as fh:
            puts[dest] = fh.read()
        deletes.discard(dest)

    missing = sorted(p for p in deletes if p not in files)
    if missing:
        errors.append("module srcs missing from the tree: " + ", ".join(missing))

    bp_new = "\n".join(l for i, l in enumerate(bp_lines) if i not in bp_doomed)
    mk_new = "\n".join(drop_mk_lines(mk_lines, mk_doomed))
    dropped = set(a.drop_module)

    remaining = [b for b in bp_blocks(bp_new.split("\n"))]
    for b in remaining:
        for name in dropped:
            if f'"{name}"' in b["body"]:
                errors.append(f"{b['name']} still references dropped module {name}")
        for src in b["srcs"]:
            if src in deletes:
                errors.append(f"{b['name']} still uses {src}")
    for name in dropped:
        if re.search(rf"(^|\s){re.escape(name)}(\s|\\|$)", mk_new, re.M):
            errors.append(f"{mk_name} still lists {name}")
    for needle in sorted(dropped | deletes):
        if needle in amk:
            errors.append(f"Android.mk mentions {needle}; edit it by hand")
    names_before = sorted(b["name"] or "" for b in blocks)
    names_after = sorted(b["name"] or "" for b in remaining)
    expected = list(names_before)
    for name in a.drop_module:
        while name in expected:
            expected.remove(name)
    if names_after != expected:
        errors.append("module set after the edit is not the expected one")
    if bp_new.count("{") - bp_new.count("}") != bp_old.count("{") - bp_old.count("}"):
        errors.append("Android.bp brace balance changed")

    changes = {}
    if bp_new != bp_old:
        changes["Android.bp"] = bp_new.encode()
    if mk_new != mk_old:
        changes[mk_name] = mk_new.encode()
    changes.update(puts)

    print(f"repo     {a.repo} {a.branch} @ {base[:12]}{'' if base == head else ' (not the branch head)'}")
    print(f"modules  -{len(a.drop_module)}: {', '.join(a.drop_module) or '-'}")
    print(f"Android.bp  -{len(bp_doomed)} lines")
    print(f"{mk_name}  -{len(mk_doomed)} lines")
    print(f"delete   {len(deletes)} files")
    for p in sorted(deletes):
        print(f"  {p}")
    for p in sorted(puts):
        print(f"put      {p} ({len(puts[p])} bytes, {'replace' if p in files else 'new'})")
    if a.diff:
        for path, old, new in (("Android.bp", bp_old, bp_new), (mk_name, mk_old, mk_new)):
            if old != new:
                sys.stdout.writelines(difflib.unified_diff(
                    old.splitlines(True), new.splitlines(True), f"a/{path}", f"b/{path}", n=1))
    if errors:
        print("\nERRORS")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("checks   module set, brace balance, dangling references: ok")
    if not a.apply:
        print("\ndry run; add --apply to commit")
        return

    if a.message_file:
        with open(a.message_file) as fh:
            msg = fh.read()
    elif a.message:
        msg = a.message
    else:
        sys.exit("--apply needs -m or -F")
    msg = msg.rstrip("\n") + "\n"
    trailers = [f"Co-authored-by: {c}" for c in a.co_author if f"Co-authored-by: {c}" not in msg]
    if not a.no_signoff and f"Signed-off-by: {ME}" not in msg:
        trailers.append(f"Signed-off-by: {ME}")
    if trailers:
        last = msg.rstrip("\n").split("\n")[-1]
        sep = "\n" if re.match(r"^[A-Za-z-]+: ", last) else "\n\n"
        msg = msg.rstrip("\n") + sep + "\n".join(trailers) + "\n"

    entries = []
    for path, data in changes.items():
        blob = gh(f"{R}/git/blobs", "POST", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    entries += [{"path": p, "mode": "100644", "type": "blob", "sha": None} for p in sorted(deletes)]
    new_tree = gh(f"{R}/git/trees", "POST", {"base_tree": base_tree, "tree": entries})["sha"]
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    an, ae = person(a.author)
    cn, ce = person(ME)
    commit = gh(f"{R}/git/commits", "POST", {
        "message": msg, "tree": new_tree, "parents": [base],
        "author": {"name": an, "email": ae, "date": now},
        "committer": {"name": cn, "email": ce, "date": now}})["sha"]

    got = {f["filename"]: f["status"] for f in gh(f"{R}/compare/{base}...{commit}")["files"]}
    want = {p: "removed" for p in deletes}
    want.update({p: ("modified" if p in files else "added") for p in changes})
    if got != want:
        sys.exit(f"commit {commit[:12]} has unexpected changes, ref not updated:\n  got {got}\n  want {want}")
    gh(f"{R}/git/refs/heads/{a.branch}", "PATCH", {"sha": commit, "force": False})
    print(f"\npushed   {commit[:12]} to {a.branch}: https://github.com/{a.repo}/commit/{commit}")


if __name__ == "__main__":
    main()
