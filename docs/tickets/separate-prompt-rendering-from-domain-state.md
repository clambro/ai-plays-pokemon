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

Add `agent/prompts.py` for prompt fragments shared by the text, battle, and
overworld agents. It should own functions equivalent to:

- `format_player_info(game_state)`;
- `format_party_info(game_state)`;
- `format_pc_info(game_state)`;
- `format_battle_info(game_state)`;
- `format_rolling_memory(memory)`;
- `format_goals(goals)`; and
- `format_agent_state(state, game_state)`, which joins the shared memory, goals,
  and player sections currently assembled in `AgentState.to_prompt_string()`.

Keep small single-consumer helpers private in this module. For example, Pokemon,
goal, and memory-entry formatting do not need public APIs merely because they are
extracted from methods.

The three feature prompt builders remain responsible for composition:

- `agent/text/prompts.py` uses the shared agent-state fragment;
- `agent/battle/prompts.py` uses the shared fragment and appends battle state;
  and
- `agent/overworld/prompts.py` uses the shared fragment and appends the explored
  map.

Battle tool results in `agent/battle/tools/utils.py` should use the same party
and battle formatting functions as the initial battle prompt. There must not be
a second implementation of those sections.

### Overworld map and entities

Add `agent/overworld/formatting.py` for model-facing map and entity rendering.
This separate module keeps the substantial overworld presentation policy out of
the explored-map domain records. It should own:

- the current `OVERWORLD_MAP_STR_FORMAT` template;
- `LEGEND_MAP` and the always-visible legend set;
- `format_overworld_map(current_map, game_state)`;
- `format_overworld_sprite(sprite, map_id)`;
- `format_overworld_sign(sign, map_id)`;
- `format_overworld_warp(warp, map_id)`; and
- private helpers for the legend, facing tile, adjacent-tile blockage notes,
  known entities, map connections, and warp-entry instructions.

Move the contents of `overworld_map/prompts.py` into this agent-owned module and
delete the old file. Update the link in `docs/philosophy.md` to the new owner.

Revisit `OverworldSprite` and `OverworldSign` as part of this move. After entity
descriptions were removed, these subclasses remain only to construct copies of
the parsed `Sprite` and `Sign` models and stringify them for the overworld
prompt. Moving that formatting into the agent layer may eliminate their last
reason to exist; if so, store the parser models directly on `OverworldMap`
instead of preserving presentation-only domain types.

### Rolling-memory compaction

Rolling-memory compaction is a separate LLM workflow owned by the memory
subsystem. Keep `COMPACTION_PROMPT`, `SYSTEM_PROMPT`, and compaction-source
formatting in `memory/rolling_memory/prompts.py`.

Remove the prompt-oriented `__str__` methods from `CurrentMemoryBlock`,
`RawMemoryBlock`, `MemorySummary`, and `RollingMemory`. Add a small formatter in
`memory/rolling_memory/prompts.py` for the source text consumed by compaction,
and have `memory/rolling_memory/service.py` use it explicitly. The agent-facing
rolling-memory explanation and XML belong in `agent/prompts.py`.

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
- entity construction such as `from_sprite()`, `from_sign()`, and `from_warp()`;
- memory mutation, ordering, lifecycle, and compaction behavior; and
- goal mutation and primary/other ordering.

Do not replace the removed methods with generic names such as `render()`,
`to_xml()`, or `to_prompt()` on the same records. That would preserve the same
ownership problem under different names.

## Implementation Sequence

1. Add the shared functions in `agent/prompts.py` and switch the text, battle,
   and overworld initial prompts plus battle tool results to them.
2. Add `agent/overworld/formatting.py`, switch the initial overworld prompt to
   it, then remove map/entity presentation methods and
   `overworld_map/prompts.py`.
3. Move agent-facing goal and rolling-memory rendering into `agent/prompts.py`. Move
   compaction-source formatting into `memory/rolling_memory/prompts.py`, then
   remove the prompt-oriented `__str__` methods.
4. Remove `AgentState.to_prompt_string()` and all now-unused presentation
   imports and constants from the domain modules.
5. Update documentation references and verify that the constructed prompts
   have not changed.

Keep each stage behavior-preserving so failures can be attributed to one
boundary move rather than a simultaneous prompt rewrite.

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

The comparison should be byte-for-byte for this refactor, including XML,
whitespace, ordering, and instructional text. Use temporary/local comparison
code where useful; do not add large snapshot fixtures or tests that merely copy
the prompt implementation.

Retain or add committed tests only where they protect a substantive formatting
rule likely to regress independently, such as stable ordering or conditional
inclusion. Do not test private helper wiring.

Run Ruff, ty, and the relevant existing prompt, tool, memory, map, and emulator
tests when implementation is complete.

## Out of Scope

- Rewriting, shortening, or otherwise improving prompt content.
- Changing XML tags, whitespace, ordering, or empty-section behavior.
- Changing parsed emulator state, explored-map behavior, navigation, or map
  persistence.
- Reworking prompt caching, tool registration, or agent lifecycle.
- Moving compaction prompts into `agent/`.
- Introducing new package initializers or re-export APIs.

## Done When

- Emulator, map, agent-state, goal, and memory records contain no agent-facing
  instructions or XML presentation policy.
- Shared gameplay-state prompt fragments have one implementation in
  `agent/prompts.py`.
- Overworld map and entity presentation is owned by
  `agent/overworld/formatting.py`.
- Rolling-memory compaction formatting remains explicitly owned by the memory
  compaction prompt module.
- No replacement prompt-rendering methods are added to domain records.
- Agent-visible prompts are unchanged by the refactor.
- Documentation points to the new prompt owner.
- Ruff, ty, and relevant tests pass.
