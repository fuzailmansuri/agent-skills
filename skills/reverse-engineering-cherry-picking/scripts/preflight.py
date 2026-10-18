#!/usr/bin/env python3
"""Static build-safety checks for an Android device tree, for when nobody builds.

  lists     drift between proprietary-*.txt and the vendor repo (bites on the next re-extract)
  vendor    <device>-vendor.mk names with no module, module srcs / copy sources that do not exist
  sepolicy  duplicate type/attribute declarations; conflicting property/service/genfs/file contexts
  vintf     the same HAL instance declared twice (device tree, hardware repos, installed vendor xml)
  init      duplicate service names across device tree and hardware repos
  modules   device-specific PRODUCT_PACKAGES that none of the given repos define

usage: preflight.py --dt DIR [--hw DIR ...] [--module-dir DIR ...]
                    [--vendor OWNER/REPO@REF | --vendor-dir DIR] [--token WORD ...]

--hw dirs are hardware repos included by the tree (e.g. hardware/nothing). When a
hw dir has a config.mk, its sepolicy includes are evaluated against the tree's
PRODUCT_PACKAGES. Exit status 1 when any ERROR is found.
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ERRORS, WARNS = [], []


def err(sec, msg):
    ERRORS.append((sec, msg))


def warn(sec, msg):
    WARNS.append((sec, msg))


def text(path):
    with open(path, errors="replace") as fh:
        return fh.read()


def files_under(root, pred):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != ".git"]
        for fn in fns:
            p = os.path.join(dp, fn)
            if pred(p):
                yield p


def mk_lists(src, var_re=r"PRODUCT_PACKAGES\w*"):
    """Items assigned to make list variables, following line continuations."""
    out, cur = [], None
    for line in src.splitlines():
        s = line.split("#", 1)[0].rstrip()
        if cur is None:
            m = re.match(rf"\s*({var_re})\s*[:+?]?=\s*(.*)$", s)
            if not m:
                continue
            cur, s = m.group(1), m.group(2)
        cont = s.endswith("\\")
        for item in s.rstrip("\\").split():
            if "$(" not in item:
                out.append(item)
        if not cont:
            cur = None
    return out


def module_names(root):
    names = set()
    for p in files_under(root, lambda p: p.endswith(("Android.bp", "Android.mk"))):
        src = text(p)
        if p.endswith(".bp"):
            names.update(re.findall(r'^\s{4}name:\s*"([^"]+)"', src, re.M))
        else:
            names.update(re.findall(r"^\s*LOCAL_(?:MODULE|PACKAGE_NAME)\s*:?=\s*(\S+)", src, re.M))
    return names


def bp_blocks(src):
    out, lines, i = [], src.split("\n"), 0
    while i < len(lines):
        if re.match(r"^[A-Za-z_]\w* \{$", lines[i]):
            j = i + 1
            while j < len(lines) and lines[j] != "}":
                j += 1
            out.append("\n".join(lines[i:j + 1]))
            i = j + 1
        else:
            i += 1
    return out


def installed_fragments(root, packages, field):
    """Files listed in `field` (vintf_fragments / init_rc) of modules that are built."""
    res = set()
    for p in files_under(root, lambda p: p.endswith("Android.bp")):
        for b in bp_blocks(text(p)):
            n = re.search(r'^\s{4}name:\s*"([^"]+)"', b, re.M)
            if not n or n.group(1) not in packages:
                continue
            m = re.search(rf"{field}:\s*\[([^\]]*)\]", b)
            if m:
                for f in re.findall(r'"([^"]+)"', m.group(1)):
                    res.add(os.path.normpath(os.path.join(os.path.dirname(p), f)))
    return res


# ---------------------------------------------------------------- vendor access
class Vendor:
    def __init__(self, spec=None, path=None):
        self.spec, self.path = spec, path
        if spec:
            self.repo, ref = spec.rsplit("@", 1)
            self.sha = self.gh(f"repos/{self.repo}/commits/{ref}")["sha"]
            tree = self.gh(f"repos/{self.repo}/git/trees/{self.sha}?recursive=1")
            if tree.get("truncated"):
                sys.exit("vendor tree listing truncated by the API; use --vendor-dir")
            self.files = {e["path"] for e in tree["tree"] if e["type"] == "blob"}
        else:
            self.files = {os.path.relpath(p, path) for p in files_under(path, lambda p: True)}

    @staticmethod
    def gh(path, raw=False):
        cmd = ["gh", "api", path] + (["-H", "Accept: application/vnd.github.raw"] if raw else [])
        out = subprocess.run(cmd, capture_output=True)
        if out.returncode:
            sys.exit(f"gh api {path}: {out.stderr.decode().strip()}")
        return out.stdout.decode("utf-8", "replace") if raw else json.loads(out.stdout)

    def read(self, rel):
        if self.path:
            return text(os.path.join(self.path, rel))
        return self.gh(f"repos/{self.repo}/contents/{rel}?ref={self.sha}", raw=True)

    def read_many(self, rels):
        with ThreadPoolExecutor(8) as pool:
            return dict(zip(rels, pool.map(self.read, rels)))


# ---------------------------------------------------------------- checks
def check_lists(dt, v):
    """List/vendor drift. The build reads the vendor makefiles, so drift only bites on the
    next extract-files/setup-makefiles run; module-level breakage is check_vendor's job."""
    listed, missing = set(), []
    for fn in sorted(os.listdir(dt)):
        m = re.match(r"proprietary-(.+)\.txt$", fn)
        if not m:
            continue
        firmware = m.group(1) == "firmware"
        for line in text(os.path.join(dt, fn)).splitlines():
            s = re.sub(r"#.*", "", line).strip().lstrip("-")
            s = re.split(r"[;|]", s)[0].strip()
            if not s:
                continue
            dest = s.split(":", 1)[1] if ":" in s else s
            want = f"radio/{os.path.basename(dest)}" if firmware else f"proprietary/{dest}"
            listed.add(want)
            if want not in v.files:
                missing.append(f"{fn}:{s}")
    if missing:
        warn("lists", f"{len(missing)} listed entries are not in the vendor repo (re-extract needed before the "
             "next setup-makefiles): " + ", ".join(missing[:12]) + (" ..." if len(missing) > 12 else ""))
    extra = sorted(p for p in v.files if p.startswith("proprietary/") and p not in listed)
    if extra:
        warn("lists", f"{len(extra)} vendor files no list names (vendor extracted against another tree?): "
             + ", ".join(extra[:12]) + (" ..." if len(extra) > 12 else ""))


