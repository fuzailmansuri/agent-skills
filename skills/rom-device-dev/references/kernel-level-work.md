# Kernel, modules and device trees

## Identify the actual kernel build

Read the manifest, kernel build configuration and module/device-tree repositories.
Record the kernel release, Android GKI generation, vendor tag and toolchain where
relevant. A shared SoC name or a similar release string does not establish ABI
compatibility. Keep root-management integrations separate only when the repository's
branch model calls for it; do not introduce them as part of unrelated bring-up.

## Module loading

Trace each required module through build selection, packaging, dependencies and the
boot phase that loads it. Inspect `modules.load*`, `modules.dep`, vendor ramdisk,
`system_dlkm` and `vendor_dlkm` placement against this device's configuration.
Preserve required ordering and early-boot dependencies.

For load failures, use kernel logs, `modinfo` where available, symbol/version data,
module signing configuration and the target kernel's exported KMI. Vermagic/release
matching is one check, not an ABI guarantee. Distinguish missing files, unknown
symbols, version CRC mismatches and signature rejection. A major kernel migration
requires coordinated drivers, configs, device trees, modules and packaging; copying
headers or adding a release suffix is not a sufficient port.

## Memory and performance changes

Trace the effective settings through fstab, init, vendor scripts, properties and
kernel configuration. Establish which path initializes zram and whether it is
already active before changing compression, size or activation. Retain low-RAM and
SKU conditions until the supported product matrix shows they are unused.

Do not prescribe a universal zram fraction, CPU mask, scheduler value or compression
algorithm. Use workload, pressure, swap, latency and thermal measurements on the
target. Remove competing writers only after proving their execution order and role.

## Device trees and node access

Read the driver's bindings and the shipped DTB/DTBO selection. Verify compatibles,
resources, interrupts, clocks, regulators and overlays at the target revision.
Source labels do not prove which nodes landed in the running device tree.

Use `/proc/device-tree` or `/sys/firmware/devicetree/base` when available; properties
can be binary or NUL-terminated. Read through a suitable decoder, not assumptions
based on `cat` output. Trace a sysfs node to the owning driver before changing it.

Match DAC ownership/mode and SELinux labels to the actual node and service domain.
Use the narrowest rule that covers the required dynamic instances; ueventd patterns,
file_contexts regexes and genfs_contexts paths have different matching semantics.

## Validation

Use available config, symbol, ABI and device-tree checks for the affected build.
When compilation or hardware tests are unavailable or prohibited, report that gap.
Boot validation includes module errors, deferred probes, driver failures, suspend
and the changed feature. Never claim root hiding, altered properties or permissive
policy guarantees compatibility or hardware-backed attestation.
