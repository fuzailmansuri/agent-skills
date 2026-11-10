# Build properties, process hooks and attestation

Trace the target tree's actual property reader or framework hook before editing it.
Record the relevant process, call order, product configuration and firmware build.
Do not invent a compatibility gate API or transplant one from a different branch.
If two hooks modify the same state, establish their ownership and execution order
before adding a guard; unrelated processes may need different treatment.

## Verify the correct state

`getprop` reads Android system properties. A process-local modification to Java
`android.os.Build` fields is different state and may require an authorized in-process
inspection or a controlled test to observe it. `/proc/<pid>/environ` contains the
process environment; it does not expose Android properties or Java Build fields.
A global property dump cannot prove a process-local hook ran.

## Keep claims about integrity precise

Build tags, fingerprints, verified boot, signing keys, patch levels, KeyMint/RKP and
Play Integrity verdicts are distinct mechanisms. Setting `release-keys`, copying a
fingerprint or hiding root does not create trusted signing or guarantee a verdict.
Preserve accurate firmware and security-patch provenance. Do not change reported
patch levels just to suppress an error without establishing the underlying mismatch.

Use observed logs and, when available, the actual attestation or compatibility test
result to identify the failed layer. State what cannot be tested. Do not weaken
SELinux, disable validation, or alter attestation paths as a speculative workaround.
Scope experiments and cross-repository changes to the user's request and existing
branch model; do not invent a universal integration or merge policy.
