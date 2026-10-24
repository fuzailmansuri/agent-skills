# Device tree & hardware HAL auditing

## 1. Sibling-device reasoning (the core method)

When your tree lacks something, do not invent it — find the closest known-good tree and diff:

1. Pick siblings: same SoC **or** the parent/child SoC in the same Qualcomm family, and a
   tree from a credible maintainer on roughly the same Android base.
2. Diff along subsystems, not wholesale (`upstream-diff.sh`, `vendor-tree-diff.py`):
   SurfaceFlinger/display props, power hints (perfconfigstore/powerhint), zram config,
   audio policy + volume tables, vibration HAL, camera, sensors, SEP.
3. Feature parity is a *tree state* question: a fix that lands in a sibling tree may depend
   on services, blobs, or power paths your tree deliberately does differently. Verify the
   dependency exists before porting.
4. Credit belongs to the author of the actual change — the cherry-picking skill's
   `references/credit.md`.

## 2. Case studies (each cost a real session to learn)

### SurfaceFlinger & display
- Pin SurfaceFlinger hot threads to the busy cluster (`4-7`) for smoother scroll on
  quad-cluster SoCs; verify against `dumpsys` cpuset membership.
- `predict_hwc_composition_strategy=1` can make blur/composite workloads skip dropped
  frames — benchmark before and after.
- Display prop packages (`vendor.prop`) should mirror the stock volume/HBM table when the
  blob set matches; mismatches produce wrong brightness behaviour.
- DPPS / dynamic FPS knobs are platform dependent; mirror the sibling tree's polarity.

### Vibrator HAL (richtap / rt6010-class drivers)
- Sending a frequency-set ioctl on **every** `on()`/`perform()` triggers `KERN_ERR`
  "unknown cmd" in dmesg when the driver does not implement runtime frequency standby —
  always read the driver source before assuming a command is repeatable: seed `f0` once
  during HAL init, never re-send unless the kernel documents support.
- Cancel in-flight `compose()` worker threads when `on()`/`perform()` overrides them.
- `dumpsys vibrator_manager` shows composition lengths; always sanity check after tuning.

### Audio & Bluetooth
- Vendor props (e.g. LHDC codec enable flags, a2dp offload cap strings) need exact
  formatting; a typo'd prop is silent until a codec negotiate fails. Guard optional SW
  codecs behind a proper init guard.
- Drop dead audio policy XMLs: the audio HAL loads a fixed set; extra files only confuse
  VTS and future greps. Confirm against the HAL binary + `audio_imports` if present.
- Keep one ad2p_offload adapter for each codec family that the fence allows; check
  `ro.bluetooth.a2dp_offload.supported` under the current vendor blob set.

### Camera & sensors
- Calibration nodes (`/data/vendor/camera/...`, `/persist`) are often written as root, while
  the camera HAL runs isolated. If the HAL reads a node, give it a proper SELinux label +
  ownership rather than widening permissions globally.
- In `ueventd`/`sepolicy` label files by **exact path** — prefix and glob labels can leak.

### Kernel & build hygiene
- Kernel branch: keep a dedicated branch per ROM/tree (bug fixes cherry-picked, not
  doubled); module/devicetree repos may live in separate trees — the manifest is the map.
- Never leave `PRODUCT_REQUIRES_INSECURE_EXECMEM_FOR_SWIFTSHADER` or permissive policy in a
  production tree: `neverallow system_server execmem` should pass through the CTS/SEC
  checks.

## 3. General audit checklist

- [ ] All HAL service `.rc` files have matching `sepolicy` domain labels.
- [ ] `property_contexts` labels every new prop the HALs read/write.
- [ ] `ueventd` rules consistent with `/sys` and `/dev` nodes actually present.
- [ ] No duplicate VINTF HAL instances (QTI blobs + OSS service) — `preflight.py` catches.
- [ ] `PRODUCT_PACKAGES` include every module referenced by the `.mk` graph.
- [ ] sepolicy severity: run `avc2rules.py` and clear all `neverallow` risks.

## 4. Only keep what is used

Before importing or keeping an entry, prove something consumes it:
- Overlay (RRO) resources: the name must exist in the target package
  (`aapt2 dump resources` / grep the package's `res/values`). An absent name is dead.
- Files and modules: referenced by a `PRODUCT_PACKAGES`/`COPY_FILES`/`.rc`/policy line.
- Props: read by some binary or framework class (`blob-intel.py`, `git grep`).
Drop the rest and say so in the commit; do not preserve dead lines "just in case".
