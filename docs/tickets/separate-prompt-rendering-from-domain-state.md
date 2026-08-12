# Ticket: Separate Prompt Rendering from Domain State

## Outcome

Make the agent layer solely responsible for turning application state into
model-facing prose and XML. Emulator, map, agent-state, goal, and memory records
should describe state and behavior; they should not contain prompt instructions,
XML structure, or knowledge about how an LLM consumes them.

This is an ownership refactor. Preserve the agent-visible prompt and tool text
exactly unless a wording change is identified and reviewed separately.

## Problem

Prompt policy is currently spread across records owned by several lower-level
packages:

- `emulator/game_state.py` renders player, party, PC, and battle sections through
  `player_info`, `party_info`, `pc_info`, `battle_info`, and
  `_pokemon_list_to_str()`.
- `overworld_map/schemas.py` renders the complete explored-map prompt, entity
  details, warp instructions, legends, connection notes, and adjacent-tile
  guidance.
- `overworld_map/prompts.py` contains agent instructions even though the
  `overworld_map` package otherwise owns explored-map state and persistence.
- `agent/state.py` knows how rolling memory, goals, and player state are
  assembled for a prompt.
- `memory/goals.py` and `memory/rolling_memory/schemas.py` use `__str__` to emit
  agent-facing prose and XML.

These methods do more than provide ordinary diagnostic string representations.
They decide what the model sees, explain how it should interpret the data, and
encode prompt-specific XML. As a result, changing an agent prompt requires
editing emulator and domain records, and those records cannot be reused without
carrying presentation policy with them.

## Ownership Model

Use plain formatting functions. Do not introduce renderer classes, protocols,
view-model hierarchies, generic XML builders, or a templating framework.

### Shared gameplay state

Keep model-facing formatting separate from prompt composition:

- formatting modules turn typed state into reusable model-facing fragments;
- prompt modules own complete instruction text and explicitly compose those
  fragments in the order required by their feature; and
- domain modules own neither responsibility.

Split the shared agent-owned formatting by the state being described:

- `agent/formatting/game_state.py` owns `format_player_info()`,
  `format_party_info()`, `format_pc_info()`, and private Pokemon formatting;
- `agent/formatting/memory.py` owns `format_rolling_memory()`,
  `format_goals()`, and private memory-entry and goal formatting; and
- `agent/battle/formatting.py` owns `format_battle_info()`, because both of its
  consumers are inside the battle feature.

`agent/formatting/` is a namespace package and does not need an `__init__.py`.
Keep small single-consumer helpers private in their owning module. Pokemon,
goal, and memory-entry formatting do not need public APIs merely because they
are extracted from methods.

The three feature prompt builders remain responsible for composition:

- `agent/text/prompts.py` composes memory, goals, and player state;
- `agent/battle/prompts.py` composes memory, goals, player state, and battle
  state; and
- `agent/overworld/prompts.py` composes the shared memory, goal, and player
  fragments around the explored-map fragment. This preserves the current
  memory-goals-map-player ordering.

The small repeated joins in the text and battle builders are intentional prompt
composition, not duplicated state rendering. Do not introduce a generic shared
state prompt solely to remove those lines; it obscures feature-specific section
ordering and cannot serve the overworld prompt cleanly.

Battle tool results in `agent/battle/tools/utils.py` should use the shared party
formatter and the same battle-local formatter as the initial battle prompt.
There must not be a second implementation of those sections.

### Overworld map and entities

Use the same two-file split as the other agent features:

- `agent/overworld/prompts.py` owns both complete prompt templates, their
  model-facing literal text, `LEGEND_MAP`, and complete prompt composition; and
- `agent/overworld/formatting.py` owns the map, entity, navigation-coordinate,
  exploration-candidate, and map-boundary text fragments, plus their private
  helpers.

This keeps prompt text visibly in a prompt module while removing presentation
behavior from explored-map records. Delete `overworld_map/prompts.py` and update
the link in `docs/philosophy.md` to the agent-owned prompt module.

