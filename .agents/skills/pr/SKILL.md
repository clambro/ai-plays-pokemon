---
name: pr
description: "Use when the user wants a pull request description or a summary of branch changes. Compares feature work with v2, or the v2 release branch with main."
---

# Generate PR Description

## Workflow

1. Run `git branch --show-current` to identify the branch and choose its base:
   - use `v2` for v2 feature branches
   - use `main` when preparing the eventual v2 release PR
2. Gather the committed branch changes:
   - `git diff <base>...HEAD --stat`
   - `git log <base>..HEAD --oneline`
   - `git diff <base>...HEAD`
3. Read relevant documentation for context:
   - `AGENTS.md`
   - `docs/workflow.md` or `docs/philosophy.md` when relevant
4. Look at the commit messages for intent
5. Generate a PR description in this format:

   ## Summary

   [A single paragraph describing what the PR does at a high level]

   [Short bullet points describing the changes]

   ## Changes

   [List of key changes, grouped by area/subject/folder if needed. Details go here, not in the summary section.]


## Rules

- Keep the description concise and focused on what changed and why
- Do not include test plans, footers, signatures, or AI attribution
- Do not push, create a PR, or change repository state unless explicitly asked
