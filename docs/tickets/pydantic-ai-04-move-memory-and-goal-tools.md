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

- retrieving selected long-term memories by title;
- creating a new long-term-memory entry;
- updating an existing long-term-memory entry; and
- updating goals.

The retrieval tool replaces the separate model call that currently chooses
memory titles. The overworld agent supplies the titles directly, and the
service performs the existing key-based lookup. Creation and update tools
write through the existing repository boundary. Goal changes update the live
agent state through the existing goals behavior.

Each successful tool call must update `AgentState` immediately so later tools
in the same overworld conversation see the change. As with the other
overworld tools, the actual result is both recorded in rolling memory and
returned with a fresh screenshot to the active conversation.

These are non-movement tools, so they do not end the overworld run.

Remove the superseded root nodes, prompts, schemas, scheduling branches, and
state fields once their behavior has moved. Leave mode routing, background
refresh, iteration finalization, and the remaining Junjo root intact for the
following root-replacement ticket.

## Staged Implementation Plan

### 1. Move long-term-memory retrieval

Prepare the available titles for the overworld agent and add a retrieval tool
that loads the requested existing titles directly. Remove the separate
retrieval model call and its root-graph path at the same time.

### 2. Move long-term-memory mutation

Add creation and update tools backed by the existing repository behavior.
Delete the corresponding root nodes and obsolete model prompts alongside the
migration.

### 3. Move goal updates

Add the goal-update tool and remove the root goal-update node and its separate
model call.

### 4. Simplify the remaining root

Remove scheduling and state that no longer has a consumer, update the current
architecture documentation, and leave the root graph ready for its dedicated
replacement ticket.
