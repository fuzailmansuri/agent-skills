#!/usr/bin/env python3
"""Turn SELinux denials (dmesg / logcat / audit) into sepolicy, the right way.

Reads denials, merges them per (domain, target, class), and prints allow rules,
but first tells you when the fix is a label (genfscon / file_contexts /
property_contexts / service_contexts) rather than a grant on a generic type.

usage: avc2rules.py [FILE ...] [--domain D] [--no-apps] [--te] [--live]

  FILE      text containing avc lines (default: stdin)
  --live    read `dmesg` and `logcat -b all -d` through su on this device
  --domain  only this source domain
  --no-apps skip app domains (untrusted_app*, isolated_app*, ...), keep the ROM's own
  --te      group rules per domain, ready to paste into <domain>.te
"""
import argparse
import re
import subprocess
import sys
from collections import defaultdict

AVC = re.compile(r"avc:\s+denied\s+\{\s*([^}]+?)\s*\}\s+for\s+(.*?)\s*$")
FIELD = re.compile(r'(\w+)=("[^"]*"|\S+)')
GENERIC = {
    "sysfs": "genfscon sysfs <path> u:object_r:<new_type>:s0 (vendor genfs_contexts), type <new_type>, sysfs_type, fs_type;",
    "proc": "genfscon proc <path> u:object_r:<new_type>:s0, type <new_type>, proc_type, fs_type;",
    "device": "file_contexts: /dev/<node> u:object_r:<new_type>:s0, type <new_type>, dev_type;",
    "default_prop": "property_contexts: <prop> u:object_r:<new_type>:s0, vendor_internal_prop(<new_type>) or system_*_prop()",
    "default_android_service": "service_contexts: <name> u:object_r:<new_type>:s0, type <new_type>, service_manager_type;",
    "default_android_hwservice": "hwservice_contexts: <name> u:object_r:<new_type>:s0",
    "default_android_vndservice": "vndservice_contexts: <name> u:object_r:<new_type>:s0",
    "vendor_file": "file_contexts: /vendor/... u:object_r:<specific_type>:s0",
    "system_file": "file_contexts for the binary, or move it to /vendor",
    "unlabeled": "the object has no label: add file_contexts/genfscon and restorecon",
    "vendor_data_file": "file_contexts: /data/vendor/<dir>(/.*)? u:object_r:<new_type>:s0",
    "mnt_vendor_file": "file_contexts: /mnt/vendor/persist/<path> u:object_r:<new_type>:s0",
    "tmpfs": "label the tmpfs mount or use a dedicated type",
    "rootfs": "label the path; rootfs grants are neverallow-prone",
}
RISKY_PERMS = {"execmem", "execmod", "module_load", "sys_admin", "sys_module", "mac_admin", "dac_override",
               "dac_read_search", "setenforce", "load_policy"}
APP_DOMAINS = re.compile(r"^(untrusted_app|isolated_app|ephemeral_app|platform_app|priv_app|system_app)")


def ctx_type(ctx):
    parts = ctx.split(":")
    return parts[2] if len(parts) > 2 else ctx


def parse(lines):
    seen = defaultdict(lambda: {"perms": set(), "count": 0, "names": set(), "ioctls": set(),
                                "permissive": set(), "comms": set()})
    for line in lines:
        m = AVC.search(line)
        if not m:
            continue
        perms, rest = m.group(1).split(), m.group(2)
        f = {k: v.strip('"') for k, v in FIELD.findall(rest)}
        if "scontext" not in f or "tcontext" not in f or "tclass" not in f:
            continue
        key = (ctx_type(f["scontext"]), ctx_type(f["tcontext"]), f["tclass"])
        e = seen[key]
        e["perms"].update(perms)
        e["count"] += 1
        for k in ("name", "path", "property"):
            if k in f:
                e["names"].add(f[k])
        if "ioctlcmd" in f:
            e["ioctls"].add(f["ioctlcmd"])
        if "permissive" in f:
            e["permissive"].add(f["permissive"])
        if "comm" in f:
            e["comms"].add(f["comm"])
    return seen


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--domain")
    ap.add_argument("--no-apps", action="store_true")
    ap.add_argument("--te", action="store_true")
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()

    lines = []
    if a.live:
        for cmd in ("dmesg", "logcat -b all -d"):
            out = subprocess.run(["su", "-c", cmd], capture_output=True, text=True, errors="replace")
            lines += out.stdout.splitlines()
    for path in a.files:
        with open(path, errors="replace") as fh:
            lines += fh.read().splitlines()
    if not a.live and not a.files:
        lines = sys.stdin.read().splitlines()

    seen = parse(lines)
    if a.domain:
        seen = {k: v for k, v in seen.items() if k[0] == a.domain}
    if a.no_apps:
        seen = {k: v for k, v in seen.items() if not re.match(r"^(untrusted_app|isolated_app|ephemeral_app|sdk_sandbox)", k[0])}
    if not seen:
        print("no denials")
        return

    by_domain = defaultdict(list)
    for key in sorted(seen):
        by_domain[key[0]].append(key)
    print(f"{sum(v['count'] for v in seen.values())} denials, {len(seen)} unique (domain, type, class)\n")
    for dom, keys in by_domain.items():
        if a.te:
            print(f"# ---- {dom}.te ----")
        for key in keys:
            _, tgt, cls = key
            e = seen[key]
            perms = sorted(e["perms"])
            notes = []
            if e["names"]:
                notes.append("names: " + ", ".join(sorted(e["names"])[:6]))
            if e["comms"]:
                notes.append("comm: " + ", ".join(sorted(e["comms"])[:4]))
            if "1" in e["permissive"]:
                notes.append("permissive=1 (domain is permissive; enforcing would block more)")
            print(f"# x{e['count']}  " + "; ".join(notes) if notes else f"# x{e['count']}")
            if tgt in GENERIC:
                print(f"# LABEL FIRST: {tgt} is generic -> {GENERIC[tgt]}")
            risky = RISKY_PERMS & e["perms"]
            if risky or (APP_DOMAINS.match(dom) and tgt in ("sysfs", "proc", "device", "vendor_file")):
                print(f"# NEVERALLOW RISK: {', '.join(sorted(risky)) or 'app domain on a generic type'}; "
                      "rethink before granting")
            if cls == "property_service" and "set" in e["perms"]:
                print(f"set_prop({dom}, {tgt})")
            elif cls == "service_manager" and e["perms"] <= {"find", "add"}:
                print(f"allow {dom} {tgt}:service_manager {{ {' '.join(perms)} }};")
            elif cls == "binder" and "call" in e["perms"]:
                print(f"binder_call({dom}, {tgt})")
                rest = sorted(e["perms"] - {"call", "transfer"})
                if rest:
                    print(f"allow {dom} {tgt}:binder {{ {' '.join(rest)} }};")
            else:
                print(f"allow {dom} {tgt}:{cls} {{ {' '.join(perms)} }};")
                if e["ioctls"]:
                    print(f"allowxperm {dom} {tgt}:{cls} ioctl {{ {' '.join(sorted(e['ioctls']))} }};")
            print()


if __name__ == "__main__":
    main()
