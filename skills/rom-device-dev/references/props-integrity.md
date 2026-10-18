# Play-services process spoofing & build integrity hygiene

## 1. The conflict (and the resolution guard)
Play-service-related framework hooks rewrite `Build` fields (fingerprint, model, device,
brand) for Play processes to pass Basic/Device Play Integrity. A compatibility layer that
runs Play processes with a different runtime shape cannot coexist with spoofing in the same
process:

```java
public static void setProps(String packageName) {
    if (isPlayCompat()) {   // the tree's own gate API
        return;
    }
    // spoofing logic
}
```

The guards must be mutually exclusive **per process**, not per build flag. If the tree runs
Play processes through its own integration plumbing, that hook yields instead of double-applying.



## 2. Branches
Any GMS-related experiment is a **branch of the whole repo set** (device, frameworks, vendor,
manifest) — never a partial mix into a shared branch. Merge direction is one-way: GMS-side
code flows from the integration branch to a standalone feature branch, never back into the
baseline silently.

## 3. Play Integrity, attestation & SELinux hygiene
- No permissive domains, no unlabelled node access in production policy.
- Release-keys hygiene: `ro.build.tags=release-keys`; clean build dates/fingerprints
  matching certified stock targets.
- No su/daemons/root artifacts visible to apps; Keystore/KeyMint and boot attestation paths
  untampered.
- Verify props changes with `getprop` in the actual process (`ps -A` + `su -c 'cat
  /proc/<pid>/environ'`) rather than globally.
