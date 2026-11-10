# Device tree and HAL review

## Compare the correct baselines

Choose a known-good reference with compatible hardware, firmware, Android base and
interface versions. A shared or related SoC is a useful search lead, not sufficient
reason to transplant tuning or drivers. Pin both sides and compare by subsystem.

Trace each proposed difference through consumers and build/runtime selection. Check
whether the target already implements the behavior differently. Preserve upstream
authorship for an actual port; explain original adaptations separately.

## Subsystem questions

- **Display:** which driver, panel mode, compositor path and power policy are active?
  Verify property readers and panel calibration. Never prescribe a CPU mask, HBM
  table, scheduler setting or HWC property from another device without evidence and
  comparable measurements.
- **Vibrator:** verify ioctl numbers, payload layouts and lifecycle against the
  exact driver. A command supported by one revision may fail on another. Check
  overlapping on/perform/compose requests, cancellation and callback ownership.
- **Audio/Bluetooth:** trace the selected HAL backend, policy imports, codec support,
  offload configuration and property format. Verify indirect consumers before
  removing apparently unused XML or libraries.
- **Camera/sensors:** preserve per-unit calibration and persistent data. Identify
  the actual reader/writer domains and nodes before changing labels or ownership.
- **Kernel:** check matching build configs, modules, KMI, DTB/DTBO selection and
  packaging; kernel repositories may be split in the manifest.

## Integration checks

Follow each installed service through `PRODUCT_PACKAGES`, Soong namespaces and
visibility, install partition, init configuration, executable label/domain, interface
registration, VINTF declaration and client expectation. Account for conditional
product/SKU configuration and generated files.

For policy, distinguish type declarations from object mappings and permissions.
Use a narrow exact, prefix or regex rule according to the relevant format and
required instances. A heuristic AVC helper is not a policy compiler.

For overlays, verify target package, resource names, overlayable policy, product
selection and configuration precedence. For properties, find the reader and writer
at this revision. For binaries, consider dynamic loading and service discovery in
addition to direct linker dependencies.

Only remove an entry after establishing it is unused in supported configurations.
A failed text search or `--orphans` result alone is insufficient. Preserve unrelated
changes. Report each proposed removal's consumer search and remaining uncertainty.

Use `preflight.py` for selected static errors, then review its limits and the raw
diff. Validate compilation, boot, regressions and performance separately when the
necessary environment and task authorization are available.