Revisit the `OverworldSprite`, `OverworldSign`, and `OverworldWarp` wrappers as
part of this move. The sprite and sign subclasses remain only to copy parsed
models. The warp subclass adds a derived `visited` flag whose only consumer is
prompt formatting. Store the immutable parser models directly on `OverworldMap`
and carry the known map IDs needed for the formatter to decide whether a warp's
destination can be named.

### Rolling-memory compaction

Rolling-memory compaction is a separate LLM workflow owned by the memory
subsystem. Keep `COMPACTION_PROMPT`, `SYSTEM_PROMPT`, and compaction-source
formatting in `memory/rolling_memory/prompts.py`.

Remove the prompt-oriented `__str__` methods from `CurrentMemoryBlock`,
`RawMemoryBlock`, `MemorySummary`, and `RollingMemory`. Add a small formatter in
`memory/rolling_memory/prompts.py` for the source text consumed by compaction,
and have `memory/rolling_memory/service.py` use it explicitly. The agent-facing
rolling-memory explanation and XML belong in `agent/formatting/memory.py`.

It is acceptable for the two prompt surfaces to select different wording in the
future. They should not share rendering through a domain record merely because
both currently use bracketed iteration labels.

## Domain Models After the Move

Remove these presentation APIs:

- `GameState.player_info`;
- `GameState.party_info`;
- `GameState.pc_info`;
- `GameState.battle_info`;
- `GameState._pokemon_list_to_str()`;
- `AgentState.to_prompt_string()`;
- `OverworldSprite.to_string()`;
- `OverworldSign.to_string()`;
- `OverworldWarp.description`;
- `OverworldWarp.to_string()`;
- `OverworldMap.to_string()` and its prompt-note helpers;
- agent-facing `__str__` methods on `Goal`, `Goals`, and the rolling-memory
  records.

Retain state-derived behavior that is used independently of prompting:

- parsing and `GameState.from_memory()`;
- text, dialog, naming-screen, HM, screen-coordinate, ASCII-screen, collision,
  and tile-classification behavior on `GameState`;
- `OverworldMap.height`, `width`, `ascii_tiles_ndarray`, and
  `ascii_tiles_str`, which are also used by map persistence and navigation;
- parsed `Sprite`, `Sign`, and `Warp` records stored directly on `OverworldMap`,
  plus the known map IDs needed to interpret warp destinations;
- memory mutation, ordering, lifecycle, and compaction behavior; and
- goal mutation and primary/other ordering.

Do not replace the removed methods with generic names such as `render()`,
`to_xml()`, or `to_prompt()` on the same records. That would preserve the same
ownership problem under different names.

## Staged Commit Plan

Implement and commit these stages in order. The ownership commits must remove
the old paths they replace, preserve current output byte-for-byte, and leave the
repository in a coherent state without temporary compatibility APIs. Commit 3
changes only operational logging; Commit 6 is the explicit prompt-content
review where deliberate wording changes are allowed.

Before the first code change, generate untracked representative prompt and
compaction-source outputs under `/tmp`. Use those outputs as the byte-for-byte
baseline for the affected surface after each stage. The comparison harness is
temporary verification code, not a new snapshot suite.

### Commit 1: Extract shared gameplay-state formatting

- Add `agent/formatting/game_state.py` with `format_player_info()`,
  `format_party_info()`, `format_pc_info()`, and the private Pokemon-list
  formatter currently owned by `GameState`.
- Add `agent/battle/formatting.py` with `format_battle_info()`; battle state is
  feature-specific even though it is reused by the battle entry prompt and
  battle tool results.
- Make the text and battle prompt builders compose their state sections
  explicitly instead of delegating composition to `AgentState`. At this stage
  they may still call the existing goal and rolling-memory string APIs; Commit
  2 removes that temporary dependency.
- Switch battle tool results to the same party and battle formatters so initial
  and refreshed battle observations cannot diverge.
- Keep the overworld prompt's current section order by composing its existing
  memory and goal strings, map string, and `format_player_info()` explicitly.
- Remove `GameState.player_info`, `party_info`, `pc_info`, `battle_info`, and
  `_pokemon_list_to_str()`, plus `AgentState.to_prompt_string()`, in this same
  commit. Update imports and type-only dependencies accordingly.
