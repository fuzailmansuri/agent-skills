# First-boot debugging: a feature broke after bring-up

The standard failure: a feature that worked in one tree is dead in another (fingerprint,
camera, vibration, charging, Wi-Fi). Debug in this order:

## 1. Capture evidence
```bash
adb logcat -c; sleep 5; adb logcat -v brief | grep -iE 'TAG1|TAG2' &
adb shell dmesg | grep -iE 'fingerprint|fps|goodix|buy'
adb shell dumpsys <service>          # e.g. fingerprint, lights, vibrator_manager
```
- Grab the service's **pid** first: `su -c 'ps -A | grep <hal>'`, then read
  `/proc/<pid>/openfiles` in the debugger. Everything else is assumption.

## 2. SEP fires first (most cases) — the label-first chain

Denials are usually about **properties, nodes or files that have no explicit label**. Fix in
this exact order (partial fixes silently produce more denials):

1. **Dedup in `property.te`**: if a prop appears twice (HAL context + vendor context label),
   neither applies cleanly — remove the duplicate first. One setting for one prop.
2. **Prefix labels in `property_contexts`**: HAL blobs usually read a *family* of props
   (`persist.vendor.<x>.*`). Add a per-prefix label for the entire family; per-prop labels
   along will not cover the whole family.
3. **Allow the writer**: whichever domain writes the prop (often `vendor_init` during boot)
   needs `set_prop(<writer>, <label>)`. Verify the write path really is in that domain: use
   `avc2rules.py` to classify each denial.
4. Re-check `logcat -b events` — a *new* denial usually means a previously invisible step
   (e.g. a secondary HAL or `system_server`) now runs and fails on the next prop.

## 3. Non-policy causes
- A **stale blob set**: if the feature still fails with zero denials, suspect the vendor
  blobs — re-extract from the same vendor build your SEP/SPI expectations were derived from.
- A missing **rc file** or no `PRODUCT_PACKAGES` entry for an additional sub-HAL.
- A feature that depends on another feature's HAL boot (e.g. camera having a fill light runs
  through the lights HAL) — the second HAL must exist.

## 4. Case study: fingerprint authentication failure from policy alone

Symptom: fingerprint service never authenticates; logcat shows a goodix/fingerprint HAL
retrying constantly.

- `hal_fingerprint_default` read vendor props under `default_prop` — five denials, one per
  lookup, but only visible on the FIRST failing verify.
- Fix chain (all three, in order): a per-HAL `set_prop` duplicate in `property.te` → a
  `vendor_init` allow rule for the fingerprint prop label → a prefix label in
  `property_contexts` so the whole `persist.vendor.<x>.*` family is labelled.
- Verify: `dumpsys fingerprint` should report a finger after wipe; `logcat | grep -i
  fingerprint` should show a clean first auth attempt.
- If policy is clean and it still fails, the blob set is suspect: re-extracting the vendor
  blobs from the matching vendor build fixed the residual mismatch.

## 5. Verify nothing regressed

`scripts/preflight.py` from the cherry-picking skill:
duplicate services, duplicate SEP entries, undefined modules, list drift. Then a full
manual review of the raw diff.
