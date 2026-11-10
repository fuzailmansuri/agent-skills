# Android artifact and runtime investigation

Start with a specific question and a pinned artifact or selected device. Distinguish
observed data, inferred behavior and unknowns. A string or import identifies a lead;
it does not establish that a code path executes or implements a feature correctly.

## Select the environment

Prefer tools already available: `readelf`/`llvm-readelf`, `nm`, `objdump`, `strings`,
JADX, apktool, `aapt2`, image extractors, or REA when connected and appropriate.
`blob-intel.py` provides a Python-standard-library ELF/string inspection fallback.
Do not imply that an unavailable decompiler or runtime trace was used. Missing
capabilities are explicit limits; continue with the evidence that can be obtained.

On a workstation select the target through `adb -s SERIAL`. In Termux, local `su`
commands refer to that phone. `--live` and `--su` in these scripts operate on the
local host; they do not discover a remote Android device. Verify permissions and
root availability. Read failure is not an empty successful observation.

## Acquire and identify artifacts

Use a supplied dump, a selected device, or files from a pinned vendor revision.
Record the source firmware/build, partition, path and content digest. Keep matching
blob families together when interface compatibility depends on them. Work on copies
when unpacking images; choose tools according to sparse/ext4/EROFS/super/payload or
boot image format rather than assuming every image can be mounted the same way.

For GitHub, a bounded raw fetch is:
`gh api 'repos/OWNER/REPO/contents/PATH?ref=SHA' -H 'Accept: application/vnd.github.raw'`.
Confirm the fetch succeeded before interpreting its output as an artifact.

## Native libraries and services

1. Inspect ELF architecture, dependencies, exports, strings and relevant sections.
   `blob-intel.py FILE` suggests interfaces, properties and paths to investigate.
2. Find consumers through linker dependencies, init services, registration and
   dynamic loading. `--missing` and `--orphans` describe only the supplied dump;
   do not delete a library solely because it has no direct DT_NEEDED consumer.
3. Correlate declarations with installed files and service state. AIDL service lists
   and HIDL `lshal` cover different mechanisms. Read selected VINTF fragments without
   mistaking a single XML for the effective merged manifest.
4. Follow relevant code references or decompile when tools permit. Use a scoped
   runtime trace when the question requires execution evidence and the target is
   authorized; attachment can affect timing and service behavior.

For example, a lights service containing a persistent calibration path and LED node
suggests a calibration flow. Confirm reads/writes and call paths before claiming
that the service supports a camera fill-light mode or that an OSS replacement lacks it.

## APKs and framework code

Inspect declarations/resources with `aapt2` or equivalent, and code with JADX/smali
when available. Match the APK/framework revision and dependencies. Treat decompiled
code as a reconstruction with possible missing or misleading constructs. Trace
permissions, Binder calls, settings and actual process selection at the target.

## Kernel, init and policy

Map nodes to their driver and inspect the exact ioctl/sysfs contract. Check module
loading, kernel logs and device-tree selection. For service startup, trace rc files,
property triggers, executable labels and domains. A removed blob's rc may also own
triggers needed elsewhere.

Use `avc2rules.py LOG` to group denials and generate candidates. Identify the real
object, label, caller and intended access before adding policy. Generic labels and
risky permissions demand investigation; neither a suggested macro nor absence of
visible AVCs proves policy correctness. Read current target macros and neverallows.

## Compare and conclude

Compare stock and ROM with matched firmware context: selected services, relevant
properties, installed interfaces, node ownership/labels and behavior under the same
reproduction. Differences generate hypotheses; test the predicted failure path.

Record source paths/revisions or artifact digests, relevant offsets/log lines, what
was actually observed and what remains inferred. State failed or unavailable checks
and residual uncertainty plainly. Keep device-specific captures and findings in
private task notes; do not publish raw private data in the reusable skill.