- Compare text prompts, all battle-state variants, player/party/PC variants,
  and battle tool results with the baseline. Run the focused agent, battle, and
  emulator checks before committing.

This is one vertical move: emulator and agent-state records stop rendering
prompts, while every existing caller moves to the new shared owner atomically.

### Commit 2: Separate goal and rolling-memory presentation

- Add `format_goals()` and `format_rolling_memory()` to
  `agent/formatting/memory.py`, with private helpers for individual goals and
  memory entries.
- Update all three feature prompt builders to use those functions instead of
  `str()` on domain records.
- Add an explicit compaction-source formatter to
  `memory/rolling_memory/prompts.py` and use it for both raw-block and summary
  compaction requests in `memory/rolling_memory/service.py`.
- Remove prompt-oriented `__str__` methods from `Goal`, `Goals`,
  `CurrentMemoryBlock`, `RawMemoryBlock`, `MemorySummary`, and `RollingMemory`.
- Keep the existing domain test for chronological memory accumulation by
  asserting stored content directly. Move the substantive chronological prompt
  ordering assertion to the agent formatter tests; do not add full prompt
  snapshots or private-helper tests.
- Compare empty and populated goals, empty and hierarchical rolling memory,
  complete shared agent state, and both compaction-source shapes with the
  baseline. Run the focused agent and rolling-memory checks before committing.

This stage updates both consumers of rolling memory together, so removing its
string API cannot break compaction while fixing agent prompt ownership.

### Commit 3: Tighten operational logging

- Remove high-frequency narration of handler dispatch, animation waits, goal
  mutation, and rolling-memory contents. These are ordinary control flow or
  authoritative application state, not operational logs.
- Remove warnings for expected tool outcomes such as rejected navigation and
  unavailable Sokoban puzzles. The result already belongs in the tool response
  and rolling memory.
- Keep rare lifecycle messages, but emit backup and fresh-database messages only
  after successful completion. Treat missing optional telemetry as informational.
- Preserve traceback context for recovered agent failures. Do not log expected
  item-use or party-order validation failures; log only unexpected exceptions at
  the boundary that converts them into a recoverable tool result.
- Document the boundary between operational logging, Logfire telemetry, and
  gameplay history in `AGENTS.md`.
- Run static checks and the focused existing checks for the touched agent,
  memory, navigation, tool, and streaming paths before committing. Prompt output
  and application behavior must not change.

This intermezzo removes telemetry-like logging exposed by the prompt and memory
work before presentation ownership continues moving across additional modules.

### Commit 4: Move overworld rendering into the agent layer

- Move the map template and legend text into `agent/overworld/prompts.py`
  alongside the existing decision prompt, and compose the complete map section
  there.
- Add `agent/overworld/formatting.py` for sprite/sign/warp fragments,
  navigation-coordinate formatting, and the remaining presentation-only map
  helpers.
- Switch `agent/overworld/prompts.py` from `OverworldMap.to_string()` to its
  agent-owned map composition and formatting functions.
- Remove `OverworldMap.to_string()` and its legend, facing-tile,
  adjacent-tile, entity-note, and connection-note helpers. Remove entity
  `to_string()` methods and `OverworldWarp.description`; the new formatter must
  preserve their exact text and error behavior.
- Delete `overworld_map/prompts.py`, update the stale link in
  `docs/philosophy.md`, and change any map-service wording that still claims
  the domain package owns rendering.
- Leave `OverworldSprite` and `OverworldSign` as temporarily empty data wrappers
  in this commit. Removing them is a separate state-model change in Commit 5,
  which keeps this already-large rendering move reviewable.
- Compare representative explored-map prompts covering the conditional cases
  listed under Verification with the baseline. Run the focused overworld-map,
  navigation, and prompt checks before committing.

This commit moves one complete presentation surface without simultaneously
changing the types stored by explored-map memory.

### Commit 5: Remove presentation-only entity wrappers

- Delete `OverworldSprite`, `OverworldSign`, and `OverworldWarp`.
- Type `OverworldMap.known_sprites`, `known_signs`, and `known_warps` as the
  parsed `Sprite`, `Sign`, and `Warp` models, and have `overworld_map/service.py`
  store those immutable parser records directly instead of copying them through
  `model_dump()`.