def check_vendor(v):
    mks = [p for p in v.files if "/" not in p and p.endswith("-vendor.mk")]
    if "Android.bp" not in v.files or len(mks) != 1:
        warn("vendor", "no Android.bp + single *-vendor.mk at the vendor root; skipped")
        return None, set()
    src = v.read_many(["Android.bp", mks[0]] + (["Android.mk"] if "Android.mk" in v.files else []))
    bp, mk = src["Android.bp"], src[mks[0]]
    names = set(re.findall(r'^\s{4}name:\s*"([^"]+)"', bp, re.M))
    names |= set(re.findall(r"^\s*LOCAL_MODULE\s*:?=\s*(\S+)", src.get("Android.mk", ""), re.M))
    pkgs = mk_lists(mk)
    for n in pkgs:
        if n not in names:
            err("vendor", f"{mks[0]} lists {n}, no such module")
    for p in sorted(set(re.findall(r'"(proprietary/[^"]+)"', bp))):
        if p not in v.files:
            err("vendor", f"Android.bp source {p} missing")
    for p in sorted(set(re.findall(r"/(proprietary/[^:\s]+):", mk))):
        if p not in v.files:
            err("vendor", f"{mks[0]} copies {p}, missing")
    copied = set(re.findall(r"/(proprietary/[^:\s]+):", mk))
    return set(pkgs), copied


