#!/usr/bin/env python3
"""Reverse-engineer Android ELF blobs (HALs, daemons, .so) with no binutils.

What a blob needs (DT_NEEDED, dlopen candidates), what it exposes (SONAME,
exported symbols, AIDL/HIDL interfaces) and what it touches (sysfs/dev nodes,
properties, paths, SELinux contexts, firmware/config files).

usage:
  blob-intel.py FILE [FILE ...] [--symbols] [--strings] [--su]
  blob-intel.py --dir DIR [--who-needs LIB] [--missing] [--orphans]

  --su         read files through `su -c cat` (live /vendor, /odm on a rooted device)
  --symbols    list exported/imported dynamic symbols (demangled when llvm-cxxfilt exists)
  --strings    dump every printable string, not just the categorised ones
  --dir        index every ELF under DIR (an extracted vendor/odm/system dump)
  --who-needs  ELFs in DIR that link LIB
  --missing    DT_NEEDED entries nothing in DIR provides (platform libs excluded)
  --orphans    shared libs in DIR that no ELF links or names (dlopen); slow
"""
import argparse
import os
import re
import shutil
import struct
import subprocess
import sys

MACHINES = {0x03: "x86", 0x28: "ARM", 0x3E: "x86-64", 0xB7: "AArch64"}
PLATFORM = set("""libc libm libdl liblog libc++ libutils libcutils libbase libbinder libbinder_ndk
libhidlbase libhwbinder libhardware libhardware_legacy libz libcrypto libssl libsync libui libgui
libEGL libGLESv1_CM libGLESv2 libGLESv3 libvulkan libnativewindow libandroid libmediandk libfmq
libvndksupport libprocessgroup libjsoncpp libexpat libxml2 libtinyxml2 libprotobuf-cpp-lite
libprotobuf-cpp-full libsqlite libbacktrace libunwindstack libnetutils libpower libpowermanager
libcamera_metadata libsysutils libdmabufheap libion libvintf libselinux libcap libnl libcurl
libaudioutils libtinyalsa libmedia_helper libstagefright_foundation libsensorndkbridge libdrm
libandroid_net libbinder_rs liblog_rust libdl_android libclang_rt libstdc++ libnativehelper
libandroid_runtime libmedia libaudioclient libcamera_client libgralloctypes libhidlmemory
libhidltransport libsoftkeymasterdevice libkeymaster_messages libkeymaster_portable libpuresoftkeymasterdevice
libnativebase libnativeloader libsync libtinycompress libaudioroute libtextclassifier_hash
libstatssocket libstatspull libmemunreachable libziparchive libcap libpcre2 libpackagelistparser
libandroidicu libicu libicuuc libicui18n libRScpp libmediautils libcgrouprc libbpf_android""".split())
PLATFORM_RE = re.compile(r"^(android|vendor\.qti|vendor\.nothing)\..*\.so$")

CATEGORIES = [
    ("interfaces", re.compile(
        r"^(?:[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+@\d+\.\d+::I[A-Z]\w*(?:/\w+)?"
        r"|[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\.I[A-Z]\w*(?:/[\w.-]+)?"
        r"|I[A-Z][A-Za-z0-9]+/[\w.-]+)$")),
    ("nodes", re.compile(r"^/(?:sys|proc|dev)/\S+$")),
    ("props", re.compile(
        r"^(?:ro|persist|vendor|sys|debug|init\.svc|ctl|odm|ril|gsm|wifi|bluetooth|bt|camera|audio|media|"
        r"log|net|nfc|qcom|qti|dalvik|dev|hw|graphics|vold|security|vendor\.display|sf)\.[A-Za-z0-9_.\-%]+$")),
    ("paths", re.compile(r"^/(?:vendor|odm|system|system_ext|product|data|mnt|persist|apex|metadata|efs|firmware|"
                         r"linkerconfig|my_\w+)/\S*$")),
    ("contexts", re.compile(r"^u:(?:object_r|r):\w+:s0")),
    ("libs", re.compile(r"^[\w.+-]*\.so(?:\.\d+)*$")),
    ("files", re.compile(r"^[\w.%/-]+\.(?:xml|conf|cfg|json|ini|bin|mbn|fw|mdt|tflite|dlc|txt|rc|db|cil)$")),
    ("urls", re.compile(r"^https?://\S+$")),
]
HINTS = [
    ("registers AIDL service", {"AServiceManager_addService", "AServiceManager_registerLazyService",
                                "AServiceManager_addServiceWithFlags"}),
    ("registers HIDL service", re.compile(r"registerAsService")),
    ("reads properties", {"__system_property_get", "__system_property_find", "__system_property_read_callback",
                          "property_get", "property_get_bool", "property_get_int32", "property_get_int64"}),
    ("sets properties", {"__system_property_set", "property_set"}),
    ("dlopen", {"dlopen", "android_dlopen_ext"}),
    ("ioctl", {"ioctl"}),
    ("sockets / netlink", {"socket", "bind", "connect", "recvmsg"}),
    ("inotify / uevent", {"inotify_init", "inotify_init1", "inotify_add_watch", "uevent_open_socket"}),
    ("mmap", {"mmap", "mmap64"}),
    ("threads", {"pthread_create"}),
    ("exec", {"execve", "execv", "execvp", "posix_spawn", "system", "popen"}),
]


