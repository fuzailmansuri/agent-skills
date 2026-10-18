# Upstream Android tree map (AOSP, Qualcomm CLO, LineageOS)

## AOSP (android.googlesource.com — mirrored on GitHub as `aosp-mirror/platform_<same>`)

| Repo | Holds |
|---|---|
| `platform_frameworks_base` | Framework/JVM `frameworks/base`: `core/java` (services + public API), `packages/SystemUI` (status bar, QS, notifications), `services/core/java` (helpers incl. fingerprint, lights, notification/backlight), `graphics`, media, `res` + `core/res` base overlays |
| `platform_frameworks_native` | SurfaceFlinger (`services/surfaceflinger/`), Binder, EGL glue, `include`
| `platform_hardware_interfaces` | HAL definitions: HIDL `.hal` + AIDL `.aidl` interfaces (light, vibrator, fingerprint, biometrics, camera, sensors) — the API surface your tree's stubs implement |
| `platform_hardware_libhardware` | Legacy HAL headers/pwmlib path (`hardware/hardware.h`), audio devices legacy paths |
| `platform_system_sepolicy` | Platform (system/private/public) selinux policy + `property_contexts`, `mac_permissions.xml` — python tests (`selinux_check_access`) available |
| `platform_packages_apps_Settings`, `-apps_Dialer`, `-packages_apps_Launcher3` | App source for stock apps incl. launcher (`packages/apps/Launcher3/src/com/android/launcher3/...`) |
| `platform_system_bt`, `platform_packages_modules_Bluetooth` | Bluetooth stacks and A2DP codec plumbing |
| `platform_system_core` | init (`init/`), `ueventd`, logd, LMKD, root dirs |
| `platform_build`(+`_soong`) | Build system: `target/` product config, `make/tools`, soong namespaces |
| `platform_external_<lib>` | External C projects (skia, boringssl, protobuf) |
| `platform_art` | ART (GC, JIT, dex2oat flags & runtime hook points) |
| `platform_bootable_recovery` | recovery, update engine, A/B mechanics |

Blob-side code is NOT public in AOSP: proprietary vendor blobs live in `vendor/<vendor>` in
ROM trees (extracted from CLO or device image), and QTI/Qualcomm closed HALs do not exist in
AOSP at all — only their interfaces in `hardware/interfaces`.

## Qualcomm CodeLinaro (git.codelinaro.org — groups `clo/la`, `quic/la`)

| Tag family | Coverage |
|---|---|
| `LA.QSSI.<ver>.<r>-...` | QSSI (system_m/odm) build-able framework components incl. frameworks/base patches |
| `LA.VENDOR.<ver>.<r>-...` | Vendor side (vendor/qcom, vendor blobs, HALs) |
| `KERNEL.PLATFORM.<ver>.<r>-...` | Kernel + modules + devicetrees |
| `LA.UM.<ver>.<r>-...` | Legacy user-misc components; QTI-adjacent |
| `AU_LINUX_ANDROID_*` | Automotive variants (skip in phone work) |

Repo families under `clo/la/kernel/` (per-SoC: `kernel/qcom/...`, `LA.BR` legacy),
`clo/la/platform/vendor/qcom-opensource/*` (Wi-Fi, bt, data, audio, diag, power +
`vendor/qcom/opensource/*` match names), `clo/la/device/qcom/<codename>` (BSP device trees).
Component mapping for a SoC: check the shipped `/vendor/build.prop`'s
`ro.vendor.qti.build.*` strings + `releasetag`s/`mm-release` notes when hunting exact tag.

## LineageOS (review.lineageos.org + github.com/LineageOS)

- Branch names: `lineage-<androidVersion>` (e.g. `lineage-24.0`, `lineage-23.2`) — one per
  Android release; CAF vendor trees live under `LineageOS/hardware/qcom-caf/<soc>/...` with
  branch `lineage-24.0-caf-<soc-alias>` (one per SoC).
- Device trees: `LineageOS/android_device_<vendor>_<codename>` mirrored on GitHub; Gerrit is
  authoritative for merged commits.
- `LineageOS/lineage_wiki` documents each device's specs/SoC/kernel paths — quick reference
  when device facts are unknown.
- `vendor/lineage` overlays/power character (`config/common_full_phone.mk` needs it).

## ROM re-hosts (GitHub orgs)

Other custom-ROM orgs keep visible device trees on GitHub for searching: AOSPA, crdroid,
Evolution-X, PixelOS, YAAP, others (naming may drift; confirm the org/repo exists before
citing it). Their device trees are frequently already patched for the same problems —
search for the error class and check the tree date; never take a patch without attribution
and dependency checks.
