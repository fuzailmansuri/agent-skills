# Static checks and validation limits

When builds are unavailable or the user prohibits them, run
`python3 scripts/preflight.py --dt DT [--hw HW ...] [--module-dir DIR ...] --vendor O/VENDOR@BR`
for device stacks. Resolve relevant findings and review warnings. Zero errors means
no matching errors were found within the supplied inputs; it does not prove the
tree compiles or boots. The scanner approximates Make/Soong selection and does not
compile policy, merge VINTF, resolve every module, or verify ABI/runtime behavior.
Unsupported layouts and omitted vendor inputs leave coverage gaps.

When builds or runtime tests are in scope, use the target's relevant checks too.
Report each result separately. Walk this list for what the scanner cannot establish.

| Area | Breaks when | Check |
|---|---|---|
| Modules | a `PRODUCT_PACKAGES` name or soong dep (`shared_libs`, `static_libs`, `rustlibs`, `required`) exists nowhere | preflight `modules` (device-specific names); for others `git grep 'name: "X"'` in the repo that should define it |
| AIDL/HIDL versions | the version lib (`android.hardware.light-V3-rust`) is not frozen on our base | `gh api 'repos/LineageOS/android_hardware_interfaces/contents/PATH/Android.bp?ref=BR' -H 'Accept: application/vnd.github.raw'` and read `versions_with_info` |
| Vendor makefiles | a module is listed but not defined, a src is missing, a dropped lib is still needed | preflight `vendor`; `vendor-api-commit.py` refuses dangling deps |
| Sepolicy | a type is declared twice in included dirs, a type/macro doesn't exist on our base, conflicting contexts | preflight `sepolicy`; `git grep` the platform policy for macros |
| Neverallow | app domains on sysfs/proc/default types, vendor domains on system data, `execmem`, `default_prop` writes | read every new allow; label instead of granting (`avc2rules.py` flags these) |
| VINTF | the same HAL instance declared twice, a manifest version that doesn't match the service, a custom HAL without a framework matrix entry | preflight `vintf`; check `DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE` for vendor.* HALs |
| Init | duplicate service names, triggers lost when a blob's rc is dropped, missing files referenced | preflight `init`; read dropped rc files |
| Props | vendor sets a non-vendor prop, new prop unlabeled | `property_contexts`; Treble: verify ownership, namespaces and property access rules on the target release |
| Priv-apps | required permission allowlisting is missing while enforcement is enabled | inspect requested permissions, partition-specific allowlists and the target enforcement policy |
| Resources / overlays | an overlay names a resource the target app doesn't have | grep the target app's `res/values` at our branch |
| Java/Kotlin | an imported class or method isn't in our framework branch | `gh api 'repos/OURS/android_frameworks_base/contents/PATH?ref=BR'` |
| Kernel | a Kconfig symbol, module list (`modules.load*`) or DT node that our kernel lacks | grep our kernel tree and the modules repo |
| Lists vs vendor | `proprietary-files.txt` and the vendor repo drift (bites on the next re-extract) | preflight `lists` (warning) |

Rules of thumb:
- An unresolved dependency is a validation gap; find its definition and selection before claiming compatibility.
- Removing is riskier than adding: search for every user of what you remove (module names,
  types, props, rc triggers, xml).
- Preserve a complete functional fix; do not omit necessary dependencies just to make a patch smaller.
