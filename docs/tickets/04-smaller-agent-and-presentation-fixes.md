> This ticket is a starting point for investigation, not a specification. It was written against an older version of the code, and the implementation may have changed since then. Verify the current behavior and code before making changes. The problem is real; the proposed solution is not set in stone.

# Smaller agent and presentation fixes

## Problem

Several smaller gameplay behaviors also need prompt adjustments. The agent leaves one or two Pokémon in the lead for too long, causing them to receive most of the experience while the rest of the party falls behind. It reaches new towns with a weak party but walks past visible Pokémon Centers instead of healing and establishing a safer recovery point. It also skips many sprites and item balls even when they are visible and have no recorded interaction.

Separately, the background stream's agent-log panel is currently built from rolling memory, so it repeats captured dialogue and routine action results that the agent needs to remember but viewers do not need to see.

The README's hourly cost estimate currently says that the logarithmic contribution from rolling-memory growth was too small to measure after several hours of play. The completed livestream now provides roughly 20 hours of timestamped backups and cumulative cost data, which may be enough to estimate that contribution more meaningfully.

## Proposed direction

Strengthen the existing gameplay guidance lightly rather than adding a new policy system. State the relevant facts and defaults: the lead Pokémon is likely to receive the most battle experience; changing the lead can distribute experience; a Pokémon Center in a newly reached town can heal the party and provide a safer recovery point; and previously untried sprites and item-ball-looking objects are usually worth investigating.

Keep this guidance contextual and non-prescriptive. Do not require equal levels, healing after every battle, entering every building, or interacting with the same entity repeatedly. Build on the interaction memory already shown for sprites, signs, and objects, and do not expose hidden ROM classifications merely to tell the agent whether something is collectible.

Keep rolling memory and the public stream log separate. Rolling memory must retain everything the agent needs, while producers explicitly add only public-facing entries to the stream log.

Revisit the README cost estimate using the longer run. Reconstruct cumulative cost over elapsed gameplay time from the available backups, compare the existing linear approximation with the expected logarithmic growth, and attempt to estimate the `ε` term in the README's `0.6 + ε log t` hourly-rate description. Update the README if the longer run supports a useful estimate; if the term is still too small or noisy to identify, say that plainly rather than forcing a value.

## Relevant code

- `agent/overworld/prompts.py` contains the local exploration and interaction guidance.
- `common/prompts.py` contains the global play-style guidance, including curiosity, healing, team building, and repeated-failure language.
- `agent/overworld/formatting.py` describes visible Pokémon Centers and shows whether sprites, signs, and objects have been interacted with.
- `agent/formatting/game_state.py` presents the current party order, levels, health, and inventory.
- `agent/overworld/tools/swap_first_pokemon/interface.py` describes the existing party-reordering tool and already contains some training guidance that may need to be made more salient rather than duplicated.
- `agent/dialog.py` records captured dialogue in rolling memory as `GAME DIALOG`.
- `agent/overworld/tools/navigate/service.py` and other tool completion paths may record dialogue in additional forms.
- `agent/state.py` owns the rolling memory and public stream log.
- `streaming/schemas.py` converts the public log into stream log entries.
- `streaming/background/script.js` renders those entries in the agent-log panel.
- `README.md` contains the current hourly cost estimate and the unresolved logarithmic term.
- The ignored `outputs/` run backups contain the timestamped cumulative-cost observations needed for the new fit.
- `llm/service.py`, `agent/context.py`, and `agent/state.py` own the cost calculation and cumulative counter whose semantics should be confirmed before fitting the data.

## Questions to answer during investigation

- Is the existing lead-Pokémon guidance ineffective because it appears only in the tool description rather than the decision context?
- Does the current healing language discourage Pokémon Center visits too strongly when the party has just reached a new town?
- Can the existing interaction language simply be strengthened without encouraging repeated interaction with entities the agent has already examined?
- Which producers write to rolling memory, and which of their entries also belong in the public log?
- Do the available backups cover one continuous cost counter, or are there resets or resumed segments that must be reconciled first?
- Does the longer run distinguish a logarithmic contribution from an ordinary linear rate strongly enough to justify publishing an `ε` estimate?

## Success criteria

