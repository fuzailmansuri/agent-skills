---
name: rom-device-dev
description: >-
  Develop and maintain Android ROM device trees, HAL integration, kernels, manifests,
  and SELinux policy. Use for device bring-up, subsystem failures, cross-tree ports,
  or SystemUI and framework changes that depend on device integration.
---

# Android device engineering

Work like an AOSP engineer: establish the target, trace the mechanism, change the
smallest responsible layer, and verify what the available environment can prove.

## Engineering judgment and honesty

- Ground claims in the checked-out branch, shipped artifacts, or captured device
  evidence. Memory, a sibling device, a commit subject, and a plausible explanation
  are leads, not proof. Never invent an API, property, module, log, test, or result.
- Separate **observed facts**, **inferences**, and **unknowns**. Say "I don't know yet"
  when appropriate, identify the missing evidence, and get it when tools permit.
- Be candid about capabilities. State when source, hardware, permissions, tools,
  or expertise are insufficient. Static review cannot prove compilation, boot,
  runtime behavior, performance, or compatibility. Do not turn a failed check into
  a success claim or call a hypothesis a root cause.
- Prefer established AOSP and target-tree mechanisms. Trace their contracts before
  inventing a wrapper, service, property, tuning value, or workaround. Challenge a
  proposed fix when evidence contradicts it; explain the technical reason plainly.
- When wrong, name the mistaken assumption, correct it, and revisit dependent
  changes. Do not defend a guess, conceal uncertainty, or keep changing unrelated
  knobs until a symptom disappears.

For diagnosis, uncertain conclusions, or a disputed approach, read
[engineering judgment](references/engineering-judgment.md).

## Establish the working context

Identify the product/device, Android branch, vendor build, kernel family, affected
repositories and manifest revisions. Inspect local changes before editing. Do not
assume this host is the phone or reuse another task's device paths and constraints.
Use an isolated worktree when the active checkout is building or contains other work.

Respect the user's build and resource constraints. Start with focused static checks;
run builds or device tests when requested or appropriate within the task's scope.
An explicit no-build instruction remains binding. Prefer local source and bounded
patch fetches; avoid large clones when a file or commit answers the question.

## Make the change reviewable

1. Trace the symptom from caller through framework, interface, service, driver and
   configuration as applicable. Compare stock and ROM at matching revisions.
2. Check dependencies in the target: module selection and namespaces, interface
   versions, partition placement, init startup, policy and kernel ABI.
3. Fix the owning layer. Preserve calibration and existing behavior outside the
   request. Absence from one search is not proof that code or a blob is unused.
4. Review the final diff and run checks that exercise the changed mechanism. Report
   each check's scope and result; list unresolved gaps without claiming readiness.

The companion `reverse-engineering-cherry-picking` skill supplies import tooling
and `preflight.py`. Use it when available for those tasks; its scan is heuristic,
not a Make/Soong evaluation, policy compiler, VINTF merge, or runtime test.

## Repository conventions

Use the target repository's configured committer identity; retain upstream authors
and source URLs for imported work. Technical messages, human credit, no AI trailers.
Keep device-specific fork maps and logs in gitignored `_personal/`; public examples
use placeholders. Do not expand a local task into publishing, changing other repos,
or rewriting published history. Existing explicit authorization remains valid;
check the exact destination and use a pinned force-with-lease for an authorized rewrite.

## Reference index

| Task | Read |
|---|---|
| Evidence, uncertainty, root-cause reasoning | [engineering-judgment.md](references/engineering-judgment.md) |
| Device/HAL audit and sibling-device comparison | [device-tree-audit.md](references/device-tree-audit.md) |
| First-boot or subsystem failure | [first-boot-debugging.md](references/first-boot-debugging.md) |
| Identity, credit, publishing and history | [git-conventions.md](references/git-conventions.md) |
| Manifest selection and cross-repo changes | [repo-manifests.md](references/repo-manifests.md) |
| Kernel, modules and device trees | [kernel-level-work.md](references/kernel-level-work.md) |
| Build properties, KeyMint and attestation | [props-integrity.md](references/props-integrity.md) |
| SystemUI and Launcher integration | [ui-ux-systemui.md](references/ui-ux-systemui.md) |
| Private fork map and sync log | [upstreams-template.md](references/upstreams-template.md) |
