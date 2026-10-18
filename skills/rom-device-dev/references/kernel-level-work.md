# Kernel-level work (bring-up, modules, devicetrees)

## 1. Repo & branch layout
- Kernel, modules, and devicetrees typically live in separate repos; the manifest is the
  map. Keep a dedicated kernel branch per ROM/tree and cherry-pick bug fixes rather than
  re-merging everything.
- Root-management branches (KernelSU-Next + SUSFS style integrations) are maintained on
  their own branch (`*-ksun-susfs` naming) — keep the clean upstream branch buildable too.
- Match kernel tags against the shipped CLO release: `KERNEL.PLATFORM.<ver>.<r>-*` families
  (see `read-android-source`, `references/android-tree-map.md`).

## 2. Module loading (GKI / system_dlkm)
- `/system_dlkm` and `/vendor_dlkm` modules must match the GKI build suffix; missing-suffix
  module loading fails silently at boot — check `dmesg | grep -i module` early.
- `vendor_boot`/`modules.load` lists drift: duplicate entries in the modprobe list waste
  init time and can shadow an updated module; dedup before every release.
- When the kernel moves major versions (5.x → 6.6), expect module ABI churn: rebuild
  modules against the target's GKI headers, not the source tree's defaults.

## 3. zram & memory plumbing
- The lz4 choice lives in more than one place historically (init rc `write ... comp_algorithm`,
  post-boot script). Decide once, grep everywhere: `rg -l 'comp_algorithm|zram0/disksize' init/`.
- `low_ram` conditionals are a Go_device legacy: if the device never ships low-RAM SKUs,
  remove the conditional entirely rather than leaving busy code both gates alive.
- A deterministic zram size (fixed fraction of the RAM, e.g. 75%) is more predictable than
  meminfo-derived formulas that can rotate per build; document the policy in the fstab or a
  dedicated rootdir script.
- Post-boot redundant swapon races the boot: remove the second activation if fstab already
  handles it (`init.qcom.post_boot.sh` vs `fstab.zram`).

## 4. Devicetrees & ueventd
- DPU/DSC/pinctrl nodes touched by init need consistent `ueventd` + `sepolicy` labelling and
  explicit ownership (`chown` in `init.<target>.rc`, matching group access in SELinux).
- Add nodes for stsafe/UWB/eMMC rpmb via precise ueventd lines (exact path, no globs).
- After a devicetree change, verify on-device with `cat /proc/device-tree/...` — the label
  says nothing about whether the node actually landed.

## 5. Root & debugging conveniences (keep them honest)
- No build attestation compromises for debug conveniences:
  `PRODUCT_REQUIRES_INSECURE_EXECMEM_FOR_SWIFTSHADER` and permissive policy break
  `neverallow system_server execmem` and Play Integrity alike — keep both clean in
  production trees.
- SUSFS-style mounts hide root from detection without touching attestation paths; prefer
  it over execmem or permissive hacks.

## 6. Security audit checklist (kernel level)
- [ ] `dmesg` clean of repeated vendor-HAL errors (check the vital-specific lines — e.g.
      a vibrator HAL spamming unknown ioctls, or unlabeled node access).
- [ ] No duplicate SEP labels in `property.te` / `file_contexts`.
- [ ] `/proc/charger/...` & battery nodes labelled per domain (vendor_proc_power_supply).
- [ ] Frida-like hooks (adb keys, tcp listener shims) documented or off in release code.