- The agent periodically considers changing its lead when party development becomes badly uneven, without being forced to equalize every level.
- The agent strongly considers entering and using a visible Pokémon Center after reaching a new town or when its party is in poor condition.
- Previously untried stationary sprites and item-ball-looking objects receive substantially more attention while recorded interactions continue to discourage pointless repetition.
- Dialogue and routine action results remain available to the agent while no longer being redundantly displayed in the background stream log.
- The public log contains only entries explicitly added to it rather than parsing rolling-memory text.
- The README cost statement is checked against the full livestream data and reports either a defensible logarithmic coefficient or the continued inability to estimate it.
- Prompt and presentation changes are reviewed directly rather than protected by tests that assert exact model-facing or displayed prose.

## Staged implementation plan

This is a starting sequence, not a complete up-front design. Each stage is one independently shippable commit with the documentation and meaningful behavioral coverage appropriate to that change, and each stage should be reviewed and merged before work begins on the next. Later stages may change when implementation or runtime evidence invalidates an assumption below; no stage should add speculative machinery for work that belongs to a later commit.

### Commit 1: Recalculate the hourly API cost

**Outcome:** The README reports an hourly cost estimate supported by the completed livestream rather than the shorter initial sample, including a logarithmic contribution only if the available observations distinguish one credibly.

**Scope:**

- Reconstruct elapsed wall-clock time and cumulative cost from the timestamped backups, treating counter resets as separate runs and continuous counters across restarted output folders as continuations rather than pooling every file into one artificial series.
- Compare the current constant-rate approximation with the cumulative curve implied by an hourly rate of the form `a + ε log t`, and check whether the fitted logarithmic term is stable across the useful run segments rather than merely improving one noisy fit.
- Update only the public cost explanation in the README with the clearest defensible result and its practical interpretation. If the coefficient remains too sensitive to run speed, pauses, or segment selection, retain a simple observed hourly estimate and state that the logarithmic term still cannot be isolated.
- Keep this as a documentation-and-analysis commit. Do not add a permanent fitting framework or tests unless the investigation exposes reusable application behavior rather than a one-time calculation.

**Review and validation:** Preserve the backup data as ignored local evidence, review the calculation and README wording directly, and run `git diff --check`. No live model calls or gameplay run are needed.

### Commit 2: Make neglected gameplay choices salient

**Outcome:** The overworld agent is more likely to rotate an overused lead, establish a newly reached town's Pokémon Center as a recovery point, and investigate visible untried stationary entities, without turning any of those defaults into rigid rules.

**Scope:**

- Put the essential lead-experience fact and the option to change the lead in the ordinary decision context, where the agent can consider them alongside the current party, instead of relying on the swap tool description to introduce the idea after tool selection.
- Reconcile the existing anti-backtracking healing guidance with the distinct value of using a visible Pokémon Center in a newly reached town: it heals the party and establishes a safer recovery point, but does not require healing after every battle or entering unrelated buildings.
- Strengthen curiosity toward visible sprites and stationary objects with no recorded interaction, while continuing to discourage repeated interactions and attempts to catch randomly wandering sprites. Use the entity and interaction information already presented to the agent; do not add hidden classifications, new persistent state, or a policy subsystem.
- Keep the guidance concise and contextual. Do not require equal party levels, fixed rotation intervals, exhaustive collection, or a walkthrough-derived order of play.

**Tests and documentation:** Review the model-facing guidance directly and rely on the existing prompt-construction and tool regressions; do not add tests that assert prompt wording. The prompt is the behavior documentation for this stage, so no unrelated public workflow documentation is needed.

### Commit 3: Separate rolling memory from the public log

**Outcome:** Viewers see a dedicated public log rather than a filtered copy of rolling memory, while the agent retains the same reasoning, dialogue, and action outcomes.

**Scope:**

- Add a dedicated bounded public log alongside rolling memory.
- Add model responses and explicit public notices to both logs; keep captured dialogue and routine action results only in rolling memory.
- Read the stream's agent-log panel directly from the public log, without parsing or filtering rolling-memory strings.
- Keep the browser rendering contract unchanged.

**Tests and documentation:** Extend the existing streaming-schema behavior test, rather than creating a new test suite, to prove that private rolling memory does not enter the public log. Update the workflow's public-log description without documenting internal implementation details.

### Validation and review cadence

For each commit, run the smallest relevant checks while iterating and then the repository's static checks and test suite in proportion to the change before presenting it for review. Do not start the indefinite application or make live model calls as validation. Work in the numbered order and pause for review after each commit-sized stage.
