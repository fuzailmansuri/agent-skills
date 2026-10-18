# Reverse engineering playbook

Goal: an evidence-backed answer ("the QTI lights service writes `dev_color` from
`/mnt/vendor/persist/color`"), not a guess. Every claim gets a source: a string, a symbol, a
trace line, a node read on the device.

## 1. Tools

Check with `command -v` before relying on one.

| Need | Present on the Termux setup | Otherwise |
|---|---|---|
| ELF headers, deps, symbols | `readelf`, `llvm-readelf`, `llvm-nm`, `nm`, `scripts/blob-intel.py` | `pkg install binutils` |
| Disassembly | `llvm-objdump -d --no-show-raw-insn` | `pkg install radare2` (`r2 -A`) |
| Strings | `strings`, `llvm-strings`, `rg -a` | `blob-intel.py --strings` |
| Syscall tracing | `strace` (run as root) | |
| APK/JAR | `aapt2`, `unzip`, `java` | jadx release zip (`jadx/bin/jadx -d out app.apk`), `java -jar apktool.jar d app.apk` |
| Images | `debugfs` (ext4: `debugfs -R 'rdump / out' img`) | `pkg install erofs-utils dtc android-tools` when available, payload-dumper-go |
| JSON | `python3 -m json.tool` | `pkg install jq` |

## 2. Getting the artifact

**Live device (rooted; the phone running Termux is the target).** `su -c` works
non-interactively (KernelSU, context `u:r:ksu:s0`). `/vendor` and `/odm` are not readable
without it.

```sh
su -c "cat /vendor/bin/hw/X" > X                                   # one file
su -c 'tar -C / -cf - vendor/bin vendor/lib64 vendor/etc odm' | tar -C "$DUMP" -xf -   # a dump
python3 scripts/blob-intel.py --su /vendor/bin/hw/X                # no copy needed
```

**Stock firmware.** `payload.bin` → partition images (payload-dumper-go). `super.img` →
`lpunpack`. Sparse → `simg2img`. EROFS → `fsck.erofs --extract=DIR img`. ext4 →
`debugfs -R 'rdump / DIR' img`. boot/vendor_boot → `unpack_bootimg` or `magiskboot unpack`.
dtb/dtbo → `dtc -I dtb -O dts`.

**Vendor repo (no clone).**
`gh api 'repos/O/R/contents/PATH?ref=BR' -H 'Accept: application/vnd.github.raw' > file`.

## 3. Native blobs (HALs, daemons, libraries)

1. `blob-intel.py FILE` first. It shows needed libs, the interfaces it registers, sysfs/dev nodes,
   props, paths, files, URLs, SELinux contexts, and behaviour from imports (props get/set, ioctl,
   dlopen, sockets, exec).
2. Who links or needs it: `blob-intel.py --dir DUMP --who-needs libfoo.so`, `--missing`,
   `--orphans` (orphans can still be dlopen'd by path; verify before dropping).
3. Interfaces on the live system: `su -c 'service list' | grep -i foo` (AIDL),
   `su -c lshal | grep -i foo` (HIDL), versions from `/vendor/etc/vintf/manifest/*.xml`.
4. Behaviour: trace it while toggling the feature.
   `su -c "strace -f -tt -s 128 -e trace=openat,read,write,ioctl -p $(su -c pidof NAME)"`.
5. Code paths: `llvm-objdump -d --no-show-raw-insn X | less`, find the function by symbol
   (`llvm-nm -D -C X`) or by the address that references a string. `r2 -A X; axt @ str.<name>`
   when radare2 is installed.
6. Find every blob that touches a node or prop: `rg -a -l 'aw20036_led' "$DUMP"`.

Worked example (2026-10-08): `blob-intel.py --su /vendor/bin/hw/vendor.qti.hardware.lights.service`
showed `/mnt/vendor/persist/color`, `/sys/class/leds/aw20036_led/dev_color`, `set_device_color`
and `allWhiteOn & rearCamOn`. That's per-unit colour calibration plus a camera fill-light mode
the OSS lights HAL doesn't implement. Five minutes, no disassembly.

## 4. Java (apps, priv-apps, framework jars)

- `aapt2 dump badging app.apk`, `aapt2 dump permissions app.apk`,
  `aapt2 dump xmltree --file AndroidManifest.xml app.apk` for components, intents, permissions.
- jadx for code, apktool for resources and smali. Search settings keys, broadcasts, binder
  descriptors, sysfs paths, `SystemProperties.get`.
- Priv-apps need every privileged permission in a `privapp-permissions-*.xml`, or a user build
  fails at boot.

## 5. Kernel, modules, device tree

- `su -c 'cat /proc/modules'`, `su -c 'ls /sys/module/M/parameters'`, `su -c dmesg`.
- Live device-tree nodes: `su -c 'ls /proc/device-tree/...'`, or `dtc -I fs /proc/device-tree`.
- Which driver owns a node: `su -c 'ls -l /sys/class/leds/x/device/driver'`.

## 6. Properties, init, services

- Value and label: `getprop P`, `su -c "getprop -Z P"`. Who sets it: `rg 'setprop\s+P' DUMP`,
  `blob-intel.py` props section.
- Services: `su -c 'ps -A -o PID,LABEL,NAME'`, `getprop | grep init.svc.`, rc files in the dump.
- A blob's rc file can carry unrelated triggers. The QTI lights rc carried Glyph `handset_mode`
  and `sub_brightness`; read rc files before dropping the blob.

## 7. SELinux

- `python3 scripts/avc2rules.py --live --no-apps` (dmesg + logcat) or pipe a log into it.
- Fix the label before granting. A denial on `sysfs`, `proc`, `default_prop`, `vendor_file` or
  `device` means the object needs its own type (genfscon / file_contexts / property_contexts),
  not an allow on the generic type.
- Labels: `su -c 'ls -Z PATH'`, `ps -Z`. `dontaudit` rules hide denials. If a feature fails
  silently, check the node's label and the domain's rules in the source policy.

## 8. Comparing stock and ROM

Diff `getprop` output, rc files, the merged VINTF manifest (`su -c cat /vendor/etc/vintf/manifest.xml`),
node permissions (`ls -lZ`) and running services between stock and the ROM. The difference
usually explains the bug.

## 9. Write it down

What, where (path, offset, symbol, string), how it was verified, and what it means for our
trees. Device-specific findings go in the device skill's notes.