- Store the authoritative set of known map IDs once on `OverworldMap`. Derive
  whether a warp destination can be named in the agent formatter instead of
  caching that presentation decision as `OverworldWarp.visited`.
- Update the Sokoban integration fixture and any other callers that construct
  the removed wrappers. Do not change navigation, entity persistence, or
  Sokoban behavior.
- Recompare overworld output with the baseline, then run the focused map,
  navigation, and Sokoban checks before committing.

This state-model stage removes types whose only purpose disappeared in Commit 4,
without conflating that model cleanup with the rendering move itself.

### Commit 6: Audit and refine the prompt contents

- Manually review every complete text, battle, overworld, and rolling-memory
  compaction prompt, plus tool instructions and model-facing tool results, after
  presentation ownership is settled.
- Evaluate whether each instruction is still accurate, necessary, placed in the
  correct prompt, and useful to the model. Remove stale guidance, accidental
  duplication, and details already communicated by structured state or tool
  schemas.
- Review section ordering, XML boundaries, whitespace, and terminology across
  prompt surfaces for consistency without forcing unrelated agents into one
  generic template.
- Exercise representative prompt outputs manually and review them as complete
  model inputs. Unlike the preceding ownership commits, wording changes are
  expected here and must be evaluated deliberately rather than compared with the
  old byte-for-byte baseline.
- Run the focused prompt and agent checks after the content is approved.

This final stage is a content review, not another ownership refactor. Keeping it
separate makes prompt behavior changes visible and prevents mechanical moves
from silently endorsing the existing wording.

After Commit 5, audit for the removed APIs and old module path with `rg`, then
run Ruff, ty, and the full relevant test set. Any cleanup found by that audit
belongs in the commit whose extraction left it behind rather than in a mixed
catch-all commit.

## Verification

Before removing the old methods, compare representative old and new outputs for:

- text-agent state with empty and populated memory;
- overworld state with known and unknown sprites, signs, warps, map connections,
  blocked adjacent tiles, and a PC tile;
- trainer, wild, Safari Zone, special, and inactive battle states;
- party members at and below the level cap, dual-typed Pokemon, empty inventory,
  and populated PC storage;
- rolling memory containing raw blocks and multi-level summaries; and
- empty and populated goals.

The comparison should be byte-for-byte through Commit 5, including XML,
whitespace, ordering, and instructional text. Use temporary/local comparison
code where useful; do not add large snapshot fixtures or tests that merely copy
the prompt implementation. Commit 6 should instead review and approve its prompt
changes as intentional content changes.

Retain or add committed tests only where they protect a substantive formatting
rule likely to regress independently, such as stable ordering or conditional
inclusion. Do not test private helper wiring.

Run Ruff, ty, and the relevant existing prompt, tool, memory, map, and emulator
tests when implementation is complete.

## Out of Scope

- Changing prompt content during the ownership stages; content changes are
  reserved for the explicit audit in Commit 6.
- Changing XML tags, whitespace, ordering, or empty-section behavior outside
  the explicit audit in Commit 6.
- Changing parsed emulator state, explored-map behavior, navigation, or map
  persistence.
- Reworking prompt caching, tool registration, or agent lifecycle.
- Moving compaction prompts into `agent/`.
- Introducing new package initializers or re-export APIs.

## Done When

- Emulator, map, agent-state, goal, and memory records contain no agent-facing
  instructions or XML presentation policy.
- Shared gameplay-state prompt fragments have one implementation in the
  focused modules under `agent/formatting/`, while each feature prompt owns its
  composition.
- Overworld prompt text is owned by `agent/overworld/prompts.py`, while its map
  and entity formatting is owned by `agent/overworld/formatting.py`.
- Rolling-memory compaction formatting remains explicitly owned by the memory
  compaction prompt module.
- No replacement prompt-rendering methods are added to domain records.
- Agent-visible prompts are unchanged through the ownership refactor, and any
  later content changes are isolated in the final prompt-audit commit.
- Documentation points to the new prompt owner.
- Ruff, ty, and relevant tests pass.
