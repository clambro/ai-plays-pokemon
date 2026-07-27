# Ticket: Establish the v2 Branch and Preserve v1

## Outcome

Preserve the current project as an immutable `v1.0.0` release, keep the
repository's default page on stable v1 during development, and integrate the
new work on a public long-lived `v2` branch.

## Branch Model

```text
main ────────────────┐
  └─ v1.0.0 tag      │ main remains frozen during v2 development
                     │
v2 ─ feature PRs ────┴─ final fast-forward to main
                         └─ v2.0.0 tag
```

- `main` remains the GitHub default branch until v2 is ready.
- Create an annotated `v1.0.0` tag and GitHub Release at the final original
  implementation commit.
- Do not create a maintained `v1` branch; v1 receives no further work.
- Create public branch `v2` from that exact commit.
- Implement each ticket on a short-lived branch based on `v2`.
- Open pull requests into `v2`, not `main`.
- Keep `main` unchanged so it remains an ancestor of `v2`.
- Promote v2 with a fast-forward-only update, then tag and release `v2.0.0`.

The v1 tag is the historical artifact. V2 starts from a clean installation
with fresh runtime data.

## Repository Settings

- Keep `main` as the default branch during development.
- Protect `main` from ordinary pushes and merges.
- Protect `v2` as the active integration branch and require the project's
  quality gates.
- Make pull request guidance explicitly tell contributors to choose `v2` as
  the base for v2 work.
- Do not make the repository private or hide the public v2 branch.

## Release Requirements

Before promoting v2:

- finish or explicitly defer the release milestone;
- update setup and architecture documentation;
- run the complete validation suite;
- confirm a clean install with fresh runtime data;
- review the combined `main..v2` diff; and
- freeze merges into `v2` during final validation.

The v2 release notes should summarize the architecture changes, fresh-start
setup, behavioral changes, known limitations, and link to `v1.0.0`.

## Out of Scope

- A `v1` maintenance branch.
- Parallel fixes on `main`.
- A private development repository.
- Squashing the complete v2 effort into one commit.

## Acceptance Criteria

- [ ] `v1.0.0` permanently identifies the original implementation and has a
      published GitHub Release.
- [ ] `v2` starts at the same commit and is the base for all v2 feature work.
- [ ] `main` remains unchanged and is the default branch during development.
- [ ] Branch protections and PR guidance reflect the workflow.
- [ ] The final `main` update is fast-forward-only.
- [ ] `v2.0.0` is tagged and released after validation.
- [ ] The `v1.0.0` tag remains unchanged after v2 ships.