def eval_hw_sepolicy(hw, packages, codename):
    """sepolicy dirs a hw repo's config.mk includes for this tree."""
    cfg = os.path.join(hw, "config.mk")
    if not os.path.exists(cfg):
        return sorted({os.path.dirname(p) for p in files_under(os.path.join(hw, "sepolicy"),
                       lambda p: p.endswith((".te", "_contexts")))})
    dirs, stack = [], []
    for line in text(cfg).splitlines():
        s = line.strip()
        m = re.match(r"ifn?eq\s*\(\$\(filter\s+(.+?)\s*,\s*\$\(PRODUCT_PACKAGES\)\),\s*\)", s)
        if m:
            want = m.group(1).replace("$(PRODUCT_DEVICE)", codename).split()
            hit = any(w in packages for w in want)
            stack.append(hit if s.startswith("ifneq") else not hit)
            continue
        if s.startswith(("ifeq", "ifneq", "ifdef", "ifndef")):
            stack.append(True)
            continue
        if s == "else" and stack:
            stack[-1] = not stack[-1]
            continue
        if s == "endif" and stack:
            stack.pop()
            continue
        m = re.search(r"SEPOLICY_DIRS\s*\+?=\s*\S*?(sepolicy/\S+)", s)
        if m and all(stack):
            dirs.append(os.path.join(hw, m.group(1)))
    return dirs


def check_sepolicy(dirs):
    decls = defaultdict(set)
    ctx = defaultdict(lambda: defaultdict(set))
    decl_re = re.compile(r"^\s*(?:type|attribute)\s+(\w+)\s*[,;]"
                         r"|^\s*(?:vendor|system|product)_(?:internal|restricted|public|vendor_config)_prop\(\s*(\w+)\s*\)", re.M)
    for d in dirs:
        scope = "vendor" if "/vendor" in d else "private" if "/private" in d else "public" if "/public" in d else d
        for p in files_under(d, lambda p: p.endswith((".te", "_contexts"))):
            src = text(p)
            if p.endswith(".te"):
                for m in decl_re.finditer(src):
                    decls[m.group(1) or m.group(2)].add(p)
                continue
            kind = os.path.basename(p)
            if kind == "seapp_contexts":
                continue
            for line in src.splitlines():
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                parts = line.split()
                if kind == "genfs_contexts" and len(parts) >= 4:
                    key, label = (parts[1], parts[2]), parts[3]
                elif len(parts) >= 2:
                    key, label = parts[0], parts[-1]
                else:
                    continue
                ctx[(scope, kind, key)][label].add(p)
    for name, where in sorted(decls.items()):
        if len(where) > 1:
            err("sepolicy", f"{name} declared in {len(where)} files: {', '.join(sorted(where))}")
    for (scope, kind, key), labels in sorted(ctx.items(), key=lambda kv: str(kv[0])):
        files = {f for fs in labels.values() for f in fs}
        if len(labels) > 1:
            err("sepolicy", f"{scope}/{kind} {key}: conflicting labels "
                + "; ".join(f"{l} ({', '.join(sorted(fs))})" for l, fs in labels.items()))
        elif len(files) > 1:
            warn("sepolicy", f"{scope}/{kind} {key} listed in {len(files)} files: {', '.join(sorted(files))}")


def hal_keys(xml_src):
    try:
        root = ET.fromstring(xml_src)
    except ET.ParseError:
        return []
    if root.tag != "manifest":
        return []
    keys = []
    for hal in root.findall("hal"):
        if hal.get("override") == "true":
            continue
        fmt, name = hal.get("format", "hidl"), (hal.findtext("name") or "").strip()
        for fq in hal.findall("fqname"):
            keys.append((fmt, name, fq.text.strip()))
        for itf in hal.findall("interface"):
            for inst in itf.findall("instance"):
                ver = (hal.findtext("version") or "").strip()
                keys.append((fmt, name, f"{('@' + ver + '::') if fmt == 'hidl' else ''}{itf.findtext('name').strip()}/{inst.text.strip()}"))
    return keys


