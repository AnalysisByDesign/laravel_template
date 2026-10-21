# Runbooks

Two kinds of document live here, and they are shaped differently on purpose.

## `diagnosis/`

Read when something is wrong and you do not yet know why.

**Ordered cheapest first.** Each step costs more than the one above it, and the cheapest checks come before any that need an ssh session, sudo, or a restart. Work down only as far as you have to, and stop at the first step that explains the symptom.

- **Restarting comes last.** A bounce destroys the evidence the earlier steps read, and fixes nothing the earlier steps diagnose.
- **Say what each step costs and who can run it.** "Browser, seconds" and "needs an admin account" tell the reader whether to escalate or keep going.

## `setup/`

Read when building something that does not exist yet.

**Ordered by dependency, and the sequence is critical.** Do not reorder these to make them cheaper or friendlier: a step is where it is because the steps after it will not work otherwise.

## Everything else at this level

One-off operator procedures, verification checklists and references that fit neither folder.

## Current contents

| Path | Kind | For |
| --- | --- | --- |
| `coverage-override.md` | Reference | Merging below the coverage floor, owner-only and logged |
| `rollback.md` | Procedure | Restoring the previous release in production |
| `diagnosis/sail-cache-permissions.md` | Diagnosis | Many tests fail at once with `touch(): Utime failed: Permission denied` |
| `setup/mac-workstation.md` | Setup | A Mac from nothing to a running app: Homebrew, the `Brewfile`, first-run tools |
