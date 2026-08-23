---
name: commit
description: "Use when the user asks to commit, save changes, or create a git commit. Reviews and stages the intended changes, then commits them with a descriptive message."
---

# Commit Changes

## Workflow

1. Inspect current state by running:
   - `git status --short`
   - `git diff`
   - `git diff --cached`
   - `git log --oneline -5`
2. Confirm the changed files belong to the requested work. Preserve unrelated
   changes and never stage ROMs, save states, credentials, databases, outputs,
   or other private runtime artifacts.
3. Stage the intended changes. Use `git add -A` only when every working-tree
   change belongs in the commit.
4. Review `git diff --cached` and `git diff --cached --check`.
5. Generate a commit message with:
   - a concise subject line
   - a short body explaining the key changes and why
6. Commit normally so the repository's pre-commit hooks run.
7. Check `git status --short` and report the commit hash.

## Rules

- Always include both a subject and a brief body
- Keep the subject short and descriptive
- Keep the body concise and focused on the key changes
- Do not commit unless the user explicitly asks
- No footers or signatures
- Never mention the AI agent or its provider
- Do not credit yourself
- Never use `--no-verify` unless the user explicitly instructs you to do so
