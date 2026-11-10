# Git identity, credit and publishing

## Identity and messages

Read `git -C TARGET config user.name` and `user.email` before committing. Use the
user's intended configured identity; do not invent one or change global config.
A work email is not inherently wrong if it is the user's chosen identity.

Preserve authorship and source URLs for upstream work. Use technical commit messages
that explain behavior and mechanism, with the repository's usual subsystem prefix.
Retain human credit; do not add AI attribution trailers. Avoid marketing or claims
of inspiration. Name an upstream project when it supplies relevant provenance.

Keep changes coherent and reviewable. Do not split, squash or rewrite existing
history merely because a different presentation is preferred. Preserve Gerrit
Change-Id when continuing the same review; adapt trailers to the actual destination.
Use sign-offs according to the target's contribution policy and the user's authority
rather than treating generated text as a substitute for that attestation.

## Remote operations

Stay within the requested repositories and actions. A local fix does not by itself
request publication or modification of upstream projects. Existing authorization
persists; do not ask again for an action already clearly authorized. Verify the
exact remote URL and branch before writing. Check the effective manifest when the
published change is supposed to alter a ROM build.

## Requested history rewriting

Record local and remote tips and `HEAD^{tree}`, create a backup, and work on an
isolated branch. A history-only rewrite must preserve the final tree and authorship;
functional changes need separate review. Do not discard entries as unused during
an authorship-only cleanup.

For an explicitly authorized published-history rewrite, use
`git push --force-with-lease=refs/heads/BRANCH:REVIEWED_SHA`. A lease failure means
the remote moved: inspect it before proceeding. Never retry with unconditional
force. Detailed mechanics live in the cherry-picking skill's history-surgery guide.

Do not edit organization profiles, disclosures or unrelated documentation as a side
effect of a coding or credit task.
