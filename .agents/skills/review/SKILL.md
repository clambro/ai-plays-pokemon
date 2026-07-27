---
name: review
description: "Use when the user asks for a code review, PR review, or branch feedback. Reviews feature work against v2, or the v2 release branch against main."
---

# Code Review

## Workflow

1. Run `git branch --show-current` to identify the branch and choose its base:
   - use `v2` for v2 feature branches
   - use `main` when reviewing the eventual v2 release
2. Gather the committed branch changes:
   - `git log <base>..HEAD --oneline`
   - `git diff <base>...HEAD`
3. Read project standards before reviewing:
   - `AGENTS.md`
   - `docs/workflow.md` when orchestration changes are involved
4. Review for correctness and regressions, with particular attention to:
   - async emulator lifecycle and game-state timing
   - ROM/parser assumptions and compatibility with saved fixtures
   - accidental live model calls, telemetry, or other paid external effects
   - Pydantic at I/O boundaries and dataclasses for internal data
   - focused tests and narrow lint/type-check exceptions
5. Report findings using the output format below.

## Output Format

For each issue found:
1. Assign a number for easy reference
2. Link the file path and line number
3. Give severity: 🔴 Problem | 🟡 Suggestion | 💭 Nitpick
4. Describe the issue
5. Briefly suggest a fix (if applicable)

Group issues by file. End with a summary of overall assessment.
If there are no findings, say so directly and mention any material residual
risks or validation gaps.
