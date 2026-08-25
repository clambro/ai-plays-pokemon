> This ticket is a starting point for investigation, not a specification. It was written against an older version of the code, and the implementation may have changed since then. Verify the current behavior and code before making changes. The problem is real; the proposed solution is not set in stone.

# Smaller agent and presentation fixes

## Problem

Several smaller gameplay behaviors also need prompt adjustments. The agent leaves one or two Pokémon in the lead for too long, causing them to receive most of the experience while the rest of the party falls behind. It reaches new towns with a weak party but walks past visible Pokémon Centers instead of healing and establishing a safer recovery point. It also skips many sprites and item balls even when they are visible and have no recorded interaction.

Separately, captured dialogue is correctly stored in rolling memory for the agent, but the same text is repeated in the background stream's agent-log panel. Viewers can already read the dialogue on the game screen, so repeating it in the log adds noise without helping the agent.

The README's hourly cost estimate currently says that the logarithmic contribution from rolling-memory growth was too small to measure after several hours of play. The completed livestream now provides roughly 20 hours of timestamped backups and cumulative cost data, which may be enough to estimate that contribution more meaningfully.

## Proposed direction

Strengthen the existing gameplay guidance lightly rather than adding a new policy system. State the relevant facts and defaults: the lead Pokémon is likely to receive the most battle experience; changing the lead can distribute experience; a Pokémon Center in a newly reached town can heal the party and provide a safer recovery point; and previously untried sprites and item-ball-looking objects are usually worth investigating.

Keep this guidance contextual and non-prescriptive. Do not require equal levels, healing after every battle, entering every building, or interacting with the same entity repeatedly. Build on the interaction memory already shown for sprites, signs, and objects, and do not expose hidden ROM classifications merely to tell the agent whether something is collectible.

For the stream, filter captured onscreen dialogue only at the presentation boundary. The text must remain in rolling memory, model prompts, persistence, and telemetry wherever it is currently required. Confirm the exact forms in which dialogue enters raw memory before filtering so ordinary reasoning and action results are not accidentally removed.

Revisit the README cost estimate using the longer run. Reconstruct cumulative cost over elapsed gameplay time from the available backups, compare the existing linear approximation with the expected logarithmic growth, and attempt to estimate the `ε` term in the README's `0.6 + ε log t` hourly-rate description. Update the README if the longer run supports a useful estimate; if the term is still too small or noisy to identify, say that plainly rather than forcing a value.

## Relevant code

- `agent/overworld/prompts.py` contains the local exploration and interaction guidance.
- `common/prompts.py` contains the global play-style guidance, including curiosity, healing, team building, and repeated-failure language.
- `agent/overworld/formatting.py` describes visible Pokémon Centers and shows whether sprites, signs, and objects have been interacted with.
- `agent/formatting/game_state.py` presents the current party order, levels, health, and inventory.
- `agent/overworld/tools/swap_first_pokemon/interface.py` describes the existing party-reordering tool and already contains some training guidance that may need to be made more salient rather than duplicated.
- `agent/dialog.py` records captured dialogue in rolling memory as `Onscreen text`.
- `agent/overworld/tools/navigate/service.py` and other tool completion paths may record dialogue in additional forms.
- `streaming/schemas.py` currently converts raw rolling-memory blocks directly into stream log entries.
- `streaming/background/script.js` renders those entries in the agent-log panel.
- `README.md` contains the current hourly cost estimate and the unresolved logarithmic term.
- The ignored `outputs/` run backups contain the timestamped cumulative-cost observations needed for the new fit.
- `llm/service.py`, `agent/context.py`, and `agent/state.py` own the cost calculation and cumulative counter whose semantics should be confirmed before fitting the data.

## Questions to answer during investigation

- Is the existing lead-Pokémon guidance ineffective because it appears only in the tool description rather than the decision context?
- Does the current healing language discourage Pokémon Center visits too strongly when the party has just reached a new town?
- Can the existing interaction language simply be strengthened without encouraging repeated interaction with entities the agent has already examined?
- Which exact memory entries are redundant dialogue, and which similar-looking entries are useful action results that should remain visible?
- Do the available backups cover one continuous cost counter, or are there resets or resumed segments that must be reconciled first?
- Does the longer run distinguish a logarithmic contribution from an ordinary linear rate strongly enough to justify publishing an `ε` estimate?

## Success criteria

- The agent periodically considers changing its lead when party development becomes badly uneven, without being forced to equalize every level.
- The agent strongly considers entering and using a visible Pokémon Center after reaching a new town or when its party is in poor condition.
- Previously untried stationary sprites and item-ball-looking objects receive substantially more attention while recorded interactions continue to discourage pointless repetition.
- Dialogue remains available to the agent and in persisted memory while no longer being redundantly displayed in the background stream log.
- Non-dialogue reasoning and action results remain unchanged in the stream.
- The README cost statement is checked against the full livestream data and reports either a defensible logarithmic coefficient or the continued inability to estimate it.
- Prompt and presentation changes are reviewed directly rather than protected by tests that assert exact model-facing or displayed prose.
