# Git conventions & policies

## 1. Identity
- Commits use the user's own git identity (`git config user.name` / `user.email`). Verify
  before the first commit of every session.
- Never commit with a work email, distro/termux defaults, or any identity that is not the
  user's. If the config is wrong, fix the repo-local config, not history.
- Authorship of upstream code is a credit matter, not an identity matter:
  see `reverse-engineering-cherry-picking`, `references/credit.md` (upstream author keeps
  authorship on picks and ports).

## 2. Commit message style
- **Technical:** what changed and why, with the mechanism. No filler ("clean up", "fix some").
- **No inspiration mentions:** never name another OS or vendor design (Apple/iOS included) in
  the message; describe the actual mechanism instead. Bad: "Add iOS-style slider animation".
  Good: "SystemUI: Implement scalable continuous slider with dynamic corner radius".
- **No AI attribution trailers.** Human co-authors only.
- AOSP style prefixes when appropriate (`device:`, `sepolicy:`, `overlay:`, subsystem `:`).
- Shape: `device: Subject` (imperative, short), blank line, optional `* ` bullets for the
  mechanism, `Signed-off-by` last. No essays, no "this commit", no marketing words.
- One topic per commit. A bulk "import from X" commit is a defect: split it per upstream
  commit/author and per subsystem (`reverse-engineering-cherry-picking`,
  `references/history-surgery.md` section 5). Never keep Gerrit `Change-Id:` lines.
- Other ROMs by name are fine only as a credited source URL, not as the reason for a change.

## 3. Remote operations & PR safety
- Never open PRs, issues, discussions or comments against third-party or upstream repos
  (ROM orgs, CLO, AOSP, individual maintainers). Only act on repositories the user controls.
- Verify the remote URL before every push; prefer `--force-with-lease` over bare force.
- Pushing to a fork is invisible to a ROM build unless the manifest points at that fork and
  branch — check the manifest.

## 4. History rewriting
- Never rewrite a pushed branch without an explicit fresh instruction from the user.
- Before any surgery: create a local backup branch (`backup/<what>`), record
  `git rev-parse HEAD^{tree}`, work on a branch, never on the shared remote directly.
- Force-push language: `git push --force-with-lease` for single-user, or plain `--force`
  when the user explicitly approves a history replacement.

## 5. Org presentation
- AI-assisted work is disclosed in the **org profile README** (`<org>/.github/profile/README.md`),
  not in the device tree: one short note, no model names. Commits never carry AI trailers.