def read(path, su):
    if not su:
        with open(path, "rb") as fh:
            return fh.read()
    out = subprocess.run(["su", "-c", f"cat '{path}'"], capture_output=True)
    if out.returncode:
        raise OSError(out.stderr.decode().strip() or f"su cat {path} failed")
    return out.stdout


class Elf:
    def __init__(self, data):
        if data[:4] != b"\x7fELF":
            raise ValueError("not an ELF")
        self.d = data
        self.b64 = data[4] == 2
        self.e = "<" if data[5] == 1 else ">"
        e, d = self.e, data
        if self.b64:
            (self.type, self.machine, _, _, phoff, shoff, _, _, phentsize, phnum, shentsize, shnum,
             shstrndx) = struct.unpack_from(e + "HHIQQQIHHHHHH", d, 16)
        else:
            (self.type, self.machine, _, _, phoff, shoff, _, _, phentsize, phnum, shentsize, shnum,
             shstrndx) = struct.unpack_from(e + "HHIIIIIHHHHHH", d, 16)
        self.phdrs = []
        for i in range(phnum):
            o = phoff + i * phentsize
            if self.b64:
                t, _, off, va, _, fsz, _, _ = struct.unpack_from(e + "IIQQQQQQ", d, o)
            else:
                t, off, va, _, fsz, _, _, _ = struct.unpack_from(e + "IIIIIIII", d, o)
            self.phdrs.append((t, off, va, fsz))
        self.shdrs = []
        for i in range(shnum if shoff and shoff + shnum * shentsize <= len(d) else 0):
            o = shoff + i * shentsize
            if self.b64:
                name, t, _, _, off, size, link, _, _, ent = struct.unpack_from(e + "IIQQQQIIQQ", d, o)
            else:
                name, t, _, _, off, size, link, _, _, ent = struct.unpack_from(e + "IIIIIIIIII", d, o)
            self.shdrs.append((name, t, off, size, link, ent))
        self.needed, self.soname, self.runpath = [], None, None
        self._dynamic()

    def v2o(self, va):
        for t, off, pva, fsz in self.phdrs:
            if t == 1 and pva <= va < pva + fsz:
                return off + va - pva
        return None

    def cstr(self, off):
        end = self.d.find(b"\0", off)
        return self.d[off:end].decode("utf-8", "replace")

    def _dynamic(self):
        dyn = next(((off, fsz) for t, off, _, fsz in self.phdrs if t == 2), None)
        if not dyn:
            return
        fmt, step = (self.e + "qQ", 16) if self.b64 else (self.e + "iI", 8)
        tags, strtab = [], None
        for o in range(dyn[0], dyn[0] + dyn[1], step):
            tag, val = struct.unpack_from(fmt, self.d, o)
            if tag == 0:
                break
            tags.append((tag, val))
            if tag == 5:
                strtab = self.v2o(val)
        if strtab is None:
            return
        for tag, val in tags:
            if tag == 1:
                self.needed.append(self.cstr(strtab + val))
            elif tag == 14:
                self.soname = self.cstr(strtab + val)
            elif tag in (15, 29):
                self.runpath = self.cstr(strtab + val)

    def symbols(self):
        """(name, defined, kind) from .dynsym; empty when section headers are stripped."""
        out = []
        for _, t, off, size, link, ent in self.shdrs:
            if t != 11 or not ent or link >= len(self.shdrs):
                continue
            stroff = self.shdrs[link][2]
            for o in range(off + ent, off + size, ent):
                if self.b64:
                    nm, info, _, shndx, _, _ = struct.unpack_from(self.e + "IBBHQQ", self.d, o)
                else:
                    nm, _, _, info, _, shndx = struct.unpack_from(self.e + "IIIBBH", self.d, o)
                if not nm or (info >> 4) == 0:
                    continue
                kind = {1: "obj", 2: "func"}.get(info & 0xF, "other")
                out.append((self.cstr(stroff + nm), shndx != 0, kind))
        return out


def strings(data, minlen=5):
    return [m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, data)]


def demangle(names):
    tool = shutil.which("llvm-cxxfilt") or shutil.which("c++filt")
    if not tool or not names:
        return names
    out = subprocess.run([tool], input="\n".join(names), capture_output=True, text=True)
    res = out.stdout.splitlines()
    return res if len(res) == len(names) else names