def check_vintf(sources):
    seen = defaultdict(set)
    for label, src in sources:
        for k in hal_keys(src):
            seen[k].add(label)
    for k, where in sorted(seen.items()):
        if len(where) > 1:
            err("vintf", f"{k[1]} {k[2]} ({k[0]}) declared by: {', '.join(sorted(where))}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dt", required=True)
    ap.add_argument("--hw", action="append", default=[])
    ap.add_argument("--module-dir", action="append", default=[])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--vendor")
    g.add_argument("--vendor-dir")
    ap.add_argument("--token", action="append", default=[], help="extra device-specific name fragment")
    a = ap.parse_args()
    dt = os.path.abspath(a.dt)

    mk_src = "\n".join(text(p) for p in files_under(dt, lambda p: p.endswith(".mk")))
    packages = set(mk_lists(mk_src))
    codename = (re.findall(r"^\s*PRODUCT_DEVICE\s*:?=\s*(\S+)", mk_src, re.M) or [os.path.basename(dt)])[0]
    brand = (re.findall(r"^\s*PRODUCT_(?:BRAND|MANUFACTURER)\s*:?=\s*(\S+)", mk_src, re.M) or [""])[0]
    print(f"device tree {dt} ({codename}), {len(packages)} PRODUCT_PACKAGES")

    v = None
    if a.vendor or a.vendor_dir:
        v = Vendor(a.vendor, a.vendor_dir and os.path.abspath(a.vendor_dir))
        print(f"vendor {a.vendor or a.vendor_dir}{' @ ' + v.sha[:12] if a.vendor else ''}: {len(v.files)} files")
        check_lists(dt, v)
        vendor_pkgs, vendor_copies = check_vendor(v)
    else:
        vendor_pkgs, vendor_copies = None, set()

    se_dirs = [d for d in (os.path.join(dt, "sepolicy", s) for s in ("vendor", "private", "public")) if os.path.isdir(d)]
    for hw in a.hw:
        se_dirs += eval_hw_sepolicy(os.path.abspath(hw), packages, codename)
    check_sepolicy(se_dirs)

    vintf = [(os.path.relpath(p, dt), text(p)) for p in files_under(dt, lambda p: p.endswith(".xml"))
             if "<manifest" in text(p)[:4000]]
    rc_files = list(files_under(dt, lambda p: p.endswith(".rc")))
    for hw in a.hw:
        hw = os.path.abspath(hw)
        for p in installed_fragments(hw, packages, "vintf_fragments"):
            if os.path.exists(p):
                vintf.append((os.path.relpath(p, os.path.dirname(hw)), text(p)))
        rc_files += [p for p in installed_fragments(hw, packages, "init_rc") if os.path.exists(p)]
    if v and vendor_pkgs is not None:
        xmls = sorted(p for p in v.files if re.match(r"proprietary/.*etc/vintf/manifest/[^/]+\.xml$", p)
                      and (os.path.basename(p) in vendor_pkgs or p in vendor_copies))
        vintf += [(f"vendor:{p}", s) for p, s in v.read_many(xmls).items()]
    check_vintf(vintf)

    services = defaultdict(set)
    for p in rc_files:
        for name in re.findall(r"^\s*service\s+(\S+)\s", text(p), re.M):
            services[name].add(p)
    for name, where in sorted(services.items()):
        if len(where) > 1:
            warn("init", f"service {name} defined in {', '.join(sorted(where))}")

    defined = module_names(dt)
    for d in a.hw + a.module_dir:
        defined |= module_names(os.path.abspath(d))
    if v and vendor_pkgs is not None:
        defined |= vendor_pkgs
    tokens = [t.lower() for t in [codename, brand] + a.token if t]
    for n in sorted(packages - defined):
        if any(t in n.lower() for t in tokens):
            warn("modules", f"{n} is not defined in the given repos (pass --module-dir for the repo that has it)")

    for title, items in (("ERROR", ERRORS), ("WARN", WARNS)):
        for sec, msg in items:
            print(f"{title:5} [{sec}] {msg}")
    print(f"\n{len(ERRORS)} error(s), {len(WARNS)} warning(s)")
    sys.exit(1 if ERRORS else 0)


if __name__ == "__main__":
    main()
