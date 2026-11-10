# First-boot and subsystem debugging

## Preserve evidence and identify the target

Select the device explicitly when more than one is connected. On a host use `adb`;
in Termux use local commands only when that phone is the target. Root availability
and readable log buffers vary. A permission error is missing evidence, not no errors.

Capture logs before clearing buffers or restarting services:

```sh
adb -s SERIAL logcat -b all -d -v threadtime > logcat-before.txt
adb -s SERIAL shell getprop > properties.txt
adb -s SERIAL shell dumpsys SERVICE > service-state.txt
adb -s SERIAL shell dmesg > kernel-log.txt
```

Record firmware, build fingerprint, kernel release, slot and reproduction steps.
Reproduce once with timestamps and collect the relevant subsequent logs. Inspect
pstore/ramoops and tombstones when a crash or reboot is involved. Redact sensitive
logs before publishing; keep raw captures local.

## Trace the failing path

Find the first relevant failure and follow the actual service chain. Check whether
the selected service binary is installed, starts in the expected domain, registers
its interface and survives the request. Inspect init configuration, properties,
VINTF declarations, linker errors, dependencies and driver nodes as applicable.
For open descriptors use `/proc/<pid>/fd` with sufficient permissions; there is no
standard `/proc/<pid>/openfiles` interface.

Do not assume SELinux causes most failures, or that no visible AVC means policy is
correct. AIDL service listings and HIDL `lshal` have different coverage. VINTF state
can combine device, vendor, ODM, system and module fragments; one XML is not the
merged manifest.

## Investigate policy when the evidence points there

Use the denial's source domain, target context, class, permission and actual object.
Check its label and ownership before considering an allow rule. Reuse an appropriate
existing type where possible. A generic label is a lead, not automatic permission
to relabel everything under that path.

Distinguish a property type declaration in `.te` from a name-to-context mapping in
`property_contexts`. Use exact matching for a single property; use a prefix only
when the entire namespace shares the intended ownership and access. Confirm the
writer and reader domains. `avc2rules.py` suggestions require review against the
target macros and neverallow rules; they are not validated policy.

## Check other plausible causes

- Linker or interface mismatch: verify the actual blob set, partition placement,
  dependencies, AIDL/HIDL version and firmware pairing.
- Missing service or plugin: trace module selection, namespace visibility, installed
  path and dynamic loading; do not add a sibling device's HAL by name alone.
- Driver or calibration failure: inspect the exact ioctl/node contract, kernel log,
  permissions and required persistent data. Preserve per-unit calibration.
- Framework/client failure: trace the request, feature flags, state and error handling.

For example, a sound-trigger fallback may justify checking
`sound_trigger.primary.<platform>.so` and the selected audio backend. It does not
establish that every platform uses the same legacy HIDL implementation.

A setup-wizard stall warrants checking its logs and dependencies first. Compare
reported patch levels and AVB metadata with the images actually flashed when
KeyMint or rollback errors point there. Do not copy stock dates into an unrelated
build or declare the mismatch causal without supporting evidence.

## Verify the result

Repeat the same reproduction and check the predicted evidence. Include a nearby
regression scenario such as service restart, suspend/resume or cancellation when
relevant. State whether the fix was only reviewed, compiled, flashed or exercised;
never substitute a static preflight result for those stages.