def report(path, data, a):
    try:
        elf = Elf(data)
    except (ValueError, struct.error) as ex:
        print(f"== {path}: {ex}")
        return
    kind = {2: "EXEC", 3: "DYN"}.get(elf.type, str(elf.type))
    print(f"== {path}")
    print(f"   ELF{64 if elf.b64 else 32} {MACHINES.get(elf.machine, hex(elf.machine))} {kind}, {len(data)} bytes"
          + (f", soname {elf.soname}" if elf.soname else ""))
    print(f"   needed ({len(elf.needed)}): {' '.join(elf.needed) or '-'}")
    if elf.runpath:
        print(f"   runpath: {elf.runpath}")
    syms = elf.symbols()
    imports = {n for n, d, _ in syms if not d}
    exports = [(n, k) for n, d, k in syms if d]
    if syms:
        print(f"   symbols: {len(exports)} exported, {len(imports)} imported")
    hints = []
    for label, test in HINTS:
        if (isinstance(test, set) and imports & test) or (not isinstance(test, set) and any(test.search(n) for n in imports)):
            hints.append(label)
    if hints:
        print(f"   behaviour (from imports): {', '.join(hints)}")

    strs = strings(data)
    seen = set(elf.needed) | ({elf.soname} if elf.soname else set())
    for cat, rx in CATEGORIES:
        hits = sorted({s.strip() for s in strs if rx.match(s.strip())} - seen)
        if cat == "libs":
            hits = [h for h in hits if h not in elf.needed]
            label = "libs named in strings (dlopen candidates)"
        else:
            label = cat
        if hits:
            shown = hits if a.strings else hits[:40]
            print(f"   {label} ({len(hits)}):")
            for h in shown:
                print(f"     {h}")
            if len(hits) > len(shown):
                print(f"     ... {len(hits) - len(shown)} more (--strings)")
    if a.symbols and syms:
        ex = demangle([n for n, _ in exports])
        print("   exports:")
        for n, (_, k) in zip(ex, exports):
            print(f"     [{k}] {n}")
        print("   imports:")
        for n in demangle(sorted(imports)):
            print(f"     {n}")
    if a.strings:
        print("   all strings:")
        for s in strs:
            print(f"     {s}")


def index_dir(root):
    elves = {}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                if os.path.islink(p) or not os.path.isfile(p):
                    continue
                with open(p, "rb") as fh:
                    if fh.read(4) != b"\x7fELF":
                        continue
                    fh.seek(0)
                    data = fh.read()
                e = Elf(data)
            except (OSError, ValueError, struct.error):
                continue
            elves[p] = (e, data)
    return elves


def dir_mode(a):
    elves = index_dir(a.dir)
    provides = {}
    for p, (e, _) in elves.items():
        provides.setdefault(os.path.basename(p), []).append(p)
        if e.soname:
            provides.setdefault(e.soname, []).append(p)
    print(f"{len(elves)} ELF files under {a.dir}")
    if a.who_needs:
        lib = os.path.basename(a.who_needs)
        users = sorted(os.path.relpath(p, a.dir) for p, (e, _) in elves.items() if lib in e.needed)
        print(f"\n== link {lib}: {len(users)}")
        for u in users:
            print(f"  {u}")
    if a.missing:
        miss = {}
        for p, (e, _) in elves.items():
            for n in e.needed:
                stem = re.sub(r"\.so(\.\d+)*$", "", n)
                if n in provides or stem in PLATFORM or PLATFORM_RE.match(n):
                    continue
                miss.setdefault(n, []).append(os.path.relpath(p, a.dir))
        print(f"\n== needed but not provided here (platform libs excluded): {len(miss)}")
        for n in sorted(miss):
            print(f"  {n}  <- {', '.join(sorted(miss[n])[:4])}{' ...' if len(miss[n]) > 4 else ''}")
    if a.orphans:
        linked = {n for e, _ in elves.values() for n in e.needed}
        named = set()
        for _, data in elves.values():
            named.update(m.group().decode() for m in re.finditer(rb"[\w.+-]+\.so", data))
        libs = sorted(p for p, (e, _) in elves.items() if e.type == 3 and p.endswith(".so"))
        orphans = [p for p in libs if os.path.basename(p) not in linked and os.path.basename(p) not in named
                   and (elves[p][0].soname or "") not in linked]
        print(f"\n== shared libs nothing here links or names: {len(orphans)} (could still be loaded by path"
              " from system, HAL loaders, or vintf/manifest; verify before dropping)")
        for p in orphans:
            print(f"  {os.path.relpath(p, a.dir)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--su", action="store_true")
    ap.add_argument("--symbols", action="store_true")
    ap.add_argument("--strings", action="store_true")
    ap.add_argument("--dir")
    ap.add_argument("--who-needs")
    ap.add_argument("--missing", action="store_true")
    ap.add_argument("--orphans", action="store_true")
    a = ap.parse_args()
    if a.dir:
        dir_mode(a)
    if not a.files and not a.dir:
        ap.error("give FILEs or --dir")
    for f in a.files:
        try:
            report(f, read(f, a.su), a)
        except OSError as ex:
            print(f"== {f}: {ex} (try --su)")


if __name__ == "__main__":
    main()
