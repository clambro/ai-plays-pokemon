# Ticket: Move Long-Term Memory and Goals into the Overworld Agent

## Outcome

Move long-term-memory retrieval, creation, and updates, plus goal updates, out
of the root Junjo graph and into the overworld agent's toolset.

The overworld agent should decide when this information is relevant and make
the change through ordinary typed tools. Their services perform deterministic
state and database work without making additional model calls.

**Depends on:** the completed overworld-agent migration.

## Design

Prepare the static information needed by these tools before starting the
overworld agent, including the available long-term-memory titles, currently
loaded memories, and current goals. Keep the tool definitions stable for the
run so prompt caching is preserved.

Add tools for:

- retrieving one selected long-term memory by title;
- creating a new long-term-memory entry;
- updating an existing long-term-memory entry; and
- updating goals.

The retrieval tool replaces the separate model call that currently chooses
memory titles. The overworld agent supplies one title directly, and the
service performs the existing key-based lookup. Creation and update tools
write through the existing repository boundary. Goal changes update the live
agent state through the existing goals behavior.

Each successful tool call must update `AgentState` immediately so later tools
and agents in the same iteration see the change. Retrieval appends its one
document to the loaded long-term-memory set and returns it with a fresh
screenshot to the active conversation; it does not duplicate that durable
document into rolling memory. Loaded long-term memory is cleared when the
workflow advances to the next iteration. Mutation results continue to be
recorded in rolling memory and returned to the active conversation.

These are non-movement tools, so they do not end the overworld run.

Remove the superseded root nodes, prompts, schemas, scheduling branches, and
state fields once their behavior has moved. Leave mode routing, background
refresh, iteration finalization, and the remaining Junjo root intact for the
following root-replacement ticket.

## Staged Implementation Plan

### 1. Move long-term-memory mutation

Add creation and update tools backed by the existing repository behavior.
Delete the corresponding root nodes and obsolete model prompts alongside the
migration.

### 2. Move long-term-memory retrieval

Add a retrieval tool that loads one requested existing title directly from the
available titles already prepared for the overworld agent. Remove the separate
retrieval model call, scheduler state, and root-graph path at the same time.

### 3. Move goal updates

Add the goal-update tool and remove the root goal-update node and its separate
model call.

### 4. Simplify the remaining root

Remove any remaining obsolete root state, update the current architecture
documentation, and leave the root graph ready for its dedicated replacement
ticket.
