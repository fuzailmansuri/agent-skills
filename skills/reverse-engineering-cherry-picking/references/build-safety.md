# Build-safety without building

Nobody runs a build to test, so a change must be right by inspection. Run
`python3 scripts/preflight.py --dt DT [--hw HW ...] [--module-dir DIR ...] --vendor O/VENDOR@BR`
for device stacks; it must show 0 errors. Then walk this list for what it can't see.

| Area | Breaks when | Check |
|---|---|---|
| Modules | a `PRODUCT_PACKAGES` name or soong dep (`shared_libs`, `static_libs`, `rustlibs`, `required`) exists nowhere | preflight `modules` (device-specific names); for others `git grep 'name: "X"'` in the repo that should define it |
| AIDL/HIDL versions | the version lib (`android.hardware.light-V3-rust`) is not frozen on our base | `gh api 'repos/LineageOS/android_hardware_interfaces/contents/PATH/Android.bp?ref=BR' -H 'Accept: application/vnd.github.raw'` and read `versions_with_info` |
| Vendor makefiles | a module is listed but not defined, a src is missing, a dropped lib is still needed | preflight `vendor`; `vendor-api-commit.py` refuses dangling deps |
| Sepolicy | a type is declared twice in included dirs, a type/macro doesn't exist on our base, conflicting contexts | preflight `sepolicy`; `git grep` the platform policy for macros |
| Neverallow | app domains on sysfs/proc/default types, vendor domains on system data, `execmem`, `default_prop` writes | read every new allow; label instead of granting (`avc2rules.py` flags these) |
| VINTF | the same HAL instance declared twice, a manifest version that doesn't match the service, a custom HAL without a framework matrix entry | preflight `vintf`; check `DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE` for vendor.* HALs |
| Init | duplicate service names, triggers lost when a blob's rc is dropped, missing files referenced | preflight `init`; read dropped rc files |
| Props | vendor sets a non-vendor prop, new prop unlabeled | `property_contexts`; Treble: vendor sets only `vendor.`, `persist.vendor.`, `ro.vendor.` |
| Priv-apps | a privileged permission missing from `privapp-permissions-*.xml` makes a user build fail at boot | `aapt2 dump permissions app.apk` vs the xml |
| Resources / overlays | an overlay names a resource the target app doesn't have | grep the target app's `res/values` at our branch |
| Java/Kotlin | an imported class or method isn't in our framework branch | `gh api 'repos/OURS/android_frameworks_base/contents/PATH?ref=BR'` |
| Kernel | a Kconfig symbol, module list (`modules.load*`) or DT node that our kernel lacks | grep our kernel tree and the modules repo |
| Lists vs vendor | `proprietary-files.txt` and the vendor repo drift (bites on the next re-extract) | preflight `lists` (warning) |

Rules of thumb:
- If you can't point at the line that defines something the change uses, it's not safe.
- Removing is riskier than adding: search for every user of what you remove (module names,
  types, props, rc triggers, xml).
- Prefer a smaller pick that is clearly safe over a complete one that might not build.
